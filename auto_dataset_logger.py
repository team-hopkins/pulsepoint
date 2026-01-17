"""
Automatic dataset logging for Phoenix traces
Logs every consultation directly to a Phoenix dataset in real-time
"""
from phoenix.client import Client
import config
from datetime import datetime
import pandas as pd
from typing import Dict, Any, Optional
import asyncio
from functools import wraps


class AutoDatasetLogger:
    """
    Automatically log consultations to a Phoenix dataset
    """

    def __init__(self, dataset_name: str = "live_consultations"):
        self.dataset_name = dataset_name
        self.client = None
        self.dataset_id = None
        self._initialize()

    def _initialize(self):
        """Initialize connection to Phoenix"""
        try:
            self.client = Client(
                base_url=config.PHOENIX_COLLECTOR_ENDPOINT,
                api_key=config.PHOENIX_API_KEY
            )
            print(f"✅ Auto-dataset logger initialized")
            print(f"   Dataset: {self.dataset_name}")
            print(f"   All consultations will be logged automatically")
        except Exception as e:
            print(f"⚠️  Auto-dataset logger failed to initialize: {str(e)}")
            self.client = None

    def log_consultation(
        self,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log a single consultation to the dataset

        Args:
            input_data: Input to the consultation (text, image, patient_id, etc.)
            output_data: Output from the consultation (response, urgency, etc.)
            metadata: Additional metadata
        """
        if not self.client:
            return False

        try:
            # Create input/output structure for Phoenix
            example_input = {
                'text': input_data.get('text', ''),
                'patient_id': input_data.get('patient_id', ''),
                'location': input_data.get('location', ''),
                'has_image': 'Yes' if input_data.get('image') else 'No',
            }

            example_output = {
                'response': output_data.get('response', ''),
                'urgency': output_data.get('urgency', ''),
                'confidence': float(output_data.get('confidence', 0.0)),
                'route_taken': output_data.get('route_taken', ''),
            }

            example_metadata = {
                'timestamp': datetime.utcnow().isoformat(),
                'experiment_variants': str(output_data.get('experiment_variants', {})),
            }

            # Add additional metadata if provided
            if metadata:
                example_metadata.update(metadata)

            # Create DataFrame for the example
            df = pd.DataFrame([{
                **example_input,
                **example_output,
                **example_metadata
            }])

            # Add to existing dataset or create new one
            try:
                # Try to add to existing dataset
                self.client.datasets.add_examples_to_dataset(
                    dataset=self.dataset_name,
                    dataframe=df,
                    input_keys=list(example_input.keys()),
                    output_keys=list(example_output.keys()),
                    metadata_keys=list(example_metadata.keys())
                )
                print(f"   📊 Added to dataset '{self.dataset_name}': {output_data.get('urgency', 'UNKNOWN')} - Patient {input_data.get('patient_id', 'unknown')}")
            except Exception as add_error:
                # If dataset doesn't exist, create it with a timestamped name to avoid conflicts
                dataset_with_timestamp = f"{self.dataset_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                print(f"   Creating new dataset '{dataset_with_timestamp}'...")
                self.client.datasets.create_dataset(
                    dataframe=df,
                    name=dataset_with_timestamp,
                    input_keys=list(example_input.keys()),
                    output_keys=list(example_output.keys()),
                    metadata_keys=list(example_metadata.keys())
                )
                # Update the dataset name to use going forward
                self.dataset_name = dataset_with_timestamp
                print(f"   📊 Created dataset and added example: {output_data.get('urgency', 'UNKNOWN')}")

            return True

        except Exception as e:
            print(f"   ⚠️  Failed to log to dataset: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def log_consultation_async(
        self,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Async version of log_consultation
        """
        # Run in background thread to not block
        import threading
        thread = threading.Thread(
            target=self.log_consultation,
            args=(input_data, output_data, metadata)
        )
        thread.daemon = True
        thread.start()


# Global instance
_auto_logger = None


def get_auto_logger(dataset_name: str = "live_consultations") -> AutoDatasetLogger:
    """Get or create the global auto logger instance"""
    global _auto_logger
    if _auto_logger is None:
        _auto_logger = AutoDatasetLogger(dataset_name)
    return _auto_logger


def log_to_dataset_decorator(func):
    """
    Decorator to automatically log consultation results to dataset

    Usage:
        @log_to_dataset_decorator
        def consult(self, text, image, patient_id, location):
            # ... your consultation code
            return result
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get the result from the original function
        result = func(*args, **kwargs)

        # Extract input data from kwargs or args
        # Assuming consult signature: consult(self, text, image, patient_id, location)
        try:
            if len(args) >= 5:
                input_data = {
                    'text': args[1],
                    'image': args[2],
                    'patient_id': args[3],
                    'location': args[4]
                }
            else:
                input_data = {
                    'text': kwargs.get('text'),
                    'image': kwargs.get('image'),
                    'patient_id': kwargs.get('patient_id'),
                    'location': kwargs.get('location')
                }

            # Log to dataset in background
            logger = get_auto_logger()
            logger.log_consultation_async(input_data, result)

        except Exception as e:
            print(f"   ⚠️  Dataset logging error: {str(e)}")

        return result

    return wrapper


def log_to_dataset_async_decorator(func):
    """
    Async version of the decorator for async functions

    Usage:
        @log_to_dataset_async_decorator
        async def consult(request):
            # ... your consultation code
            return result
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Get the result from the original function
        result = await func(*args, **kwargs)

        # Extract input and log in background
        try:
            # For FastAPI endpoints, the request is usually the first arg
            if hasattr(args[0], 'text'):
                request = args[0]
                input_data = {
                    'text': request.text,
                    'image': request.image,
                    'patient_id': request.patient_id,
                    'location': request.location
                }
                output_data = {
                    'response': result.response if hasattr(result, 'response') else str(result),
                    'urgency': result.urgency if hasattr(result, 'urgency') else 'UNKNOWN',
                    'confidence': result.confidence if hasattr(result, 'confidence') else 0.0,
                    'route_taken': result.route_taken if hasattr(result, 'route_taken') else 'unknown'
                }

                logger = get_auto_logger()
                logger.log_consultation_async(input_data, output_data)
        except Exception as e:
            print(f"   ⚠️  Dataset logging error: {str(e)}")

        return result

    return wrapper


if __name__ == "__main__":
    # Test the auto logger
    print("="*80)
    print("AUTO DATASET LOGGER - TEST")
    print("="*80)

    logger = get_auto_logger("test_consultations")

    # Example consultation
    input_data = {
        'text': 'I have a headache',
        'image': None,
        'patient_id': 'test_001',
        'location': 'test'
    }

    output_data = {
        'response': 'Rest and hydrate',
        'urgency': 'LOW',
        'confidence': 0.85,
        'route_taken': 'fast'
    }

    logger.log_consultation(input_data, output_data)

    print("\n" + "="*80)
