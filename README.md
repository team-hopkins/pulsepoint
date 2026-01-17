# CarePoint AI System - Build Instructions

## System Overview

FastAPI endpoint receives text/image → LLM Council debates → Returns text response → Dashboards visualize

## 1. API Endpoint (FastAPI)

```
POST /consult
Input: { text: str?, image: base64?, patient_id: str, location: str }
Output: { response: str, urgency: str, confidence: float, council_votes: {} }
```

## 2. LangGraph Council (Core Intelligence)

**Orchestrator**: Routes based on input

- Text-only → Fast path (single GPT-4)
- Image → Visual path (Gemini multimodal)
- High-stakes → Full council (3 models debate)

**Council Members** (parallel execution):

- Gemini 2.0 Flash: Vision + text analysis
- GPT-4o: Fast reasoning
- Claude Sonnet 4: Medical expertise

**Debate Phase**: Agents critique each other
**Synthesis**: Generate consensus response

## 3. LangChain Tools

- Medical knowledge API
- Drug database
- First aid instructions
- Emergency protocols

## 4. Arize Monitoring

```python
from arize.otel import register
from openinference.instrumentation.langchain import LangChainInstrumentor

# Instrument all LLM calls
tracer_provider = register(space_id=..., api_key=...)
LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
```

Logs: prompts, responses, latencies, council votes, confidence scores

## 5. Lovable Dashboards (Build in 1-2 hours)

### Dashboard 1: Doctor Portal

**Pull from Arize API:**

```javascript
// Fetch live consultations
GET https://api.arize.com/v1/spaces/{space_id}/traces

Display:
- Active consultations (real-time)
- Council voting breakdown (Gemini/GPT/Claude decisions)
- Model confidence scores
- Patient queue (waiting for doctor)
- [JOIN VIDEO CALL] buttons (LiveKit integration)
```

ARIZE_API_KEY=ak-b15b7f66-b95f-42f7-b5d8-a06b808b9ed7-b7gDKrO0sKTp27snEuQyQh5uh0Jsa2xe
ARIZE_SPACE_KEY=U3BhY2U6MzU4NDA6M1BiWg==

### Dashboard 2: Admin Analytics

**Pull from Arize API:**

```javascript
// Fetch metrics
GET https://api.arize.com/v1/spaces/{space_id}/metrics

Display:
- Total consultations today
- Emergency detection rate
- Model accuracy comparison (bar chart)
- Average response time (line chart)
- Device status map (all first aid stations)
- Council agreement rate (pie chart: unanimous/majority/split)
```

### Lovable Build Steps:

1. Sign in to lovable.dev
2. Prompt: "Create healthcare dashboard with real-time consultation cards, model performance charts, and device status map"
3. Add Arize API integration (paste API endpoint)
4. Customize: Add LiveKit room join buttons
5. Deploy: Get shareable URL for demo

## 6. Integration Flow

```
Text/Image Input
    ↓
FastAPI Endpoint
    ↓
LangGraph Routes
    ↓
Council Debates (if needed)
    ↓
Text Response Output
    ↓
[Parallel] → Arize Logs Everything
    ↓
Lovable Dashboards Pull & Display
```

## Build Priority

**Day 1:**

1. FastAPI endpoint (text input only)
2. Single LLM response (GPT-4)
3. Arize basic instrumentation
4. Test end-to-end

**Day 2:** 5. Add LangGraph 3-model council 6. Add debate/synthesis phases 7. Add image input (Gemini) 8. Build Lovable dashboards 9. Connect dashboards to Arize API 10. Polish & test

## Tech Stack

- FastAPI (API)
- LangGraph (orchestration)
- LangChain (tools)
- Arize (monitoring)
- Lovable (dashboards)
- OpenAI/Anthropic/Google (LLMs)
