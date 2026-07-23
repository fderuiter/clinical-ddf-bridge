"""UCUM Unit Standardization Engine.

This module provides rules and functions for translating and normalizing clinical
measurements using the Unified Code for Units of Measure (UCUM) standard.
No third-party scientific or data analysis libraries are used.
"""

from typing import Dict, Optional, Tuple


# A matrix of standard conversion factors.
# Format: (source_unit, target_unit) -> (multiplier, offset, precision)
# A domain or concept name can be optionally used to disambiguate mg/dL -> umol/L.
UCUM_CONVERSION_RULES: Dict[Tuple[str, str], Tuple[float, float, int]] = {
    ("[degF]", "Cel"): (0.5555555555555556, -17.77777777777778, 2),
    ("Cel", "Cel"): (1.0, 0.0, 2),
    ("[lb_av]", "kg"): (0.45359237, 0.0, 3),
    ("g", "kg"): (0.001, 0.0, 3),
    ("[in_i]", "cm"): (2.54, 0.0, 1),
    ("mg/dL", "mmol/L"): (0.0555, 0.0, 2),  # Default Glucose
    ("mmol/L", "mmol/L"): (1.0, 0.0, 2),
}

# Explicit mappings for Creatinine and Bilirubin to handle mg/dL -> umol/L disambiguation
MG_DL_TO_UMOL_L_CREATININE = (88.4, 0.0, 1)
MG_DL_TO_UMOL_L_BILIRUBIN = (17.1, 0.0, 1)


def convert_ucum(
    value: float,
    source_unit: str,
    target_unit: str,
    domain: Optional[str] = None,
) -> Tuple[Optional[float], Optional[float], Optional[float], bool]:
    """Standardizes numeric values and verifies scale compatibility between UCUM units.

    This function implements the general transformation:
        V_target = (V_original * Multiplier) + Offset

    Args:
        value (float): The original raw value to convert.
        source_unit (str): The UCUM code representing the original unit.
        target_unit (str): The UCUM code representing the target standard unit.
        domain (str, optional): The clinical domain or substance identifier to
            disambiguate conversion rules (e.g. "Creatinine" or "Bilirubin").

    Returns:
        Tuple[Optional[float], Optional[float], Optional[float], bool]:
            - target_value: The standardized numeric value, rounded to standard precision.
            - scale_factor: The multiplier used in the conversion equation.
            - offset: The additive offset used in the conversion equation.
            - is_compatible: True if the source and target units are compatible, False otherwise.
    """
    # Direct standard mapping
    if source_unit == target_unit:
        return value, 1.0, 0.0, True

    # Handle domain-specific mg/dL -> umol/L conversion
    if source_unit == "mg/dL" and target_unit == "umol/L":
        if domain and "bilirubin" in domain.lower():
            mult, offset, precision = MG_DL_TO_UMOL_L_BILIRUBIN
        else:
            # Default or explicit creatinine
            mult, offset, precision = MG_DL_TO_UMOL_L_CREATININE
        target_val = (value * mult) + offset
        return round(target_val, precision), mult, offset, True

    # Check standard rules
    rule_key = (source_unit, target_unit)
    if rule_key in UCUM_CONVERSION_RULES:
        mult, offset, precision = UCUM_CONVERSION_RULES[rule_key]
        # Temperature conversion requires special attention due to floating point precision
        if source_unit == "[degF]" and target_unit == "Cel":
            # Target = (Original - 32) * 5/9
            target_val = (value - 32.0) * (5.0 / 9.0)
        else:
            target_val = (value * mult) + offset
        return round(target_val, precision), mult, offset, True

    # Fallback/Incompatible units
    return None, None, None, False
