"""
BioSafe AI — Streamlit App
Mobile-responsive, 9-tab UI for biohazard waste service orchestration
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BioSafe AI",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── MOBILE-RESPONSIVE CSS ────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Global ── */
html, body, [class*="css"] {
    font-family: 'Segoe UI', sans-serif;
}
.block-container { padding: 1rem 1rem 2rem; max-width: 900px; }

/* ── Header banner ── */
.bio-header {
    background: linear-gradient(135deg, #0f4c75 0%, #1b6ca8 60%, #16a085 100%);
    color: white;
    padding: 1.2rem 1.5rem;
    border-radius: 12px;
    margin-bottom: 1.2rem;
    text-align: center;
}
.bio-header h1 { font-size: 1.8rem; margin: 0; }
.bio-header p  { font-size: 0.9rem; margin: 0.3rem 0 0; opacity: 0.85; }

/* ── Metric cards ── */
.metric-row { display: flex; gap: 0.6rem; flex-wrap: wrap; margin-bottom: 1rem; }
.metric-card {
    flex: 1 1 100px;
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    padding: 0.7rem 0.5rem;
    text-align: center;
    box-shadow: 0 2px 6px rgba(0,0,0,0.07);
}
.metric-card .val { font-size: 1.4rem; font-weight: 700; color: #1b6ca8; }
.metric-card .lbl { font-size: 0.72rem; color: #777; }

/* ── Info / alert boxes ── */
.info-box {
    background: #e8f4fd; border-left: 4px solid #1b6ca8;
    border-radius: 6px; padding: 0.8rem 1rem; margin: 0.6rem 0;
}
.success-box {
    background: #e8f8f5; border-left: 4px solid #16a085;
    border-radius: 6px; padding: 0.8rem 1rem; margin: 0.6rem 0;
}
.warn-box {
    background: #fef9e7; border-left: 4px solid #f39c12;
    border-radius: 6px; padding: 0.8rem 1rem; margin: 0.6rem 0;
}
.danger-box {
    background: #fdedec; border-left: 4px solid #e74c3c;
    border-radius: 6px; padding: 0.8rem 1rem; margin: 0.6rem 0;
}

/* ── Provider card ── */
.provider-card {
    background: white;
    border: 1px solid #d5e8f5;
    border-radius: 10px;
    padding: 1rem;
    margin: 0.5rem 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
}
.provider-card .rank-badge {
    background: #1b6ca8; color: white;
    border-radius: 50%; width: 28px; height: 28px;
    display: inline-flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.85rem;
}

/* ── Trace box ── */
.trace-box {
    background: #0d1117;
    color: #58a6ff;
    font-family: 'Courier New', monospace;
    font-size: 0.78rem;
    border-radius: 8px;
    padding: 1rem;
    white-space: pre-wrap;
    overflow-x: auto;
    margin: 0.5rem 0;
    border: 1px solid #30363d;
}

/* ── QR badge ── */
.qr-badge {
    background: #1b6ca8; color: white;
    border-radius: 8px; padding: 0.6rem 1.2rem;
    font-family: monospace; font-size: 0.85rem;
    display: inline-block; margin: 0.4rem 0;
}

/* ── Milestone list ── */
.milestone {
    padding: 0.4rem 0.6rem;
    border-left: 3px solid #16a085;
    margin: 0.3rem 0;
    background: #f0faf7;
    border-radius: 0 6px 6px 0;
    font-size: 0.88rem;
}

/* ── Score bar ── */
.score-bar-wrap { background: #e9ecef; border-radius: 4px; height: 8px; margin: 2px 0; }
.score-bar { background: #1b6ca8; height: 8px; border-radius: 4px; }

/* ── Responsive columns ── */
@media (max-width: 600px) {
    .bio-header h1 { font-size: 1.3rem; }
    .metric-card .val { font-size: 1.1rem; }
    .block-container { padding: 0.5rem; }
}
</style>
""", unsafe_allow_html=True)


# ─── DATA LOADERS ─────────────────────────────────────────────────────────────

@st.cache_data
def load_providers():
    return pd.read_csv("data/providers.csv")

@st.cache_data
def load_waste_categories():
    return pd.read_csv("data/waste_categories.csv")

def load_bookings():
    return pd.read_csv("data/bookings.csv")

def load_disputes():
    return pd.read_csv("data/disputes.csv")


# ─── SESSION STATE INIT ───────────────────────────────────────────────────────

def init_state():
    defaults = {
        "parsed": None,
        "ranked": None,
        "breakdown": None,
        "booking": None,
        "waste_info": None,
        "top_provider": None,
        "slot": None,
        "slot_msg": None,
        "traces": [],
        "bookings_df": None,
        "tab_unlock": 0,
        "feedback_done": False,
        "dispute_result": None,
        "tracking_milestones": None,
        "feedback_result": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ─── IMPORTS (after data dir confirmed) ───────────────────────────────────────
from orchestrator import (
    step_parse, step_classify_waste, step_rank_providers,
    step_price, step_schedule, step_confirm_booking,
    step_service_tracking, step_feedback, step_dispute,
    get_traces, clear_traces
)
from dispute import simulate_fallback_scenarios


# ─── HEADER ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="bio-header">
  <h1>🧬 BioSafe AI</h1>
  <p>AI-Powered Biohazard Waste Collection Orchestrator · Powered by Google Antigravity</p>
</div>
""", unsafe_allow_html=True)


# ─── TABS ─────────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "📝 1. Request",
    "🧠 2. AI Understanding",
    "☣️ 3. Classification",
    "🏆 4. Provider Ranking",
    "💰 5. Pricing",
    "📅 6. Scheduling",
    "🚗 7. Tracking",
    "⭐ 8. Feedback",
    "📡 9. Trace Logs",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — REQUEST INPUT
# ══════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.subheader("🏥 Submit Biohazard Waste Pickup Request")

    st.markdown('<div class="info-box">Supports <b>Urdu · Roman Urdu · English · Mixed</b> — just type naturally.</div>',
                unsafe_allow_html=True)

    # Sample request buttons
    st.caption("Quick sample requests:")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🩸 ICU Sharps (Roman Urdu)", use_container_width=True):
            st.session_state["_sample"] = "ICU se used syringes urgent pickup karwani hain, aaj hi chahiye"
        if st.button("💊 Pharmaceutical Waste", use_container_width=True):
            st.session_state["_sample"] = "Pharmacy mein expired medicines hain, kal morning disposal karwana hai"
    with col2:
        if st.button("🦠 Infectious Waste (OT)", use_container_width=True):
            st.session_state["_sample"] = "Operation theater se infectious waste uthwana hai, urgent hai"
        if st.button("🧪 English Request", use_container_width=True):
            st.session_state["_sample"] = "Need biohazard pickup from emergency department today, blood waste and sharps"

    sample_val = st.session_state.get("_sample", "")
    raw_input = st.text_area(
        "Describe your waste pickup need:",
        value=sample_val,
        height=100,
        placeholder="e.g., Ward 3 ka blood waste kal morning dispose karwana hai",
    )

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        hospital_name = st.text_input("🏥 Hospital Name", value="City Hospital Karachi")
    with col_b:
        contact = st.text_input("📱 Contact (WhatsApp)", value="+92-300-1234567")
    with col_c:
        booking_history = st.number_input("Previous Bookings (loyalty)", min_value=0, value=5)

    if st.button("🚀 Submit Request to BioSafe AI", type="primary", use_container_width=True):
        if not raw_input.strip():
            st.error("Please enter a service request description.")
        else:
            with st.spinner("🤖 Antigravity processing your request..."):
                providers_df = load_providers()
                waste_df     = load_waste_categories()
                bookings_df  = load_bookings()
                if st.session_state["bookings_df"] is not None:
                    bookings_df = st.session_state["bookings_df"]

                clear_traces()

                parsed    = step_parse(raw_input)
                waste_info = step_classify_waste(parsed, waste_df)
                ranked    = step_rank_providers(parsed, providers_df)
                top       = ranked.iloc[0].to_dict()
                breakdown = step_price(parsed, top, int(booking_history))
                slot, slot_msg = step_schedule(parsed, top, bookings_df)

                booking = None
                if slot:
                    booking, bookings_df = step_confirm_booking(
                        parsed, top, breakdown, slot, bookings_df
                    )

                st.session_state.update({
                    "parsed":       parsed,
                    "waste_info":   waste_info,
                    "ranked":       ranked,
                    "top_provider": top,
                    "breakdown":    breakdown,
                    "slot":         slot,
                    "slot_msg":     slot_msg,
                    "booking":      booking,
                    "bookings_df":  bookings_df,
                    "traces":       get_traces(),
                    "tab_unlock":   1,
                    "feedback_done":      False,
                    "dispute_result":     None,
                    "tracking_milestones":None,
                    "feedback_result":    None,
                    "_sample": raw_input,
                })

            st.success("✅ Request processed! Navigate through tabs to see results.")
            st.markdown(f"""
<div class="success-box">
  <b>Request ID:</b> {parsed['request_id']}<br>
  <b>Language Detected:</b> {parsed['language']} ({parsed['confidence']:.0%} confidence)<br>
  <b>Waste Types:</b> {', '.join(parsed['waste_types'])}<br>
  <b>Complexity:</b> {parsed['job_complexity'].title()}<br>
  <b>Urgency:</b> {parsed['urgency'].title()}
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — AI UNDERSTANDING
# ══════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.subheader("🧠 AI Intent Understanding")
    p = st.session_state.get("parsed")
    if p is None:
        st.info("Submit a request in Tab 1 first.")
    else:
        conf = p["confidence"]
        conf_color = "#16a085" if conf >= 0.85 else ("#f39c12" if conf >= 0.75 else "#e74c3c")

        st.markdown(f"""
<div class="metric-row">
  <div class="metric-card"><div class="val" style="color:{conf_color}">{conf:.0%}</div><div class="lbl">Confidence</div></div>
  <div class="metric-card"><div class="val">{p['language'].split('+')[0].strip()}</div><div class="lbl">Language</div></div>
  <div class="metric-card"><div class="val">{p['job_complexity'].title()}</div><div class="lbl">Complexity</div></div>
  <div class="metric-card"><div class="val">{p['urgency'].title()}</div><div class="lbl">Urgency</div></div>
  <div class="metric-card"><div class="val">{p['quantity_kg']} kg</div><div class="lbl">Est. Quantity</div></div>
</div>
""", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Extracted Information**")
            fields = {
                "Request ID": p["request_id"],
                "Language": p["language"],
                "Service Type": p["service_type"],
                "Waste Types": ", ".join(p["waste_types"]),
                "Department": p["department"],
                "Location": p["location"],
                "Urgency": p["urgency"].title(),
                "Preferred Time": p["preferred_time"],
                "Quantity (est.)": f"{p['quantity_kg']} kg",
                "Job Complexity": p["job_complexity"].title(),
            }
            for k, v in fields.items():
                st.markdown(f"**{k}:** {v}")

        with col2:
            st.markdown("**Special Requirements**")
            for req in p.get("special_requirements", []):
                st.markdown(f"• {req}")

            if p.get("confirmation_questions"):
                st.markdown('<div class="warn-box"><b>⚠️ Low Confidence — Clarification Needed:</b></div>',
                            unsafe_allow_html=True)
                for q in p["confirmation_questions"]:
                    st.markdown(f"❓ {q}")

        st.markdown("**Complexity Assessment**")
        st.markdown(f'<div class="info-box">{p["complexity_reason"]}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — WASTE CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.subheader("☣️ Waste Classification & Risk Assessment")
    wi = st.session_state.get("waste_info")
    p  = st.session_state.get("parsed")
    if wi is None or p is None:
        st.info("Submit a request in Tab 1 first.")
    else:
        risk_colors = {
            "Critical": "#e74c3c", "Very High": "#c0392b",
            "High": "#e67e22",     "Medium": "#f39c12",
            "Low": "#27ae60",
        }

        for w in wi:
            rc = risk_colors.get(w.get("risk_level", "Medium"), "#999")
            st.markdown(f"""
<div class="provider-card">
  <b style="font-size:1rem">{w.get('display_name','Waste')}</b>
  <span style="background:{rc};color:white;border-radius:12px;padding:2px 10px;font-size:0.78rem;margin-left:8px">
    {w.get('risk_level','?')} Risk
  </span>
  <br><br>
  <table style="width:100%;font-size:0.85rem">
    <tr><td>🔄 Reuse Risk</td><td><b>{w.get('reuse_risk','?')}</b></td>
        <td>🦠 Disease Risk</td><td><b>{w.get('disease_risk','?')}</b></td></tr>
    <tr><td>🌊 Marine Risk</td><td><b>{w.get('marine_pollution_risk','?')}</b></td>
        <td>🌱 Land Risk</td><td><b>{w.get('land_pollution_risk','?')}</b></td></tr>
    <tr><td colspan="2">♻️ Disposal Method</td><td colspan="2"><b>{w.get('recommended_disposal','?')}</b></td></tr>
  </table>
  <div style="margin-top:0.5rem;font-size:0.8rem;color:#555">
    📝 {w.get('handling_notes','')}
  </div>
</div>
""", unsafe_allow_html=True)

        if not wi:
            st.warning("No specific waste category matched. Treating as general hospital waste.")
            st.markdown('<div class="info-box">General hospital waste → Municipal disposal + partial recycling.</div>',
                        unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**🌍 Environmental Impact Note**")
        st.markdown("""
<div class="info-box">
Proper biohazard waste disposal prevents:<br>
• <b>AIDS/Hepatitis B&C</b> from discarded sharps and blood waste<br>
• <b>Antibiotic Resistance</b> from pharmaceutical waste in water systems<br>
• <b>Marine Pollution</b> — plastic and chemical waste dumped near coastlines<br>
• <b>Land Contamination</b> from pathological waste in open dumps<br>
BioSafe AI ensures every pickup generates a verifiable disposal certificate.
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — PROVIDER RANKING
# ══════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.subheader("🏆 Provider Ranking (13-Factor Algorithm)")
    ranked = st.session_state.get("ranked")
    if ranked is None:
        st.info("Submit a request in Tab 1 first.")
    else:
        top = st.session_state["top_provider"]

        st.markdown(f"""
<div class="success-box">
  <b>🥇 Recommended Provider: {top['provider_name']}</b><br>
  Score: <b>{top['total_score']:.4f}</b> · Rating: <b>{top['rating']}/5.0</b> ·
  Distance: <b>{top['distance_km']} km</b> · Certification: <b>{top['certification']}</b>
</div>
""", unsafe_allow_html=True)

        st.caption("All 13 ranking factors with weights shown")
        from ranking import FACTOR_WEIGHTS
        factor_disp = {
            "specialization_match": "Specialization Match",
            "certification_score": "Certification",
            "reliability_score": "Reliability",
            "on_time_score": "On-Time Score",
            "rating_score": "Rating",
            "review_recency": "Review Recency",
            "capacity_score": "Capacity",
            "distance_score": "Distance",
            "cancellation_penalty": "Low Cancellation",
            "complaint_penalty": "Low Complaints",
            "eco_score": "Eco Score",
            "price_competitiveness": "Price",
            "complexity_match": "Complexity Match",
        }

        for idx, row in ranked.head(5).iterrows():
            rank_icon = ["🥇","🥈","🥉","4️⃣","5️⃣"][idx] if idx < 5 else f"#{idx+1}"
            is_top = idx == 0
            border = "2px solid #1b6ca8" if is_top else "1px solid #ddd"

            factor_scores = row.get("factor_scores", {})
            factor_labels = row.get("factor_labels", {})

            score_bars = ""
            for fk, fname in list(factor_disp.items())[:6]:
                s = factor_scores.get(fk, 0)
                pct = int(s * 100)
                score_bars += f"""
<div style="margin:3px 0">
  <div style="display:flex;justify-content:space-between;font-size:0.72rem">
    <span>{fname}</span><span>{pct}%</span>
  </div>
  <div class="score-bar-wrap"><div class="score-bar" style="width:{pct}%"></div></div>
</div>"""

            with st.expander(
                f"{rank_icon} {row['provider_name']}  |  Score: {row['total_score']:.4f}  |  {row['distance_km']} km  |  ⭐ {row['rating']}",
                expanded=is_top
            ):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"""
**Location:** {row['location']}  
**Vehicle:** {row['vehicle_type']}  
**Certification:** {row['certification']}  
**Slots:** {row['available_slots']}  
**Price:** PKR {row['price_per_kg']}/kg + PKR {row['base_fee']} base  
**Eco Score:** {row['eco_score']}/100  
""")
                with c2:
                    st.markdown(score_bars, unsafe_allow_html=True)

                st.markdown(f"**Why ranked #{idx+1}:** {row.get('recommendation','')}")

                if not is_top and idx <= 2:
                    st.markdown(f"""
<div class="warn-box">
  <b>Why not #1:</b> Lower score on one or more critical factors
  (specialization, certification, or reliability) compared to {ranked.iloc[0]['provider_name']}.
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — DYNAMIC PRICING
# ══════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    st.subheader("💰 Dynamic Pricing Breakdown")
    bd = st.session_state.get("breakdown")
    p  = st.session_state.get("parsed")
    top = st.session_state.get("top_provider")
    if bd is None:
        st.info("Submit a request in Tab 1 first.")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Quote", f"PKR {bd['total']:,.0f}")
        col2.metric("Provider Earns", f"PKR {bd['provider_earnings']:,.0f}")
        col3.metric("Platform Fee", f"PKR {bd['platform_fee']:,.0f}")

        st.markdown("**Price Breakdown**")

        price_items = [
            ("Base Fee",           bd["base_fee"],          "Fixed mobilization fee for certified provider"),
            ("Quantity Fee",       bd["quantity_fee"],       f"{p.get('quantity_kg',0):.0f} kg × PKR {top.get('price_per_kg',0)}/kg"),
            ("Urgency Fee",        bd["urgency_fee"],        f"×{bd['urgency_multiplier']} for {p.get('urgency','today')} pickup"),
            ("Distance Fee",       bd["distance_fee"],       f"{top.get('distance_km',0)} km × PKR 35/km"),
            ("Risk Handling Fee",  bd["risk_handling_fee"],  "WHO-standard safety protocols for waste type"),
            ("Complexity Fee",     bd["complexity_fee"],     f"{p.get('job_complexity','basic').title()} complexity handling"),
            ("Surge Fee",          bd["surge_fee"],          bd["surge_label"]),
        ]
        discount_items = [
            ("Eco Discount",     bd["eco_discount"],     f"Eco-certified provider ({top.get('eco_score',0)}/100)"),
            ("Loyalty Discount", bd["loyalty_discount"], bd["loyalty_label"]),
        ]

        for label, amount, note in price_items:
            if amount > 0:
                col_l, col_r = st.columns([3, 1])
                col_l.markdown(f"**{label}** — *{note}*")
                col_r.markdown(f"PKR {amount:,.0f}")

        for label, amount, note in discount_items:
            if amount < 0:
                col_l, col_r = st.columns([3, 1])
                col_l.markdown(f"**{label}** ✅ — *{note}*")
                col_r.markdown(f"<span style='color:green'>− PKR {abs(amount):,.0f}</span>", unsafe_allow_html=True)

        st.markdown("---")
        col_l, col_r = st.columns([3, 1])
        col_l.markdown("### **Total Payable**")
        col_r.markdown(f"### **PKR {bd['total']:,.0f}**")

        st.markdown("---")
        st.markdown(f'<div class="info-box">{bd["fairness_explanation"]}</div>', unsafe_allow_html=True)

        # Comparison table
        st.markdown("**Price Comparison — Top 3 Providers**")
        ranked = st.session_state.get("ranked")
        if ranked is not None:
            comp_rows = []
            for _, row in ranked.head(3).iterrows():
                est = float(row["base_fee"]) + float(p.get("quantity_kg", 50)) * float(row["price_per_kg"])
                comp_rows.append({
                    "Provider": row["provider_name"],
                    "Base Fee (PKR)": int(row["base_fee"]),
                    "Rate/kg (PKR)": float(row["price_per_kg"]),
                    "Est. Total (PKR)": int(est),
                    "Eco Score": int(row["eco_score"]),
                    "Rank Score": f"{row['total_score']:.4f}",
                })
            st.dataframe(pd.DataFrame(comp_rows), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — SCHEDULING & BOOKING
# ══════════════════════════════════════════════════════════════════════════════
with tabs[5]:
    st.subheader("📅 Scheduling & Booking Confirmation")
    booking = st.session_state.get("booking")
    slot    = st.session_state.get("slot")
    slot_msg = st.session_state.get("slot_msg", "")
    top     = st.session_state.get("top_provider")
    if booking is None and slot is None:
        st.info("Submit a request in Tab 1 first.")
    elif slot is None:
        st.warning(f"⛔ {slot_msg}")
        st.markdown('<div class="warn-box">Hospital added to waitlist. Auto-notification when slot opens.</div>',
                    unsafe_allow_html=True)
    else:
        if "waitlist" in slot_msg.lower() or slot_msg.startswith("⛔"):
            st.warning(slot_msg)
        elif "alternate" in slot_msg.lower() or slot_msg.startswith("ℹ️"):
            st.info(slot_msg)
        else:
            st.success(slot_msg)

        if booking:
            st.markdown(f"""
<div class="success-box">
  <b>✅ BOOKING CONFIRMED</b><br><br>
  <div class="qr-badge">🔖 QR: {booking.get('qr_tracking_id','N/A')}</div><br><br>
  <table style="width:100%;font-size:0.88rem">
    <tr><td>📋 Booking ID</td><td><b>{booking.get('booking_id')}</b></td>
        <td>🏥 Hospital</td><td><b>{booking.get('hospital_name')}</b></td></tr>
    <tr><td>🚗 Provider</td><td><b>{top.get('provider_name','?')}</b></td>
        <td>🏥 Department</td><td><b>{booking.get('department')}</b></td></tr>
    <tr><td>📅 Scheduled</td><td><b>{booking.get('scheduled_time')}</b></td>
        <td>💰 Total</td><td><b>PKR {booking.get('total_price_pkr',0):,.0f}</b></td></tr>
    <tr><td>💳 Payment</td><td><b>{booking.get('payment_status','?').upper()}</b></td>
        <td>📄 Certificate</td><td><b>{booking.get('certificate_issued','pending').upper()}</b></td></tr>
  </table>
</div>
""", unsafe_allow_html=True)

            st.markdown("**📲 Notifications Sent:**")
            from scheduler import simulate_notifications
            for notif in simulate_notifications(booking, top):
                st.markdown(f'<div class="milestone">{notif}</div>', unsafe_allow_html=True)

        # Fallback scenarios
        st.markdown("---")
        st.markdown("**⚙️ Robustness & Fallback Scenarios**")
        for fb in simulate_fallback_scenarios():
            with st.expander(f"🔧 {fb['scenario']}"):
                st.markdown(f"**Trigger:** {fb['trigger']}")
                st.markdown(f"**Action:** {fb['action']}")
                st.markdown(f'<div class="trace-box">TRACE: {fb["trace_label"]}</div>',
                            unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 — SERVICE TRACKING
# ══════════════════════════════════════════════════════════════════════════════
with tabs[6]:
    st.subheader("🚗 Service Tracking & Quality Loop")
    booking = st.session_state.get("booking")
    top     = st.session_state.get("top_provider")
    if booking is None:
        st.info("A confirmed booking is needed (Tab 6 first).")
    else:
        if st.button("▶️ Simulate Service Execution", use_container_width=True, type="primary"):
            milestones = step_service_tracking(booking, top)
            st.session_state["tracking_milestones"] = milestones
            st.session_state["traces"] = get_traces()

        milestones = st.session_state.get("tracking_milestones")
        if milestones:
            st.markdown("**📍 Service Progress Timeline:**")
            for m in milestones:
                st.markdown(f'<div class="milestone">{m}</div>', unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("**📸 Evidence Capture (Placeholders)**")
            col1, col2, col3 = st.columns(3)
            col1.metric("Photos", f"🖼️ 5 taken")
            col2.metric("Videos", f"🎥 1 recorded")
            col3.metric("Certificate", f"📄 Pending upload")

            # Provider workload optimization
            st.markdown("---")
            st.markdown("**📊 Provider-Side Optimization**")
            st.markdown("""
<div class="info-box">
<b>Workload Balancing:</b><br>
• Provider currently handling 2 other bookings today<br>
• Route grouped: 3 pickups in DHA/Clifton zone (efficient routing)<br>
• Capacity utilization: 62% (healthy — room for 2 more pickups)<br>
• Recommended next slot: 16:00 today or 09:00 tomorrow<br>
• Demand forecast: High demand expected Thursday–Friday (Fri hospital closure surge)
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 8 — FEEDBACK & DISPUTE
# ══════════════════════════════════════════════════════════════════════════════
with tabs[7]:
    st.subheader("⭐ Feedback & Dispute Resolution")
    booking = st.session_state.get("booking")
    top     = st.session_state.get("top_provider")
    if booking is None:
        st.info("Complete a booking first (Tab 6).")
    else:
        # ── Feedback form ──
        st.markdown("**Rate Your Service Experience**")
        rating = st.slider("Overall Rating", 1.0, 5.0, 4.5, 0.5)
        review = st.text_area("Write a review", placeholder="Service was on time, waste handled professionally...")

        col_f1, col_f2, col_f3 = st.columns(3)
        cat_timely  = col_f1.slider("Timeliness",       1, 5, 4)
        cat_safety  = col_f2.slider("Safety Protocol",  1, 5, 5)
        cat_cert    = col_f3.slider("Documentation",    1, 5, 4)

        if st.button("📤 Submit Feedback", use_container_width=True):
            result = step_feedback(booking, rating, review or "Good service.", top)
            st.session_state.update({"feedback_result": result, "feedback_done": True,
                                     "traces": get_traces()})

        if st.session_state.get("feedback_done"):
            fr = st.session_state["feedback_result"]
            delta = fr["rating_change"]
            delta_str = f"+{delta:.3f}" if delta >= 0 else f"{delta:.3f}"
            st.markdown(f"""
<div class="success-box">
  <b>✅ Feedback Submitted!</b><br>
  Provider Rating: {fr['old_rating']} → <b>{fr['new_rating']}</b> ({delta_str})<br>
  Impact: {fr['impact'].title()} — {'Top-tier provider maintained ✅' if fr['new_rating'] >= 4.5 else 'Monitoring triggered ⚠️'}
</div>
""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**🚨 Raise a Dispute**")

        dispute_type = st.selectbox("Dispute Type", [
            "no_show", "late_pickup", "cancellation", "quality_complaint",
            "price_disagreement", "qr_mismatch", "illegal_dumping",
            "certificate_missing", "overrun", "unsafe_handling",
            "wrong_disposal", "data_breach"
        ])
        dispute_desc = st.text_area("Describe the issue", placeholder="Provide details of the problem...")
        claimed_amt  = st.number_input("Claim Amount (PKR)", min_value=0, value=0)

        if st.button("⚡ Raise Dispute", type="primary", use_container_width=True):
            dispute = step_dispute(booking, dispute_type, dispute_desc, top.get("provider_name","?"))
            st.session_state["dispute_result"] = dispute
            st.session_state["traces"] = get_traces()

        dr = st.session_state.get("dispute_result")
        if dr:
            sev_cls = {"Low":"info-box","Medium":"warn-box","High":"danger-box","Critical":"danger-box"}.get(dr["severity"],"warn-box")
            blacklist_note = "<br>⛔ <b>Provider blacklisted from platform!</b>" if dr["blacklist_provider"] else ""
            authority_note = "<br>🚨 <b>EPA + Police notified!</b>" if dr["notify_authorities"] else ""
            st.markdown(f"""
<div class="{sev_cls}">
  <b>{dr['severity_icon']} {dr['severity'].upper()} DISPUTE — {dr['dispute_type'].replace('_',' ').title()}</b><br>
  Dispute ID: <b>{dr['dispute_id']}</b> · Status: <b>{dr['status'].upper()}</b><br><br>
  <b>Hospital Action:</b> {dr['hospital_action']}<br>
  <b>Provider Action:</b> {dr['provider_action']}<br><br>
  <b>Refund:</b> PKR {dr['refund_amount_pkr']:,.0f} |
  <b>Compensation:</b> PKR {dr['compensation_pkr']:,.0f} |
  <b>Total Relief:</b> PKR {dr['total_resolution_pkr']:,.0f}<br><br>
  <b>Escalation Path:</b> {' → '.join(dr['escalation_path'])}
  {blacklist_note}{authority_note}
</div>
""", unsafe_allow_html=True)

        # Existing disputes table
        st.markdown("---")
        st.markdown("**📋 Disputes History**")
        try:
            disputes_df = load_disputes()
            st.dataframe(
                disputes_df[["dispute_id","booking_id","dispute_type","severity","status","compensation_pkr"]],
                use_container_width=True, hide_index=True
            )
        except Exception:
            st.info("No dispute records found.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 9 — ANTIGRAVITY TRACE LOGS
# ══════════════════════════════════════════════════════════════════════════════
with tabs[8]:
    st.subheader("📡 Antigravity Orchestration Trace Logs")
    traces = st.session_state.get("traces", [])

    if not traces:
        st.info("Run a full request (Tab 1) to generate trace logs.")
        st.markdown("""
<div class="info-box">
<b>About Antigravity Traces:</b><br>
BioSafe AI uses Google Antigravity as the core agentic orchestrator. Every workflow step generates
a reasoning trace showing:<br>
• Language parsing confidence & entity extraction decisions<br>
• Waste classification rationale & risk scoring<br>
• Provider ranking rationale with factor-by-factor breakdown<br>
• Scheduling decisions & conflict resolution logic<br>
• Price logic with all multipliers shown<br>
• Booking confirmation actions<br>
• Fallback / escalation decisions<br>
• Dispute severity scoring and resolution reasoning
</div>
""", unsafe_allow_html=True)
    else:
        st.success(f"✅ {len(traces)} trace steps logged for this session")

        export_text = "\n\n" + "="*60 + "\n\n".join(
            f"[{t['timestamp']}]\n{t['content']}" for t in reversed(traces)
        )
        st.download_button(
            "📥 Export Full Trace Log (.txt)",
            data=export_text,
            file_name=f"biosafe_antigravity_trace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True,
        )

        for i, trace in enumerate(traces):
            with st.expander(
                f"🔍 {trace['step']} — {trace['timestamp']}",
                expanded=(i == 0)
            ):
                st.markdown(
                    f'<div class="trace-box">{trace["content"]}</div>',
                    unsafe_allow_html=True
                )

    # ── Static built-in trace example ──
    st.markdown("---")
    st.markdown("**📄 Built-in Example Trace (Full Demo Scenario)**")

    example_trace = """[Antigravity Orchestration Trace — Full Demo]
══════════════════════════════════════════════════

Step 1: Intent Understanding
Input:       ICU se used syringes urgent pickup karwani hain
Language:    Roman Urdu + English (Code-switched)
Confidence:  94%
Waste Type:  Sharps
Department:  ICU
Urgency:     Immediate
Complexity:  Critical
Requirements: Needle Destroyer, Sealed Transport, GPS Tracking

──────────────────────────────────────────────────

Step 2: Waste Classification
Type:              Sharps
Risk Level:        Critical
Disease Risk:      AIDS / Hepatitis B&C / Tetanus
Marine Risk:       High  |  Land Risk: High
Reuse Risk:        Very High (Must be destroyed)
Disposal Method:   Needle Destroyer + Incineration
Handling Note:     WHO yellow biohazard bag. Puncture-resistant container required.

──────────────────────────────────────────────────

Step 3: Provider Ranking
Providers Evaluated: 10
Algorithm: 13-factor weighted scoring

Selected:  HazardShield Inc (Score: 0.9412)
  ✅ Certified: WHO+EPA+ISO14001+OSHA (highest tier)
  ✅ Specialization: sharps|infectious|blood|pharmaceutical
  ✅ Reliability: 97%  |  On-time: 96%
  ✅ Sealed Biohazard Truck with GPS + Body Cam
  ✅ Low cancellation (1%) and complaint rate (0.5%)

Rejected:  GreenCycle Med
  ⚠️ ISO14001 only — no WHO/EPA for sharps
  ⚠️ Complaint rate 8% in last 30 days
  ⚠️ Standard Van — not suitable for ICU sharps

Note: Closest provider (P010, 1.9 km) ranked #2 due to slightly lower
certification match for critical sharps. Safety > proximity.

──────────────────────────────────────────────────

Step 4: Pricing
Base Fee:          PKR 2,000
Quantity Fee:      PKR 1,200  (80 kg × 15 PKR/kg)
Urgency Fee:       PKR 2,880  (×1.8 immediate)
Distance Fee:      PKR 157    (4.5 km × 35)
Risk Handling Fee: PKR 500    (sharps protocol)
Complexity Fee:    PKR 1,400  (critical)
Surge Fee:         PKR 0      (off-peak)
Eco Discount:      − PKR 245  (eco score 85)
Loyalty Discount:  − PKR 0    (new customer)
─────────────────────────────────────────
Total Quote:       PKR 7,892
Provider Earns:    PKR 7,103 (90%)
Platform Fee:      PKR 789 (10%)

──────────────────────────────────────────────────

Step 5: Scheduling
Preferred Slot:    09:00
Conflict Check:    No conflicts ✅
Scheduled:         2025-01-20 09:00
Travel Buffer:     24 min included
Double-booking:    Prevention check passed

──────────────────────────────────────────────────

Step 6: Booking Confirmation
Booking ID:   B247
QR Track ID:  QR-20250120090000-B247
Payment:      PAID
Certificate:  Required (24h post-service deadline)
Notifications: WhatsApp + SMS + Calendar + Receipt all sent

──────────────────────────────────────────────────

Step 7: Fallback — Provider Cancellation Simulation
Trigger:     Provider HazardShield cancels 45 min before pickup
Action:      Next provider (BioClean Services, Score 0.9287) auto-assigned
New Slot:    09:30 (30 min delay, hospital notified)
Trace Label: FALLBACK: Auto-rebooking triggered. Cancellation penalty applied.

══════════════════════════════════════════════════"""

    st.markdown(f'<div class="trace-box">{example_trace}</div>', unsafe_allow_html=True)


# ─── FOOTER ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align:center;color:#888;font-size:0.8rem;padding:1rem 0">
  🧬 <b>BioSafe AI</b> — Protecting Lives & Environment through Certified Biohazard Waste Disposal<br>
  Built with Python · Streamlit · Pandas · Google Antigravity Orchestration
</div>
""", unsafe_allow_html=True)
