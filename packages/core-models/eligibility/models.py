"""
Shared AST, eligibility criteria, and deterministic evaluation domain contracts.

This module provides Pydantic v2 models for inclusion/exclusion criteria,
structured AST expression trees, and comprehensive detailed node/aggregate
evaluation outputs. All models conform to FDA 21 CFR Part 11 auditing principles.
"""

import re
from typing import Any, Dict, List, Literal, Optional

# Import standard GxP audit fields
from organization_domain.models import AuditFields
from pydantic import BaseModel, Field, field_validator, model_validator

# Regex pattern for eCRF.<DOMAIN>.<VARIABLE> references
FIELD_REF_RE = re.compile(r"^eCRF\.([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)$")


class FieldReference(BaseModel):
    """
    Represents a structured field reference pointing to an eCRF domain variable.
    Format must strictly follow: eCRF.<DOMAIN>.<VARIABLE>
    """

    raw_reference: str = Field(
        ...,
        description="Raw field reference string, e.g., 'eCRF.DM.AGE'.",
    )
    domain: str = Field(
        ...,
        description="The target eCRF domain, e.g., 'DM'.",
    )
    variable: str = Field(
        ...,
        description="The domain variable, e.g., 'AGE'.",
    )

    @field_validator("raw_reference")
    @classmethod
    def validate_raw_reference(cls, v: str) -> str:
        """
        Validate that the raw reference string strictly follows the 'eCRF.<DOMAIN>.<VARIABLE>' format.
        """
        match = FIELD_REF_RE.match(v)
        if not match:
            raise ValueError(
                f"Field reference '{v}' is malformed. Must strictly follow format: 'eCRF.<DOMAIN>.<VARIABLE>'"
            )
        return v

    @model_validator(mode="after")
    def validate_internal_consistency(self) -> "FieldReference":
        """
        Ensure that the domain and variable match the components extracted from raw_reference.
        """
        match = FIELD_REF_RE.match(self.raw_reference)
        if match:
            dom, var = match.groups()
            if self.domain != dom or self.variable != var:
                raise ValueError(
                    f"Domain/variable mismatch. raw_reference={self.raw_reference!r} suggests domain={dom!r}, variable={var!r}."
                )
        return self


class ExpressionNode(BaseModel):
    """
    Recursive node inside a structured clinical expression tree (AST).
    Supported types are: logical, comparison, field_ref, constant.
    """

    type: Literal["logical", "comparison", "field_ref", "constant"] = Field(
        ...,
        description="Node type indicating the structure of the node.",
    )
    operator: Optional[str] = Field(
        None,
        description="Operator for logical (and, or, not) or comparison (==, !=, <, <=, >, >=) nodes.",
    )
    operands: Optional[List["ExpressionNode"]] = Field(
        None,
        description="Child operands of logical or comparison nodes.",
    )
    value: Optional[Any] = Field(
        None,
        description="Literal constant value of type constant.",
    )
    field_ref: Optional[FieldReference] = Field(
        None,
        description="Field reference details of type field_ref.",
    )

    @model_validator(mode="after")
    def validate_node(self) -> "ExpressionNode":
        """
        Validate node contents based on its type.
        """
        if self.type == "constant":
            # value can be any literal (including None / boolean False)
            pass
        elif self.type == "field_ref":
            if self.field_ref is None:
                raise ValueError("Field reference node must provide 'field_ref'.")
        elif self.type == "logical":
            if self.operator not in ("and", "or", "not"):
                raise ValueError(f"Invalid logical operator: '{self.operator}'.")
            if not self.operands:
                raise ValueError(f"Logical node '{self.operator}' requires operands.")
            if self.operator == "not" and len(self.operands) != 1:
                raise ValueError("Logical 'not' operator requires exactly 1 operand.")
            if self.operator in ("and", "or") and len(self.operands) < 2:
                raise ValueError(
                    f"Logical '{self.operator}' operator requires at least 2 operands."
                )
        elif self.type == "comparison":
            if self.operator not in ("==", "!=", "<", "<=", ">", ">="):
                raise ValueError(f"Invalid comparison operator: '{self.operator}'.")
            if not self.operands or len(self.operands) != 2:
                raise ValueError(
                    f"Comparison operator '{self.operator}' requires exactly 2 operands."
                )
        return self


# Rebuild recursive models in Pydantic v2
ExpressionNode.model_rebuild()


class EligibilityCriterion(AuditFields):
    """
    Represents a single inclusion or exclusion criterion with full GxP audit metadata.
    """

    criterion_id: str = Field(
        ...,
        description="Unique identifier of this eligibility criterion, e.g., 'INC_01'.",
    )
    criterion_type: Literal["inclusion", "exclusion"] = Field(
        ...,
        description="Whether this is an inclusion or exclusion criterion.",
    )
    description: str = Field(
        ...,
        description="Human-readable text description of the criterion.",
    )
    dsl_source: str = Field(
        ...,
        description="The raw DSL statement source, e.g., 'eCRF.DM.AGE >= 18'.",
    )
    condition: ExpressionNode = Field(
        ...,
        description="The parsed structured AST of this criterion.",
    )
    expected_outcome: bool = Field(
        True,
        description="Expected Boolean outcome of evaluating the condition node. "
        "Typically True for inclusions and False for exclusions.",
    )

    @model_validator(mode="after")
    def validate_expected_outcome_defaults(self) -> "EligibilityCriterion":
        """
        Set or validate expected outcomes defaults if needed, aligning with the criterion type.
        """
        # Inclusions expect the condition to be True, exclusions expect the condition to be False (to not be excluded)
        # However, users can override this. We keep the defaults.
        return self


class NodeEvaluation(BaseModel):
    """
    Detailed evaluation output for a single node inside the AST expression tree.
    Provides complete node-level traceability for regulatory compliance.
    """

    node_type: str = Field(
        ...,
        description="The type of AST node that was evaluated.",
    )
    operator: Optional[str] = Field(
        None,
        description="The operator utilized during evaluation.",
    )
    value: Optional[Any] = Field(
        None,
        description="The evaluated literal value of the node, if determined.",
    )
    is_indeterminate: bool = Field(
        False,
        description="Indicates if the evaluation is indeterminate (e.g. due to missing or null data).",
    )
    explanation: str = Field(
        ...,
        description="Trace explanation detailing how this node evaluated to its outcome.",
    )
    children: List["NodeEvaluation"] = Field(
        default_factory=list,
        description="Child node evaluation details.",
    )


NodeEvaluation.model_rebuild()


class CriterionEvaluation(BaseModel):
    """
    Evaluation summary for a single eligibility criterion.
    """

    criterion_id: str = Field(
        ...,
        description="The identifier of the criterion evaluated.",
    )
    criterion_type: Literal["inclusion", "exclusion"] = Field(
        ...,
        description="Whether this is an inclusion or exclusion criterion.",
    )
    description: str = Field(
        ...,
        description="Human-readable description of the criterion.",
    )
    dsl_source: str = Field(
        ...,
        description="Raw DSL source string of the criterion.",
    )
    expected_outcome: bool = Field(
        ...,
        description="Expected Boolean outcome of the condition evaluation.",
    )
    evaluation_detail: NodeEvaluation = Field(
        ...,
        description="The recursive evaluation trace tree of the condition.",
    )
    is_indeterminate: bool = Field(
        ...,
        description="Indicates if the evaluation was indeterminate.",
    )
    is_met: bool = Field(
        ...,
        description="Indicates if the subject satisfies this criterion.",
    )


class AggregateEligibilityResult(BaseModel):
    """
    Aggregated eligibility outcome over a set of inclusion/exclusion criteria.
    """

    eligible: Optional[bool] = Field(
        None,
        description="Aggregated eligibility. True if all criteria are met. "
        "False if any criterion failed. None if indeterminate and no hard failures exist.",
    )
    failed_criteria: List[str] = Field(
        default_factory=list,
        description="List of criterion IDs that failed evaluation.",
    )
    indeterminate_criteria: List[str] = Field(
        default_factory=list,
        description="List of criterion IDs that were indeterminate due to missing/null values.",
    )
    criteria_evaluations: Dict[str, CriterionEvaluation] = Field(
        default_factory=dict,
        description="A map of detailed evaluation results keyed by criterion ID.",
    )
