"""
BioSafe AI - Provider Ranking Engine
Multi-factor matching: 13 factors weighted by importance
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple


# ─── FACTOR WEIGHTS ───────────────────────────────────────────────────────────

FACTOR_WEIGHTS = {
    "specialization_match": 0.18,
    "certification_score":  0.16,
    "reliability_score":    0.12,
    "on_time_score":        0.12,
    "rating_score":         0.10,
    "review_recency":       0.08,
    "capacity_score":       0.08,
    "distance_score":       0.07,
    "cancellation_penalty": 0.05,
    "complaint_penalty":    0.05,
    "eco_score":            0.04,
    "price_competitiveness":0.03,
    "complexity_match":     0.02,
}

CERT_TIER = {
    "WHO+EPA+ISO14001+OSHA": 1.0,
    "WHO+EPA+ISO14001":      0.90,
    "WHO+EPA":               0.75,
    "ISO14001":              0.55,
    "None":                  0.10,
}


# ─── INDIVIDUAL FACTOR SCORERS ────────────────────────────────────────────────

def score_specialization(provider_row: pd.Series, waste_types: List[str]) -> Tuple[float, str]:
    spec = str(provider_row["specialization"]).lower()
    matched = [w for w in waste_types if w in spec]
    ratio = len(matched) / max(len(waste_types), 1)
    label = f"{len(matched)}/{len(waste_types)} waste types matched"
    return round(ratio, 3), label


def score_certification(provider_row: pd.Series) -> Tuple[float, str]:
    cert = str(provider_row["certification_status"])
    for key, val in CERT_TIER.items():
        if key == cert:
            return val, f"Certification: {cert}"
    # Partial match
    for key, val in CERT_TIER.items():
        if all(c in cert for c in key.split("+")):
            return val * 0.95, f"Partial cert match: {cert}"
    return 0.40, f"Unknown certification: {cert}"


def score_distance(provider_row: pd.Series, urgency: str) -> Tuple[float, str]:
    dist = float(provider_row["distance_km"])
    # Urgency adjusts distance sensitivity
    if urgency == "immediate":
        penalty = dist * 0.08   # very sensitive
    elif urgency == "today":
        penalty = dist * 0.05
    else:
        penalty = dist * 0.025
    raw = max(0, 1.0 - penalty)
    return round(raw, 3), f"{dist:.1f} km away ({provider_row['travel_time_min']} min)"


def score_capacity(provider_row: pd.Series, quantity_kg: float) -> Tuple[float, str]:
    cap = float(provider_row["capacity_kg"])
    load = float(provider_row["current_load_kg"])
    available = cap - load
    if available <= 0:
        return 0.0, "No capacity available"
    if available >= quantity_kg * 1.5:
        return 1.0, f"{available:.0f} kg available (ample)"
    elif available >= quantity_kg:
        return 0.75, f"{available:.0f} kg available (sufficient)"
    else:
        return 0.30, f"Only {available:.0f} kg available (tight)"


def score_review_recency(provider_row: pd.Series) -> Tuple[float, str]:
    days = int(provider_row["review_recency_days"])
    if days <= 7:
        return 1.0, f"Reviews from {days} days ago (very recent)"
    elif days <= 30:
        return 0.80, f"Reviews from {days} days ago (recent)"
    elif days <= 60:
        return 0.55, f"Reviews from {days} days ago (moderate)"
    else:
        return 0.30, f"Reviews from {days} days ago (stale)"


def score_price_competitiveness(provider_row: pd.Series, all_prices: List[float]) -> Tuple[float, str]:
    price = float(provider_row["price_per_kg"])
    if not all_prices:
        return 0.5, "No comparison data"
    min_p, max_p = min(all_prices), max(all_prices)
    if max_p == min_p:
        return 0.7, "All providers same price"
    # Lower price = higher score, but not the ONLY factor
    ratio = 1.0 - (price - min_p) / (max_p - min_p)
    return round(ratio * 0.8 + 0.2, 3), f"PKR {price}/kg (competitive)"


def score_complexity_match(provider_row: pd.Series, complexity: str) -> Tuple[float, str]:
    tools = str(provider_row["tools_certifications"]).lower()
    vehicle = str(provider_row["vehicle_type"]).lower()

    if complexity == "critical":
        needed = ["autoclave", "gps", "ppe", "biohazard"]
        score = sum(1 for t in needed if t in tools or t in vehicle) / len(needed)
        return round(score, 3), f"Critical complexity check: {int(score*100)}% match"
    elif complexity == "complex":
        needed = ["autoclave", "ppe", "biohazard"]
        score = sum(1 for t in needed if t in tools or t in vehicle) / len(needed)
        return round(score, 3), f"Complex complexity check: {int(score*100)}% match"
    elif complexity == "intermediate":
        needed = ["ppe", "biohazard"]
        score = sum(1 for t in needed if t in tools or t in vehicle) / len(needed)
        return round(score, 3), f"Intermediate complexity check: {int(score*100)}% match"
    return 0.9, "Basic complexity — standard provider suitable"


# ─── MAIN RANKING FUNCTION ────────────────────────────────────────────────────

def rank_providers(
    providers_df: pd.DataFrame,
    parsed_request: Dict[str, Any]
) -> pd.DataFrame:
    """
    Score and rank all providers.
    Returns DataFrame with scores, explanations, and final rank.
    """
    waste_types = parsed_request.get("waste_types", ["general"])
    urgency     = parsed_request.get("urgency", "today")
    quantity    = parsed_request.get("quantity_kg", 50.0)
    complexity  = parsed_request.get("job_complexity", "basic")

    all_prices = providers_df["price_per_kg"].astype(float).tolist()
    results = []

    for _, row in providers_df.iterrows():
        factor_scores = {}
        factor_labels = {}

        s, l = score_specialization(row, waste_types)
        factor_scores["specialization_match"] = s
        factor_labels["specialization_match"] = l

        s, l = score_certification(row)
        factor_scores["certification_score"] = s
        factor_labels["certification_score"] = l

        factor_scores["reliability_score"] = float(row["reliability_score"])
        factor_labels["reliability_score"] = f"Reliability: {float(row['reliability_score']):.0%}"

        factor_scores["on_time_score"] = float(row["on_time_score"])
        factor_labels["on_time_score"] = f"On-time: {float(row['on_time_score']):.0%}"

        factor_scores["rating_score"] = (float(row["rating"]) - 1) / 4
        factor_labels["rating_score"] = f"Rating: {row['rating']}/5.0"

        s, l = score_review_recency(row)
        factor_scores["review_recency"] = s
        factor_labels["review_recency"] = l

        s, l = score_capacity(row, quantity)
        factor_scores["capacity_score"] = s
        factor_labels["capacity_score"] = l

        s, l = score_distance(row, urgency)
        factor_scores["distance_score"] = s
        factor_labels["distance_score"] = l

        cancel_pen = max(0, 1.0 - float(row["cancellation_rate"]) * 5)
        factor_scores["cancellation_penalty"] = cancel_pen
        factor_labels["cancellation_penalty"] = f"Cancellation rate: {float(row['cancellation_rate']):.0%}"

        complaint_pen = max(0, 1.0 - float(row["complaint_rate"]) * 8)
        factor_scores["complaint_penalty"] = complaint_pen
        factor_labels["complaint_penalty"] = f"Complaint rate: {float(row['complaint_rate']):.0%}"

        factor_scores["eco_score"] = float(row["eco_score"]) / 100
        factor_labels["eco_score"] = f"Eco score: {row['eco_score']}/100"

        s, l = score_price_competitiveness(row, all_prices)
        factor_scores["price_competitiveness"] = s
        factor_labels["price_competitiveness"] = l

        s, l = score_complexity_match(row, complexity)
        factor_scores["complexity_match"] = s
        factor_labels["complexity_match"] = l

        # Weighted total (capped at 1.0)
        total = min(1.0, sum(
            factor_scores[f] * FACTOR_WEIGHTS[f]
            for f in FACTOR_WEIGHTS
            if f in factor_scores
        ))

        results.append({
            "provider_id":    row["provider_id"],
            "provider_name":  row["provider_name"],
            "location":       row["location"],
            "distance_km":    row["distance_km"],
            "travel_time_min":row["travel_time_min"],
            "rating":         row["rating"],
            "certification":  row["certification_status"],
            "vehicle_type":   row["vehicle_type"],
            "available_slots":row["available_slots"],
            "price_per_kg":   row["price_per_kg"],
            "base_fee":       row["base_fee"],
            "eco_score":      row["eco_score"],
            "risk_score":     row["risk_score"],
            "total_score":    round(total, 4),
            "factor_scores":  factor_scores,
            "factor_labels":  factor_labels,
            "recommendation": _build_recommendation(row, factor_scores, factor_labels),
        })

    ranked_df = pd.DataFrame(results).sort_values("total_score", ascending=False).reset_index(drop=True)
    ranked_df["rank"] = ranked_df.index + 1
    return ranked_df


def _build_recommendation(row: pd.Series, scores: Dict, labels: Dict) -> str:
    """Build human-readable recommendation explanation."""
    top_factors = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
    pros = []
    for factor, score in top_factors:
        if score >= 0.75:
            pros.append(f"✅ {labels.get(factor, factor)}")

    weak_factors = sorted(scores.items(), key=lambda x: x[1])[:2]
    cons = []
    for factor, score in weak_factors:
        if score < 0.50:
            cons.append(f"⚠️ {labels.get(factor, factor)}")

    rec = " | ".join(pros)
    if cons:
        rec += " | " + " | ".join(cons)
    return rec
