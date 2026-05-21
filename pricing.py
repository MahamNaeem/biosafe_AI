"""
BioSafe AI - Dynamic Pricing Engine
Transparent breakdown with fairness explanation
"""

from typing import Dict, Any, Tuple
from datetime import datetime


# ─── MULTIPLIER TABLES ────────────────────────────────────────────────────────

URGENCY_MULTIPLIERS = {
    "immediate": 1.80,
    "today":     1.35,
    "tomorrow":  1.15,
    "scheduled": 1.00,
}

COMPLEXITY_FEES = {
    "basic":        0,
    "intermediate": 300,
    "complex":      700,
    "critical":    1400,
}

RISK_HANDLING_FEES = {
    "sharps":       500,
    "infectious":   600,
    "blood":        500,
    "pharmaceutical":400,
    "plastic":      150,
    "general":       50,
    "chemical":     900,
    "radioactive": 2000,
}

ECO_DISCOUNT_RATES = {
    90: 0.05,   # eco_score >= 90 → 5% discount
    80: 0.03,
    70: 0.01,
    0:  0.00,
}

SURGE_HOURS = list(range(8, 10)) + list(range(17, 20))  # 8-9am, 5-7pm


def is_surge_time() -> Tuple[bool, str]:
    hour = datetime.now().hour
    if hour in SURGE_HOURS:
        return True, f"Surge pricing active ({hour}:00 peak hour)"
    return False, "Off-peak time (no surge)"


def get_eco_discount(eco_score: float) -> float:
    for threshold in sorted(ECO_DISCOUNT_RATES.keys(), reverse=True):
        if eco_score >= threshold:
            return ECO_DISCOUNT_RATES[threshold]
    return 0.0


def get_loyalty_discount(booking_count: int) -> Tuple[float, str]:
    """Simulate loyalty tier."""
    if booking_count >= 50:
        return 0.10, "Platinum member (10% loyalty discount)"
    elif booking_count >= 20:
        return 0.07, "Gold member (7% loyalty discount)"
    elif booking_count >= 10:
        return 0.05, "Silver member (5% loyalty discount)"
    elif booking_count >= 3:
        return 0.03, "Regular member (3% loyalty discount)"
    return 0.0, "New customer (no loyalty discount)"


# ─── MAIN PRICING FUNCTION ────────────────────────────────────────────────────

def calculate_price(
    provider: Dict[str, Any],
    parsed_request: Dict[str, Any],
    booking_count: int = 0
) -> Dict[str, Any]:
    """
    Calculate dynamic price with full transparent breakdown.
    Returns dict with all components and total.
    """
    base_fee        = float(provider.get("base_fee", 1500))
    price_per_kg    = float(provider.get("price_per_kg", 12))
    quantity_kg     = float(parsed_request.get("quantity_kg", 50))
    urgency         = parsed_request.get("urgency", "today")
    waste_types     = parsed_request.get("waste_types", ["general"])
    complexity      = parsed_request.get("job_complexity", "basic")
    distance_km     = float(provider.get("distance_km", 5))
    eco_score       = float(provider.get("eco_score", 75))

    # 1. Quantity fee
    quantity_fee = quantity_kg * price_per_kg

    # 2. Urgency multiplier (applied to base + quantity)
    urgency_mult = URGENCY_MULTIPLIERS.get(urgency, 1.0)
    urgency_fee  = (base_fee + quantity_fee) * (urgency_mult - 1)

    # 3. Distance fee
    distance_fee = distance_km * 35   # PKR 35/km

    # 4. Risk handling fee (sum of all waste types)
    risk_fee = sum(RISK_HANDLING_FEES.get(w, 50) for w in waste_types)

    # 5. Complexity fee
    complexity_fee = COMPLEXITY_FEES.get(complexity, 0)

    # 6. Surge condition
    surge_active, surge_label = is_surge_time()
    surge_mult = 1.20 if surge_active else 1.0
    subtotal_before_surge = base_fee + quantity_fee + urgency_fee + distance_fee + risk_fee + complexity_fee
    surge_fee = subtotal_before_surge * (surge_mult - 1)

    subtotal = subtotal_before_surge + surge_fee

    # 7. Eco discount
    eco_disc_rate  = get_eco_discount(eco_score)
    eco_discount   = subtotal * eco_disc_rate

    # 8. Loyalty discount
    loyalty_rate, loyalty_label = get_loyalty_discount(booking_count)
    loyalty_discount = subtotal * loyalty_rate

    # 9. Total
    total = max(500, subtotal - eco_discount - loyalty_discount)

    # Provider earnings estimate (after platform fee of 10%)
    provider_earnings = total * 0.90

    breakdown = {
        "base_fee":          round(base_fee, 2),
        "quantity_fee":      round(quantity_fee, 2),
        "urgency_fee":       round(urgency_fee, 2),
        "distance_fee":      round(distance_fee, 2),
        "risk_handling_fee": round(risk_fee, 2),
        "complexity_fee":    round(complexity_fee, 2),
        "surge_fee":         round(surge_fee, 2),
        "eco_discount":      round(-eco_discount, 2),
        "loyalty_discount":  round(-loyalty_discount, 2),
        "total":             round(total, 2),
        "currency":          "PKR",
        # Meta
        "urgency_multiplier":  urgency_mult,
        "surge_multiplier":    surge_mult,
        "surge_label":         surge_label,
        "loyalty_label":       loyalty_label,
        "eco_discount_rate":   eco_disc_rate,
        "provider_earnings":   round(provider_earnings, 2),
        "platform_fee":        round(total * 0.10, 2),
    }

    breakdown["fairness_explanation"] = _fairness_explanation(breakdown, provider, parsed_request)
    return breakdown


def _fairness_explanation(breakdown: Dict, provider: Dict, request: Dict) -> str:
    return (
        f"📋 Pricing Fairness Note:\n"
        f"• Hospital pays PKR {breakdown['total']:,.0f} for certified, traceable biohazard disposal.\n"
        f"• Provider earns PKR {breakdown['provider_earnings']:,.0f} (90% after 10% platform fee).\n"
        f"• Risk handling fee (PKR {breakdown['risk_handling_fee']:,.0f}) reflects WHO-standard safety protocols.\n"
        f"• Urgency surcharge (PKR {breakdown['urgency_fee']:,.0f}) compensates provider for priority scheduling.\n"
        f"• Eco-discount (PKR {abs(breakdown['eco_discount']):,.0f}) rewards eco-certified providers.\n"
        f"• No hidden fees — all components shown transparently."
    )
