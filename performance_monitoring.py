"""Performance monitoring and alerting for medical AI system"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PerformanceThreshold:
    """Performance threshold configuration"""
    metric_name: str
    max_value: Optional[float] = None
    min_value: Optional[float] = None
    warning_level: float = 0.8  # Trigger warning at 80% of threshold


class PerformanceMonitor:
    """Monitor performance metrics and detect anomalies"""

    # Define performance thresholds for medical AI system
    THRESHOLDS = {
        "response_latency": PerformanceThreshold(
            metric_name="response_latency",
            max_value=15.0,  # Max 15 seconds for consultation
            warning_level=0.8  # Warn at 12 seconds
        ),
        "word_count": PerformanceThreshold(
            metric_name="word_count",
            max_value=30.0,  # TTS limit
            warning_level=0.9  # Warn at 27 words
        ),
        "confidence_score": PerformanceThreshold(
            metric_name="confidence_score",
            min_value=0.7,  # Minimum acceptable confidence
            warning_level=0.9  # Warn if below 0.77
        ),
        "hallucination_score": PerformanceThreshold(
            metric_name="hallucination_score",
            max_value=0.3,  # Max acceptable hallucination likelihood
            warning_level=0.7  # Warn at 0.21
        ),
        "council_consensus": PerformanceThreshold(
            metric_name="council_consensus",
            min_value=0.66,  # At least 2/3 agreement
            warning_level=0.9  # Warn if below 0.73
        )
    }

    @staticmethod
    def check_threshold(metric_name: str, value: float) -> Dict[str, Any]:
        """
        Check if metric violates performance threshold

        Args:
            metric_name: Name of the metric
            value: Metric value

        Returns:
            Dict with threshold check results
        """
        threshold = PerformanceMonitor.THRESHOLDS.get(metric_name)

        if not threshold:
            return {
                "metric": metric_name,
                "value": value,
                "status": "unknown",
                "message": "No threshold defined"
            }

        status = "ok"
        message = ""
        severity = None

        # Check max threshold
        if threshold.max_value is not None:
            warning_threshold = threshold.max_value * threshold.warning_level
            if value > threshold.max_value:
                status = "critical"
                severity = "error"
                message = f"{metric_name} exceeded max threshold: {value} > {threshold.max_value}"
            elif value > warning_threshold:
                status = "warning"
                severity = "warning"
                message = f"{metric_name} approaching max threshold: {value} > {warning_threshold:.2f}"

        # Check min threshold
        if threshold.min_value is not None:
            warning_threshold = threshold.min_value / threshold.warning_level
            if value < threshold.min_value:
                status = "critical"
                severity = "error"
                message = f"{metric_name} below min threshold: {value} < {threshold.min_value}"
            elif value < warning_threshold:
                status = "warning"
                severity = "warning"
                message = f"{metric_name} approaching min threshold: {value} < {warning_threshold:.2f}"

        return {
            "metric": metric_name,
            "value": value,
            "status": status,
            "severity": severity,
            "message": message,
            "threshold": {
                "max": threshold.max_value,
                "min": threshold.min_value
            }
        }

    @staticmethod
    def check_all_metrics(metrics: Dict[str, float]) -> Dict[str, Any]:
        """
        Check all performance metrics against thresholds

        Args:
            metrics: Dict of metric_name -> value

        Returns:
            Dict with all threshold check results
        """
        results = {
            "checks": [],
            "critical_count": 0,
            "warning_count": 0,
            "all_ok": True
        }

        for metric_name, value in metrics.items():
            check_result = PerformanceMonitor.check_threshold(metric_name, value)
            results["checks"].append(check_result)

            if check_result["status"] == "critical":
                results["critical_count"] += 1
                results["all_ok"] = False
            elif check_result["status"] == "warning":
                results["warning_count"] += 1

        return results


def extract_performance_metrics(
    processing_time: float,
    evaluations: Dict[str, Any],
    confidence: float
) -> Dict[str, float]:
    """
    Extract performance metrics from consultation results

    Args:
        processing_time: Time taken for consultation
        evaluations: Evaluation results
        confidence: Confidence score

    Returns:
        Dict of metric_name -> value
    """
    metrics = {
        "response_latency": processing_time,
        "confidence_score": confidence
    }

    # Extract word count
    if "word_count" in evaluations:
        metrics["word_count"] = float(evaluations["word_count"].get("count", 0))

    # Extract hallucination score
    if "hallucination" in evaluations:
        h_score = evaluations["hallucination"].get("hallucination_score")
        if h_score is not None:
            metrics["hallucination_score"] = float(h_score)

    # Extract council consensus
    if "council_consensus" in evaluations:
        consensus = evaluations["council_consensus"].get("consensus_score")
        if consensus is not None:
            metrics["council_consensus"] = float(consensus)

    return metrics


def log_performance_metrics(metrics: Dict[str, float], threshold_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format performance metrics for OpenTelemetry logging

    Args:
        metrics: Performance metrics
        threshold_results: Threshold check results

    Returns:
        Dict formatted for span attributes
    """
    attributes = {
        "performance.all_ok": threshold_results["all_ok"],
        "performance.critical_count": threshold_results["critical_count"],
        "performance.warning_count": threshold_results["warning_count"]
    }

    # Log individual metrics
    for metric_name, value in metrics.items():
        attributes[f"performance.{metric_name}"] = value

    # Log threshold violations
    for idx, check in enumerate(threshold_results["checks"]):
        if check["status"] != "ok":
            attributes[f"performance.alert.{idx}.metric"] = check["metric"]
            attributes[f"performance.alert.{idx}.status"] = check["status"]
            attributes[f"performance.alert.{idx}.value"] = check["value"]
            if check.get("severity"):
                attributes[f"performance.alert.{idx}.severity"] = check["severity"]

    return attributes
