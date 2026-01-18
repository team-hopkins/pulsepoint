"""A/B Testing framework for prompt variations and model configurations"""
from typing import Dict, Any, Literal
import random
from enum import Enum


class PromptVariant(Enum):
    """Different prompt strategies to test"""
    CONCISE = "concise"  # Current 50-word limit
    DETAILED = "detailed"  # More comprehensive responses
    EMPATHETIC = "empathetic"  # Focus on bedside manner
    CLINICAL = "clinical"  # Technical medical terminology


class ABTestConfig:
    """A/B test configuration for experiments"""

    # Current active experiments
    ACTIVE_EXPERIMENTS = {
        "prompt_style": {
            "enabled": True,
            "variants": {
                "control": 0.70,  # 70% get current concise prompts
                "detailed": 0.15,  # 15% get detailed prompts
                "empathetic": 0.15  # 15% get empathetic prompts
            }
        },
        "council_threshold": {
            "enabled": False,  # Disabled by default
            "variants": {
                "control": 0.50,  # Current: all high-stakes to council
                "sensitive": 0.25,  # Lower threshold - more to council
                "aggressive": 0.25  # Higher threshold - more to fast path
            }
        }
    }

    @staticmethod
    def get_variant(experiment_name: str, patient_id: str) -> str:
        """
        Assign patient to experiment variant using consistent hashing

        Args:
            experiment_name: Name of the experiment
            patient_id: Patient identifier for consistent assignment

        Returns:
            Variant name (e.g., "control", "detailed")
        """
        experiment = ABTestConfig.ACTIVE_EXPERIMENTS.get(experiment_name)

        if not experiment or not experiment.get("enabled"):
            return "control"

        # Use patient_id hash for consistent assignment
        hash_value = hash(f"{experiment_name}:{patient_id}") % 100

        # Assign based on percentage thresholds
        cumulative = 0
        for variant, percentage in experiment["variants"].items():
            cumulative += int(percentage * 100)
            if hash_value < cumulative:
                return variant

        return "control"


def get_prompt_for_variant(variant: str, base_prompt: str) -> str:
    """
    Modify prompt based on A/B test variant

    Args:
        variant: Variant name from experiment
        base_prompt: Original prompt template

    Returns:
        Modified prompt based on variant
    """
    if variant == "detailed":
        return base_prompt.replace(
            "CRITICAL INSTRUCTION: Respond in EXACTLY 50 words or less.",
            "Provide a detailed assessment in 80-100 words. Include reasoning and context."
        )

    elif variant == "empathetic":
        return base_prompt + "\n\nIMPORTANT: Use warm, empathetic language. Acknowledge patient concerns."

    elif variant == "clinical":
        return base_prompt + "\n\nIMPORTANT: Use precise medical terminology. Be clinically accurate."

    else:  # control
        return base_prompt


def log_experiment_assignment(patient_id: str, experiments: Dict[str, str]) -> Dict[str, Any]:
    """
    Log experiment variant assignments for tracking

    Args:
        patient_id: Patient identifier
        experiments: Dict of experiment_name -> variant

    Returns:
        Dict formatted for OpenTelemetry span attributes
    """
    attributes = {
        "experiment.patient_id": patient_id,
        "experiment.count": len(experiments)
    }

    for idx, (exp_name, variant) in enumerate(experiments.items()):
        attributes[f"experiment.{idx}.name"] = exp_name
        attributes[f"experiment.{idx}.variant"] = variant

    return attributes


def should_route_to_council_variant(variant: str, is_high_stakes: bool, has_image: bool) -> bool:
    """
    Determine routing based on A/B test variant

    Args:
        variant: Council threshold variant
        is_high_stakes: Whether input contains emergency keywords
        has_image: Whether input includes image

    Returns:
        True if should route to council
    """
    if variant == "sensitive":
        # Lower threshold - route more to council
        # Route if: has_image OR high_stakes OR random 30%
        return has_image or is_high_stakes or (random.random() < 0.3)

    elif variant == "aggressive":
        # Higher threshold - route less to council
        # Only route if: has_image AND high_stakes
        return has_image and is_high_stakes

    else:  # control
        # Current behavior: route if has_image OR high_stakes
        return has_image or is_high_stakes
