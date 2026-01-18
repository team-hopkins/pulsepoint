"""Guardrails for medical AI responses"""
import config
from typing import Dict, Tuple

def check_emergency_keywords_routed(patient_input: str, route: str) -> Tuple[bool, str]:
    """
    Guardrail: Check if emergency keywords are routed properly (warning only, non-blocking)

    Args:
        patient_input: Patient's query
        route: Route taken by system

    Returns:
        (passed: bool, message: str)
    """
    has_emergency = any(keyword in patient_input.lower() for keyword in config.HIGH_STAKES_KEYWORDS)

    if has_emergency and route == "fast":
        return True, f"WARNING: Emergency keywords detected but routed to fast path"

    return True, "Emergency routing check passed"


def check_response_length(response: str, max_words: int = 50) -> Tuple[bool, str]:
    """
    Guardrail: Check response word limit for TTS (warning only, non-blocking)

    Args:
        response: AI response
        max_words: Maximum allowed words

    Returns:
        (passed: bool, message: str)
    """
    word_count = len(response.split())

    if word_count > max_words:
        return True, f"WARNING: Response exceeds limit ({word_count} words > {max_words} words for TTS)"

    return True, f"Length check passed ({word_count}/{max_words} words)"


def check_urgency_present(response: str) -> Tuple[bool, str]:
    """
    Guardrail: Check if response contains urgency level (warning only, non-blocking)

    Args:
        response: AI response

    Returns:
        (passed: bool, message: str)
    """
    urgency_levels = ["LOW", "MEDIUM", "HIGH", "EMERGENCY"]
    has_urgency = any(level in response.upper() for level in urgency_levels)

    if not has_urgency:
        return True, f"WARNING: Response missing urgency level"

    return True, "Urgency level present in response"


def check_medical_disclaimer_compliance(response: str, route: str) -> Tuple[bool, str]:
    """
    Guardrail: Check if critical warnings are implied (warning only, non-blocking)

    Args:
        response: AI response
        route: Route taken

    Returns:
        (passed: bool, message: str)
    """
    # For emergency cases, check if immediate action is recommended
    if "EMERGENCY" in response.upper():
        action_keywords = ["call", "emergency", "911", "hospital", "ambulance", "immediately"]
        has_action = any(keyword in response.lower() for keyword in action_keywords)

        if not has_action:
            return True, "WARNING: Emergency urgency without immediate action directive"

    return True, "Disclaimer compliance check passed"


def run_all_guardrails(patient_input: str, response: str, urgency: str, route: str) -> Dict:
    """
    Run all guardrails on the response (non-blocking, logs warnings only)

    Args:
        patient_input: Patient's original query
        response: AI's response
        urgency: Assigned urgency level
        route: Route taken

    Returns:
        dict with guardrail results (always passes, may contain warnings)
    """
    results = {
        "all_passed": True,  # Always pass - guardrails are non-blocking
        "warnings": [],
        "checks": []
    }

    # Run each guardrail
    checks = [
        ("emergency_routing", check_emergency_keywords_routed(patient_input, route)),
        ("response_length", check_response_length(response)),
        ("urgency_present", check_urgency_present(response)),
        ("disclaimer_compliance", check_medical_disclaimer_compliance(response, route))
    ]

    for check_name, (passed, message) in checks:
        results["checks"].append({
            "name": check_name,
            "passed": passed,
            "message": message
        })

        # Track warnings (messages starting with "WARNING:")
        if "WARNING:" in message:
            results["warnings"].append({
                "check": check_name,
                "message": message
            })

    return results
