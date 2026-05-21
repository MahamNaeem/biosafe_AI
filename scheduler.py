"""
BioSafe AI - Scheduling Engine
Prevents double booking, manages waitlists, handles rescheduling
"""

import pandas as pd
import uuid
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple


# ─── SLOT GENERATION ─────────────────────────────────────────────────────────

def parse_slots(available_slots_str: str) -> List[str]:
    """Parse pipe-separated slot string into list."""
    return [s.strip() for s in str(available_slots_str).split("|") if s.strip()]


def get_base_date(urgency: str) -> str:
    """Determine target date from urgency."""
    today = datetime.now().date()
    if urgency == "immediate":
        return str(today)
    elif urgency == "today":
        return str(today)
    elif urgency == "tomorrow":
        return str(today + timedelta(days=1))
    else:
        return str(today + timedelta(days=2))


def build_datetime(date_str: str, time_str: str) -> datetime:
    return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")


# ─── CONFLICT CHECKER ─────────────────────────────────────────────────────────

def is_slot_booked(
    bookings_df: pd.DataFrame,
    provider_id: str,
    candidate_dt: datetime,
    duration_minutes: int = 90
) -> bool:
    """Check whether provider has an overlapping booking in this slot."""
    if bookings_df is None or bookings_df.empty:
        return False
    prov_bookings = bookings_df[
        (bookings_df["provider_id"] == provider_id) &
        (~bookings_df["status"].isin(["cancelled", "completed"]))
    ]
    for _, row in prov_bookings.iterrows():
        try:
            booked_dt = datetime.strptime(str(row["scheduled_time"]), "%Y-%m-%d %H:%M")
            booked_end = booked_dt + timedelta(minutes=duration_minutes + 30)  # +30 buffer
            candidate_end = candidate_dt + timedelta(minutes=duration_minutes)
            # Overlap check
            if not (candidate_end <= booked_dt or candidate_dt >= booked_end):
                return True
        except Exception:
            continue
    return False


# ─── SLOT FINDER ─────────────────────────────────────────────────────────────

def find_available_slot(
    provider: Dict[str, Any],
    parsed_request: Dict[str, Any],
    bookings_df: pd.DataFrame,
    preferred_time: Optional[str] = None
) -> Tuple[Optional[str], str]:
    """
    Returns (datetime_string, status_message)
    status: "confirmed" | "alternate_slot" | "waitlisted"
    """
    urgency    = parsed_request.get("urgency", "today")
    pref_time  = preferred_time or parsed_request.get("preferred_time", "09:00")
    base_date  = get_base_date(urgency)
    slots      = parse_slots(provider.get("available_slots", "09:00|13:00|16:00"))
    duration   = _estimate_duration(parsed_request)
    buffer     = int(provider.get("travel_time_min", 30))

    # Try preferred time first
    try:
        candidate_dt = build_datetime(base_date, pref_time)
        if not is_slot_booked(bookings_df, provider["provider_id"], candidate_dt, duration):
            return (
                candidate_dt.strftime("%Y-%m-%d %H:%M"),
                f"✅ Preferred slot {pref_time} on {base_date} is available."
            )
    except Exception:
        pass

    # Try all available slots
    for slot in slots:
        try:
            candidate_dt = build_datetime(base_date, slot)
            if not is_slot_booked(bookings_df, provider["provider_id"], candidate_dt, duration):
                return (
                    candidate_dt.strftime("%Y-%m-%d %H:%M"),
                    f"ℹ️ Preferred slot unavailable. Alternate slot suggested: {slot} on {base_date}."
                )
        except Exception:
            continue

    # Try next day
    next_date = str((datetime.strptime(base_date, "%Y-%m-%d") + timedelta(days=1)).date())
    for slot in slots:
        try:
            candidate_dt = build_datetime(next_date, slot)
            if not is_slot_booked(bookings_df, provider["provider_id"], candidate_dt, duration):
                return (
                    candidate_dt.strftime("%Y-%m-%d %H:%M"),
                    f"⏭️ No slots today. Next available: {slot} on {next_date}."
                )
        except Exception:
            continue

    return None, "⛔ No slots available in next 48 hours. Added to waitlist."


def _estimate_duration(parsed_request: Dict) -> int:
    """Estimate job duration in minutes."""
    complexity = parsed_request.get("job_complexity", "basic")
    qty = float(parsed_request.get("quantity_kg", 50))
    base = {"basic": 45, "intermediate": 75, "complex": 120, "critical": 180}
    minutes = base.get(complexity, 60)
    if qty > 150:
        minutes += 30
    return minutes


# ─── BOOKING CREATOR ──────────────────────────────────────────────────────────

def create_booking(
    parsed_request: Dict[str, Any],
    provider: Dict[str, Any],
    price_breakdown: Dict[str, Any],
    scheduled_time: str,
    bookings_df: pd.DataFrame
) -> Tuple[Dict[str, Any], pd.DataFrame]:
    """
    Create a new booking record, append to bookings_df, return booking + updated df.
    """
    booking_id   = f"B{random.randint(100,999)}"
    qr_id        = f"QR-{datetime.now().strftime('%Y%m%d%H%M%S')}-{booking_id}"

    booking = {
        "booking_id":      booking_id,
        "request_id":      parsed_request.get("request_id", "REQ-UNKNOWN"),
        "hospital_name":   parsed_request.get("location", "Hospital"),
        "department":      parsed_request.get("department", "General Ward"),
        "provider_id":     provider.get("provider_id", "P000"),
        "waste_type":      "|".join(parsed_request.get("waste_types", ["general"])),
        "quantity_kg":     parsed_request.get("quantity_kg", 50),
        "scheduled_time":  scheduled_time,
        "status":          "confirmed",
        "total_price_pkr": price_breakdown.get("total", 0),
        "urgency":         parsed_request.get("urgency", "today"),
        "qr_tracking_id":  qr_id,
        "payment_status":  "paid",
        "certificate_issued": "pending",
        "created_at":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Append to DataFrame
    new_row = pd.DataFrame([booking])
    updated_df = pd.concat([bookings_df, new_row], ignore_index=True)

    return booking, updated_df


# ─── RESCHEDULING ─────────────────────────────────────────────────────────────

def reschedule_booking(
    booking: Dict[str, Any],
    next_best_provider: Dict[str, Any],
    parsed_request: Dict[str, Any],
    bookings_df: pd.DataFrame,
    reason: str = "Provider cancelled"
) -> Tuple[Dict[str, Any], str]:
    """
    Handle provider cancellation by finding next available slot/provider.
    Returns (new booking dict, trace message)
    """
    new_slot, slot_msg = find_available_slot(
        next_best_provider, parsed_request, bookings_df
    )

    trace = (
        f"🔄 Rescheduling triggered — Reason: {reason}\n"
        f"  Original Provider: {booking.get('provider_id')}\n"
        f"  New Provider: {next_best_provider.get('provider_id')} — "
        f"{next_best_provider.get('provider_name')}\n"
        f"  {slot_msg}\n"
        f"  Hospital notified via WhatsApp.\n"
        f"  Updated calendar entry sent."
    )

    new_booking = dict(booking)
    new_booking["provider_id"]    = next_best_provider.get("provider_id")
    new_booking["scheduled_time"] = new_slot or "TBD — awaiting confirmation"
    new_booking["status"]         = "rescheduled"

    return new_booking, trace


# ─── NOTIFICATION SIMULATOR ───────────────────────────────────────────────────

def simulate_notifications(booking: Dict[str, Any], provider: Dict[str, Any]) -> List[str]:
    """Return list of simulated notification actions."""
    return [
        f"📱 WhatsApp sent to Hospital: 'Booking {booking['booking_id']} confirmed for {booking['scheduled_time']}'",
        f"📱 SMS sent to Provider ({provider.get('provider_name', 'Provider')}): 'New pickup assignment. QR: {booking['qr_tracking_id']}'",
        f"📅 Calendar invite created for {booking['scheduled_time']}",
        f"🧾 Receipt generated: PKR {booking['total_price_pkr']:,.0f} — Booking {booking['booking_id']}",
        f"🗄️ Booking record saved to database (bookings.csv updated)",
        f"🔔 Disposal certificate reminder scheduled 24h post-pickup",
    ]
