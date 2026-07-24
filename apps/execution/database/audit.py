from datetime import datetime

from sqlalchemy import event, inspect, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import get_history

from apps.execution.trial_lock import NotificationRouter, TrialLockManager
from packages.security.context import (
    current_change_reason,
    current_ip_address,
    current_timestamp,
    current_user_id,
)

from .models import AuditedModel, AuditLog, ClinicalObservation, SDVSignOff


def get_primary_key(obj):
    mapper = inspect(obj).mapper
    pk_cols = mapper.primary_key
    if not pk_cols:
        return "unknown"
    return str(getattr(obj, pk_cols[0].name))


@event.listens_for(Session, "before_flush")
def receive_before_flush(session: Session, flush_context, instances):
    if not session.is_modified:
        return

    # If the session contains eTMF, Interop, CTMS, Quality, eISF, or Notifications objects, skip execution auditing
    for obj in list(session.new) + list(session.dirty) + list(session.deleted):
        if hasattr(obj, "__tablename__") and obj.__tablename__ in (
            "tmf_documents",
            "tmf_audit_logs",
            "tmf_expected_documents",
            "tmf_document_qc_transitions",
            "epro_submissions",
            "interop_audit_logs",
            "instruments",
            "subject_assignments",
            "ctms_studies",
            "ctms_audit_logs",
            "ctms_monitoring_visits",
            "ctms_monitoring_visit_findings",
            "ctms_generated_letters",
            "ctms_recruitment_records",
            "ctms_site_milestones",
            "ctms_cra_allocations",
            "quality_deviations",
            "quality_root_cause_analyses",
            "quality_capa_records",
            "quality_audit_logs",
            "isf_documents",
            "isf_audit_logs",
            "notification_records",
            "notification_audit_logs",
            "consent_documents",
            "consent_audit_logs",
        ):
            return

    # Check for read-only freeze
    if TrialLockManager.is_locked() and (
        session.new or session.dirty or session.deleted
    ):
        raise PermissionError(
            "Trial is currently locked in a read-only state due to a security violation."
        )

    # Check for site-level and visit-level locks
    for obj in list(session.new) + list(session.dirty) + list(session.deleted):
        if not hasattr(obj, "__tablename__") or obj.__tablename__ == "audit_logs":
            continue

        site_id = getattr(obj, "site_id", None) or getattr(obj, "site", None)
        if site_id is not None and TrialLockManager.is_site_locked(str(site_id)):
            raise PermissionError(
                f"Site {site_id} is currently locked in a read-only state."
            )

        visit_id = getattr(obj, "visit_id", None) or getattr(obj, "visit", None)
        if visit_id is not None and TrialLockManager.is_visit_locked(str(visit_id)):
            raise PermissionError(
                f"Visit {visit_id} is currently locked in a read-only state."
            )

    # Pre-pass on session.dirty to detect clinical value edits on verified observations
    # and perform auto-drop verification workflow.
    for obj in list(session.dirty):
        if isinstance(obj, ClinicalObservation):
            # Check if it was previously verified
            is_sdv_hist = get_history(obj, "is_sdv_verified")
            if is_sdv_hist.has_changes():
                was_verified = (
                    bool(is_sdv_hist.deleted[0]) if is_sdv_hist.deleted else False
                )
            else:
                was_verified = bool(obj.is_sdv_verified)

            if was_verified:
                # Check if clinical value changed
                clinical_value_changed = False
                for field in ["value", "value_string", "normalized_value"]:
                    hist = get_history(obj, field)
                    if hist.has_changes():
                        old_val = hist.deleted[0] if hist.deleted else None
                        new_val = hist.added[0] if hist.added else getattr(obj, field)
                        if old_val != new_val:
                            clinical_value_changed = True
                            break

                if clinical_value_changed:
                    # Enforce meaningful change reason
                    current_reason = current_change_reason.get()
                    if (
                        not current_reason
                        or current_reason == "system_operation"
                        or not current_reason.strip()
                    ):
                        raise ValueError(
                            "Meaningful GxP change reason is required for modifying previously verified clinical values."
                        )

                    # Save verifier for notification before we clear it!
                    old_verifier = obj.sdv_verified_by

                    # Clear verification state on the observation itself
                    obj.is_sdv_verified = False
                    obj.sdv_verified_by = None
                    obj.sdv_verified_at = None

                    # Update associated SDVSignOff records to unverified state
                    stmt = select(SDVSignOff).where(
                        SDVSignOff.scope == "FIELD",
                        SDVSignOff.target_id == obj.id,
                        SDVSignOff.is_verified.is_(True),
                    )
                    res = session.execute(stmt)
                    sign_offs = res.scalars().all()
                    for so in sign_offs:
                        so.is_verified = False
                        so.dropped_reason = "Clinical value modified"
                        so.dropped_at = datetime.utcnow()

                    # Send notification to the previous verifier
                    if old_verifier:
                        msg = f"Previously verified field modified on Subject {obj.subject_id} - Visit {obj.visit_id}."
                        payload = {
                            "message": msg,
                            "study_id": obj.study_id,
                            "subject_id": obj.subject_id,
                            "visit_id": obj.visit_id,
                            "observation_id": obj.id,
                            "editor": current_user_id.get(),
                            "change_reason": current_reason,
                        }
                        NotificationRouter().send_dashboard_notification(
                            [old_verifier], payload
                        )

    audit_logs = []
    user_id = current_user_id.get()
    reason = current_change_reason.get()
    ip_address = current_ip_address.get()
    timestamp = current_timestamp.get()

    # Track Inserts
    for obj in session.new:
        if not hasattr(obj, "__tablename__") or obj.__tablename__ == "audit_logs":
            continue

        new_values = {}
        mapper = inspect(obj).mapper
        for attr in mapper.column_attrs:
            val = getattr(obj, attr.key)
            if isinstance(val, datetime):
                val = val.isoformat()
            new_values[attr.key] = val

        kwargs = {
            "table_name": obj.__tablename__,
            "record_id": get_primary_key(obj) or "pending",
            "action": "INSERT",
            "user_id": user_id,
            "ip_address": ip_address,
            "old_values": None,
            "new_values": new_values,
            "version_index": getattr(obj, "version", 1),
            "change_reason": reason,
        }
        if timestamp is not None:
            kwargs["timestamp"] = timestamp

        audit_logs.append(AuditLog(**kwargs))

    # Track Updates
    for obj in session.dirty:
        if not hasattr(obj, "__tablename__") or obj.__tablename__ == "audit_logs":
            continue
        if not session.is_modified(obj, include_collections=False):
            continue

        old_values = {}
        new_values = {}
        mapper = inspect(obj).mapper
        for attr in mapper.column_attrs:
            history = get_history(obj, attr.key)
            if history.has_changes():
                # history.deleted has the previous value, history.added has the new value
                # but only if it changed!
                old_val = (
                    history.deleted[0] if history.deleted else getattr(obj, attr.key)
                )
                new_val = history.added[0] if history.added else getattr(obj, attr.key)

                # Verify that it actually changed
                if old_val != new_val:
                    if isinstance(old_val, datetime):
                        old_val = old_val.isoformat()
                    if isinstance(new_val, datetime):
                        new_val = new_val.isoformat()
                    old_values[attr.key] = old_val
                    new_values[attr.key] = new_val

        if old_values or new_values:
            # Check if this is a soft delete
            action = "UPDATE"
            if (
                getattr(obj, "is_deleted", False) is True
                and old_values.get("is_deleted") is False
            ):
                action = "DELETE"

            # Increment version index
            if hasattr(obj, "version") and "version" not in new_values:
                obj.version += 1
                new_values["version"] = obj.version

            kwargs = {
                "table_name": obj.__tablename__,
                "record_id": get_primary_key(obj),
                "action": action,
                "user_id": user_id,
                "ip_address": ip_address,
                "old_values": old_values,
                "new_values": new_values,
                "version_index": getattr(obj, "version", 1),
                "change_reason": reason,
            }
            if timestamp is not None:
                kwargs["timestamp"] = timestamp

            audit_logs.append(AuditLog(**kwargs))

    # Prevent hard deletions
    for obj in session.deleted:
        if isinstance(obj, AuditLog):
            raise ValueError(
                "Deletion of AuditLog is strictly forbidden to comply with 21 CFR Part 11."
            )
        if isinstance(obj, AuditedModel):
            raise ValueError(
                f"Hard deletion of {obj.__class__.__name__} is forbidden. Use soft deletes by setting is_deleted=True."
            )

        if not hasattr(obj, "__tablename__") or obj.__tablename__ == "audit_logs":
            continue

        # If it's another non-audited model, capture its deletion? The requirement says "all clinical records must be versioned..."
        # We can just record a DELETE action for it.
        old_values = {}
        mapper = inspect(obj).mapper
        for attr in mapper.column_attrs:
            val = getattr(obj, attr.key)
            if isinstance(val, datetime):
                val = val.isoformat()
            old_values[attr.key] = val

        kwargs = {
            "table_name": obj.__tablename__,
            "record_id": get_primary_key(obj),
            "action": "DELETE",
            "user_id": user_id,
            "ip_address": ip_address,
            "old_values": old_values,
            "new_values": None,
            "version_index": getattr(obj, "version", 1),
            "change_reason": reason,
        }
        if timestamp is not None:
            kwargs["timestamp"] = timestamp

        audit_logs.append(AuditLog(**kwargs))

    if audit_logs:
        session.add_all(audit_logs)
