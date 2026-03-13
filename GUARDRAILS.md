# Guardrails in LangChain — Middleware for Trustworthy LLM Agents

## Table of Contents

1. [What Are Guardrails?](#1-what-are-guardrails)
2. [How LangChain Implements Guardrails](#2-how-langchain-implements-guardrails)
3. [Middleware Architecture](#3-middleware-architecture)
4. [What We Built — Our Implementation](#4-what-we-built--our-implementation)
5. [Built-in Middleware Reference](#5-built-in-middleware-reference)
6. [Custom Middleware — Going Beyond Built-ins](#6-custom-middleware--going-beyond-built-ins)
7. [Other Guardrail Approaches](#7-other-guardrail-approaches)
8. [Guardrail Strategy Matrix](#8-guardrail-strategy-matrix)

---

## 1. What Are Guardrails?

Guardrails are safety controls that **validate and filter content at key points** in an agent's execution. They prevent unsafe, non-compliant, or incorrect behavior before it causes real-world harm.

**Common use cases:**

| Category | Examples |
|----------|----------|
| **PII Protection** | Redact emails, credit cards, SSNs before they reach the model or logs |
| **Human Oversight** | Require approval before executing financial transactions or sending emails |
| **Content Safety** | Block harmful, hateful, or inappropriate content |
| **Business Rules** | Enforce refund caps, rate limits, compliance requirements |
| **Output Validation** | Verify the agent's response is safe and accurate before returning to user |
| **Prompt Injection** | Detect and block attempts to manipulate the agent via crafted inputs |

### Two Complementary Approaches

| Type | How It Works | Pros | Cons |
|------|-------------|------|------|
| **Deterministic** | Rule-based logic: regex, keyword matching, explicit checks | Fast, predictable, cost-effective | May miss nuanced violations |
| **Model-based** | LLM or classifier evaluates content semantically | Catches subtle issues rules miss | Slower, more expensive, adds latency |

---

## 2. How LangChain Implements Guardrails

LangChain v1.0+ uses **middleware** as the primary mechanism for guardrails. Middleware is passed to `create_agent()` and intercepts execution at strategic points in the agent loop.

```python
from langchain.agents import create_agent
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,
    PIIMiddleware,
)

agent = create_agent(
    model="gpt-4.1",
    tools=[...],
    middleware=[                                 # ← Guardrails go here
        PIIMiddleware("email", strategy="redact", apply_to_input=True),
        HumanInTheLoopMiddleware(interrupt_on={"send_email": True}),
    ],
)
```

Middleware executes **in order** — you can stack multiple layers for defense-in-depth:

```
Layer 1: Deterministic input filter  (before agent)
Layer 2: PII protection              (before/after model)
Layer 3: Human approval              (around tool calls)
Layer 4: Model-based safety check    (after agent)
```

---

## 3. Middleware Architecture

### The Agent Execution Lifecycle

LangChain middleware hooks into **six points** in the agent loop:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Agent Invocation                         │
│                                                                 │
│  ┌──────────────┐                                               │
│  │ before_agent │  ← Validate input, load memory                │
│  └──────┬───────┘                                               │
│         │                                                       │
│         ▼    ┌─── Agent Loop ──────────────────────────────┐    │
│              │                                             │    │
│              │  ┌──────────────┐                           │    │
│              │  │ before_model │  ← Trim messages, PII     │    │
│              │  └──────┬───────┘                           │    │
│              │         │                                   │    │
│              │         ▼                                   │    │
│              │  ┌────────────────┐                         │    │
│              │  │ wrap_model_call│  ← Intercept LLM call   │    │
│              │  └──────┬─────────┘                         │    │
│              │         │                                   │    │
│              │         ▼                                   │    │
│              │  ┌─────────────┐                            │    │
│              │  │ after_model │  ← Validate output, HITL   │    │
│              │  └──────┬──────┘                            │    │
│              │         │                                   │    │
│              │         ▼                                   │    │
│              │  ┌────────────────┐                         │    │
│              │  │ wrap_tool_call │  ← Intercept tool exec  │    │
│              │  └──────┬─────────┘                         │    │
│              │         │                                   │    │
│              └─────────┘  (loop until no more tool calls)  │    │
│                                                                 │
│  ┌─────────────┐                                                │
│  │ after_agent │  ← Final safety check, cleanup                 │
│  └─────────────┘                                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

| Hook | When It Runs | Guardrail Use Cases |
|------|-------------|---------------------|
| `before_agent` | Once, before the agent starts | Validate input, load context, block banned content |
| `before_model` | Before each LLM call | Trim messages, redact PII from input, inject context |
| `wrap_model_call` | Around each LLM call | Intercept/modify request and response, retry logic |
| `after_model` | After each LLM response | HITL approval, validate tool calls, output filtering |
| `wrap_tool_call` | Around each tool execution | Block/modify tool calls, enforce business rules |
| `after_agent` | Once, after agent completes | Final safety scan, compliance check, audit logging |

---

## 4. What We Built — Our Implementation

Our customer support swarm uses **three guardrails** on the `shop_assist` agent and **one** on the `escalation_agent`:

### Architecture Overview

```
                    ┌──────────┐
                    │  Router  │  (no guardrails — classification only)
                    └────┬─────┘
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
    ┌──────────────┐ ┌────────┐ ┌──────────────┐
    │  ShopAssist  │ │ Policy │ │  Escalation  │
    │              │ │Advisor │ │    Agent     │
    │ 3 guardrails │ │  none  │ │ 1 guardrail  │
    └──────────────┘ └────────┘ └──────────────┘
```

### Guardrail 1: Human-in-the-Loop (`HumanInTheLoopMiddleware`)

**What it does:** Pauses the agent and waits for a human to approve, edit, or reject sensitive tool calls before they execute.

**Where we use it:**
- `shop_assist`: interrupts on `process_refund` and `send_email`
- `escalation_agent`: interrupts on `send_email`

**How it works:**

```python
from langchain.agents.middleware import HumanInTheLoopMiddleware

HumanInTheLoopMiddleware(
    interrupt_on={
        "process_refund": {
            "description": "Review this refund before processing",
            "allowed_decisions": ["approve", "edit", "reject"],
        },
        "send_email": {
            "description": "Review this email before sending",
            "allowed_decisions": ["approve", "edit", "reject"],
        },
    }
)
```

**Under the hood:**
1. Agent calls the model → model proposes a tool call (e.g., `process_refund`)
2. Middleware's `after_model` hook inspects the tool call
3. If the tool matches `interrupt_on`, it calls `interrupt()` — pausing the graph
4. Graph state is saved to the **checkpointer** (PostgreSQL in our case)
5. The human reviews the proposed tool call in the UI
6. Human sends a `Command(resume={"decisions": [{"type": "approve"}]})` to continue
7. Middleware executes the approved call (or rejects/edits it)

**Requires:** A checkpointer (LangGraph API provides one automatically) and a `thread_id` for persistence.

**Decision types:**
- `approve` — Execute the tool call as-is
- `edit` — Modify the arguments before executing
- `reject` — Skip the tool call and return an error message to the model

### Guardrail 2: Refund Cap Enforcement (`RefundCapMiddleware`)

**What it does:** Hard-blocks any `process_refund` call exceeding $150, before the tool ever executes.

**Type:** Deterministic (rule-based), custom middleware.

**Our implementation** (`support_swarm/guardrails.py`):

```python
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage

class RefundCapMiddleware(AgentMiddleware):
    """Blocks refund tool calls that exceed a configurable dollar cap."""

    def __init__(self, max_amount: float = 150.0):
        self.max_amount = max_amount

    def wrap_tool_call(self, request, handler):
        tool_call = request.tool_call
        if tool_call["name"] == "process_refund":
            amount = tool_call["args"].get("amount", 0)
            if amount > self.max_amount:
                return ToolMessage(
                    content=json.dumps({
                        "success": False,
                        "error": f"Refund ${amount:.2f} exceeds the "
                                 f"${self.max_amount:.2f} policy cap.",
                    }),
                    tool_call_id=tool_call["id"],
                )
        return handler(request)

    async def awrap_tool_call(self, request, handler):
        # Same logic for async context (required when using ainvoke)
        ...
        return await handler(request)
```

**Key design decisions:**
- Uses `wrap_tool_call` to intercept **before** the tool runs (not after)
- Returns a `ToolMessage` with an error, so the LLM sees the rejection and can explain it to the user
- Both sync (`wrap_tool_call`) and async (`awrap_tool_call`) implementations are required since our workflow uses `ainvoke()`

### Guardrail 3: PII Redaction (`PIIMiddleware`)

**What it does:** Detects and redacts credit card numbers in the agent's output before returning to the user.

```python
from langchain.agents.middleware import PIIMiddleware

PIIMiddleware("credit_card", strategy="redact", apply_to_output=True)
```

**Result:** `4111-1111-1111-1111` → `[REDACTED_CREDIT_CARD]`

### Combined Middleware Stack

In `workflow.py`, the ShopAssist agent stacks all three:

```python
agent = create_agent(
    model=get_chat_client(),
    tools=spec.get_tools(),
    system_prompt=spec.render_system_prompt(store_name="Acme Corp"),
    middleware=[
        # Layer 1: Human approval for sensitive operations
        HumanInTheLoopMiddleware(
            interrupt_on={
                "process_refund": {
                    "description": "Review this refund before processing",
                    "allowed_decisions": ["approve", "edit", "reject"],
                },
                "send_email": {
                    "description": "Review this email before sending",
                    "allowed_decisions": ["approve", "edit", "reject"],
                },
            }
        ),
        # Layer 2: Hard business rule — refund cap
        RefundCapMiddleware(max_amount=150.0),
        # Layer 3: PII protection in output
        PIIMiddleware("credit_card", strategy="redact", apply_to_output=True),
    ],
)
```

---

## 5. Built-in Middleware Reference

LangChain provides several pre-built middleware out of the box:

### 5.1 `HumanInTheLoopMiddleware`

Pauses execution for human approval before sensitive tool calls.

```python
from langchain.agents.middleware import HumanInTheLoopMiddleware

HumanInTheLoopMiddleware(
    interrupt_on={
        "send_email": {
            "description": "Please review this email",
            "allowed_decisions": ["approve", "edit", "reject"],
        },
        "delete_record": True,      # Simple boolean — all decisions allowed
        "search": False,            # Auto-approve (no interrupt)
    }
)
```

**Requirements:** Checkpointer + `thread_id`.

**Resuming after interrupt:**

```python
from langgraph.types import Command

# Approve
agent.invoke(Command(resume={"decisions": [{"type": "approve"}]}), config=config)

# Reject
agent.invoke(Command(resume={"decisions": [{"type": "reject", "message": "Too expensive"}]}), config=config)

# Edit (modify the tool arguments)
agent.invoke(Command(resume={"decisions": [{"type": "edit", "edited_action": {...}}]}), config=config)
```

### 5.2 `PIIMiddleware`

Detects and handles Personally Identifiable Information.

**Built-in PII types:**

| Type | Description |
|------|-------------|
| `email` | Email addresses |
| `credit_card` | Credit card numbers (Luhn validated) |
| `ip` | IP addresses |
| `mac_address` | MAC addresses |
| `url` | URLs |

**Strategies:**

| Strategy | Description | Example Output |
|----------|-------------|----------------|
| `redact` | Replace with placeholder | `[REDACTED_EMAIL]` |
| `mask` | Partially obscure | `****-****-****-1234` |
| `hash` | Deterministic hash | `a8f5f167...` |
| `block` | Raise exception | Error thrown |

**Configuration:**

```python
PIIMiddleware(
    "email",                    # pii_type (built-in or custom name)
    strategy="redact",          # How to handle detected PII
    detector=None,              # Custom regex or function (optional)
    apply_to_input=True,        # Check user messages before model call
    apply_to_output=False,      # Check AI messages after model call
    apply_to_tool_results=False # Check tool result messages
)
```

**Custom PII types with regex:**

```python
PIIMiddleware(
    "phone_number",
    detector=r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{4}",
    strategy="block",
    apply_to_input=True,
)
```

**Custom PII types with function:**

```python
def detect_ssn(content: str) -> list[dict]:
    import re
    matches = []
    for m in re.finditer(r"\b\d{3}-\d{2}-\d{4}\b", content):
        matches.append({"text": m.group(), "start": m.start(), "end": m.end()})
    return matches

PIIMiddleware("ssn", detector=detect_ssn, strategy="redact", apply_to_input=True)
```

### 5.3 `SummarizationMiddleware`

Condenses conversation history when it gets too long, preventing context window overflow.

```python
from langchain.agents.middleware import SummarizationMiddleware

SummarizationMiddleware(
    model="gpt-4.1-mini",      # Model to use for summarization
    trigger={"tokens": 1000},   # Trigger when conversation exceeds 1000 tokens
)
```

### 5.4 OpenAI Content Moderation Middleware

Moderates agent traffic using OpenAI's moderation endpoint to detect unsafe content.

```python
from langchain.agents.middleware import OpenAIModerationMiddleware

OpenAIModerationMiddleware(
    model="gpt-4.1",                            # Model whose client accesses moderation
    moderation_model="omni-moderation-latest",   # Moderation model to use
    check_input=True,                            # Check user input
    check_output=True,                           # Check model output
    check_tool_results=False,                    # Check tool results
    exit_behavior="end",                         # 'error' | 'end' | 'replace'
)
```

---

## 6. Custom Middleware — Going Beyond Built-ins

### 6.1 Class-based Middleware (Full Control)

Subclass `AgentMiddleware` and implement any combination of hooks:

```python
from langchain.agents.middleware import AgentMiddleware, AgentState, ModelRequest
from langchain.agents.middleware.types import ModelResponse

class MyGuardrail(AgentMiddleware):
    def before_agent(self, state, runtime):
        """Validate input before the agent starts."""
        ...

    def before_model(self, state, runtime):
        """Modify messages before each LLM call."""
        ...

    def wrap_model_call(self, request, handler):
        """Intercept and modify each LLM call."""
        return handler(request)

    def after_model(self, state, runtime):
        """Validate output after each LLM response."""
        ...

    def wrap_tool_call(self, request, handler):
        """Intercept and modify each tool execution."""
        return handler(request)

    def after_agent(self, state, runtime):
        """Final validation after agent completes."""
        ...
```

### 6.2 Decorator-based Middleware (Quick & Simple)

For single-hook middleware, use decorators:

```python
from langchain.agents.middleware import before_model, after_agent, wrap_tool_call

@before_model
def log_model_calls(state, runtime):
    print(f"Calling model with {len(state['messages'])} messages")
    return None

@after_agent(can_jump_to=["end"])
def safety_check(state, runtime):
    last = state["messages"][-1]
    if "harmful" in last.content.lower():
        last.content = "I cannot provide that response."
    return None

@wrap_tool_call
def audit_tool_calls(request, handler):
    print(f"Tool: {request.tool_call['name']}, Args: {request.tool_call['args']}")
    return handler(request)

agent = create_agent(
    model="gpt-4.1",
    tools=[...],
    middleware=[log_model_calls, safety_check, audit_tool_calls],
)
```

### 6.3 Model-based Output Guardrail (after_agent)

Use a separate LLM to evaluate whether the agent's final response is safe:

```python
from langchain.agents.middleware import after_agent, AgentState
from langchain.chat_models import init_chat_model
from langchain.messages import AIMessage

safety_model = init_chat_model("gpt-4.1-mini")

@after_agent(can_jump_to=["end"])
def safety_guardrail(state: AgentState, runtime):
    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage):
        return None

    result = safety_model.invoke([{
        "role": "user",
        "content": f"Is this response safe? Reply SAFE or UNSAFE.\n\n{last_message.content}"
    }])

    if "UNSAFE" in result.content:
        last_message.content = "I cannot provide that response."

    return None
```

---

## 7. Other Guardrail Approaches

Beyond LangChain middleware, there are several alternative approaches to implementing guardrails:

### 7.1 Prompt Engineering (System Prompt Rules)

Embed safety rules directly in the system prompt. This is what our `shop_assist.yaml` does:

```yaml
system_prompt: |
  ## Rules
  - Always call `lookup_order` before `process_refund`.
  - Never refund more than $150.
  - Always call `send_email` after every refund.
```

| Pros | Cons |
|------|------|
| Zero latency overhead | LLM can ignore/hallucinate past rules |
| No additional code | No hard enforcement |
| Easy to iterate | Vulnerable to prompt injection |

**Best for:** Soft guidelines the LLM should follow, not hard constraints.

### 7.2 Pydantic Input Validation (Tool Schemas)

Validate tool arguments at the schema level using Pydantic:

```python
class ProcessRefundInput(BaseModel):
    order_id: str = Field(description="Order ID in ORD-XXXX format")
    amount: float = Field(gt=0, le=150.0, description="Refund amount")
```

| Pros | Cons |
|------|------|
| Catching invalid args before tool runs | Only validates structure, not business logic |
| Native Python, no extra infra | Can't enforce multi-step workflows |
| Fast and deterministic | LLM might generate invalid values repeatedly |

**Best for:** Type safety and basic value constraints.

### 7.3 LangGraph `interrupt()` Directly

Use LangGraph's raw `interrupt()` function at the graph node level instead of middleware:

```python
from langgraph.types import interrupt, Command

async def shop_assist(state: MessagesState):
    # ... run agent ...
    decision = interrupt({"question": "Approve this refund?", "details": result})
    if not decision:
        return {"messages": [AIMessage(content="Refund cancelled by reviewer.")]}
    # ... proceed ...
```

| Pros | Cons |
|------|------|
| Full control over interrupt logic | More boilerplate code |
| Can interrupt on arbitrary conditions | Must manually build the approval UI payload |
| Works at any point in the graph | Doesn't compose as cleanly as middleware |

**Best for:** Complex approval flows that don't fit the simple tool-level pattern.

### 7.4 Tool-level Validation (Inside the Tool Function)

Put validation logic directly inside the tool:

```python
@register_tool(args_schema=ProcessRefundInput)
def process_refund(order_id: str, amount: float) -> str:
    if amount > 150:
        return json.dumps({"error": "Exceeds $150 cap"})
    if amount <= 0:
        return json.dumps({"error": "Amount must be positive"})
    # ... process ...
```

| Pros | Cons |
|------|------|
| Simple, self-contained | Tool already executed (side effects may happen) |
| No middleware dependency | Can't prevent the LLM from calling the tool |
| Easy to test | Mixes business logic with safety logic |

**Best for:** Last-line-of-defense validation. Works well alongside middleware.

### 7.5 External Guardrail Services

Use third-party guardrail providers:

- **OpenAI Moderation API** — Detects harmful content categories
- **Microsoft Presidio** — Enterprise PII detection and anonymization
- **Amazon Comprehend** — PII detection via AWS
- **Guardrails AI** — Open source guardrail framework with validators
- **NeMo Guardrails (NVIDIA)** — Programmable guardrails for LLM apps

| Pros | Cons |
|------|------|
| Battle-tested, production-grade | External API dependency, latency |
| Broader PII/content detection | Cost per API call |
| Compliance certifications | Vendor lock-in |

---

## 8. Guardrail Strategy Matrix

| Guardrail Type | Approach | Speed | Catches Nuance? | Our Usage |
|---------------|----------|-------|-----------------|-----------|
| **HITL** | Middleware (`HumanInTheLoopMiddleware`) | Human-speed | Yes (human judges) | `process_refund`, `send_email` |
| **Refund Cap** | Custom middleware (`wrap_tool_call`) | Instant | N/A (deterministic) | `process_refund > $150` |
| **PII Redaction** | Built-in middleware (`PIIMiddleware`) | Instant | Limited (regex) | Credit card in output |
| **Prompt Rules** | System prompt | Zero overhead | Depends on LLM | `shop_assist.yaml` rules |
| **Schema Validation** | Pydantic `Field()` | Instant | No | `ProcessRefundInput` |
| **Tool Validation** | Inside tool function | Instant | No | `amount > 0` check |
| **Content Moderation** | OpenAI Moderation API | ~100ms | Yes | Not used (available) |
| **Output Safety** | `after_agent` + LLM judge | ~500ms | Yes | Not used (available) |

### Recommended Layering Strategy

```
Layer 1:  Prompt Engineering         — soft guidance (always on)
Layer 2:  Schema Validation          — type + range checks (always on)
Layer 3:  Deterministic Middleware   — business rules like refund cap (always on)
Layer 4:  PII Middleware             — protect sensitive data (always on)
Layer 5:  HITL Middleware            — human review for critical actions (always on)
Layer 6:  Model-based Guardrails    — LLM safety judge (optional, adds latency)
Layer 7:  Tool-level Validation      — last-line defense (always on)
```

---

## References

- [LangChain Guardrails Guide](https://docs.langchain.com/oss/python/langchain/guardrails)
- [LangChain Middleware Overview](https://docs.langchain.com/oss/python/langchain/middleware/overview)
- [Built-in Middleware Reference](https://docs.langchain.com/oss/python/langchain/middleware/built-in)
- [Custom Middleware Guide](https://docs.langchain.com/oss/python/langchain/middleware/custom)
- [Human-in-the-Loop Guide](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)
- [LangGraph Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [LangGraph Persistence (Checkpointers)](https://docs.langchain.com/oss/python/langgraph/persistence)
