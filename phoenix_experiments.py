"""
Phoenix Cloud Experiments - Dataset & Experiments API
Upload evaluation dataset and run experiments comparing prompt variants
"""
import os
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
import time

# Phoenix imports for experiments
from phoenix.experiments import run_experiment, evaluate_experiment
from phoenix.experiments.types import Example, EvaluationResult
from openinference.instrumentation.openai import OpenAIInstrumentor

from council import MedicalCouncil
from evaluation_dataset import get_dataset
from ab_testing import ABTestConfig
import config

# Set Phoenix environment variables
os.environ["PHOENIX_API_KEY"] = config.PHOENIX_API_KEY
os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = config.PHOENIX_COLLECTOR_ENDPOINT


def create_phoenix_dataset():
    """
    Create Phoenix dataset from evaluation cases

    Returns:
        List of Example objects for Phoenix
    """
    dataset = get_dataset()

    examples = []
    for test_case in dataset:
        example = Example(
            input={
                "text": test_case["input"],
                "patient_id": f"eval_{test_case['id']}",
                "location": "experiment"
            },
            reference_output={
                "expected_urgency": test_case["expected_urgency"],
                "expected_keywords": test_case["expected_keywords"],
                "category": test_case["category"]
            },
            metadata={
                "test_case_id": test_case["id"],
                "category": test_case["category"]
            }
        )
        examples.append(example)

    print(f"✅ Created Phoenix dataset with {len(examples)} examples")
    return examples


def run_consultation_with_variant(example: Example, variant: str) -> Dict[str, Any]:
    """
    Run a single consultation with specific variant

    Args:
        example: Phoenix Example object
        variant: Prompt variant to test

    Returns:
        Consultation result
    """
    council = MedicalCouncil()

    # Override variant assignment
    original_get_variant = ABTestConfig.get_variant
    ABTestConfig.get_variant = lambda exp_name, pid: variant

    try:
        result = council.consult(
            text=example.input["text"],
            image=None,
            patient_id=example.input["patient_id"],
            location=example.input["location"]
        )

        return {
            "response": result["response"],
            "urgency": result["urgency"],
            "confidence": result["confidence"],
            "route": result["route_taken"],
            "council_votes": result.get("council_votes", {}),
            "variant": variant
        }
    finally:
        ABTestConfig.get_variant = original_get_variant


def evaluate_urgency_accuracy(output: Dict[str, Any], expected: Dict[str, Any]) -> float:
    """Evaluate if urgency level matches expectation"""
    return 1.0 if output["urgency"] == expected["expected_urgency"] else 0.0


def evaluate_keyword_presence(output: Dict[str, Any], expected: Dict[str, Any]) -> float:
    """Evaluate if response contains expected keywords"""
    response = output["response"].lower()
    keywords = expected["expected_keywords"]

    matches = sum(1 for keyword in keywords if keyword.lower() in response)
    return matches / len(keywords) if keywords else 0.0


def evaluate_word_count_compliance(output: Dict[str, Any], expected: Dict[str, Any]) -> float:
    """Evaluate if response is within 30-word limit"""
    word_count = len(output["response"].split())
    return 1.0 if word_count <= 35 else 0.0


def run_phoenix_experiment_manual():
    """
    Manually run experiment and create CSV for Phoenix Cloud upload

    Phoenix Cloud doesn't have a direct Python API for experiments yet,
    so we'll run the experiment locally and create properly formatted CSVs
    to upload to Phoenix Cloud UI.
    """
    print("\n" + "="*80)
    print("PHOENIX CLOUD EXPERIMENTS - Manual Dataset Creation")
    print("="*80)
    print(f"Project: {config.PROJECT_NAME}")
    print(f"Phoenix Endpoint: {config.PHOENIX_COLLECTOR_ENDPOINT}")
    print("="*80 + "\n")

    # Get dataset
    dataset = get_dataset()
    variants = ["control", "detailed", "empathetic"]

    all_results = []

    for variant in variants:
        print(f"\n{'='*60}")
        print(f"Testing Variant: {variant.upper()}")
        print(f"{'='*60}")

        council = MedicalCouncil()

        for idx, test_case in enumerate(dataset, 1):
            print(f"  [{idx}/{len(dataset)}] {test_case['id']}...", end=" ")

            # Override variant
            original_get_variant = ABTestConfig.get_variant
            ABTestConfig.get_variant = lambda exp_name, pid: variant

            try:
                result = council.consult(
                    text=test_case["input"],
                    image=None,
                    patient_id=f"exp_{variant}_{test_case['id']}",
                    location="experiment"
                )

                # Calculate evaluations
                urgency_match = result["urgency"] == test_case["expected_urgency"]
                response_lower = result["response"].lower()
                keyword_matches = sum(1 for kw in test_case["expected_keywords"] if kw.lower() in response_lower)
                word_count = len(result["response"].split())

                all_results.append({
                    # Input fields
                    "test_case_id": test_case["id"],
                    "category": test_case["category"],
                    "input_text": test_case["input"],
                    "expected_urgency": test_case["expected_urgency"],
                    "expected_keywords": ", ".join(test_case["expected_keywords"]),

                    # Variant
                    "variant": variant,

                    # Output fields
                    "response": result["response"],
                    "urgency": result["urgency"],
                    "confidence": result["confidence"],
                    "route": result["route_taken"],
                    "word_count": word_count,

                    # Evaluation metrics
                    "urgency_accuracy": 1.0 if urgency_match else 0.0,
                    "keyword_coverage": keyword_matches / len(test_case["expected_keywords"]),
                    "word_limit_compliance": 1.0 if word_count <= 30 else 0.0,

                    # Metadata
                    "timestamp": datetime.utcnow().isoformat()
                })

                symbol = "✓" if urgency_match else "✗"
                print(f"{symbol} {result['urgency']} (expected: {test_case['expected_urgency']})")

            except Exception as e:
                print(f"❌ ERROR: {str(e)}")
                all_results.append({
                    "test_case_id": test_case["id"],
                    "category": test_case["category"],
                    "input_text": test_case["input"],
                    "variant": variant,
                    "error": str(e)
                })
            finally:
                ABTestConfig.get_variant = original_get_variant

            # Rate limiting
            time.sleep(0.5)

    # Create DataFrame
    df = pd.DataFrame(all_results)

    # Calculate summary metrics
    print("\n" + "="*80)
    print("RESULTS SUMMARY BY VARIANT")
    print("="*80)

    summary_data = []
    for variant in variants:
        variant_df = df[df["variant"] == variant]

        if len(variant_df) > 0:
            summary = {
                "Variant": variant,
                "Total Cases": len(variant_df),
                "Urgency Accuracy": f"{variant_df['urgency_accuracy'].mean():.1%}",
                "Avg Keyword Coverage": f"{variant_df['keyword_coverage'].mean():.1%}",
                "Word Limit Compliance": f"{variant_df['word_limit_compliance'].mean():.1%}",
                "Avg Confidence": f"{variant_df['confidence'].mean():.3f}",
                "Avg Word Count": f"{variant_df['word_count'].mean():.1f}"
            }
            summary_data.append(summary)

    summary_df = pd.DataFrame(summary_data)
    print("\n" + summary_df.to_string(index=False))
    print("\n" + "="*80)

    # Save files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Detailed results
    results_file = f"phoenix_experiments_detailed_{timestamp}.csv"
    df.to_csv(results_file, index=False)
    print(f"\n📁 Detailed results: {results_file}")

    # Summary metrics
    summary_file = f"phoenix_experiments_summary_{timestamp}.csv"
    summary_df.to_csv(summary_file, index=False)
    print(f"📁 Summary metrics: {summary_file}")

    # Best variant
    best_variant = summary_df.loc[summary_df['Urgency Accuracy'].str.rstrip('%').astype(float).idxmax(), 'Variant']
    print(f"\n🏆 BEST VARIANT: {best_variant.upper()}")

    print("\n" + "="*80)
    print("NEXT STEPS:")
    print("="*80)
    print("1. Go to Phoenix Cloud: https://app.phoenix.arize.com")
    print("2. Navigate to 'Datasets' section")
    print(f"3. Upload {results_file}")
    print("4. Create an Experiment using the uploaded dataset")
    print("5. Compare variants side-by-side in Phoenix UI")
    print("="*80 + "\n")

    # Optionally upload to Phoenix dataset
    upload = input("Would you like to upload this to Phoenix as a dataset? (y/n): ").strip().lower()
    if upload == 'y':
        upload_to_phoenix_dataset(df, timestamp)

    return df, summary_df, results_file, summary_file


def upload_to_phoenix_dataset(df: pd.DataFrame, timestamp: str):
    """
    Upload experiment results directly to Phoenix as a dataset

    Args:
        df: DataFrame with experiment results
        timestamp: Timestamp for dataset naming
    """
    try:
        from phoenix.client import Client

        print("\n📤 Uploading to Phoenix Cloud...")

        # Connect to Phoenix
        px_client = Client(
            base_url=config.PHOENIX_COLLECTOR_ENDPOINT,
            api_key=config.PHOENIX_API_KEY
        )

        dataset_name = f"medical_experiments_{timestamp}"

        # Create dataset
        dataset = px_client.datasets.create_dataset(
            dataframe=df,
            name=dataset_name,
            input_keys=["input_text", "test_case_id", "category"],
            output_keys=["response", "urgency", "confidence", "route"],
        )

        print(f"✅ Dataset uploaded to Phoenix!")
        print(f"   Dataset: {dataset_name}")
        print(f"   Records: {len(df)}")
        print(f"   View at: {config.PHOENIX_COLLECTOR_ENDPOINT}/datasets")

    except Exception as e:
        print(f"❌ Error uploading to Phoenix: {str(e)}")
        print(f"   You can manually upload {dataset_name}.csv from the Phoenix UI")


if __name__ == "__main__":
    run_phoenix_experiment_manual()
