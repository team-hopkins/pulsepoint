"""Arize OpenTelemetry monitoring setup - Updated for latest SDK with LangGraph agent visualization"""
from arize.otel import register
from openinference.instrumentation.langchain import LangChainInstrumentor
from openinference.instrumentation.openai import OpenAIInstrumentor
from openinference.instrumentation.vertexai import VertexAIInstrumentor
import config
import logging
from phoenix.otel import register as phoenix_register

tracer_provider = phoenix_register(
  project_name="pulsepoint",
  endpoint="https://app.phoenix.arize.com/s/arnabbibhuti4901",
  auto_instrument=True
)
# Suppress transient gRPC/SSL errors from OTEL exporter
logging.getLogger('opentelemetry.exporter.otlp.proto.grpc.exporter').setLevel(logging.CRITICAL)

def setup_arize_monitoring():
    """
    Initialize Arize monitoring for all LLM calls using latest arize-otel SDK

    Automatically instruments:
    - LangChain (including LangGraph workflows for agent visualization)
    - OpenAI API calls
    - Google Gemini/VertexAI API calls
    - Anthropic API calls (via LangChain)

    Agent graphs will appear in Arize's Agent Path visualization.
    """

    # Validate required configuration
    if not config.ARIZE_SPACE_KEY or not config.ARIZE_API_KEY:
        print("⚠️  Warning: Arize credentials not configured. Set ARIZE_SPACE_KEY and ARIZE_API_KEY in .env")
        print("   Monitoring will not be active until credentials are provided.")
        return None

    try:
        # Register Arize tracer with latest SDK using HTTP protocol
        # HTTP is more reliable than gRPC for cross-platform compatibility
        tracer_provider = register(
            space_id=config.ARIZE_SPACE_KEY,
            api_key=config.ARIZE_API_KEY,
            project_name=config.PROJECT_NAME,
        )

        # Instrument LangChain for automatic tracing
        # NOTE: This also instruments LangGraph automatically!
        # LangGraph agent nodes, edges, and state will be captured
        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)

        # Instrument OpenAI for automatic tracing of direct API calls
        OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)

        # Instrument Google Gemini/VertexAI for automatic tracing
        VertexAIInstrumentor().instrument(tracer_provider=tracer_provider)

        print(f"✅ Arize monitoring initialized successfully!")
        print(f"   Project: {config.PROJECT_NAME}")
        print(f"   Space ID: {config.ARIZE_SPACE_KEY[:8]}...")
        print(f"   Dashboard: https://app.arize.com")
        print(f"   📊 LangGraph agent visualization: ENABLED")

        return tracer_provider

    except Exception as e:
        print(f"❌ Error initializing Arize monitoring: {str(e)}")
        print(f"   Check your credentials and network connection")
        return None
