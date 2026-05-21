"""
BioSafe AI - Google Antigravity Orchestrator
Coordinates all agentic workflow steps with visible reasoning traces
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd

from parser import parse_request
from ranking import rank_providers
from pricing import calculate_price
from scheduler import find_available_slot, create_booking, simulate_notifications, reschedule_booking
from dispute import raise_dispute, get_dispute_trace


# ─── TRACE STORE ─────────────────────────────────────────────────────────────

_trace_store: List[Dict[str, Any]] = []


def _add_trace(step: str, content: str, metadata: Optional[Dict] = None):
    entry = {
        "step":      step,
        "content":   content,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "metadata":  metadata or {},
    }
    _trace_store.append(entry)
    return entry


def get_traces() -> List[Dict[str, Any]]:
    return list(reversed(_trace_store))


def clear_traces():
    _trace_store.clear()


# ─── STEP RUNNERS ─────────────────────────────────────────────────────────────

def step_parse(raw_input: str) -> Dict[str, Any]:
    """Step 1: Language parsing and intent extraction."""
    result = parse_request(raw_input)
    conf = result["confidence"]
    lang = result["language"]
    waste = ", ".join(result["waste_types"])
    dept = result["department"]
    urg = result["urgency"]
    complexity = result["job_complexity"]
    qty = result["quantity_kg"]

    low_conf_note = ""
    if conf < 0.75:
        qs = "\n".join(f"  ❓ {q}" for q in result.get("confirmation_questions", []))
        low_conf_note = f"\n⚠️  LOW CONFIDENCE ({conf:.0%}) — Clarification requested:\n{qs}"

    trace_text = (
        f"[Antigravity Orchestration Trace]\n"
        f"Step 1: Intent Understanding\n"
        f"Input:            \"{raw_input}\"\n"
        f"Detected Language: {lang}\n"
        f"Confidence:        {conf:.0%}\n"
        f"Extracted Intent:  Biohazard Waste Pickup & Disposal\n"
        f"Waste Type(s):     {waste}\n"
        f"Department:        {dept}\n"
        f"Urgency:           {urg.title()}\n"
        f"Quantity (est.):   {qty} kg\n"
        f"Complexity:        {complexity.title()}\n"
        f"Preferred Time:    {result.get('preferred_time', 'Not specified')}\n"
        f"Requirements:      {'; '.join(result.get('special_requirements', [])) or 'None'}"
        f"{low_conf_note}"
    )
    _add_trace("Step 1: Intent Understanding", trace_text, {"confidence": conf})
    return result


def step_classify_waste(parsed: Dict[str, Any], waste_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Step 2: Waste classification and risk assignment."""
    waste_types = parsed.get("waste_types", ["general"])
    matched = []
    for wt in waste_types:
        rows = waste_df[waste_df["waste_type"] == wt]
        if not rows.empty:
            matched.append(rows.iloc[0].to_dict())

    lines = []
    for w in matched:
        lines.append(
            f"  • {w['display_name']}: Risk={w['risk_level']}, "
            f"Marine={w['marine_pollution_risk']}, Land={w['land_pollution_risk']}, "
            f"Disposal={w['recommended_disposal']}"
        )
    classification_text = "\n".join(lines) if lines else "  • General waste — standard protocols"

    trace_text = (
        f"[Antigravity Orchestration Trace]\n"
        f"Step 2: Waste Classification\n"
        f"Waste Types Detected: {', '.join(waste_types)}\n"
        f"Risk Assessment:\n{classification_text}\n"
        f"Job Complexity: {parsed.get('job_complexity', 'basic').title()}\n"
        f"Complexity Reason: {parsed.get('complexity_reason', 'Standard conditions')}\n"
        f"Environmental Impact: Proper disposal prevents marine/land pollution."
    )
    _add_trace("Step 2: Waste Classification", trace_text)
    return matched


def step_rank_providers(parsed: Dict[str, Any], providers_df: pd.DataFrame) -> pd.DataFrame:
    """Step 3: Multi-factor provider ranking."""
    ranked = rank_providers(providers_df, parsed)
    top3 = ranked.head(3)

    selected = top3.iloc[0]
    rejected_lines = []
    for _, row in top3.iloc[1:].iterrows():
        fl = row.get("factor_labels", {})
        weak = sorted(row.get("factor_scores", {}).items(), key=lambda x: x[1])[:2]
        reasons = "; ".join(fl.get(f, f) for f, _ in weak)
        rejected_lines.append(
            f"  Rejected:  {row['provider_name']} (Score: {row['total_score']:.4f})\n"
            f"  Reason:    {reasons}"
        )

    fl = selected.get("factor_labels", {})
    selected_pros = [
        f"  ✅ {fl.get(f, f)}"
        for f, s in sorted(selected.get("factor_scores", {}).items(), key=lambda x: x[1], reverse=True)[:5]
        if s >= 0.75
    ]

    trace_text = (
        f"[Antigravity Orchestration Trace]\n"
        f"Step 3: Provider Ranking\n"
        f"Total Providers Evaluated: {len(ranked)}\n"
        f"Ranking Factors (13): specialization, certification, reliability, on-time, rating, "
        f"review recency, capacity, distance, cancellation rate, complaint rate, eco score, "
        f"price, complexity match\n\n"
        f"Selected Provider:  {selected['provider_name']} (Score: {selected['total_score']:.4f})\n"
        + "\n".join(selected_pros) + "\n\n"
        + "\n".join(rejected_lines) + "\n\n"
        f"Note: Closest provider not always ranked #1. "
        f"Certification, reliability, and specialization outweigh proximity for safety-critical waste."
    )
    _add_trace("Step 3: Provider Ranking", trace_text, {"top_provider": selected["provider_name"]})
    return ranked


def step_price(parsed: Dict[str, Any], provider: Dict, booking_count: int = 0) -> Dict[str, Any]:
    """Step 4: Dynamic pricing calculation."""
    breakdown = calculate_price(provider, parsed, booking_count)

    trace_text = (
        f"[Antigravity Orchestration Trace]\n"
        f"Step 4: Dynamic Pricing\n"
        f"Provider:           {provider.get('provider_name', 'Unknown')}\n"
        f"Base Fee:           PKR {breakdown['base_fee']:,.0f}\n"
        f"Quantity Fee:       PKR {breakdown['quantity_fee']:,.0f} "
        f"({parsed.get('quantity_kg', 0):.0f} kg × PKR {provider.get('price_per_kg', 0)}/kg)\n"
        f"Urgency Fee:        PKR {breakdown['urgency_fee']:,.0f} "
        f"(×{breakdown['urgency_multiplier']} for {parsed.get('urgency', 'today')})\n"
        f"Distance Fee:       PKR {breakdown['distance_fee']:,.0f} "
        f"({provider.get('distance_km', 0)} km × PKR 35)\n"
        f"Risk Handling Fee:  PKR {breakdown['risk_handling_fee']:,.0f}\n"
        f"Complexity Fee:     PKR {breakdown['complexity_fee']:,.0f}\n"
        f"Surge Fee:          PKR {breakdown['surge_fee']:,.0f} ({breakdown['surge_label']})\n"
        f"Eco Discount:       PKR {abs(breakdown['eco_discount']):,.0f} "
        f"(Eco score: {provider.get('eco_score', 0)}/100)\n"
        f"Loyalty Discount:   PKR {abs(breakdown['loyalty_discount']):,.0f} "
        f"({breakdown['loyalty_label']})\n"
        f"─────────────────────────────────────────\n"
        f"Total Quote:        PKR {breakdown['total']:,.0f}\n"
        f"Provider Earnings:  PKR {breakdown['provider_earnings']:,.0f} (90%)\n"
        f"Platform Fee:       PKR {breakdown['platform_fee']:,.0f} (10%)\n"
        f"\n{breakdown['fairness_explanation']}"
    )
    _add_trace("Step 4: Dynamic Pricing", trace_text, {"total_pkr": breakdown["total"]})
    return breakdown


def step_schedule(
    parsed: Dict[str, Any],
    provider: Dict,
    bookings_df: pd.DataFrame
) -> tuple:
    """Step 5: Scheduling and booking."""
    slot, slot_msg = find_available_slot(provider, parsed, bookings_df)

    if slot is None:
        trace_text = (
            f"[Antigravity Orchestration Trace]\n"
            f"Step 5: Scheduling\n"
            f"Provider: {provider.get('provider_name')}\n"
            f"Outcome: ⛔ No available slots in next 48 hours.\n"
            f"Action: Hospital added to waitlist. Next available provider suggested.\n"
            f"Fallback: System will auto-notify when slot opens."
        )
        _add_trace("Step 5: Scheduling (Waitlisted)", trace_text)
        return None, slot_msg

    trace_text = (
        f"[Antigravity Orchestration Trace]\n"
        f"Step 5: Scheduling\n"
        f"Provider:         {provider.get('provider_name')}\n"
        f"Requested Slot:   {parsed.get('preferred_time', 'Not specified')}\n"
        f"Scheduled Slot:   {slot}\n"
        f"Status:           {slot_msg}\n"
        f"Duration Est.:    ~{_duration_est(parsed)} minutes\n"
        f"Travel Buffer:    {provider.get('travel_time_min', 30)} min included\n"
        f"Double-booking:   Check passed ✅"
    )
    _add_trace("Step 5: Scheduling", trace_text, {"scheduled_time": slot})
    return slot, slot_msg


def step_confirm_booking(
    parsed: Dict[str, Any],
    provider: Dict,
    breakdown: Dict,
    slot: str,
    bookings_df: pd.DataFrame
) -> tuple:
    """Step 6: Create and confirm booking."""
    booking, updated_df = create_booking(parsed, provider, breakdown, slot, bookings_df)
    notifications = simulate_notifications(booking, provider)
    notif_text = "\n".join(f"  {n}" for n in notifications)

    trace_text = (
        f"[Antigravity Orchestration Trace]\n"
        f"Step 6: Booking Confirmation\n"
        f"Booking ID:       {booking['booking_id']}\n"
        f"QR Tracking ID:   {booking['qr_tracking_id']}\n"
        f"Provider:         {provider.get('provider_name')}\n"
        f"Scheduled:        {booking['scheduled_time']}\n"
        f"Total:            PKR {booking['total_price_pkr']:,.0f}\n"
        f"Payment:          {booking['payment_status'].upper()}\n"
        f"Certificate:      Required (pending after service)\n"
        f"\nNotifications Sent:\n{notif_text}"
    )
    _add_trace("Step 6: Booking Confirmation", trace_text, {"booking_id": booking["booking_id"]})
    return booking, updated_df


def step_service_tracking(booking: Dict, provider: Dict) -> List[str]:
    """Step 7: Service tracking milestones."""
    milestones = [
        f"✅ Provider Assigned: {provider.get('provider_name')} | Vehicle: {provider.get('vehicle_type')}",
        f"🚗 Provider En Route — ETA: {provider.get('travel_time_min', 30)} minutes",
        f"📦 Waste Bags Sealed at Source — QR: {booking.get('qr_tracking_id')}",
        f"🔒 Waste Loaded into Biohazard Vehicle — Chain of Custody Started",
        f"🏭 Waste Delivered to Treatment Facility",
        f"♻️  Treatment/Disposal Completed",
        f"📄 Disposal Certificate Uploaded to Portal",
        f"✅ Service Completed — Rating prompt sent to Hospital",
    ]
    trace_text = (
        f"[Antigravity Orchestration Trace]\n"
        f"Step 7: Service Tracking\n"
        f"Booking:   {booking.get('booking_id')}\n"
        f"Milestones Logged:\n" +
        "\n".join(f"  {m}" for m in milestones) + "\n"
        f"\nEvidence: Photo/Video placeholders created in disposal record.\n"
        f"GPS trail stored for audit purposes."
    )
    _add_trace("Step 7: Service Tracking", trace_text)
    return milestones


def step_feedback(booking: Dict, rating: float, review: str, provider: Dict) -> Dict:
    """Step 8: Process feedback and update reputation."""
    old_rating = float(provider.get("rating", 4.0))
    # Simple moving average update
    total_reviews = 50  # mock
    new_rating = round(
        (old_rating * total_reviews + rating) / (total_reviews + 1), 2
    )

    impact = "increased" if rating > old_rating else ("unchanged" if rating == old_rating else "decreased")

    trace_text = (
        f"[Antigravity Orchestration Trace]\n"
        f"Step 8: Feedback & Reputation Update\n"
        f"Booking:       {booking.get('booking_id')}\n"
        f"Rating Given:  {rating}/5.0\n"
        f"Review:        \"{review}\"\n"
        f"Provider Old Rating: {old_rating}/5.0\n"
        f"Provider New Rating: {new_rating}/5.0 (rating {impact})\n"
        f"Matching Impact: {'Positive — provider stays in top tier' if rating >= 4.0 else 'Negative — ranking score reduced'}\n"
        f"Future Behavior: Provider will {'be prioritized' if rating >= 4.5 else 'be monitored'} in next matches."
    )
    _add_trace("Step 8: Feedback & Reputation", trace_text)

    return {
        "old_rating": old_rating,
        "new_rating": new_rating,
        "rating_change": round(new_rating - old_rating, 3),
        "impact": impact,
    }


def step_dispute(booking: Dict, dispute_type: str, description: str, provider_name: str) -> Dict:
    """Step 9: Dispute handling."""
    dispute = raise_dispute(booking, dispute_type, description)
    trace_text = get_dispute_trace(dispute, provider_name)
    _add_trace("Step 9: Dispute & Escalation", trace_text, {"severity": dispute["severity"]})
    return dispute


# ─── FULL PIPELINE ─────────────────────────────────────────────────────────────

def run_full_pipeline(
    raw_input: str,
    providers_df: pd.DataFrame,
    waste_df: pd.DataFrame,
    bookings_df: pd.DataFrame,
    booking_count: int = 0,
) -> Dict[str, Any]:
    """
    Run complete Antigravity orchestration pipeline and return all artifacts.
    """
    clear_traces()

    parsed      = step_parse(raw_input)
    waste_info  = step_classify_waste(parsed, waste_df)
    ranked      = step_rank_providers(parsed, providers_df)
    top_provider = ranked.iloc[0].to_dict()
    breakdown   = step_price(parsed, top_provider, booking_count)
    slot, slot_msg = step_schedule(parsed, top_provider, bookings_df)

    booking = None
    updated_df = bookings_df
    if slot:
        booking, updated_df = step_confirm_booking(
            parsed, top_provider, breakdown, slot, bookings_df
        )

    return {
        "parsed":        parsed,
        "waste_info":    waste_info,
        "ranked":        ranked,
        "top_provider":  top_provider,
        "breakdown":     breakdown,
        "slot":          slot,
        "slot_msg":      slot_msg,
        "booking":       booking,
        "bookings_df":   updated_df,
        "traces":        get_traces(),
    }


# helpers
def _duration_est(parsed: Dict) -> int:
    base = {"basic": 45, "intermediate": 75, "complex": 120, "critical": 180}
    return base.get(parsed.get("job_complexity", "basic"), 60)
