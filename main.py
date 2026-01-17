"""
CarePoint AI System - FastAPI Application
Medical consultation endpoint with LLM Council and Arize monitoring

Features:
- Multi-model LLM council for medical consultations
- Intelligent routing (fast/visual/council paths)
- Complete observability with Arize tracing
- Structured medical assessment outputs
"""
import time
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import uvicorn

# Import our modules
from monitoring import setup_arize_monitoring
from council import MedicalCouncil
from evaluators import evaluate_response_quality, log_evaluation_to_span
from guardrails import run_all_guardrails
from performance_monitoring import PerformanceMonitor, extract_performance_metrics, log_performance_metrics
from mongodb_client import (
    connect_mongodb, close_mongodb, store_consultation, store_feedback,
    update_consultation_feedback, get_patient_history, get_urgency_distribution,
    get_model_consensus_stats, get_consultation_by_trace_id
)
import config

# Setup Arize monitoring with OpenTelemetry
tracer_provider = setup_arize_monitoring()

# Initialize FastAPI app with enhanced metadata
app = FastAPI(
    title="CarePoint AI System",
    description="AI-powered medical consultation API with LLM Council deliberation",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware for web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Medical Council with all LLM agents
print("🏥 Initializing Medical Council...")
medical_council = MedicalCouncil()


# Define Pydantic models first
class QAPair(BaseModel):
    """Single question-answer pair from conversation"""
    assistant: str = Field(..., description="Question asked by the assistant")
    human: str = Field(..., description="Patient's response")


def format_qa_conversation(qa_pairs: list[QAPair]) -> str:
    """
    Convert Q&A conversation pairs into a formatted text string
    
    Args:
        qa_pairs: List of QAPair objects
        
    Returns:
        Formatted conversation string
    """
    conversation_lines = []
    for i, qa in enumerate(qa_pairs, 1):
        conversation_lines.append(f"Q{i}: {qa.assistant}")
        conversation_lines.append(f"A{i}: {qa.human}")
    
    return "\n".join(conversation_lines)


@app.on_event("startup")
async def startup_db_client():
    """Initialize MongoDB connection on startup"""
    await connect_mongodb()
    print("🚀 Application startup complete")


@app.on_event("shutdown")
async def shutdown_db_client():
    """Close MongoDB connection on shutdown"""
    await close_mongodb()
    print("👋 Application shutdown complete")


class ConsultationRequest(BaseModel):
    """Request model for consultation endpoint"""
    text: Optional[str | list[QAPair]] = Field(
        None, 
        description="Either a simple text string OR a list of Q&A conversation pairs"
    )
    image: Optional[str] = Field(None, description="Base64 encoded image")
    patient_id: str = Field(..., description="Unique patient identifier")
    location: str = Field(..., description="Patient location/device station")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "text": "I have a persistent headache and feel dizzy",
                    "patient_id": "P12345",
                    "location": "Station-A-Floor2"
                },
                {
                    "text": [
                        {"assistant": "Can you describe the pain?", "human": "it feels like pressure"},
                        {"assistant": "Where is the pain located?", "human": "in my back"}
                    ],
                    "patient_id": "P12345",
                    "location": "Station-A-Floor2"
                }
            ]
        }


class ConsultationResponse(BaseModel):
    """Response model for consultation endpoint"""
    response: str = Field(..., description="Medical guidance and recommendations")
    urgency: str = Field(..., description="Urgency level: LOW/MEDIUM/HIGH/EMERGENCY")
    confidence: float = Field(..., description="Confidence score (0-1)")
    council_votes: Dict[str, Any] = Field(..., description="Individual model assessments")
    route_taken: str = Field(..., description="Processing path: fast/visual/council")
    patient_id: str
    location: str
    trace_id: Optional[str] = Field(None, description="OpenTelemetry trace ID for feedback linking")


class FeedbackRequest(BaseModel):
    """Request model for human feedback"""
    trace_id: str = Field(..., description="Trace ID from consultation response")
    rating: int = Field(..., description="1-5 star rating or thumbs up (1) / down (0)")
    feedback_text: Optional[str] = Field(None, description="Optional text feedback")
    patient_id: str = Field(..., description="Patient identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "trace_id": "abc123xyz",
                "rating": 1,
                "feedback_text": "Response was helpful and clear",
                "patient_id": "P12345"
            }
        }


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "CarePoint AI System",
        "version": "1.0.0",
        "monitoring": "Arize enabled"
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "api": "operational",
        "council": "ready",
        "models": ["gpt-4o", "claude-sonnet-4", "gemini-2.0-flash"],
        "monitoring": "active"
    }


@app.post("/consult", response_model=ConsultationResponse)
async def consult(request: ConsultationRequest) -> ConsultationResponse:
    from opentelemetry import trace as otel_trace
    import uuid

    start_time = time.time()

    # Get current trace ID for feedback linking
    current_span = otel_trace.get_current_span()
    trace_id = None
    if current_span and current_span.get_span_context().is_valid:
        trace_id = format(current_span.get_span_context().trace_id, '032x')
    
    # Fallback: Generate UUID if no OpenTelemetry trace_id
    if not trace_id:
        trace_id = str(uuid.uuid4())

    try:
        # Input validation
        if not request.text and not request.image:
            raise HTTPException(
                status_code=400,
                detail="Either text or image must be provided"
            )
        
        # Convert Q&A format to text if needed
        formatted_text: Optional[str] = None
        if request.text:
            if isinstance(request.text, list):
                formatted_text = format_qa_conversation(request.text)
                input_type = "Conversation Q&A"
            else:
                formatted_text = request.text
                input_type = "Text only" if not request.image else "Text + Image"
        else:
            input_type = "Image only"
        
        print(f"📋 New consultation request received")
        print(f"   Patient: {request.patient_id}")
        print(f"   Location: {request.location}")
        print(f"   Input: {input_type}")

        # Run consultation through LangGraph council
        # Image will be uploaded to Spaces inside council.consult()
        result = medical_council.consult(
            text=formatted_text,
            image=request.image,
            patient_id=request.patient_id,
            location=request.location
        )

        # Get image metadata from council result
        image_metadata = result.get("image_storage")

        # Calculate processing time
        processing_time = round(time.time() - start_time, 2)

        # Run guardrails first - block response if any fail
        print(f"   🛡️ Running guardrails validation...")
        guardrail_results = run_all_guardrails(
            patient_input=formatted_text or "Image consultation",
            response=result["response"],
            urgency=result["urgency"],
            route=result["route_taken"]
        )

        # If guardrails fail, return error
        if not guardrail_results["all_passed"]:
            print(f"   ❌ Guardrail failed: {guardrail_results['blocked_reason']}")
            raise HTTPException(
                status_code=400,
                detail=f"Response blocked by guardrails: {guardrail_results['blocked_reason']}"
            )

        # Run evaluations (hallucination detection, word count, format check, urgency alignment, council consensus)
        print(f"   🔍 Running quality evaluations...")
        evaluations = evaluate_response_quality(
            patient_input=formatted_text or "Image consultation",
            ai_response=result["response"],
            urgency=result["urgency"],
            route=result["route_taken"],
            council_votes=result.get("council_votes", {})
        )

        # Add guardrail results to evaluations
        evaluations["guardrails"] = guardrail_results

        # Add experiment variants to evaluations
        evaluations["experiments"] = result.get("experiment_variants", {})

        # Check performance thresholds
        performance_metrics = extract_performance_metrics(
            processing_time=processing_time,
            evaluations=evaluations,
            confidence=result["confidence"]
        )
        threshold_results = PerformanceMonitor.check_all_metrics(performance_metrics)

        # Log performance alerts if any
        if threshold_results["critical_count"] > 0:
            print(f"   🚨 {threshold_results['critical_count']} critical performance alerts!")
            for check in threshold_results["checks"]:
                if check["status"] == "critical":
                    print(f"      ❌ {check['message']}")
        elif threshold_results["warning_count"] > 0:
            print(f"   ⚠️  {threshold_results['warning_count']} performance warnings")

        # Add performance data to evaluations
        evaluations["performance"] = {
            "metrics": performance_metrics,
            "threshold_results": threshold_results
        }

        # Log evaluations to OpenTelemetry span for Arize
        log_evaluation_to_span(evaluations, tracer_provider)

        # Store consultation in MongoDB
        consultation_record = {
            "timestamp": datetime.utcnow(),
            "patient_id": request.patient_id,
            "location": request.location,
            "input": {
                "text": formatted_text,
                "has_image": request.image is not None,
                "is_conversation": isinstance(request.text, list),
                "qa_pairs_count": len(request.text) if isinstance(request.text, list) else 0,
                "image_storage": image_metadata if image_metadata else None
            },
            "output": {
                "response": result["response"],
                "urgency": result["urgency"],
                "confidence": result["confidence"]
            },
            "council_votes": result["council_votes"],
            "route": result["route_taken"],
            "evaluations": {
                "word_count": evaluations.get("word_count"),
                "urgency_alignment": evaluations.get("urgency_alignment"),
                "council_consensus": evaluations.get("council_consensus"),
                "guardrails_passed": evaluations.get("guardrails", {}).get("all_passed")
            },
            "trace_id": trace_id,
            "experiment_variants": result.get("experiment_variants", {}),
            "processing_time": processing_time
        }

        try:
            await store_consultation(consultation_record)
        except Exception as e:
            print(f"⚠️  Failed to store consultation in MongoDB: {str(e)}")
            # Don't fail the request if MongoDB storage fails

        # Auto-log to Phoenix dataset
        try:
            from auto_dataset_logger import get_auto_logger
            logger = get_auto_logger("pulsepoint")
            logger.log_consultation_async(
                input_data={
                    'text': formatted_text,
                    'image': request.image,
                    'patient_id': request.patient_id,
                    'location': request.location
                },
                output_data={
                    'response': result["response"],
                    'urgency': result["urgency"],
                    'confidence': result["confidence"],
                    'route_taken': result["route_taken"],
                    'experiment_variants': result.get("experiment_variants", {})
                },
                metadata={
                    'processing_time': processing_time,
                    'trace_id': trace_id
                }
            )
        except Exception as e:
            print(f"⚠️  Failed to log to Phoenix dataset: {str(e)}")
            # Don't fail the request if dataset logging fails

        # Build response
        response = ConsultationResponse(
            response=result["response"],
            urgency=result["urgency"],
            confidence=result["confidence"],
            council_votes=result["council_votes"],
            route_taken=result["route_taken"],
            patient_id=request.patient_id,
            location=request.location,
            trace_id=trace_id
        )

        print(f"\n✅ Consultation completed successfully")
        print(f"   Route: {result['route_taken']}")
        print(f"   Urgency: {result['urgency']}")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Processing time: {processing_time}s")
        print(f"   Models used: {len(result['council_votes'])}")

        # Log evaluation results
        if evaluations.get("hallucination"):
            h = evaluations["hallucination"]
            print(f"   📊 Hallucination: {h['label']} (score: {h.get('hallucination_score', 'N/A')})")
        if evaluations.get("word_count"):
            wc = evaluations["word_count"]
            status = "✓" if wc["within_limit"] else "✗"
            print(f"   📊 Word count: {wc['count']}/30 {status}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        processing_time = round(time.time() - start_time, 2)
        print(f"\n Consultation failed after {processing_time}s")
        print(f"   Patient: {request.patient_id}")
        print(f"   Error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Consultation failed: {str(e)}"
        )


@app.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """Submit human feedback for a consultation"""
    from opentelemetry import trace as otel_trace
    from openinference.semconv.trace import SpanAttributes

    try:
        # Get tracer
        tracer = tracer_provider.get_tracer(__name__)

        # Create feedback span linked to original trace
        with tracer.start_as_current_span("feedback") as feedback_span:
            # Mark as feedback span
            feedback_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, "CHAIN")

            # Log feedback attributes
            feedback_span.set_attribute("feedback.trace_id", feedback.trace_id)
            feedback_span.set_attribute("feedback.rating", feedback.rating)
            feedback_span.set_attribute("feedback.patient_id", feedback.patient_id)

            if feedback.feedback_text:
                feedback_span.set_attribute("feedback.text", feedback.feedback_text)

            # Determine feedback label
            if feedback.rating == 1:
                feedback_label = "positive"
            elif feedback.rating == 0:
                feedback_label = "negative"
            else:
                feedback_label = f"rating_{feedback.rating}"

            feedback_span.set_attribute("feedback.label", feedback_label)

            print(f"📝 Feedback received for trace {feedback.trace_id}: {feedback_label}")

        # Store feedback in MongoDB
        try:
            await store_feedback(feedback.trace_id, {
                "rating": feedback.rating,
                "feedback_text": feedback.feedback_text,
                "patient_id": feedback.patient_id
            })

            # Update the original consultation record with feedback
            await update_consultation_feedback(feedback.trace_id, feedback.rating)
        except Exception as e:
            print(f"⚠️  Failed to store feedback in MongoDB: {str(e)}")
            # Don't fail the request if MongoDB storage fails

        return {
            "status": "success",
            "message": "Feedback recorded",
            "trace_id": feedback.trace_id,
            "rating": feedback.rating
        }

    except Exception as e:
        print(f"⚠️  Failed to record feedback: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to record feedback: {str(e)}"
        )


@app.get("/stats")
async def get_stats():
    """Get basic statistics (placeholder for Arize dashboard integration)"""
    return {
        "message": "Full analytics available in Arize dashboard",
        "arize_project": config.PROJECT_NAME,
        "view_dashboard": "https://app.arize.com"
    }


@app.get("/analytics/urgency-distribution")
async def urgency_distribution(hours: int = 24):
    """
    Get urgency level distribution over last N hours

    Args:
        hours: Number of hours to analyze (default: 24)

    Returns:
        Distribution of urgency levels
    """
    try:
        distribution = await get_urgency_distribution(hours)

        return {
            "status": "success",
            "period_hours": hours,
            "distribution": distribution,
            "total_consultations": sum(distribution.values())
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get urgency distribution: {str(e)}"
        )


@app.get("/analytics/patient-history/{patient_id}")
async def patient_history(patient_id: str, limit: int = 10):
    """
    Get consultation history for a specific patient

    Args:
        patient_id: Patient identifier
        limit: Maximum number of records (default: 10)

    Returns:
        List of patient consultations
    """
    try:
        history = await get_patient_history(patient_id, limit)

        return {
            "status": "success",
            "patient_id": patient_id,
            "consultation_count": len(history),
            "consultations": history
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get patient history: {str(e)}"
        )


@app.get("/analytics/model-consensus")
async def model_consensus(days: int = 7):
    """
    Get model consensus statistics

    Args:
        days: Number of days to analyze (default: 7)

    Returns:
        Consensus metrics between models
    """
    try:
        stats = await get_model_consensus_stats(days)

        return {
            "status": "success",
            **stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get consensus stats: {str(e)}"
        )


@app.get("/analytics/consultation/{trace_id}")
async def get_consultation(trace_id: str):
    """
    Retrieve a specific consultation by trace ID

    Args:
        trace_id: OpenTelemetry trace ID

    Returns:
        Consultation details
    """
    try:
        consultation = await get_consultation_by_trace_id(trace_id)

        if not consultation:
            raise HTTPException(
                status_code=404,
                detail=f"Consultation not found: {trace_id}"
            )

        return {
            "status": "success",
            "consultation": consultation
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve consultation: {str(e)}"
        )


@app.get("/analytics/consultation/{trace_id}/image")
async def get_consultation_image(trace_id: str, regenerate_url: bool = False):
    """
    Get image URL from consultation by trace ID
    
    Args:
        trace_id: OpenTelemetry trace ID
        regenerate_url: If True, generate a fresh signed URL (default: False)
    
    Returns:
        Image storage details with URL
    """
    try:
        consultation = await get_consultation_by_trace_id(trace_id)
        
        if not consultation:
            raise HTTPException(
                status_code=404,
                detail=f"Consultation not found: {trace_id}"
            )
        
        # Get image storage metadata
        image_storage = consultation.get("input", {}).get("image_storage")
        
        if not image_storage:
            raise HTTPException(
                status_code=404,
                detail="No image found in this consultation"
            )
        
        # Regenerate signed URL if requested (since they expire after 1 hour)
        if regenerate_url:
            from spaces_storage import get_spaces_storage
            spaces = get_spaces_storage()
            object_key = image_storage.get("key")
            
            if object_key and spaces.client:
                fresh_url = spaces.get_signed_url(object_key, expires_in=3600)
                if fresh_url:
                    image_storage["url"] = fresh_url
                    image_storage["url_regenerated"] = True
        
        return {
            "status": "success",
            "trace_id": trace_id,
            "patient_id": consultation.get("patient_id"),
            "image_storage": image_storage
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve image: {str(e)}"
        )


if __name__ == "__main__":
    print(f"Arize Project: {config.PROJECT_NAME}")
    print(f"Environment: {config.ENVIRONMENT}")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if config.ENVIRONMENT == "development" else False,
        log_level="info"
    )