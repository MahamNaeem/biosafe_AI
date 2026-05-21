"""
BioSafe AI - Dispute & Escalation Workflow
Handles all dispute types with severity scoring and resolutions
"""

from datetime import datetime
from typing import Dict, Any, List, Tuple


# ─── DISPUTE CONFIG ───────────────────────────────────────────────────────────

DISPUTE_TYPES = {
    "no_show":           ("High",     "Provider did not arrive for scheduled pickup"),
    "late_pickup":       ("Medium",   "Provider arrived significantly late"),
    "cancellation":      ("Medium",   "Provider cancelled after confirmation"),
    "quality_complaint": ("High",     "Service quality below acceptable standard"),
    "price_disagreement":("Medium",   "Charged amount differs from quoted price"),
    "qr_mismatch":       ("High",     "QR code on waste bag doesn't match booking"),
    "illegal_dumping":   ("Critical", "Evidence of illegal or improper waste dumping"),
    "certificate_missing":("Medium",  "Disposal certificate not provided"),
    "overrun":           ("Low",      "Service took significantly longer than estimated"),
    "unsafe_handling":   ("Critical", "Unsafe waste handling observed"),
    "wrong_disposal":    ("Critical", "Wrong disposal method used for waste type"),
    "data_breach":       ("High",     "Patient/hospital data mishandled"),
}

RESOLUTION_RULES = {
    "no_show": {
        "refund_pct": 1.0,
        "compensation_pkr": 500,
        "provider_action": "Warning issued. 3 warnings = suspension.",
        "hospital_action": "Emergency rebooking triggered with next-ranked provider.",
    },
    "late_pickup": {
        "refund_pct": 0.15,
        "compensation_pkr": 300,
        "provider_action": "Late penalty applied to provider rating.",
        "hospital_action": "Partial refund of urgency fee.",
    },
    "cancellation": {
        "refund_pct": 1.0,
        "compensation_pkr": 1000,
        "provider_action": "Cancellation logged. High rate = ranking penalised.",
        "hospital_action": "Immediate rebooking. Compensation for inconvenience.",
    },
    "quality_complaint": {
        "refund_pct": 0.5,
        "compensation_pkr": 1500,
        "provider_action": "Quality audit required before next assignment.",
        "hospital_action": "50% refund. Free rebooking.",
    },
    "price_disagreement": {
        "refund_pct": 0.0,
        "compensation_pkr": 0,
        "provider_action": "Invoice reviewed by platform team.",
        "hospital_action": "Overcharge refunded if confirmed.",
    },
    "qr_mismatch": {
        "refund_pct": 1.0,
        "compensation_pkr": 2000,
        "provider_action": "Chain-of-custody investigation launched.",
        "hospital_action": "Full refund. EPA notification sent.",
    },
    "illegal_dumping": {
        "refund_pct": 1.0,
        "compensation_pkr": 10000,
        "provider_action": "IMMEDIATE BLACKLIST. EPA + Police notified.",
        "hospital_action": "Full refund. Incident report filed. Free priority rebook.",
    },
    "certificate_missing": {
        "refund_pct": 0.0,
        "compensation_pkr": 0,
        "provider_action": "7-day deadline to submit certificate or fine applied.",
        "hospital_action": "Follow-up reminder sent. Escalated after 7 days.",
    },
    "overrun": {
        "refund_pct": 0.0,
        "compensation_pkr": 0,
        "provider_action": "Overrun logged for capacity planning.",
        "hospital_action": "No charge for additional time if < 30 min overrun.",
    },
    "unsafe_handling": {
        "refund_pct": 1.0,
        "compensation_pkr": 5000,
        "provider_action": "Immediate suspension. WHO compliance audit required.",
        "hospital_action": "Full refund. Incident report to Ministry of Health.",
    },
    "wrong_disposal": {
        "refund_pct": 1.0,
        "compensation_pkr": 8000,
        "provider_action": "Immediate suspension. Liability claim filed.",
        "hospital_action": "Full refund. Emergency environmental remediation.",
    },
    "data_breach": {
        "refund_pct": 0.0,
        "compensation_pkr": 5000,
        "provider_action": "GDPR/Privacy audit. Potential criminal referral.",
        "hospital_action": "PTA/Data Protection notification sent.",
    },
}

SEVERITY_COLORS = {
    "Low":      "🟢",
    "Medium":   "🟡",
    "High":     "🔴",
    "Critical": "💀",
}

ESCALATION_PATHS = {
    "Low":      ["Auto-resolve with system notification"],
    "Medium":   ["Platform Support Team review within 24h"],
    "High":     ["Senior Escalation Team", "Possible provider suspension"],
    "Critical": ["Immediate human review", "EPA/Ministry notification", "Potential blacklisting", "Police if illegal"],
}


# ─── CORE DISPUTE HANDLER ─────────────────────────────────────────────────────

def raise_dispute(
    booking: Dict[str, Any],
    dispute_type: str,
    description: str,
    claimed_amount: float = 0
) -> Dict[str, Any]:
    """
    Process a dispute, compute severity, resolution, and compensation.
    Returns full dispute record.
    """
    severity_label, default_desc = DISPUTE_TYPES.get(
        dispute_type, ("Medium", "General dispute")
    )
    resolution = RESOLUTION_RULES.get(dispute_type, {
        "refund_pct": 0.0,
        "compensation_pkr": 0,
        "provider_action": "Under review.",
        "hospital_action": "Being investigated.",
    })

    total_paid = float(booking.get("total_price_pkr", 0))
    refund_amount = total_paid * resolution["refund_pct"]
    compensation   = resolution["compensation_pkr"]

    dispute_id = f"D{datetime.now().strftime('%Y%m%d%H%M%S')}"
    status     = "escalated" if severity_label == "Critical" else "open"

    return {
        "dispute_id":          dispute_id,
        "booking_id":          booking.get("booking_id", "UNKNOWN"),
        "dispute_type":        dispute_type,
        "description":         description or default_desc,
        "severity":            severity_label,
        "severity_icon":       SEVERITY_COLORS.get(severity_label, "⚪"),
        "status":              status,
        "refund_amount_pkr":   round(refund_amount, 2),
        "compensation_pkr":    compensation,
        "total_resolution_pkr":round(refund_amount + compensation, 2),
        "provider_action":     resolution["provider_action"],
        "hospital_action":     resolution["hospital_action"],
        "escalation_path":     ESCALATION_PATHS.get(severity_label, []),
        "requires_human":      severity_label in ("High", "Critical"),
        "blacklist_provider":  dispute_type in ("illegal_dumping", "unsafe_handling", "wrong_disposal"),
        "notify_authorities":  dispute_type in ("illegal_dumping", "unsafe_handling"),
        "created_at":          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def get_dispute_trace(dispute: Dict[str, Any], provider_name: str = "Provider") -> str:
    """Generate Antigravity trace log for dispute."""
    escalation = "\n    → ".join(dispute.get("escalation_path", []))
    blacklist_note = (
        "\n⛔ PROVIDER BLACKLISTED — removed from platform." if dispute["blacklist_provider"] else ""
    )
    authority_note = (
        "\n🚨 EPA + Police notified due to environmental risk." if dispute["notify_authorities"] else ""
    )

    return (
        f"[Antigravity Dispute Trace]\n"
        f"Dispute ID:      {dispute['dispute_id']}\n"
        f"Booking ID:      {dispute['booking_id']}\n"
        f"Type:            {dispute['dispute_type'].replace('_', ' ').title()}\n"
        f"Severity:        {dispute['severity_icon']} {dispute['severity']}\n"
        f"Status:          {dispute['status'].upper()}\n"
        f"Description:     {dispute['description']}\n"
        f"\nResolution:\n"
        f"  Hospital:   {dispute['hospital_action']}\n"
        f"  Provider:   {dispute['provider_action']}\n"
        f"\nFinancial:\n"
        f"  Refund:       PKR {dispute['refund_amount_pkr']:,.0f}\n"
        f"  Compensation: PKR {dispute['compensation_pkr']:,.0f}\n"
        f"  Total Relief: PKR {dispute['total_resolution_pkr']:,.0f}\n"
        f"\nEscalation Path:\n    → {escalation}"
        f"{blacklist_note}{authority_note}\n"
        f"Timestamp: {dispute['created_at']}"
    )


def simulate_fallback_scenarios() -> List[Dict[str, Any]]:
    """Predefined fallback scenario descriptions for display."""
    return [
        {
            "scenario":    "No Provider Available",
            "trigger":     "All providers at capacity or outside service area",
            "action":      "Hospital added to waitlist. Auto-notify when slot opens. Show next-available provider ETA.",
            "trace_label": "FALLBACK: Waitlist activated",
        },
        {
            "scenario":    "Low Confidence Parsing",
            "trigger":     "Confidence < 75% from multilingual parser",
            "action":      "Confirmation questions sent to hospital contact. Workflow paused until clarity.",
            "trace_label": "FALLBACK: Clarification requested",
        },
        {
            "scenario":    "Provider Cancels After Confirmation",
            "trigger":     "Provider marks booking cancelled within 1h of pickup",
            "action":      "Next-ranked provider auto-assigned. Hospital notified. Cancellation logged.",
            "trace_label": "FALLBACK: Auto-rebooking triggered",
        },
        {
            "scenario":    "Payment Failure",
            "trigger":     "Payment gateway timeout or card decline",
            "action":      "Booking held for 15 mins. Retry prompt sent. On 2nd failure: invoice generated.",
            "trace_label": "FALLBACK: Payment retry initiated",
        },
        {
            "scenario":    "API/Maps Failure",
            "trigger":     "Distance or routing API unavailable",
            "action":      "Fallback to haversine formula for distance. Provider self-reports ETA.",
            "trace_label": "FALLBACK: Offline distance estimation used",
        },
        {
            "scenario":    "High-Rated Provider with Recent Complaints",
            "trigger":     "Provider rating ≥4.5 but complaint_rate ≥ 0.05 in last 30 days",
            "action":      "System downgrades effective rank. Hospital warned. Certificate history reviewed.",
            "trace_label": "FALLBACK: Recent complaint override applied",
        },
        {
            "scenario":    "Scheduling Conflict — Two Hospitals Same Slot",
            "trigger":     "Two simultaneous requests for same provider-slot",
            "action":      "First confirmed booking wins. Second gets next-best provider suggestion.",
            "trace_label": "FALLBACK: Double-booking prevented",
        },
    ]
