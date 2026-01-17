"""Guardrails for medical AI responses"""
import config
from typing import Dict, Tuple

def check_emergency_keywords_routed(patient_input: str, route: str) -> Tuple[bool, str]:
    """
    Guardrail: Ensure emergency keywords are routed to council

    Args:
        patient_input: Patient's query
        route: Route taken by system

    Returns:
        (passed: bool, message: str)
    """
    has_emergency = any(keyword in patient_input.lower() for keyword in config.HIGH_STAKES_KEYWORDS)

    if has_emergency and route == "fast":
        return False, f"BLOCKED: Emergency keywords detected but routed to fast path. Keywords: {config.HIGH_STAKES_KEYWORDS}"

    return True, "Emergency routing check passed"


def check_response_length(response: str, max_words: int = 30) -> Tuple[bool, str]:
    """
    Guardrail: Ensure response is within word limit for TTS

    Args:
        response: AI response
        max_words: Maximum allowed words

    Returns:
        (passed: bool, message: str)
    """
    word_count = len(response.split())

    if word_count > max_words:
        return False, f"BLOCKED: Response too long ({word_count} words > {max_words} words limit for TTS)"

    return True, f"Length check passed ({word_count}/{max_words} words)"


def check_urgency_present(response: str) -> Tuple[bool, str]:
    """
    Guardrail: Ensure response contains urgency level

    Args:
        response: AI response

    Returns:
        (passed: bool, message: str)
    """
    urgency_levels = ["LOW", "MEDIUM", "HIGH", "EMERGENCY"]
    has_urgency = any(level in response.upper() for level in urgency_levels)

    if not has_urgency:
        return False, f"BLOCKED: Response missing urgency level. Must contain one of: {urgency_levels}"

    return True, "Urgency level present in response"


def check_medical_disclaimer_compliance(response: str, route: str) -> Tuple[bool, str]:
    """
    Guardrail: For TTS responses, ensure critical warnings are implied

    Args:
        response: AI response
        route: Route taken

    Returns:
        (passed: bool, message: str)
    """
    # For emergency cases, ensure immediate action is recommended
    if "EMERGENCY" in response.upper():
        action_keywords = ["call", "emergency", "911", "hospital", "ambulance", "immediately"]
        has_action = any(keyword in response.lower() for keyword in action_keywords)

        if not has_action:
            return False, "BLOCKED: Emergency urgency without immediate action directive"

    return True, "Disclaimer compliance check passed"


def run_all_guardrails(patient_input: str, response: str, urgency: str, route: str) -> Dict:
    """
    Run all guardrails on the response

    Args:
        patient_input: Patient's original query
        response: AI's response
        urgency: Assigned urgency level
        route: Route taken

    Returns:
        dict with guardrail results
    """
    results = {
        "all_passed": True,
        "checks": []
    }

    # Run each guardrail
    checks = [
        check_emergency_keywords_routed(patient_input, route),
        check_response_length(response),
        check_urgency_present(response),
        check_medical_disclaimer_compliance(response, route)
    ]

    for passed, message in checks:
        results["checks"].append({
            "passed": passed,
            "message": message
        })

        if not passed:
            results["all_passed"] = False
            results["blocked_reason"] = message
            break  # Stop on first failure

    return results
