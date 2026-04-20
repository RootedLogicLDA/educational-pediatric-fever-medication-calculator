"""
Paracetamol / ibuprofen dosing tools for pediatric use.

DISCLAIMER: This is an educational tool only. Always consult a doctor or
pharmacist before administering medication to children.
"""

import logging
import re

logger = logging.getLogger(__name__)


# Approximate median weight (kg) by age in months — based on WHO growth charts
_WEIGHT_TABLE: dict[int, float] = {
    1: 4.5,
    2: 5.5,
    3: 6.0,
    4: 6.5,
    5: 7.0,
    6: 7.5,
    9: 8.5,
    12: 9.5,
    18: 11.0,
    24: 12.0,
    30: 13.0,
    36: 14.0,
    48: 16.0,
    60: 18.0,
    72: 20.0,
    84: 22.0,
    96: 25.0,
    108: 28.0,
    120: 32.0,
    132: 36.0,
    144: 40.0,
}


def _parse_weight_and_concentration(args: str) -> tuple[float, float] | str:
    """Extract (weight_kg, concentration_mg_per_ml) from a free-form string."""
    numbers = re.findall(r"\d+\.?\d*", args)
    if len(numbers) < 2:
        return (
            "Error: provide weight in kg and concentration in mg/mL. "
            "Example: '11.0, 40' or '12 kg, 40 mg/ml'."
        )
    weight_kg = float(numbers[0])
    concentration = float(numbers[1])
    if weight_kg <= 0 or concentration <= 0:
        return "Error: weight and concentration must be positive numbers."
    if weight_kg > 80:
        return f"Weight {weight_kg} kg seems too high for a child. Please verify."
    return weight_kg, concentration


def get_child_weight(age_str: str) -> str:
    """
    Returns estimated weight for a child given their age.

    Accepts: "18 months", "2 years", "6 meses", "3 anos", or a bare number
    (treated as years if ≤ 14, otherwise months).
    """
    logger.info("[tool] get_child_weight called with: %r", age_str)
    age_str = age_str.strip().lower()

    match = re.search(r"(\d+\.?\d*)", age_str)
    if not match:
        return "Error: could not parse age. Please provide age as '18 months' or '2 years'."

    num = float(match.group(1))

    if any(kw in age_str for kw in ("month", "mes", "mês", "meses")):
        months = round(num)
    elif any(kw in age_str for kw in ("year", "ano", "anos")):
        months = round(num * 12)
    else:
        months = round(num * 12) if num <= 14 else round(num)

    if months < 1:
        return "Child is under 1 month. Do not administer any antipyretic without direct medical supervision."
    if months > 144:
        return f"Child is over 12 years ({months} months). Use adult/adolescent dosing under medical advice."

    closest_age = min(_WEIGHT_TABLE.keys(), key=lambda x: abs(x - months))
    weight_kg = _WEIGHT_TABLE[closest_age]

    return (
        f"Estimated weight for a child of {months} months: {weight_kg} kg "
        f"(based on WHO median; actual weight may differ)."
    )


def paracetamol_calculator(args: str) -> str:
    """
    Calculates the paracetamol (Benuron) dose in mL.

    Args: "WEIGHT_KG, CONCENTRATION_MG_PER_ML"
    Examples: "11.0, 40"  |  "12 kg, 40mg/ml"

    Standard dose: 15 mg/kg per dose, every 6–8 h, max 4×/day.
    Single-dose cap: 1000 mg.
    """
    logger.info("[tool] paracetamol_calculator called with: %r", args)
    parsed = _parse_weight_and_concentration(args.strip().lower())
    if isinstance(parsed, str):
        return parsed

    weight_kg, concentration = parsed

    dose_mg = min(15.0 * weight_kg, 1000.0)
    dose_ml = dose_mg / concentration
    max_daily_mg = min(60.0 * weight_kg, 4000.0)
    max_doses = int(max_daily_mg // dose_mg)

    return (
        f"Paracetamol dose: {dose_mg:.1f} mg → {dose_ml:.1f} mL "
        f"of {concentration} mg/mL solution. "
        f"Give every 6–8 hours (min 4 h apart), up to {max_doses}× per day. "
        f"Max daily: {max_daily_mg:.0f} mg. "
        "IMPORTANT: educational estimate only — confirm with a healthcare professional."
    )


def ibuprofen_calculator(args: str) -> str:
    """
    Calculates the ibuprofen (Brufen/Nurofen) dose in mL.

    Args: "WEIGHT_KG, CONCENTRATION_MG_PER_ML"
    Examples: "11.0, 20"  |  "12 kg, 20mg/ml"

    Standard dose: 10 mg/kg per dose, every 6–8 h, max 3×/day.
    Single-dose cap: 400 mg.
    Not for children under 3 months or under 5 kg.
    Common concentrations: 20 mg/mL (Brufen/Nurofen suspension).
    """
    logger.info("[tool] ibuprofen_calculator called with: %r", args)
    parsed = _parse_weight_and_concentration(args.strip().lower())
    if isinstance(parsed, str):
        return parsed

    weight_kg, concentration = parsed

    if weight_kg < 5:
        return (
            f"Weight {weight_kg} kg is under 5 kg. "
            "Ibuprofen is NOT recommended for children under 3 months or under 5 kg. "
            "Consult a doctor immediately."
        )

    dose_mg = min(10.0 * weight_kg, 400.0)
    dose_ml = dose_mg / concentration
    max_daily_mg = min(30.0 * weight_kg, 1200.0)
    max_doses = int(max_daily_mg // dose_mg)

    return (
        f"Ibuprofen dose: {dose_mg:.1f} mg → {dose_ml:.1f} mL "
        f"of {concentration} mg/mL solution. "
        f"Give every 6–8 hours (min 6 h apart), up to {max_doses}× per day. "
        f"Max daily: {max_daily_mg:.0f} mg. "
        "Do not give on an empty stomach. "
        "Avoid if child has kidney issues, asthma, or chickenpox. "
        "IMPORTANT: educational estimate only — confirm with a healthcare professional."
    )


def get_product_concentration(product_str: str) -> str:
    """
    Returns the concentration in mg/mL for a named product.

    Accepts: 'Benuron 40mg/ml', 'Brufen 20mg/ml', 'syrup', 'xarope', '40 mg/ml'.
    """
    logger.info("[tool] get_product_concentration called with: %r", product_str)
    product_str = product_str.strip().lower()

    match = re.search(r"(\d+\.?\d*)\s*mg\s*/\s*m[lL]", product_str)
    if match:
        return f"Concentration: {float(match.group(1))} mg/mL."

    _aliases: dict[str, float] = {
        # Paracetamol
        "benuron": 40.0,
        "xarope": 40.0,
        "syrup": 40.0,
        "suspension": 40.0,
        "solução oral": 40.0,
        "oral solution": 40.0,
        # Ibuprofen
        "brufen": 20.0,
        "nurofen": 20.0,
        "advil": 20.0,
    }
    for alias, conc in _aliases.items():
        if alias in product_str:
            return f"Concentration: {conc} mg/mL."

    return (
        "Could not determine concentration. "
        "Please provide it explicitly, e.g. '40mg/ml' or '20mg/ml'."
    )


known_actions = {
    "get_child_weight": get_child_weight,
    "paracetamol_calculator": paracetamol_calculator,
    "ibuprofen_calculator": ibuprofen_calculator,
    "get_product_concentration": get_product_concentration,
}
