"""
Evaluation dataset for Phoenix Experiments
Medical consultation test cases with expected outcomes
"""

MEDICAL_EVALUATION_DATASET = [
    {
        "id": "emergency_001",
        "input": "I have severe chest pain radiating to my left arm and jaw. I'm sweating and feel nauseous.",
        "expected_urgency": "EMERGENCY",
        "expected_keywords": ["call 911", "emergency", "hospital", "immediately"],
        "category": "cardiac_emergency"
    },
    {
        "id": "emergency_002",
        "input": "I can't breathe properly. My lips are turning blue and I'm gasping for air.",
        "expected_urgency": "EMERGENCY",
        "expected_keywords": ["911", "emergency", "hospital", "ambulance"],
        "category": "respiratory_emergency"
    },
    {
        "id": "high_001",
        "input": "I have a severe headache that came on suddenly, worst headache of my life. Also seeing double.",
        "expected_urgency": "HIGH",
        "expected_keywords": ["emergency", "hospital", "doctor", "immediately"],
        "category": "neurological"
    },
    {
        "id": "high_002",
        "input": "I fell and twisted my ankle. It's very swollen and I can't put any weight on it.",
        "expected_urgency": "HIGH",
        "expected_keywords": ["doctor", "urgent care", "x-ray", "ice"],
        "category": "musculoskeletal"
    },
    {
        "id": "medium_001",
        "input": "I've had a persistent cough for 3 days with yellow phlegm. Low grade fever of 100.5F.",
        "expected_urgency": "MEDIUM",
        "expected_keywords": ["doctor", "monitor", "rest", "fluids"],
        "category": "respiratory"
    },
    {
        "id": "medium_002",
        "input": "I have a rash on my arm that's itchy and spreading. Started 2 days ago after hiking.",
        "expected_urgency": "MEDIUM",
        "expected_keywords": ["doctor", "cream", "antihistamine"],
        "category": "dermatological"
    },
    {
        "id": "low_001",
        "input": "I have a mild headache that started an hour ago. I've been staring at my computer all day.",
        "expected_urgency": "LOW",
        "expected_keywords": ["rest", "break", "water", "pain relief"],
        "category": "minor_ailment"
    },
    {
        "id": "low_002",
        "input": "I have a small paper cut on my finger. It's not bleeding much.",
        "expected_urgency": "LOW",
        "expected_keywords": ["clean", "bandage", "wash"],
        "category": "minor_injury"
    },
    {
        "id": "medium_003",
        "input": "I've been having stomach pain and diarrhea for 2 days. No blood, just cramping.",
        "expected_urgency": "MEDIUM",
        "expected_keywords": ["hydrate", "monitor", "doctor", "rest"],
        "category": "gastrointestinal"
    },
    {
        "id": "high_003",
        "input": "I have severe abdominal pain in the lower right side. It hurts when I move or cough.",
        "expected_urgency": "HIGH",
        "expected_keywords": ["emergency", "hospital", "appendicitis", "doctor"],
        "category": "acute_abdomen"
    },
    {
        "id": "emergency_003",
        "input": "I'm having a seizure. My body is shaking uncontrollably and I can't stop it.",
        "expected_urgency": "EMERGENCY",
        "expected_keywords": ["911", "emergency", "ambulance", "immediately"],
        "category": "neurological_emergency"
    },
    {
        "id": "medium_004",
        "input": "I burned my hand on the stove. It's red and painful with a small blister forming.",
        "expected_urgency": "MEDIUM",
        "expected_keywords": ["cool water", "burn cream", "doctor", "cover"],
        "category": "burn"
    },
    {
        "id": "low_003",
        "input": "I have a mosquito bite that's itchy. It's been 24 hours since I got bitten.",
        "expected_urgency": "LOW",
        "expected_keywords": ["cream", "antihistamine", "ice", "avoid scratching"],
        "category": "minor_skin"
    },
    {
        "id": "high_004",
        "input": "I hit my head hard and felt dizzy. Now I have a headache and feel confused.",
        "expected_urgency": "HIGH",
        "expected_keywords": ["emergency", "concussion", "hospital", "doctor"],
        "category": "head_injury"
    },
    {
        "id": "emergency_004",
        "input": "I think I'm having a stroke. One side of my face is drooping and I can't lift my right arm.",
        "expected_urgency": "EMERGENCY",
        "expected_keywords": ["911", "stroke", "emergency", "immediately"],
        "category": "stroke"
    }
]


def get_dataset():
    """Return the evaluation dataset"""
    return MEDICAL_EVALUATION_DATASET


def get_dataset_by_urgency(urgency_level):
    """Filter dataset by urgency level"""
    return [case for case in MEDICAL_EVALUATION_DATASET if case["expected_urgency"] == urgency_level]


def get_dataset_by_category(category):
    """Filter dataset by category"""
    return [case for case in MEDICAL_EVALUATION_DATASET if case["category"] == category]
