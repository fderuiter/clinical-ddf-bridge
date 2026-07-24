import time
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import select

from apps.ctms.database import db_manager
from apps.ctms.main import app
from apps.ctms.models import (
    Base,
    CTMSAuditLog,
    InvestigatorGrant,
    BudgetLineItem,
    PaymentMilestone,
    InvestigatorPayable,
)
from tests.test_ctms import setup_db, get_auth_headers


@pytest.mark.asyncio
async def test_ctms_finances_full_workflow():
    """
    Verify complete investigator grants, budgets, milestones, and payables workflow.
    Covers RBAC, locking, milestone triggering, idempotency, and GxP/Part 11 auditing.
    """
    client = TestClient(app)

    # 1. Auth Headers
    grants_mgr_headers = get_auth_headers(roles="Grants Manager", change_reason="Initial finance setup")
    sponsor_admin_headers = get_auth_headers(roles="Sponsor Admin", change_reason="Sponsor oversight")
    cra_headers = get_auth_headers(roles="CRA", change_reason="CRA duties")
    unauthorized_headers = get_auth_headers(roles="Site Investigator", change_reason="Snoop")

    # 2. Setup Study (Requires privileged role or we can use CRA)
    study_payload = {
        "study_id": "STUDY_FIN_01",
        "name": "Financial Test Study",
        "status": "ACTIVE",
    }
    client.post("/api/v1/ctms/studies", json=study_payload, headers=cra_headers)

    # 3. Create Investigator Grant (RBAC Check)
    grant_payload = {
        "investigator_id": "inv_99",
        "site_id": "site_99",
        "study_id": "STUDY_FIN_01",
        "total_budget": 50000.0,
        "currency": "EUR",
        "status": "DRAFT"
    }

    # Deny unauthorized role
    response_denied = client.post("/api/v1/ctms/grants", json=grant_payload, headers=unauthorized_headers)
    assert response_denied.status_code == 403

    # Accept authorized role
    response_created = client.post("/api/v1/ctms/grants", json=grant_payload, headers=grants_mgr_headers)
    assert response_created.status_code == 201
    grant_data = response_created.json()
    grant_id = grant_data["id"]
    assert grant_data["investigator_id"] == "inv_99"
    assert grant_data["total_budget"] == 50000.0
    assert grant_data["status"] == "DRAFT"
    assert grant_data["created_by"] == "test_user"
    assert grant_data["reason_for_change"] == "Initial finance setup"

    # 4. Create Budget Line Item
    budget_payload = {
        "grant_id": grant_id,
        "category": "IMV Visits",
        "planned_amount": 12000.0,
        "actual_amount": 0.0
    }
    # Deny unauthorized role
    response_b_denied = client.post("/api/v1/ctms/budgets/line-items", json=budget_payload, headers=unauthorized_headers)
    assert response_b_denied.status_code == 403

    # Accept authorized
    response_b_created = client.post("/api/v1/ctms/budgets/line-items", json=budget_payload, headers=grants_mgr_headers)
    assert response_b_created.status_code == 201
    budget_item = response_b_created.json()
    budget_item_id = budget_item["id"]
    assert budget_item["category"] == "IMV Visits"
    assert budget_item["planned_amount"] == 12000.0

    # 5. Create Payment Milestone
    milestone_payload = {
        "description": "Trigger after IMV completed",
        "trigger_type": "VISIT_COMPLETED",
        "trigger_condition": "IMV",
        "amount": 3000.0
    }
    # Deny unauthorized
    response_m_denied = client.post(
        f"/api/v1/ctms/grants/{grant_id}/milestones", json=milestone_payload, headers=unauthorized_headers
    )
    assert response_m_denied.status_code == 403

    # Accept authorized
    response_m_created = client.post(
        f"/api/v1/ctms/grants/{grant_id}/milestones", json=milestone_payload, headers=grants_mgr_headers
    )
    assert response_m_created.status_code == 201
    milestone_data = response_m_created.json()
    milestone_id = milestone_data["id"]
    assert milestone_data["trigger_type"] == "VISIT_COMPLETED"
    assert milestone_data["payment_status"] == "PENDING"

    # 6. Evaluate Milestone (conditions not met yet because no IMV is completed)
    response_eval_not_met = client.post(
        f"/api/v1/ctms/grants/{grant_id}/milestones/{milestone_id}/evaluate", headers=grants_mgr_headers
    )
    assert response_eval_not_met.status_code == 200
    assert response_eval_not_met.json()["triggered"] is False
    assert response_eval_not_met.json()["payable"] is None

    # 7. Complete a Monitoring Visit to satisfy milestone condition
    visit_payload = {
        "study_id": "STUDY_FIN_01",
        "site_id": "site_99",
        "cra_id": "cra_fderuiter",
        "visit_type": "IMV",
        "scheduled_date": (datetime.utcnow() + timedelta(days=1)).isoformat()
    }
    response_visit = client.post("/api/v1/ctms/monitoring-visits", json=visit_payload, headers=cra_headers)
    assert response_visit.status_code == 201
    visit_id = response_visit.json()["id"]

    # Complete the visit
    comp_payload = {
        "actual_date": datetime.utcnow().isoformat(),
        "findings": []
    }
    response_comp = client.post(f"/api/v1/ctms/monitoring-visits/{visit_id}/complete", json=comp_payload, headers=cra_headers)
    assert response_comp.status_code == 200

    # 8. Evaluate Milestone again (conditions met now)
    response_eval_met = client.post(
        f"/api/v1/ctms/grants/{grant_id}/milestones/{milestone_id}/evaluate", headers=grants_mgr_headers
    )
    assert response_eval_met.status_code == 200
    eval_result = response_eval_met.json()
    assert eval_result["triggered"] is True
    assert eval_result["milestone"]["payment_status"] == "TRIGGERED"
    payable_data = eval_result["payable"]
    assert payable_data is not None
    assert payable_data["amount"] == 3000.0
    assert payable_data["status"] == "UNPAID"
    payable_id = payable_data["id"]

    # 9. Idempotency Check: Evaluate again, should not duplicate payable and should return same data
    response_eval_idempotent = client.post(
        f"/api/v1/ctms/grants/{grant_id}/milestones/{milestone_id}/evaluate", headers=grants_mgr_headers
    )
    assert response_eval_idempotent.status_code == 200
    assert response_eval_idempotent.json()["triggered"] is True
    assert response_eval_idempotent.json()["payable"]["id"] == payable_id

    # 10. Check payment status exposure
    response_pay_status = client.get(f"/api/v1/ctms/grants/{grant_id}/payments", headers=grants_mgr_headers)
    assert response_pay_status.status_code == 200
    p_status = response_pay_status.json()
    assert len(p_status["milestones"]) == 1
    assert len(p_status["payables"]) == 1
    assert p_status["payables"][0]["id"] == payable_id

    # 11. Pay Payable & Update budget actualspent amount (category 'IMV Visits' matches 'Trigger after IMV completed')
    response_pay = client.post(
        f"/api/v1/ctms/grants/{grant_id}/payables/{payable_id}/pay", headers=sponsor_admin_headers
    )
    assert response_pay.status_code == 200
    paid_payable = response_pay.json()
    assert paid_payable["status"] == "PAID"
    assert paid_payable["payment_date"] is not None

    # Check that budget actual amount got updated
    response_budget_list = client.get(f"/api/v1/ctms/budgets/line-items?grant_id={grant_id}", headers=grants_mgr_headers)
    assert response_budget_list.status_code == 200
    items = response_budget_list.json()
    target_item = next(item for item in items if item["id"] == budget_item_id)
    assert target_item["actual_amount"] == 3000.0

    # 12. Approved Grant version locking
    # Approve the grant
    approve_payload = {"status": "APPROVED"}
    response_approve = client.put(f"/api/v1/ctms/grants/{grant_id}", json=approve_payload, headers=grants_mgr_headers)
    assert response_approve.status_code == 200
    assert response_approve.json()["status"] == "APPROVED"

    # Try modifying the approved grant -> 400 Bad Request
    try_update_grant = client.put(
        f"/api/v1/ctms/grants/{grant_id}", json={"total_budget": 999999}, headers=grants_mgr_headers
    )
    assert try_update_grant.status_code == 400
    assert "approved investigator grant" in try_update_grant.json()["detail"]

    # Try creating a new budget line item on the approved grant -> 400 Bad Request
    try_create_budget = client.post(
        "/api/v1/ctms/budgets/line-items",
        json={"grant_id": grant_id, "category": "Locked item", "planned_amount": 100},
        headers=grants_mgr_headers
    )
    assert try_create_budget.status_code == 400
    assert "approved investigator grant" in try_create_budget.json()["detail"]

    # Try updating existing budget item on the approved grant -> 400 Bad Request
    try_update_budget = client.put(
        f"/api/v1/ctms/budgets/line-items/{budget_item_id}",
        json={"planned_amount": 99999},
        headers=grants_mgr_headers
    )
    assert try_update_budget.status_code == 400
    assert "approved investigator grant" in try_update_budget.json()["detail"]

    # Try creating milestone on approved grant -> 400 Bad Request
    try_create_milestone = client.post(
        f"/api/v1/ctms/grants/{grant_id}/milestones",
        json={"description": "new", "trigger_type": "MANUAL", "amount": 10},
        headers=grants_mgr_headers
    )
    assert try_create_milestone.status_code == 400
    assert "approved investigator grant" in try_create_milestone.json()["detail"]

    # 13. Part 11 Audit Trail Verification
    async with db_manager.get_session_maker()() as session:
        stmt = select(CTMSAuditLog).order_by(CTMSAuditLog.timestamp.desc())
        result = await session.execute(stmt)
        logs = result.scalars().all()

        actions = [log.action for log in logs]
        assert "CREATE_GRANT" in actions
        assert "CREATE_BUDGET_ITEM" in actions
        assert "CREATE_MILESTONE" in actions
        assert "TRIGGER_MILESTONE" in actions
        assert "PAY_PAYABLE" in actions

        create_grant_log = next(log for log in logs if log.action == "CREATE_GRANT")
        assert create_grant_log.user_role == "Grants Manager"
        assert "Initial finance setup" in create_grant_log.details

        pay_log = next(log for log in logs if log.action == "PAY_PAYABLE")
        assert pay_log.user_role == "Sponsor Admin"
        assert "Paid investigator payable" in pay_log.details
