"""
CDISC Controlled Terminology and Domain Enums for SDTM.

This module provides the shared controlled vocabularies (enums) for SDTM domains,
SEX, RACE, Adverse Event severity/seriousness/relationship/outcome, and HL7 Null-Flavor codes.
"""

from enum import Enum


class SDTMDomain(str, Enum):
    """
    Standard CDISC SDTM domains.
    """

    DM = "DM"
    AE = "AE"
    VS = "VS"
    LB = "LB"
    CM = "CM"
    MH = "MH"


class Sex(str, Enum):
    """
    CDISC SEX controlled terminology.
    """

    M = "M"
    F = "F"
    U = "U"


class Race(str, Enum):
    """
    CDISC RACE controlled terminology (including MULTIPLE and OTHER).
    """

    AMERICAN_INDIAN_OR_ALASKA_NATIVE = "AMERICAN INDIAN OR ALASKA NATIVE"
    ASIAN = "ASIAN"
    BLACK_OR_AFRICAN_AMERICAN = "BLACK OR AFRICAN AMERICAN"
    NATIVE_HAWAIIAN_OR_OTHER_PACIFIC_ISLANDER = (
        "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER"
    )
    WHITE = "WHITE"
    MULTIPLE = "MULTIPLE"
    OTHER = "OTHER"


class AESeverity(str, Enum):
    """
    Adverse Event Severity (AESEV) controlled terminology.
    """

    MILD = "MILD"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"


class AESeriousness(str, Enum):
    """
    Adverse Event Seriousness (AESER) controlled terminology.
    """

    Y = "Y"
    N = "N"


class AERelationship(str, Enum):
    """
    Adverse Event Relationship to Treatment (AEREL) controlled terminology.
    """

    RELATED = "RELATED"
    NOT_RELATED = "NOT RELATED"
    POSSIBLY_RELATED = "POSSIBLY RELATED"


class AEOutcome(str, Enum):
    """
    Adverse Event Outcome (AEOUT) controlled terminology.
    """

    RECOVERED_RESOLVED = "RECOVERED/RESOLVED"
    RECOVERING_RESOLVING = "RECOVERING/RESOLVING"
    NOT_RECOVERED_NOT_RESOLVED = "NOT RECOVERED/NOT RESOLVED"
    RECOVERED_RESOLVED_WITH_SEQUELAE = "RECOVERED/RESOLVED WITH SEQUELAE"
    FATAL = "FATAL"
    UNKNOWN = "UNKNOWN"


class NullFlavor(str, Enum):
    """
    Standard HL7/CDISC Null Flavor codes representing why clinical data is missing.
    """

    NI = "NI"
    NA = "NA"
    UNK = "UNK"
    ASKU = "ASKU"
    NASK = "NASK"
    MSNG = "MSNG"
