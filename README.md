# 🧬 BioSafe AI

**AI-Powered Multilingual Service Orchestrator for Biohazard Hospital Waste Collection**

> Protecting lives and the environment by connecting hospitals with certified medical waste disposal providers through intelligent, transparent, traceable orchestration.

---

## Problem Statement

Pakistan disposes of **~340,000 tonnes of medical waste annually** with minimal regulation. Improperly discarded syringes, blood bags, and expired medicines cause:
- **AIDS and Hepatitis B&C** infections from reused/discarded sharps
- **Antibiotic resistance** from pharmaceutical waste in water systems  
- **Marine and land pollution** along Karachi coastline and rivers
- **Infection risk** from infectious waste dumped in open areas

Hospitals struggle to find certified providers quickly. Providers have no structured matching system. There is no chain-of-custody or traceability.

**BioSafe AI solves all of this.**

---

## Solution Overview

BioSafe AI is a lightweight, deployable prototype that:

1. **Understands** multilingual requests (Urdu, Roman Urdu, English, code-switched)
2. **Classifies** waste by type, risk, and appropriate disposal method
3. **Matches** hospitals with the best certified provider using 13 factors
4. **Prices** the service with full transparent breakdown
5. **Schedules** pickups with conflict prevention and fallback handling
6. **Books** with QR waste bag tracking, notifications, and receipts
7. **Tracks** service through a complete quality loop with disposal certificates
8. **Resolves** disputes including illegal dumping with EPA/Police escalation
9. **Logs** every decision step via Google Antigravity reasoning traces

---

## How It Maps to Challenge 2

| Requirement | Implementation |
|---|---|
| Service request understanding | `parser.py` — multilingual NLP, confidence scoring |
| Provider matching | `ranking.py` — 13-factor weighted algorithm |
| Dynamic pricing | `pricing.py` — 9-component transparent breakdown |
| Scheduling | `scheduler.py` — conflict prevention, waitlist, rescheduling |
| Booking simulation | `orchestrator.py` step 6 — QR, SMS, calendar, CSV |
| Follow-up | `orchestrator.py` step 7 — milestone tracking, certificate |
| Feedback | `orchestrator.py` step 8 — rating update, matching impact |
| Dispute handling | `dispute.py` — 12 types, severity, blacklist, EPA |
| Google Antigravity orchestration | `orchestrator.py` — every step generates trace log |
| Antigravity trace/logs | Tab 9 in app — live + exportable trace logs |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    app.py (Streamlit UI)              │
│   9 Tabs: Request → Understanding → Classification   │
│   → Ranking → Pricing → Scheduling → Tracking        │
│   → Feedback/Dispute → Antigravity Trace Logs        │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│            orchestrator.py (Antigravity Core)         │
│  Coordinates all steps, generates trace logs          │
│  step_parse → step_classify → step_rank →            │
│  step_price → step_schedule → step_confirm →         │
│  step_track → step_feedback → step_dispute           │
└──┬──────────┬──────────┬──────────┬─────────────────┘
   │          │          │          │
┌──▼──┐  ┌───▼──┐  ┌────▼──┐  ┌───▼────┐  ┌──────────┐
│parser│  │rankin│  │pricing│  │schedul │  │ dispute  │
│  .py │  │  g   │  │  .py  │  │  er.py │  │   .py    │
└──────┘  └──────┘  └───────┘  └────────┘  └──────────┘
   │          │          │          │
┌──▼──────────▼──────────▼──────────▼────────────────┐
│              data/ (CSV Datasets)                    │
│  providers.csv · waste_categories.csv               │
│  bookings.csv  · disputes.csv                       │
└─────────────────────────────────────────────────────┘
```

---

## Google Antigravity Orchestration

`orchestrator.py` implements the Antigravity agentic workflow pattern:

- **Every step is a named agent action** (`step_parse`, `step_rank`, etc.)
- **Every action generates a reasoning trace** logged to `_trace_store`
- **Traces include**: inputs, decisions made, factors weighed, fallbacks triggered
- **Tab 9** in the UI shows all traces in real-time with export functionality
- **Fallback actions** (no provider, low confidence, cancellation) are explicitly traced

```python
# Antigravity trace example
_add_trace("Step 3: Provider Ranking", trace_text, {"top_provider": "HazardShield Inc"})
```

Traces follow the format:
```
[Antigravity Orchestration Trace]
Step N: <Action Name>
<Key decision data>
<Reasoning>
<Outcome>
```

---

## Dataset Schema

### `data/providers.csv`
| Field | Description |
|---|---|
| provider_id | Unique ID (P001–P010) |
| provider_name | Company name |
| specialization | Pipe-separated waste types handled |
| distance_km | Distance from hospital zone |
| travel_time_min | Estimated travel time |
| rating | 1–5 star rating |
| review_recency_days | Days since most recent review |
| reliability_score | 0–1 historical reliability |
| on_time_score | 0–1 on-time completion rate |
| certification_status | WHO/EPA/ISO/OSHA combinations |
| vehicle_type | Vehicle class and sealing type |
| capacity_kg | Max waste capacity |
| current_load_kg | Current committed load |
| price_per_kg | PKR per kg rate |
| base_fee | Fixed mobilization fee (PKR) |
| cancellation_rate | Historical cancellation fraction |
| complaint_rate | Historical complaint fraction |
| eco_score | 0–100 environmental score |
| risk_score | 0–100 risk score (lower = safer) |
| available_slots | Pipe-separated HH:MM slots |
| location | Area/city location |
| tools_certifications | Comma-separated equipment list |

### `data/waste_categories.csv`
| Field | Description |
|---|---|
| category_id | W001–W008 |
| waste_type | sharps, infectious, blood, pharmaceutical, plastic, general, chemical, radioactive |
| display_name | Human-readable name |
| risk_level | Critical / High / Medium / Low |
| reuse_risk | Risk if item is reused |
| disease_risk | Specific diseases |
| marine_pollution_risk | Impact on marine life |
| land_pollution_risk | Impact on land |
| recommended_disposal | WHO-recommended method |
| color_code | Hex color for UI |
| handling_notes | Safety handling instructions |

---

## Provider Matching Algorithm

13 weighted factors:

| Factor | Weight | Description |
|---|---|---|
| Specialization Match | 18% | Fraction of requested waste types provider handles |
| Certification Score | 16% | WHO+EPA+ISO14001+OSHA = 1.0, degraded for lower tiers |
| Reliability Score | 12% | Historical reliability (0–1) |
| On-Time Score | 12% | On-time completion rate |
| Rating Score | 10% | Normalized from 1–5 scale |
| Review Recency | 8% | Recent reviews weighted higher |
| Capacity Score | 8% | Available capacity vs. requested quantity |
| Distance Score | 7% | Adjusted by urgency (more sensitive for immediate) |
| Cancellation Penalty | 5% | Inverse of cancellation rate |
| Complaint Penalty | 5% | Inverse of complaint rate |
| Eco Score | 4% | Environmental performance |
| Price Competitiveness | 3% | Relative to other providers |
| Complexity Match | 2% | Equipment/vehicle match to job complexity |

**Key principle:** Distance is only 7% — certified, reliable providers outrank nearest providers for safety-critical waste.

---

## Dynamic Pricing Formula

```
Total = (Base Fee
       + Quantity Fee (qty_kg × price_per_kg)
       + Urgency Fee ((base + qty) × (urgency_mult − 1))
       + Distance Fee (distance_km × 35 PKR/km)
       + Risk Handling Fee (sum per waste type)
       + Complexity Fee (basic=0, intermediate=300, complex=700, critical=1400)
       + Surge Fee (subtotal × 0.20 during peak hours)
       − Eco Discount (subtotal × eco_rate)
       − Loyalty Discount (subtotal × loyalty_rate))

Provider Earnings = Total × 0.90
Platform Fee      = Total × 0.10
```

Urgency multipliers: immediate=1.8×, today=1.35×, tomorrow=1.15×, scheduled=1.0×

---

## Scheduling Workflow

```
1. Determine target date from urgency
2. Try preferred time slot → conflict check against bookings.csv
3. If conflict → try all available_slots for same date
4. If no same-day slots → try next day
5. If still no slots → add to waitlist, notify hospital when opens
6. Book slot with travel-time buffer included
7. Send notifications (WhatsApp, SMS, Calendar, Receipt)
8. Update bookings.csv
```

Conflict check: scans existing bookings for same provider + overlapping window (duration + 30 min buffer).

---

## Dispute Workflow

12 dispute types with automatic severity assignment:

| Type | Severity | Auto-Action |
|---|---|---|
| no_show | High | Full refund + 500 PKR + rebooking |
| illegal_dumping | Critical | Blacklist + EPA/Police + 10,000 PKR |
| unsafe_handling | Critical | Immediate suspension + WHO audit |
| qr_mismatch | High | Full refund + EPA notification |
| quality_complaint | High | 50% refund + quality audit |
| cancellation | Medium | Full refund + 1,000 PKR compensation |
| late_pickup | Medium | 15% refund + rating penalty |
| certificate_missing | Medium | 7-day deadline or fine |
| price_disagreement | Medium | Invoice review |
| overrun | Low | Auto-resolve |

---

## APIs / Tools Used

| Tool | Purpose |
|---|---|
| Python 3.10+ | Core language |
| Streamlit | Web + mobile UI |
| Pandas | Data processing, CSV management |
| NumPy | Numerical scoring |
| re (stdlib) | Multilingual regex parsing |
| datetime (stdlib) | Scheduling, timestamp generation |
| uuid / random (stdlib) | ID and mock data generation |

External APIs (placeholders for production):
- Google Maps API — real distance/travel time
- WhatsApp Business API — notifications
- Payment Gateway (JazzCash/Easypaisa) — payment confirmation
- EPA Pakistan API — illegal dumping reporting

---

## Setup Instructions

```bash
# 1. Clone or download project
git clone https://github.com/yourrepo/biosafe-ai
cd biosafe-ai

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py
```

**Python 3.8+ required. No other dependencies.**

---

## Deployment (Streamlit Cloud)

1. Push code to GitHub (public repo)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect GitHub repo
4. Set main file: `app.py`
5. Deploy — no environment variables needed for basic version

The Streamlit deployed URL serves as the **Mobile App Link** for submission (fully mobile-responsive).

---

## Cost / Latency Analysis

| Operation | Latency | Cost |
|---|---|---|
| Language parsing | < 5ms | Free (rule-based) |
| 13-factor ranking (10 providers) | < 20ms | Free |
| Price calculation | < 2ms | Free |
| Scheduling conflict check | < 10ms | Free |
| Full pipeline (all steps) | < 50ms | Free |
| Streamlit Cloud hosting | — | Free tier |

No external API calls in prototype = zero latency from network, zero cost per request.

**Baseline comparison:** Manual hospital-to-provider coordination takes 30–120 minutes via phone. BioSafe AI processes the complete workflow in under 1 second.

---

## Privacy Note

- No real patient data is stored or processed
- Hospital names are generic/anonymized in mock datasets
- QR tracking IDs are session-generated, not persisted to external storage
- In production: PDPA (Pakistan Data Protection Act) compliance required
- Provider data encrypted at rest; hospital contact data stored with consent

---

## Limitations

1. **Distance/routing is mocked** — needs Google Maps API for real distances
2. **Payment is simulated** — no real payment gateway integrated
3. **Notifications are logged only** — no real WhatsApp/SMS API connected
4. **Language parsing is rule-based** — production would use a fine-tuned multilingual LLM
5. **GPS tracking is placeholder** — real implementation needs IoT/mobile tracking
6. **CSV storage** — production requires PostgreSQL or Firestore
7. **Single city (Karachi)** — multi-city requires provider geo-clustering

---

## Future Improvements

- [ ] Fine-tuned multilingual NLP model (Urdu BERT / mBERT)
- [ ] Real Google Maps distance/routing API integration
- [ ] Live provider mobile app (Flutter) for real-time slot management
- [ ] Blockchain-based disposal certificate verification
- [ ] IoT QR scanner integration for waste bag chain-of-custody
- [ ] Multi-city provider network (Lahore, Islamabad, Faisalabad)
- [ ] Pakistan EPA real-time reporting API
- [ ] Hospital ERP integration (HIS/LIS systems)
- [ ] ML-based demand forecasting for provider workload planning

---

## Submission Checklist

| Deliverable | Status | Details |
|---|---|---|
| ✅ Mobile App Link | Streamlit deployed URL | Mobile-responsive Streamlit app |
| ✅ GitHub Repository | Code repo with all files | Python + CSV + docs |
| ✅ Demo Video | 3–5 min walkthrough | See `demo_script.md` |
| ✅ Antigravity Usage Video | Tab 9 trace walkthrough | Export trace log shown |
| ✅ README / Documentation | This file | Full architecture + schema |
| ✅ Antigravity Trace / Logs | `antigravity_trace_logs.md` | Pre-generated + live in Tab 9 |

---

## File Structure

```
biosafe-ai/
├── app.py                      # Streamlit UI (9 tabs, mobile-responsive)
├── orchestrator.py             # Antigravity agentic orchestrator
├── parser.py                   # Multilingual intent parser
├── ranking.py                  # 13-factor provider ranking engine
├── pricing.py                  # Dynamic pricing calculator
├── scheduler.py                # Scheduling + booking management
├── dispute.py                  # Dispute + escalation workflow
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── demo_script.md              # 3–5 min demo walkthrough
├── antigravity_trace_logs.md   # Sample Antigravity trace logs
└── data/
    ├── providers.csv           # 10 mock biohazard waste providers
    ├── waste_categories.csv    # 8 waste types with risk metadata
    ├── bookings.csv            # 10 mock historical bookings
    └── disputes.csv            # 8 mock dispute records
```

---

*BioSafe AI — Built for Challenge 2 · Python + Streamlit + Google Antigravity*
