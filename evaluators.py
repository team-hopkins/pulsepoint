"""LLM Evaluators for medical AI responses using Phoenix"""
from phoenix.evals import HallucinationEvaluator, llm_classify, AnthropicModel
import config
import os

# Use Claude for Phoenix evaluators (OpenRouter doesn't support legacy 'functions' API)
# Claude Sonnet 3.5 is excellent for evaluations and avoids OpenRouter compatibility issues
os.environ["ANTHROPIC_API_KEY"] = config.ANTHROPIC_API_KEY

# Initialize hallucination detector using Claude Sonnet 3.5 for evaluation
# Note: AnthropicModel reads API key from ANTHROPIC_API_KEY environment variable
hallucination_evaluator = HallucinationEvaluator(
    model=AnthropicModel(model="claude-3-5-sonnet-20240620")
)

def evaluate_hallucination(input_text: str, output_text: str, reference_text: str = None) -> dict:
    """
    Evaluate if the medical response contains hallucinations

    Args:
        input_text: Patient's original query
        output_text: AI's response to evaluate
        reference_text: Optional ground truth or expert opinions for comparison

    Returns:
        dict with hallucination score and explanation
    """
    try:
        import pandas as pd

        # Create DataFrame in the format expected by Phoenix evaluator
        df = pd.DataFrame({
            "input": [input_text],
            "output": [output_text],
            "reference": [reference_text if reference_text else input_text]
        })

        # Run hallucination detection on the dataframe
        eval_result = hallucination_evaluator.evaluate(df)

        # Phoenix returns a DataFrame with evaluation results
        if isinstance(eval_result, pd.DataFrame) and len(eval_result) > 0:
            label = eval_result["label"].iloc[0]
            score = eval_result["score"].iloc[0] if "score" in eval_result.columns else None
            explanation = eval_result["explanation"].iloc[0] if "explanation" in eval_result.columns else ""

            return {
                "hallucination_score": score,
                "label": label,
                "explanation": explanation,
                "is_hallucinated": label == "hallucinated"
            }
        else:
            return {
                "hallucination_score": None,
                "label": "no_result",
                "explanation": "No evaluation result returned",
                "is_hallucinated": None
            }
    except Exception as e:
        print(f"⚠️  Hallucination evaluation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "hallucination_score": None,
            "label": "error",
            "explanation": str(e),
            "is_hallucinated": None
        }


def evaluate_urgency_alignment(patient_input: str, assigned_urgency: str) -> dict:
    """
    Evaluate if the urgency level matches the symptom severity

    Args:
        patient_input: Patient's query
        assigned_urgency: Urgency level assigned by the system

    Returns:
        dict with alignment score and explanation
    """
    import config

    # Check for high-stakes keywords
    has_emergency_keywords = any(keyword in patient_input.lower() for keyword in config.HIGH_STAKES_KEYWORDS)

    # Simple rule-based evaluation
    if has_emergency_keywords:
        expected_urgency = "HIGH or EMERGENCY"
        is_aligned = assigned_urgency in ["HIGH", "EMERGENCY"]
    else:
        expected_urgency = "LOW or MEDIUM"
        is_aligned = assigned_urgency in ["LOW", "MEDIUM"]

    return {
        "expected_urgency": expected_urgency,
        "assigned_urgency": assigned_urgency,
        "is_aligned": is_aligned,
        "has_emergency_keywords": has_emergency_keywords
    }


def evaluate_council_consensus(council_votes: dict) -> dict:
    """
    Evaluate agreement between council members

    Args:
        council_votes: Dict of votes from council members

    Returns:
        dict with consensus metrics
    """
    if not council_votes or len(council_votes) < 2:
        return {
            "consensus_score": None,
            "urgency_agreement": None,
            "confidence_variance": None
        }

    # Extract urgencies and confidences
    urgencies = [v.get("urgency") for v in council_votes.values() if v.get("urgency")]
    confidences = [v.get("confidence") for v in council_votes.values() if v.get("confidence")]

    # Calculate urgency agreement (percentage that agree)
    if urgencies:
        most_common_urgency = max(set(urgencies), key=urgencies.count)
        urgency_agreement = urgencies.count(most_common_urgency) / len(urgencies)
    else:
        urgency_agreement = None

    # Calculate confidence variance
    if confidences and len(confidences) > 1:
        mean_conf = sum(confidences) / len(confidences)
        variance = sum((c - mean_conf) ** 2 for c in confidences) / len(confidences)
        confidence_variance = round(variance, 4)
    else:
        confidence_variance = None

    return {
        "consensus_score": urgency_agreement,
        "urgency_agreement": urgency_agreement,
        "confidence_variance": confidence_variance,
        "num_models": len(council_votes)
    }


def evaluate_response_quality(patient_input: str, ai_response: str, urgency: str, route: str, council_votes: dict = None) -> dict:
    """
    Comprehensive quality evaluation for medical responses

    Args:
        patient_input: Patient's query
        ai_response: AI's response
        urgency: Urgency level assigned
        route: Which path was taken (fast/visual/council)

    Returns:
        dict with multiple evaluation metrics
    """
    evaluations = {}

    # 1. Hallucination check
    hallucination_result = evaluate_hallucination(patient_input, ai_response)
    evaluations["hallucination"] = hallucination_result

    # 2. Word count check (should be ≤50 for TTS)
    word_count = len(ai_response.split())
    evaluations["word_count"] = {
        "count": word_count,
        "within_limit": word_count <= 50,
        "limit": 50
    }

    # 3. Format validation (contains urgency level)
    has_urgency = any(level in ai_response.upper() for level in ["LOW", "MEDIUM", "HIGH", "EMERGENCY"])
    evaluations["format_check"] = {
        "has_urgency_level": has_urgency,
        "urgency_assigned": urgency
    }

    # 4. Urgency alignment check
    urgency_alignment = evaluate_urgency_alignment(patient_input, urgency)
    evaluations["urgency_alignment"] = urgency_alignment

    # 5. Council consensus (if council path was used)
    if route == "council":
        evaluations["council_used"] = True
        if council_votes:
            consensus_metrics = evaluate_council_consensus(council_votes)
            evaluations["council_consensus"] = consensus_metrics
    else:
        evaluations["council_used"] = False

    return evaluations


def log_evaluation_to_span(evaluations: dict, tracer_provider=None):
    """Log evaluation results as OpenTelemetry span attributes for Arize"""
    try:
        from opentelemetry import trace as otel_trace
        from openinference.semconv.trace import SpanAttributes

        # Get tracer
        if tracer_provider:
            tracer = tracer_provider.get_tracer(__name__)
        else:
            tracer = otel_trace.get_tracer(__name__)

        # Create a new span for evaluation with proper semantic conventions
        with tracer.start_as_current_span("evaluation") as eval_span:
            # Mark as evaluation span type using OpenInference conventions
            eval_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, "EVALUATOR")

            # Log evaluations using OpenInference format for Arize Evaluations tab
            eval_results = []

            # 1. Hallucination evaluation
            if "hallucination" in evaluations:
                h = evaluations["hallucination"]
                eval_results.append({
                    "name": "hallucination",
                    "score": h.get("hallucination_score") if h.get("hallucination_score") is not None else 0.0,
                    "label": h.get("label", "unknown")
                })

            # 2. Word count evaluation
            if "word_count" in evaluations:
                wc = evaluations["word_count"]
                eval_results.append({
                    "name": "word_count_limit",
                    "score": 1.0 if wc.get("within_limit") else 0.0,
                    "label": "pass" if wc.get("within_limit") else "fail"
                })

            # 3. Urgency alignment evaluation
            if "urgency_alignment" in evaluations:
                ua = evaluations["urgency_alignment"]
                eval_results.append({
                    "name": "urgency_alignment",
                    "score": 1.0 if ua.get("is_aligned") else 0.0,
                    "label": "aligned" if ua.get("is_aligned") else "misaligned"
                })

            # 4. Council consensus evaluation
            if "council_consensus" in evaluations:
                cc = evaluations["council_consensus"]
                if cc.get("consensus_score") is not None:
                    eval_results.append({
                        "name": "council_consensus",
                        "score": cc.get("consensus_score"),
                        "label": "high" if cc.get("consensus_score") >= 0.8 else "low"
                    })

            # Log each evaluation result as individual attributes
            for idx, eval_result in enumerate(eval_results):
                eval_span.set_attribute(f"llm.evaluation.{idx}.name", eval_result["name"])
                eval_span.set_attribute(f"llm.evaluation.{idx}.score", float(eval_result["score"]))
                eval_span.set_attribute(f"llm.evaluation.{idx}.label", str(eval_result["label"]))

            # Also log as regular attributes for easy filtering
            if "word_count" in evaluations:
                wc = evaluations["word_count"]
                eval_span.set_attribute("eval.word_count", int(wc.get("count")))
                eval_span.set_attribute("eval.word_count.within_limit", bool(wc.get("within_limit")))

            if "urgency_alignment" in evaluations:
                ua = evaluations["urgency_alignment"]
                eval_span.set_attribute("eval.urgency_alignment.is_aligned", bool(ua.get("is_aligned")))
                eval_span.set_attribute("eval.urgency", str(evaluations["format_check"].get("urgency_assigned")))

            if "council_consensus" in evaluations:
                cc = evaluations["council_consensus"]
                if cc.get("consensus_score") is not None:
                    eval_span.set_attribute("eval.council.consensus_score", float(cc.get("consensus_score")))
                    eval_span.set_attribute("eval.council.num_models", int(cc.get("num_models")))

            eval_span.set_attribute("eval.council_used", bool(evaluations.get("council_used", False)))

            # 5. Guardrail results (non-blocking, logs warnings)
            if "guardrails" in evaluations:
                gr = evaluations["guardrails"]
                eval_span.set_attribute("eval.guardrails.all_passed", bool(gr.get("all_passed")))
                eval_span.set_attribute("eval.guardrails.warning_count", len(gr.get("warnings", [])))

                # Log individual guardrail checks
                for idx, check in enumerate(gr.get("checks", [])):
                    eval_span.set_attribute(f"eval.guardrails.{idx}.name", str(check.get("name", f"check_{idx}")))
                    eval_span.set_attribute(f"eval.guardrails.{idx}.passed", bool(check.get("passed")))
                    eval_span.set_attribute(f"eval.guardrails.{idx}.message", str(check.get("message")))

                # Log warnings separately for easy filtering
                for idx, warning in enumerate(gr.get("warnings", [])):
                    eval_span.set_attribute(f"eval.guardrails.warning.{idx}.check", str(warning.get("check")))
                    eval_span.set_attribute(f"eval.guardrails.warning.{idx}.message", str(warning.get("message")))

            # 6. A/B test experiment variants
            if "experiments" in evaluations:
                experiments = evaluations["experiments"]
                eval_span.set_attribute("experiment.count", len(experiments))

                for idx, (exp_name, variant) in enumerate(experiments.items()):
                    eval_span.set_attribute(f"experiment.{idx}.name", str(exp_name))
                    eval_span.set_attribute(f"experiment.{idx}.variant", str(variant))

                # Also log as flat attributes for easier filtering
                for exp_name, variant in experiments.items():
                    eval_span.set_attribute(f"experiment.{exp_name}", str(variant))

            # 7. Performance monitoring metrics
            if "performance" in evaluations:
                perf = evaluations["performance"]
                metrics = perf.get("metrics", {})
                threshold_results = perf.get("threshold_results", {})

                # Log performance status
                eval_span.set_attribute("performance.all_ok", bool(threshold_results.get("all_ok", True)))
                eval_span.set_attribute("performance.critical_count", int(threshold_results.get("critical_count", 0)))
                eval_span.set_attribute("performance.warning_count", int(threshold_results.get("warning_count", 0)))

                # Log individual metrics
                for metric_name, value in metrics.items():
                    eval_span.set_attribute(f"performance.{metric_name}", float(value))

                # Log threshold violations
                for idx, check in enumerate(threshold_results.get("checks", [])):
                    if check.get("status") != "ok":
                        eval_span.set_attribute(f"performance.alert.{idx}.metric", str(check.get("metric")))
                        eval_span.set_attribute(f"performance.alert.{idx}.status", str(check.get("status")))
                        eval_span.set_attribute(f"performance.alert.{idx}.value", float(check.get("value", 0)))
                        if check.get("severity"):
                            eval_span.set_attribute(f"performance.alert.{idx}.severity", str(check.get("severity")))

            print(f"✅ Logged {len(eval_results)} evaluations to Arize")

    except Exception as e:
        print(f"⚠️  Failed to log evaluations to span: {str(e)}")
        import traceback
        traceback.print_exc()
