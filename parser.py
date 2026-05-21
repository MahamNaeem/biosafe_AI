"""
BioSafe AI - Multilingual Parser
Handles Urdu, Roman Urdu, English, and code-switched input
"""

import re
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple


# ─── KEYWORD MAPS ────────────────────────────────────────────────────────────

WASTE_KEYWORDS = {
    "sharps": [
        "syringe", "syringes", "needle", "needles", "blade", "blades",
        "scalpel", "sharps", "injection", "suichi", "sui", "suiyan",
        "katedar", "lance", "lancet"
    ],
    "infectious": [
        "infectious", "infection", "pathological", "specimen", "culture",
        "bacteria", "virus", "infected", "contaminated", "biohazard",
        "mazroo", "mutassir", "tissue", "organ", "biopsy"
    ],
    "blood": [
        "blood", "خون", "khoon", "khun", "blood bag", "plasma", "serum",
        "hemolysis", "transfusion", "blood waste", "bloody", "hemorrhage",
        "bloodstained", "blood-contaminated", "lab waste"
    ],
    "pharmaceutical": [
        "medicine", "medicines", "dawai", "tablet", "tablets", "capsule",
        "expired", "dawa", "pharma", "pharmaceutical", "drug", "drugs",
        "injection medicine", "vial", "ampoule", "iv bag", "drip bag",
        "saline", "antibiotic", "chemotherapy", "chemo"
    ],
    "plastic": [
        "plastic", "tube", "catheter", "iv tube", "gloves", "mask", "apron",
        "gown", "drape", "wrapping", "packaging", "container", "bottle",
        "plastic waste", "non-sharp"
    ],
    "general": [
        "general", "regular", "normal", "garbage", "kachra", "waste",
        "rubbish", "non-hazardous", "paper", "food", "packaging"
    ]
}

DEPARTMENT_KEYWORDS = {
    "ICU": ["icu", "intensive care", "critical care", "intensive", "icu ward"],
    "Emergency": ["emergency", "er", "casualty", "accident", "trauma", "urgency ward"],
    "Operation Theater": ["ot", "operation theater", "operation theatre", "surgery", "surgical", "operation"],
    "Ward": ["ward", "ward 1", "ward 2", "ward 3", "ward 4", "ward 5", "general ward", "patient ward"],
    "Laboratory": ["lab", "laboratory", "pathology", "microbiology", "clinical lab", "blood bank"],
    "Maternity": ["maternity", "delivery", "gynae", "obstetrics", "labor room", "neonatal"],
    "Pharmacy": ["pharmacy", "dispensary", "drug store", "medicine room"],
    "Radiology": ["radiology", "xray", "x-ray", "mri", "ct scan", "imaging"],
    "Dialysis": ["dialysis", "kidney", "renal", "hemodialysis"]
}

URGENCY_KEYWORDS = {
    "immediate": [
        "urgent", "emergency", "abhi", "now", "right now", "asap",
        "immediately", "fori", "jaldi", "foran", "critical",
        "aaj abhi", "turant", "فوری"
    ],
    "today": [
        "today", "aaj", "same day", "aaj hi", "آج", "this evening",
        "this morning", "this afternoon", "aaj shaam", "aaj subah"
    ],
    "tomorrow": [
        "tomorrow", "kal", "کل", "next day", "kal subah", "kal morning",
        "tomorrow morning", "agle din"
    ],
    "scheduled": [
        "schedule", "plan", "book", "next week", "agle hafte",
        "2 days", "3 days", "arrange", "fix"
    ]
}

TIME_KEYWORDS = {
    "morning": ["morning", "subah", "صبح", "am", "9am", "10am", "8am"],
    "afternoon": ["afternoon", "dopahar", "دوپہر", "pm", "1pm", "2pm", "3pm"],
    "evening": ["evening", "shaam", "شام", "4pm", "5pm", "6pm"],
    "night": ["night", "raat", "رات", "8pm", "9pm", "10pm"]
}

QUANTITY_PATTERNS = [
    r"(\d+)\s*kg",
    r"(\d+)\s*kilo",
    r"(\d+)\s*kilogram",
    r"(\d+)\s*bags?",
    r"(\d+)\s*boxes?",
    r"(\d+)\s*containers?",
    r"(\d+)\s*liters?",
    r"(\d+)\s*units?"
]

HOSPITAL_KEYWORDS = [
    "hospital", "clinic", "medical center", "health center",
    "dispensary", "nursing home", "polyclinic"
]


# ─── LANGUAGE DETECTOR ────────────────────────────────────────────────────────

def detect_language(text: str) -> Tuple[str, float]:
    """Detect language type and return (language, confidence)"""
    text_lower = text.lower()

    has_urdu_script = bool(re.search(r'[\u0600-\u06FF]', text))
    roman_urdu_words = [
        "mujhe", "chahiye", "hai", "hain", "kal", "aaj", "karwana",
        "karwani", "uthwana", "uthwani", "dijiye", "se", "main", "ka",
        "ki", "ke", "ho", "nahi", "karo", "karna", "kiya", "tha"
    ]
    english_words = [
        "need", "please", "pickup", "disposal", "waste", "from",
        "the", "and", "urgent", "hospital"
    ]

    urdu_count = sum(1 for w in roman_urdu_words if w in text_lower)
    english_count = sum(1 for w in english_words if w in text_lower)

    if has_urdu_script and english_count > 0:
        return "Urdu + English (Code-switched)", 0.92
    elif has_urdu_script:
        return "Urdu Script", 0.95
    elif urdu_count >= 3 and english_count >= 2:
        return "Roman Urdu + English (Code-switched)", 0.91
    elif urdu_count >= 3:
        return "Roman Urdu", 0.88
    elif english_count >= 3:
        return "English", 0.93
    else:
        return "Mixed/Ambiguous", 0.65


# ─── ENTITY EXTRACTOR ─────────────────────────────────────────────────────────

def extract_waste_types(text: str) -> List[str]:
    text_lower = text.lower()
    found = []
    for waste_type, keywords in WASTE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            found.append(waste_type)
    return found if found else ["general"]


def extract_department(text: str) -> str:
    text_lower = text.lower()
    for dept, keywords in DEPARTMENT_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return dept
    return "General Ward"


def extract_urgency(text: str) -> str:
    text_lower = text.lower()
    for urgency, keywords in URGENCY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return urgency
    return "today"


def extract_preferred_time(text: str) -> str:
    text_lower = text.lower()

    # Try to find specific time like "9am", "14:00"
    time_match = re.search(r'(\d{1,2})\s*(?:am|pm|:00)', text_lower)
    if time_match:
        return time_match.group(0)

    for time_of_day, keywords in TIME_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            defaults = {
                "morning": "09:00",
                "afternoon": "13:00",
                "evening": "17:00",
                "night": "20:00"
            }
            return defaults[time_of_day]
    return "10:00"


def extract_quantity(text: str) -> float:
    text_lower = text.lower()
    for pattern in QUANTITY_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            return float(match.group(1))
    # Estimate based on department keywords
    if any(k in text_lower for k in ["icu", "emergency", "operation theater", "ot"]):
        return random.uniform(40, 120)
    if any(k in text_lower for k in ["ward", "laboratory"]):
        return random.uniform(20, 60)
    return random.uniform(15, 45)


def extract_location(text: str) -> str:
    """Extract or infer hospital/location from text"""
    text_lower = text.lower()
    known_hospitals = [
        "aga khan", "liaquat national", "south city", "ziauddin",
        "civil hospital", "jinnah", "indus", "patel", "dmc", "ojha"
    ]
    for h in known_hospitals:
        if h in text_lower:
            return h.title() + " Hospital"
    return "Hospital (Location Inferred from GPS)"


def classify_job_complexity(waste_types: List[str], quantity: float,
                            urgency: str, department: str) -> Tuple[str, str]:
    """
    Returns (complexity_level, explanation)
    Levels: basic, intermediate, complex, critical
    """
    critical_waste = {"sharps", "infectious", "blood", "chemical", "radioactive"}
    high_risk_depts = {"ICU", "Emergency", "Operation Theater"}

    has_critical_waste = bool(set(waste_types) & critical_waste)
    is_high_risk_dept = department in high_risk_depts
    is_urgent = urgency in ("immediate", "today")
    multi_waste = len(waste_types) > 2
    large_quantity = quantity > 100

    score = sum([
        has_critical_waste * 2,
        is_high_risk_dept * 2,
        is_urgent * 1,
        multi_waste * 1,
        large_quantity * 1
    ])

    if score >= 5:
        return "critical", (
            "Critical: High-risk waste types from critical department with urgency. "
            "Requires fully-certified provider with sealed vehicle and all safety equipment."
        )
    elif score >= 3:
        return "complex", (
            "Complex: Multiple risk factors present. "
            "Requires certified biohazard specialist with proper vehicle."
        )
    elif score >= 2:
        return "intermediate", (
            "Intermediate: Some risk factors present. "
            "Requires certified provider with standard biohazard equipment."
        )
    else:
        return "basic", (
            "Basic: Low-risk waste types with standard conditions. "
            "Requires certified provider with basic equipment."
        )


def compute_confidence(text: str, waste_types: List[str],
                       urgency: str, department: str) -> Tuple[float, List[str]]:
    """Compute parsing confidence and generate confirmation questions if low."""
    score = 0.50
    questions = []

    # Boost for clear signals
    if waste_types != ["general"]:
        score += 0.15
    if urgency != "today":
        score += 0.10
    if department != "General Ward":
        score += 0.10
    if len(text.split()) > 5:
        score += 0.08
    if re.search(r'\d', text):
        score += 0.07

    score = min(score, 0.98)

    if score < 0.75:
        if waste_types == ["general"]:
            questions.append("What type of waste needs to be disposed of? (e.g., sharps, blood, medicines)")
        if department == "General Ward":
            questions.append("Which hospital department is this request from?")
        if urgency == "today":
            questions.append("How urgent is this pickup? (Immediate/Today/Tomorrow/Scheduled)")
        questions.append("Please confirm the approximate quantity (kg) of waste.")

    return round(score, 2), questions


# ─── MAIN PARSE FUNCTION ──────────────────────────────────────────────────────

def parse_request(raw_input: str) -> Dict[str, Any]:
    """
    Main entry point for parsing a service request.
    Returns structured intent with confidence score.
    """
    text = raw_input.strip()
    language, lang_conf = detect_language(text)
    waste_types = extract_waste_types(text)
    department = extract_department(text)
    urgency = extract_urgency(text)
    preferred_time = extract_preferred_time(text)
    quantity = extract_quantity(text)
    location = extract_location(text)
    complexity, complexity_reason = classify_job_complexity(
        waste_types, quantity, urgency, department
    )
    confidence, confirmation_questions = compute_confidence(
        text, waste_types, urgency, department
    )

    # Build parsed result
    result = {
        "raw_input": raw_input,
        "language": language,
        "language_confidence": lang_conf,
        "service_type": "Biohazard Medical Waste Pickup & Disposal",
        "waste_types": waste_types,
        "department": department,
        "location": location,
        "urgency": urgency,
        "preferred_time": preferred_time,
        "quantity_kg": round(quantity, 1),
        "job_complexity": complexity,
        "complexity_reason": complexity_reason,
        "special_requirements": _infer_requirements(waste_types, complexity),
        "user_preferences": _default_preferences(),
        "confidence": confidence,
        "confirmation_questions": confirmation_questions,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "request_id": f"REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}",
    }
    return result


def _infer_requirements(waste_types: List[str], complexity: str) -> List[str]:
    reqs = []
    if "sharps" in waste_types:
        reqs.append("Needle Destroyer or Puncture-Resistant Container")
    if "blood" in waste_types or "infectious" in waste_types:
        reqs.append("Sealed Biohazard Transport + Autoclave Facility")
    if "pharmaceutical" in waste_types:
        reqs.append("Licensed Pharmaceutical Disposal Certificate")
    if complexity in ("complex", "critical"):
        reqs.append("Full PPE for Handling Personnel")
        reqs.append("Disposal Certificate (Mandatory)")
    if complexity == "critical":
        reqs.append("GPS Tracking + Chain of Custody Documentation")
    return reqs


def _default_preferences() -> Dict[str, Any]:
    return {
        "preferred_gender_team": "any",
        "language": "Urdu/English",
        "notification_channel": "WhatsApp",
        "require_certificate": True
    }
