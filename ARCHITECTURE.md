# System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INPUT                                   │
│                     (Text / Image / Both)                            │
└────────────────────────────┬────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FastAPI Endpoint                                │
│                     POST /consult                                    │
│  Input: {text, image, patient_id, location}                         │
└────────────────────────────┬────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LangGraph Orchestrator                            │
│                    (council.py)                                      │
│                                                                      │
│  Decision Logic:                                                     │
│  • Has image? → Visual Path                                         │
│  • High-stakes keywords? → Council Path                             │
│  • Otherwise → Fast Path                                            │
└────────────────┬────────────────┬────────────────┬──────────────────┘
                 ▼                ▼                ▼
      ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
      │  FAST PATH   │  │ VISUAL PATH  │  │ COUNCIL PATH │
      │              │  │              │  │              │
      │   GPT-4o     │  │  Gemini 2.0  │  │  ALL THREE   │
      │   (single)   │  │  Flash       │  │   MODELS     │
      │              │  │ (multimodal) │  │   (debate)   │
      │  ~2-3 sec    │  │  ~3-5 sec    │  │  ~8-12 sec   │
      └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
             │                 │                 │
             │                 │                 ▼
             │                 │        ┌─────────────────┐
             │                 │        │ PARALLEL EXEC   │
             │                 │        │ ┌────────────┐  │
             │                 │        │ │ GPT-4o     │  │
             │                 │        │ └────────────┘  │
             │                 │        │ ┌────────────┐  │
             │                 │        │ │ Claude     │  │
             │                 │        │ │ Sonnet 4   │  │
             │                 │        │ └────────────┘  │
             │                 │        │ ┌────────────┐  │
             │                 │        │ │ Gemini     │  │
             │                 │        │ │ 2.0 Flash  │  │
             │                 │        │ └────────────┘  │
             │                 │        └────────┬────────┘
             │                 │                 ▼
             │                 │        ┌─────────────────┐
             │                 │        │ DEBATE PHASE    │
             │                 │        │ Models critique │
             │                 │        │ each other      │
             │                 │        └────────┬────────┘
             └─────────────────┴─────────────────┘
                               ▼
             ┌─────────────────────────────────────┐
             │        SYNTHESIS NODE                │
             │   • Combine best insights            │
             │   • Resolve disagreements            │
             │   • Calculate avg confidence         │
             │   • Determine max urgency            │
             └─────────────┬───────────────────────┘
                           ▼
             ┌─────────────────────────────────────┐
             │         FINAL RESPONSE               │
             │  {                                   │
             │    response: "Medical guidance...",  │
             │    urgency: "HIGH",                  │
             │    confidence: 0.92,                 │
             │    council_votes: {...}              │
             │  }                                   │
             └─────────────┬───────────────────────┘
                           ▼
    ┌────────────────────────────────────────────────────┐
    │              ARIZE MONITORING                       │
    │          (monitoring.py)                            │
    │                                                     │
    │  Logs Everything:                                  │
    │  • All prompts sent to models                      │
    │  • All model responses                             │
    │  • Latencies per step                              │
    │  • Council votes & debates                         │
    │  • Patient metadata                                │
    │  • Urgency & confidence scores                     │
    │                                                     │
    │  Instrumented via OpenTelemetry                    │
    └─────────────┬──────────────────────────────────────┘
                  ▼
    ┌────────────────────────────────────────────────────┐
    │          ARIZE DASHBOARD                            │
    │          https://app.arize.com                      │
    │                                                     │
    │  View:                                             │
    │  • Real-time traces                                │
    │  • Model performance comparison                    │
    │  • Response time trends                            │
    │  • Urgency distribution                            │
    │  • Council agreement rates                         │
    └────────────────────────────────────────────────────┘

                  ║ (optional)
                  ▼
    ┌────────────────────────────────────────────────────┐
    │         LOVABLE DASHBOARDS                          │
    │         https://lovable.dev                         │
    │                                                     │
    │  Dashboard 1: DOCTOR PORTAL                        │
    │  • Live consultations                              │
    │  • Council voting breakdown                        │
    │  • Patient queue                                   │
    │  • Video call buttons                              │
    │                                                     │
    │  Dashboard 2: ADMIN ANALYTICS                      │
    │  • Total consultations                             │
    │  • Emergency detection rate                        │
    │  • Model accuracy charts                           │
    │  • Response time trends                            │
    │  • Device status map                               │
    └────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════
                         DATA FLOW
═══════════════════════════════════════════════════════════════════

TEXT INPUT                    ROUTING DECISION
    │                              │
    ├─ Simple query ──────────────> Fast Path
    ├─ High-stakes ───────────────> Council Path
    └─ With image ────────────────> Visual Path
                                    │
                                    ▼
                            MODEL EXECUTION
                                    │
                                    ▼
                            SYNTHESIS & RESPONSE
                                    │
                          ┌─────────┴─────────┐
                          ▼                   ▼
                    USER RESPONSE      ARIZE LOGGING
                                            │
                                            ▼
                                    DASHBOARDS UPDATE


═══════════════════════════════════════════════════════════════════
                        KEY COMPONENTS
═══════════════════════════════════════════════════════════════════

main.py          → FastAPI app, /consult endpoint
council.py       → LangGraph orchestration + AI council
monitoring.py    → Arize instrumentation
config.py        → Environment & settings
test_api.py      → Test suite for all paths
tools.py         → LangChain tools (future)

═══════════════════════════════════════════════════════════════════
```
