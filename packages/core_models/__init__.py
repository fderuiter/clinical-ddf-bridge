"""Centralized shared CDISC USDM validation models.

This package provides Pydantic v2 representations of CDISC USDM objects,
extending the official `usdm_model` package types to implement strict schema
verification at the API controller boundary.
"""

from typing import List, Literal, Optional

import usdm_model
from pydantic import BaseModel, Field


class USDMItem(BaseModel):
    """Represents an individual study item or question within a protocol.

    Attributes:
        id (Optional[str]): The unique identifier for the item.
        name (str): The name/label of the item.
        type (str): The data type of the item (e.g., string, int, date).
    """

    id: Optional[str] = Field(
        default=None, description="The unique identifier for the item."
    )
    name: str = Field(..., description="The name/label of the item.")
    type: str = Field(..., description="The data type of the item.")


class USDMProtocol(BaseModel):
    """Represents the protocol configuration containing nested items.

    Attributes:
        items (List[USDMItem]): The list of items defined in the protocol.
    """

    items: List[USDMItem] = Field(
        ..., description="The list of items defined in the protocol."
    )


class USDMStudyArm(usdm_model.StudyArm):
    """Represents a customized study arm extending the official CDISC USDM StudyArm type.

    Attributes:
        instanceType (Literal['USDMStudyArm']): Force instance type for serialization and validation.
    """

    instanceType: Literal["USDMStudyArm"] = Field(
        default="USDMStudyArm",
        description="Forced instance type for serialization and validation compatibility.",
    )


class USDMStudy(usdm_model.Study):
    """Represents a study configuration extending the official CDISC USDM Study.

    Integrates the required protocol schema for upfront boundary validation.

    Attributes:
        name (str): The name of the study.
        protocol (USDMProtocol): The nested protocol specification.
        instanceType (Literal['USDMStudy']): Force instance type for serialization and validation.
    """

    name: str = Field(..., description="The name of the study.")
    protocol: USDMProtocol = Field(
        ..., description="The nested protocol specification."
    )
    instanceType: Literal["USDMStudy"] = Field(
        default="USDMStudy",
        description="Forced instance type for serialization and validation compatibility.",
    )
