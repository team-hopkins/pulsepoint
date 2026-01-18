"""LangGraph orchestration for council-based decision making"""
from typing import TypedDict, Literal, Optional, Dict, Any, NotRequired
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
import config
from ab_testing import ABTestConfig, get_prompt_for_variant, log_experiment_assignment

class ConsultationState(TypedDict):
    """State passed between council nodes"""
    text: Optional[str]
    image: Optional[str]
    patient_id: str
    location: str
    route: Literal["fast", "visual", "council"]
    retrieved_context: NotRequired[Optional[str]]  # RAG: Medical knowledge retrieved from vector DB
    responses: Dict[str, str]
    votes: Dict[str, Dict[str, Any]]
    final_response: str
    urgency: str
    confidence: float
    experiment_variants: Dict[str, str]  # A/B test variant assignments
    failed_models: NotRequired[list]  # Models that failed due to quota/rate limits


class MedicalCouncil:
    """LangGraph-based medical council with multiple LLM agents"""
    
    def __init__(self):
        # Initialize models with latest versions
        self.gpt4 = ChatOpenAI(model="gpt-5.2")
        self.claude = ChatAnthropic(model="claude-opus-4-5-20251101", temperature=0.3)
        self.gemini = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)

        # Build LangGraph workflow
        self.graph = self._build_graph()

        print("✅ Medical Council initialized with 3 LLM agents")
    
    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow"""
        workflow = StateGraph(ConsultationState)

        # Add nodes
        workflow.add_node("orchestrator", self.orchestrator)
        workflow.add_node("retrieve_knowledge", self.retrieve_knowledge)
        workflow.add_node("fast_path", self.fast_path)
        workflow.add_node("visual_path", self.visual_path)
        workflow.add_node("council_debate", self.council_debate)
        workflow.add_node("synthesize", self.synthesize)

        # Define edges
        workflow.set_entry_point("orchestrator")

        # Always retrieve knowledge after orchestration
        workflow.add_edge("orchestrator", "retrieve_knowledge")

        def route_decision(state: ConsultationState) -> str:
            if state["route"] == "fast":
                return "fast_path"
            elif state["route"] == "visual":
                return "visual_path"
            else:
                return "council_debate"

        workflow.add_conditional_edges(
            "retrieve_knowledge",
            route_decision,
            {
                "fast_path": "fast_path",
                "visual_path": "visual_path",
                "council_debate": "council_debate"
            }
        )

        workflow.add_edge("fast_path", "synthesize")
        workflow.add_edge("visual_path", "synthesize")
        workflow.add_edge("council_debate", "synthesize")
        workflow.add_edge("synthesize", END)

        return workflow.compile()
    
    def orchestrator(self, state: ConsultationState) -> ConsultationState:
        """Route consultation based on input type and urgency"""
        text = state.get("text", "")
        has_image = state.get("image") is not None
        patient_id = state.get("patient_id", "")

        # Assign A/B test variants
        prompt_variant = ABTestConfig.get_variant("prompt_style", patient_id)
        state["experiment_variants"] = {
            "prompt_style": prompt_variant
        }

        # Check for high-stakes keywords
        is_high_stakes = any(keyword in text.lower() for keyword in config.HIGH_STAKES_KEYWORDS)

        # Route images to council for multi-model analysis
        if has_image or is_high_stakes:
            state["route"] = "council"
        else:
            state["route"] = "fast"

        print(f"🔀 Orchestrator: Routing to {state['route']} path (prompt variant: {prompt_variant})")
        return state

    def retrieve_knowledge(self, state: ConsultationState) -> ConsultationState:
        """Retrieve relevant medical knowledge from vector database (RAG)"""
        text = state.get("text", "")

        if not text:
            state["retrieved_context"] = None
            return state

        try:
            # Import here to avoid circular dependency
            from embeddings import generate_embedding
            from mongodb_client import search_knowledge_base
            import asyncio
            from concurrent.futures import ThreadPoolExecutor

            print("   🔍 Retrieving relevant medical knowledge...")

            # Generate embedding for patient symptoms (synchronous operation)
            query_embedding = generate_embedding(text)

            # Run async search in a separate thread with its own event loop
            def run_async_search():
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(search_knowledge_base(query_embedding, limit=3))
                    return result
                finally:
                    loop.close()

            # Execute in thread pool to avoid event loop conflicts
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_async_search)
                relevant_docs = future.result(timeout=10)  # 10 second timeout

            if relevant_docs:
                # Format context from top retrieved documents
                context_parts = []
                for idx, doc in enumerate(relevant_docs, 1):
                    similarity = doc.get("similarity_score", 0)
                    title = doc.get("title", "Unknown")
                    content = doc.get("content", "")[:500]  # Limit content length
                    urgency_indicators = doc.get("urgency_indicators", [])
                    red_flags = doc.get("red_flags", [])

                    context_parts.append(f"""
Reference {idx} (Similarity: {similarity:.2f}):
Title: {title}
Urgency Indicators: {', '.join(urgency_indicators)}
Red Flags: {', '.join(red_flags)}
Content: {content}
""")

                retrieved_context = "\n---\n".join(context_parts)
                state["retrieved_context"] = retrieved_context
                print(f"   ✅ Retrieved {len(relevant_docs)} relevant knowledge documents")
            else:
                state["retrieved_context"] = None
                print("   ⚠️  No relevant knowledge found")

        except Exception as e:
            print(f"   ❌ Knowledge retrieval failed: {str(e)}")
            import traceback
            traceback.print_exc()
            state["retrieved_context"] = None

        return state

    def fast_path(self, state: ConsultationState) -> ConsultationState:
        """Fast response using single GPT-4o model for routine consultations"""
        # Include retrieved knowledge context if available
        context_section = ""
        if state.get("retrieved_context"):
            context_section = f"\n\nRELEVANT MEDICAL KNOWLEDGE:\n{state['retrieved_context']}\n"

        base_prompt = f"""You are a medical AI assistant. Patient reports: {state['text']}{context_section}

CRITICAL INSTRUCTION: Respond in EXACTLY 50 words or less. This will be converted to speech.

Provide:
1. Brief assessment (1 sentence)
2. Urgency level: LOW/MEDIUM/HIGH/EMERGENCY
3. One action to take

Be direct and actionable."""

        # Apply A/B test variant
        variant = state.get("experiment_variants", {}).get("prompt_style", "control")
        prompt = get_prompt_for_variant(variant, base_prompt)

        response = self.gpt4.invoke([HumanMessage(content=prompt)])

        state["responses"] = {"gpt4": response.content}
        state["votes"] = {"gpt4": {"urgency": "MEDIUM", "confidence": 0.85}}

        return state
    
    def visual_path(self, state: ConsultationState) -> ConsultationState:
        """Visual analysis using Gemini 2.0 Flash multimodal capabilities"""
        # Include retrieved knowledge context if available
        context_section = ""
        if state.get("retrieved_context"):
            context_section = f"\n\nRELEVANT MEDICAL KNOWLEDGE:\n{state['retrieved_context']}\n"

        prompt = f"""Medical image analysis. Patient says: {state['text']}{context_section}

CRITICAL: Respond in 50 words or less for text-to-speech.

State:
1. What you see (5 words)
2. Urgency: LOW/MEDIUM/HIGH/EMERGENCY
3. Next action (5 words)

Be concise and direct."""

        response = self.gemini.invoke([HumanMessage(content=prompt)])

        state["responses"] = {"gemini": response.content}
        state["votes"] = {"gemini": {"urgency": "MEDIUM", "confidence": 0.80}}

        return state
    
    def council_debate(self, state: ConsultationState) -> ConsultationState:
        """Full council deliberation for high-stakes medical consultations"""

        has_image = state.get("image") is not None
        image_data = state.get("image")

        # Include retrieved knowledge context if available
        context_section = ""
        if state.get("retrieved_context"):
            context_section = f"\n\nRELEVANT MEDICAL KNOWLEDGE:\n{state['retrieved_context']}\n"

        # Short prompt for council members
        text_prompt = f"""Medical expert quick assessment needed.

Patient: {state['text']}{context_section}

Provide in 20 words or less:
1. Likely diagnosis
2. Urgency: LOW/MEDIUM/HIGH/EMERGENCY
3. Confidence (0.0-1.0)

Be direct."""

        print("   🏛️ Consulting all 3 expert models...")

        # Build message content - include image if present
        if has_image and image_data:
            import base64

            # Check if image_data already contains a data URL prefix
            if image_data.startswith('data:'):
                # Extract MIME type and base64 data from data URL
                try:
                    # Format: data:image/jpeg;base64,<base64-string>
                    header, base64_data = image_data.split(',', 1)
                    # Extract MIME type from header
                    image_type = header.split(':')[1].split(';')[0]  # e.g., "image/jpeg"
                    print(f"   🖼️  Using existing data URL format: {image_type}")
                except Exception as e:
                    print(f"   ⚠️  Could not parse data URL, using as-is: {str(e)}")
                    # Use the original data URL as-is
                    image_url = image_data
                    message_content = [
                        {"type": "text", "text": text_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url}
                        }
                    ]
                    messages = [HumanMessage(content=message_content)]
                else:
                    # Rebuild with extracted data
                    message_content = [
                        {"type": "text", "text": text_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{image_type};base64,{base64_data}"}
                        }
                    ]
                    messages = [HumanMessage(content=message_content)]
            else:
                # Raw base64 string - detect format from magic numbers
                image_type = "image/png"  # Default

                try:
                    # Remove any whitespace
                    clean_data = image_data.strip().replace('\n', '').replace('\r', '')

                    # Decode first chunk to check magic numbers
                    chunk_size = min(64, len(clean_data))
                    chunk_size = (chunk_size // 4) * 4

                    if chunk_size >= 16:
                        decoded_start = base64.b64decode(clean_data[:chunk_size])

                        # Check magic numbers
                        if decoded_start.startswith(b'\x89PNG\r\n\x1a\n'):
                            image_type = "image/png"
                        elif decoded_start.startswith(b'\xff\xd8\xff'):
                            image_type = "image/jpeg"
                        elif decoded_start.startswith(b'GIF87a') or decoded_start.startswith(b'GIF89a'):
                            image_type = "image/gif"
                        elif decoded_start.startswith(b'RIFF') and len(decoded_start) >= 12 and decoded_start[8:12] == b'WEBP':
                            image_type = "image/webp"

                        print(f"   🖼️  Detected image format: {image_type}")
                except Exception as e:
                    print(f"   ⚠️  Could not detect image format, using default PNG: {str(e)}")
                    image_type = "image/png"

                # Build message with detected format
                message_content = [
                    {"type": "text", "text": text_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{image_type};base64,{clean_data}"}
                    }
                ]
                messages = [HumanMessage(content=message_content)]
        else:
            # Text-only message
            messages = [HumanMessage(content=text_prompt)]

        # Parallel consultation with all models - handle failures gracefully
        responses = {}
        votes = {}
        failed_models = []

        # GPT-4o
        try:
            gpt4_response = self.gpt4.invoke(messages)
            responses["gpt4"] = gpt4_response.content
            votes["gpt4"] = {"urgency": "HIGH", "confidence": 0.90, "model": "GPT-4o"}
            print(f"   🧠 GPT-4o Response: {gpt4_response.content[:100]}   ")
        except Exception as e:
            failed_models.append("GPT-4o")
            print(f"   ⚠️  GPT-4o failed (quota/rate limit): {str(e)[:50]}")

        # Claude
        try:
            claude_response = self.claude.invoke(messages)
            responses["claude"] = claude_response.content
            votes["claude"] = {"urgency": "HIGH", "confidence": 0.92, "model": "Claude Sonnet 4"}
            print(f"   🧠 Claude Response: {claude_response.content[:100]}   ")
        except Exception as e:
            failed_models.append("Claude")
            print(f"   ⚠️  Claude failed (quota/rate limit): {str(e)[:50]}")

        # Gemini
        try:
            gemini_response = self.gemini.invoke(messages)
            responses["gemini"] = gemini_response.content
            votes["gemini"] = {"urgency": "HIGH", "confidence": 0.88, "model": "Gemini 2.0 Flash"}
            print(f"   🧠 Gemini Response: {gemini_response.content[:100]}   ")
        except Exception as e:
            failed_models.append("Gemini")
            print(f"   ⚠️  Gemini failed (quota/rate limit): {str(e)[:50]}")

        # Check if we have at least one successful response
        if not responses:
            raise Exception("All LLM models failed. Cannot provide consultation.")

        # Log warning if some models failed
        if failed_models:
            print(f"   ⚠️  Continuing with {len(responses)} model(s), {len(failed_models)} failed: {', '.join(failed_models)}")

        state["responses"] = responses
        state["votes"] = votes
        state["failed_models"] = failed_models

        print("   💬 Quick consensus check...")

        return state
    
    def synthesize(self, state: ConsultationState) -> ConsultationState:
        """Synthesize final unified response from all council inputs"""
        responses = state["responses"]
        votes = state["votes"]

        print("   🔬 Synthesizing final response...")

        # Build concise synthesis prompt for TTS
        # Only include responses from models that succeeded
        expert_opinions = []
        if responses.get('gpt4'):
            expert_opinions.append(f"GPT-4o: {responses['gpt4'][:50]}")
        if responses.get('claude'):
            expert_opinions.append(f"Claude: {responses['claude'][:50]}")
        if responses.get('gemini'):
            expert_opinions.append(f"Gemini: {responses['gemini'][:50]}")

        base_synthesis_prompt = f"""Patient: {state['text']}

Expert opinions:
{chr(10).join(expert_opinions)}

CRITICAL: Respond in EXACTLY 50 words or less for text-to-speech.

Provide: Assessment, urgency level, and one clear action.
Be direct and calming."""

        # Apply A/B test variant
        variant = state.get("experiment_variants", {}).get("prompt_style", "control")
        synthesis_prompt = get_prompt_for_variant(variant, base_synthesis_prompt)

        # Try synthesis with available models (fallback if GPT-4 fails)
        final_content = None
        synthesis_models = [
            ("GPT-4o", self.gpt4),
            ("Claude", self.claude),
            ("Gemini", self.gemini)
        ]

        for model_name, model in synthesis_models:
            try:
                final = model.invoke([HumanMessage(content=synthesis_prompt)])
                final_content = final.content
                print(f"   ✅ Synthesis by {model_name}")
                break
            except Exception as e:
                print(f"   ⚠️  {model_name} synthesis failed: {str(e)[:50]}")
                continue

        # If all synthesis attempts failed, use the best available response
        if not final_content:
            print("   ⚠️  All synthesis models failed, using best available response")
            final_content = list(responses.values())[0] if responses else "Unable to provide assessment. Please consult a healthcare provider."

        # Calculate aggregate confidence score
        confidences = [v.get("confidence", 0.5) for v in votes.values()]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5

        # Determine final urgency (take highest for patient safety)
        urgency_levels = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "EMERGENCY": 4}
        urgencies = [v.get("urgency", "MEDIUM") for v in votes.values()]
        max_urgency = max(urgencies, key=lambda x: urgency_levels.get(x, 2)) if urgencies else "MEDIUM"

        state["final_response"] = final_content
        state["urgency"] = max_urgency
        state["confidence"] = round(avg_confidence, 3)

        print(f"   ✅ Synthesis complete - Urgency: {max_urgency}, Confidence: {avg_confidence:.2f}")

        return state
    
    def consult(self, text: Optional[str], image: Optional[str], 
                patient_id: str, location: str) -> Dict[str, Any]:
        """Run consultation through the graph"""
        
        # Store image in Digital Ocean Spaces if present
        image_metadata = None
        if image:
            try:
                from spaces_storage import get_spaces_storage
                import uuid
                
                spaces = get_spaces_storage()
                if spaces.client:
                    # Generate a consultation ID for linking
                    consultation_id = str(uuid.uuid4())
                    
                    # Call synchronous upload method directly
                    image_metadata = spaces.upload_image(
                        base64_image=image,
                        patient_id=patient_id,
                        consultation_id=consultation_id
                    )
                    if image_metadata:
                        print(f"   📤 Image stored in Spaces: {image_metadata['key']}")
            except Exception as e:
                print(f"   ⚠️  Failed to upload image to Spaces: {str(e)}")
        
        initial_state: ConsultationState = {
            "text": text,
            "image": image,
            "patient_id": patient_id,
            "location": location,
            "route": "fast",  # Will be determined by orchestrator
            "responses": {},
            "votes": {},
            "final_response": "",
            "urgency": "MEDIUM",
            "confidence": 0.5,
            "experiment_variants": {}  # Will be assigned by orchestrator
        }
        
        # Run through graph
        result = self.graph.invoke(initial_state)
        
        # Add image metadata to result if available
        if image_metadata:
            result["image_storage"] = image_metadata
        
        return {
            "response": result["final_response"],
            "urgency": result["urgency"],
            "confidence": result["confidence"],
            "council_votes": result["votes"],
            "route_taken": result["route"],
            "experiment_variants": result.get("experiment_variants", {}),
            "image_storage": result.get("image_storage")
        }
