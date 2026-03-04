# Agno Framework - Complete API Reference & Documentation Research

> Researched: March 4, 2026  
> Source: docs.agno.com  
> Package: `pip install -U agno`

---

## Table of Contents

1. [Installation & Setup](#1-installation--setup)
2. [Workflows Overview](#2-workflows-overview-httpdocsagnocomworkflowsoverview)
3. [Sequential Workflow Pattern](#3-sequential-workflow-pattern-httpdocsagnocomworkflowsworkflow-patternssequential)
4. [Custom Function Step Workflow](#4-custom-function-step-workflow-httpdocsagnocomworkflowsworkflow-patternscustom-function-step-workflow)
5. [Step with Function Usage](#5-step-with-function-usage-httpdocsagnocomworkflowsusagestep-with-function)
6. [Running Workflows](#6-running-workflows-httpdocsagnocomworkflowsrunning-workflows)
7. [Step Reference](#7-step-reference-httpdocsagnocomreferenceworkflowsstep)
8. [Agents Overview](#8-agents-overview-httpdocsagnocomagentsoverview)
9. [Building Agents](#9-building-agents-httpdocsagnocomagentsbuilding-agents)
10. [Agent Tools](#10-agent-tools-httpdocsagnocomagentstools)

---

## 1. Installation & Setup

```bash
pip install -U agno
```

```bash
# Recommended: use a virtual environment
python3 -m venv ~/.venvs/agno
source ~/.venvs/agno/bin/activate
pip install -U agno
```

---

## 2. Workflows Overview — `https://docs.agno.com/workflows/overview`

Agno Workflows are **deterministic, stateful, multi-agent programs** designed to automate complex processes by orchestrating a series of steps executed in a controlled sequence.

### Key Features

- **Built-in storage and caching** via `session_state`
- **State management** persisted across runs when a database is configured
- **Pure Python** — no new DSL, uses native Python loops/conditionals/exception handling
- **Flexible executors** — each step can be an Agent, Team, or custom Python function
- **Asynchronous triggering** — avoids request timeout issues

### Core Building Blocks

| Component | Purpose |
|-----------|---------|
| `Step` | Fundamental execution unit encapsulating one executor |
| `Workflow` | Top-level orchestrator managing the entire execution |
| `Router` | Specifies which steps execute next (branching logic) |
| `Condition` | Makes steps conditional based on criteria |
| `Parallel` | Enables concurrent step execution |
| `Loop` | Executes steps repeatedly until a condition is met |

### Supported Workflow Patterns

- **Sequential** — linear step-by-step processing
- **Parallel** — concurrent independent tasks
- **Conditional** — branching based on conditions
- **Iterative** — loop-based execution
- **Branching** — dynamic routing and path selection
- **Grouped Steps** — reusable, modular sequences

### Core Import Statements

```python
from agno.workflow.workflow import Workflow
from agno.workflow.step import Step, StepInput, StepOutput
from agno.agent import Agent
from agno.team import Team
```

Or using the top-level `agno.workflow` module (also valid):

```python
from agno.workflow import Workflow, Step, Router, Condition, Parallel, Loop
from agno.workflow.types import StepInput, StepOutput
```

---

## 3. Sequential Workflow Pattern — `https://docs.agno.com/workflows/workflow-patterns/sequential`

Sequential workflows are **linear, deterministic processes** where each step depends on the output of the previous step. They ensure predictable execution order and clear data flow.

### Data Flow Pattern

```
Research → Data Processing → Content Creation → Final Review
```

Each step:
- Receives input via `StepInput` (from previous step's `StepOutput`)
- Returns output via `StepOutput` (passed to the next step)

### Basic Sequential Example

```python
from agno.agent import Agent
from agno.team import Team
from agno.models.openai import OpenAIChat
from agno.workflow.workflow import Workflow
from agno.workflow.step import Step

# Define individual agents
researcher = Agent(
    name="Researcher",
    model=OpenAIChat(id="gpt-4o"),
    instructions="Research the topic thoroughly.",
)

writer = Agent(
    name="Writer",
    model=OpenAIChat(id="gpt-4o"),
    instructions="Write a clear article based on the research provided.",
)

editor = Agent(
    name="Editor",
    model=OpenAIChat(id="gpt-4o"),
    instructions="Review and polish the article.",
)

# Create sequential workflow
workflow = Workflow(
    name="Article Creation Pipeline",
    steps=[researcher, writer, editor],  # Can pass agents directly
)

# Run
workflow.print_response(input="AI trends in 2025", markdown=True)
```

### Named Steps (Explicit Step Objects)

```python
from agno.workflow.step import Step
from agno.workflow.workflow import Workflow

research_step = Step(name="Research Step", agent=researcher)
writing_step = Step(name="Writing Step", agent=writer)
editing_step = Step(name="Editing Step", agent=editor)

workflow = Workflow(
    name="Article Creation Workflow",
    steps=[research_step, writing_step, editing_step],
)
```

### Mixed Executor Pipeline (Agent + Team + Function)

```python
from agno.workflow.workflow import Workflow

workflow = Workflow(
    name="Mixed Execution Pipeline",
    steps=[
        research_team,       # Team
        data_preprocessor,   # Custom function
        content_agent,       # Agent
    ],
)
```

The workflow passes each step's output as the next step's input automatically.

---

## 4. Custom Function Step Workflow — `https://docs.agno.com/workflows/workflow-patterns/custom-function-step-workflow`

Custom function steps allow you to inject **pure Python logic** into the workflow between agent/team steps.

### Pattern: Function-Based Executor

```python
from agno.workflow.step import StepInput, StepOutput

def custom_content_planning_function(step_input: StepInput) -> StepOutput:
    """Custom function for intelligent content planning with context awareness."""
    message = step_input.input                         # Original workflow input
    previous_step_content = step_input.previous_step_content  # Previous step output

    try:
        result = process_data(message, previous_step_content)
        return StepOutput(content=result, success=True)
    except Exception as e:
        return StepOutput(content=f"Failed: {str(e)}", success=False)
```

### Pattern: Class-Based Executor

```python
from agno.workflow.step import Step, StepInput, StepOutput

class CustomContentPlanning:
    """Reusable, stateful class-based step executor."""
    
    def __call__(self, step_input: StepInput) -> StepOutput:
        message = step_input.input
        previous_step_content = step_input.previous_step_content
        # Custom logic here
        return StepOutput(content="result")

# Wrap in Step
content_planning_step = Step(
    name="Content Planning Step",
    executor=CustomContentPlanning(),
)
```

### Complete Mixed Workflow Example

```python
from agno.agent import Agent
from agno.team import Team
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools
from agno.workflow.step import Step, StepInput, StepOutput
from agno.workflow.workflow import Workflow

# --- Agents ---
search_agent = Agent(
    name="Search Agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
    instructions="Search the web for relevant information.",
)

finance_agent = Agent(
    name="Finance Agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[YFinanceTools()],
    instructions="Fetch financial data and analysis.",
)

writer_agent = Agent(
    name="Writer",
    model=OpenAIChat(id="gpt-4o"),
    instructions="Write a comprehensive blog post based on the research provided.",
)

# --- Research Team ---
research_team = Team(
    name="Research Team",
    members=[search_agent, finance_agent],
    instructions="Research the topic comprehensively.",
)

# --- Custom Functions ---
def prepare_input_for_web_search(step_input: StepInput) -> StepOutput:
    topic = step_input.input
    return StepOutput(content=f"Search for articles and news on: {topic}")

def prepare_input_for_writer(step_input: StepInput) -> StepOutput:
    topic = step_input.input
    research_output = step_input.previous_step_content
    return StepOutput(
        content=(
            f"Write a detailed blog post on: {topic}\n\n"
            f"Use the following research:\n{research_output}"
        )
    )

# --- Workflow ---
blog_post_workflow = Workflow(
    name="Blog Post Creation Workflow",
    steps=[
        prepare_input_for_web_search,   # Function: shapes search query
        research_team,                   # Team: executes research
        prepare_input_for_writer,        # Function: shapes writer prompt
        writer_agent,                    # Agent: writes the final post
    ],
)

if __name__ == "__main__":
    blog_post_workflow.print_response(
        input="AI trends in 2025",
        markdown=True,
    )
```

---

## 5. Step with Function Usage — `https://docs.agno.com/workflows/usage/step-with-function`

### Import Statements

```python
from agno.workflow.step import Step, StepInput, StepOutput
from agno.workflow.workflow import Workflow
```

### `StepInput` — Complete Attribute Reference

| Attribute | Type | Description |
|-----------|------|-------------|
| `input` | `Optional[Union[str, Dict, List, BaseModel]]` | Primary input to the step |
| `previous_step_content` | `Optional[str]` | Content output from the immediately preceding step |
| `previous_step_outputs` | `Dict[str, StepOutput]` | All previous step outputs keyed by step name |
| `workflow_message` | `Optional[str]` | The original workflow input message |
| `additional_data` | `Optional[Dict[str, Any]]` | Extra context/metadata passed at runtime |
| `images` | `Optional[List]` | Image inputs |
| `videos` | `Optional[List]` | Video inputs |
| `audio` | `Optional[List]` | Audio inputs |
| `files` | `Optional[List]` | File inputs |

### `StepInput` — Helper Methods

```python
# Get output from a specific named previous step
content = step_input.get_step_content("Research Step")

# Get output object from a specific named previous step
output_obj = step_input.get_step_output("Research Step")

# Get all previous step outputs combined
all_content = step_input.get_all_previous_content()
```

### `StepOutput` — Complete Field Reference

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `content` | `Optional[Union[str, Dict, List, BaseModel]]` | `None` | Primary output |
| `success` | `bool` | `True` | Whether execution succeeded |
| `error` | `Optional[str]` | `None` | Error message if failed |
| `stop` | `bool` | `False` | Set `True` to halt the workflow early |
| `step_name` | `Optional[str]` | `None` | Step identifier |
| `step_id` | `Optional[str]` | `None` | Step UUID |
| `step_type` | `Optional[str]` | `None` | Type of step |
| `executor_type` | `Optional[str]` | `None` | Agent/team/function |
| `executor_name` | `Optional[str]` | `None` | Name of the executor |
| `images` | `Optional[List]` | `None` | Image outputs |
| `videos` | `Optional[List]` | `None` | Video outputs |
| `audio` | `Optional[List]` | `None` | Audio outputs |
| `files` | `Optional[List]` | `None` | File outputs |
| `metrics` | `Optional[Dict]` | `None` | Execution metrics |
| `steps` | `Optional[List[StepOutput]]` | `None` | Nested step outputs |

### Complete Step-with-Function Examples

#### Simple function step (inline, no `Step` wrapper needed):

```python
from agno.workflow.step import StepInput, StepOutput

def format_research_query(step_input: StepInput) -> StepOutput:
    topic = step_input.input
    return StepOutput(content=f"Search for: {topic}")
```

#### Function step wrapped in explicit `Step`:

```python
from agno.workflow.step import Step, StepInput, StepOutput

def data_processor(step_input: StepInput) -> StepOutput:
    message = step_input.input
    previous = step_input.previous_step_content
    processed = f"Processed: {previous}"
    return StepOutput(content=processed)

processor_step = Step(
    name="Data Processor",
    executor=data_processor,
)
```

#### Accessing multiple previous steps:

```python
from agno.workflow.step import StepInput, StepOutput

def create_final_report(step_input: StepInput) -> StepOutput:
    topic = step_input.input

    # Access specific named previous steps
    research_data = step_input.get_step_content("Research Step")
    analysis_data = step_input.get_step_content("Analysis Step")

    # Access all previous steps combined
    all_content = step_input.get_all_previous_content()

    # Access additional runtime data
    additional_data = step_input.additional_data or {}
    user_email = additional_data.get("user_email")
    priority = additional_data.get("priority", "normal")

    report = f"""
# Final Report: {topic}

## Research Findings
{research_data}

## Analysis
{analysis_data}

## Priority: {priority}
"""
    return StepOutput(content=report, success=True)
```

#### Early workflow termination:

```python
def quality_gate(step_input: StepInput) -> StepOutput:
    content = step_input.previous_step_content
    if not content or len(content) < 100:
        return StepOutput(
            content="Quality check failed: insufficient content.",
            success=False,
            stop=True,   # Halt the entire workflow
        )
    return StepOutput(content=content, success=True)
```

---

## 6. Running Workflows — `https://docs.agno.com/workflows/running-workflows`

### Import Statements

```python
from agno.workflow.workflow import Workflow
from agno.run.workflow import WorkflowRunOutput
```

### `Workflow.run()` — Method Signature & Parameters

```python
response: WorkflowRunOutput = workflow.run(
    input="Your topic or prompt here",          # str | dict | list | BaseModel
    markdown=True,                               # format output as markdown
    stream=False,                                # True = streaming iterator
    stream_events=False,                         # stream intermediate step events
    stream_executor_events=True,                 # stream agent/team events
    store_executor_outputs=True,                 # persist executor responses
    additional_data={"key": "value"},            # pass extra context to steps
)
```

### `Workflow.print_response()` — Development Helper

```python
workflow.print_response(
    input="Your topic or prompt here",
    markdown=True,
)
```

### `Workflow.arun()` — Async Execution

```python
import asyncio

async def main():
    response = await workflow.arun(
        input="Your topic",
        markdown=True,
    )
    print(response.content)

asyncio.run(main())
```

### Streaming Mode

```python
from agno.workflow.workflow import Workflow

stream = workflow.run(
    input="AI trends in 2025",
    stream=True,
    stream_events=True,
)

for event in stream:
    print(event)
```

### `WorkflowRunOutput` — Complete Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `content` | `Optional[str]` | Main output from the workflow |
| `content_type` | `str` | Type of content (default: `"str"`) |
| `step_results` | `List[StepOutput]` | Results from each step |
| `status` | `str` | Run status (`"pending"`, `"completed"`, `"failed"`) |
| `workflow_id` | `Optional[str]` | Workflow identifier |
| `workflow_name` | `Optional[str]` | Workflow name |
| `run_id` | `Optional[str]` | Run UUID |
| `session_id` | `Optional[str]` | Session identifier |
| `images` | `Optional[List]` | Workflow-level image outputs |
| `videos` | `Optional[List]` | Workflow-level video outputs |
| `audio` | `Optional[List]` | Workflow-level audio outputs |
| `step_executor_runs` | `Optional[List]` | Agent/team responses with `parent_run_id` |
| `events` | `Optional[List]` | Events captured during execution |
| `metrics` | `Optional[Dict]` | Duration, per-step metrics |
| `metadata` | `Optional[Dict]` | Additional metadata |
| `created_at` | `int` | Unix timestamp of creation |

### Complete Run Example

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.workflow.workflow import Workflow
from agno.workflow.step import Step, StepInput, StepOutput
from agno.db.sqlite import SqliteDb

agent1 = Agent(name="Researcher", model=OpenAIChat(id="gpt-4o"), instructions="Research.")
agent2 = Agent(name="Writer", model=OpenAIChat(id="gpt-4o"), instructions="Write.")

workflow = Workflow(
    name="Research & Write",
    description="Research a topic and write a summary",
    steps=[agent1, agent2],
    db=SqliteDb(db_file="tmp/workflow.db"),   # enables persistence
)

# Synchronous run
response = workflow.run(input="Quantum computing breakthroughs 2025")
print(response.content)
print(f"Steps completed: {len(response.step_results)}")

# Or pretty-print in terminal
workflow.print_response(input="Quantum computing breakthroughs 2025", markdown=True)
```

---

## 7. Step Reference — `https://docs.agno.com/reference/workflows/step`

### `Step` Class — Complete Parameter Reference

```python
from agno.workflow.step import Step

step = Step(
    # Identification
    name="Step Name",                    # str — step identifier (used in get_step_content())
    
    # Executor (provide exactly one)
    agent=my_agent,                      # Agent — agent executor
    team=my_team,                        # Team — multi-agent team executor
    executor=my_function,                # Callable — custom function or class with __call__
    
    # Human-in-the-Loop (HITL)
    requires_confirmation=False,         # bool — pause for user approval before execution
    confirmation_message="Proceed?",     # str — message shown for confirmation prompt
    requires_user_input=False,           # bool — collect user parameters before execution
    user_input_message="Please provide:", # str — prompt shown when collecting user input
    user_input_schema=[],                # List[UserInputField] — schema for input fields
)
```

### `Step` Executor Types

Each `Step` encapsulates **exactly one** executor:

| Executor Parameter | Type | When to Use |
|-------------------|------|-------------|
| `agent` | `Agent` | Single AI agent with specific role |
| `team` | `Team` | Multi-agent team for collaborative tasks |
| `executor` | `Callable` | Custom Python function or class |

You may also pass an `Agent`, `Team`, or function **directly** to the `steps` list without wrapping in `Step`:

```python
workflow = Workflow(
    name="Direct Executor Workflow",
    steps=[
        agent1,                          # Agent passed directly
        my_team,                         # Team passed directly
        my_custom_function,              # Function passed directly
        Step(name="Named Step", agent=agent2),  # Explicit Step with name
    ],
)
```

### Advanced Workflow Components

#### `Router` — Branching Logic

```python
from agno.workflow import Router

def route_selector(step_input: StepInput) -> str:
    """Return the name of the next step to execute."""
    if "finance" in step_input.input.lower():
        return "Finance Step"
    return "General Step"

router = Router(
    name="Topic Router",
    selector=route_selector,
    steps=[finance_step, general_step],
)
```

#### `Condition` — Conditional Execution

```python
from agno.workflow import Condition

def should_search_hackernews(step_input: StepInput) -> bool:
    return "tech" in step_input.input.lower()

hn_condition = Condition(
    name="HackerNews Condition",
    evaluator=should_search_hackernews,
    steps=[hackernews_research_step],
)
```

#### `Parallel` — Concurrent Execution

```python
from agno.workflow import Parallel, Condition

parallel_research = Parallel(
    Condition(
        name="HackerNews Check",
        evaluator=check_if_search_hn,
        steps=[hackernews_step],
    ),
    Condition(
        name="Finance Check",
        evaluator=check_if_search_finance,
        steps=[finance_step],
    ),
)
```

#### `Loop` — Iterative Execution

```python
from agno.workflow import Loop

def research_quality_check(step_input: StepInput) -> bool:
    """Return True to end the loop, False to continue."""
    content = step_input.previous_step_content or ""
    return len(content) > 500  # Stop when we have enough content

research_loop = Loop(
    name="Deep Research Loop",
    steps=[research_step],
    end_condition=research_quality_check,
    max_iterations=3,
)
```

### `Workflow` Class — Complete Parameter Reference

```python
from agno.workflow.workflow import Workflow
from agno.db.sqlite import SqliteDb

workflow = Workflow(
    # Core
    name="Workflow Name",                        # str
    description="What this workflow does",       # str
    steps=[step1, step2, step3],                 # List of Steps/Agents/Teams/Functions/Routers

    # Persistence
    db=SqliteDb(
        session_table="workflow_session",
        db_file="tmp/workflow.db",
    ),

    # Session State (shared across all steps)
    session_state={
        "counter": 0,
        "processed_items": [],
    },
)
```

### Session State Access (in custom functions)

```python
from agno.workflow.step import StepInput, StepOutput
from agno.run.context import RunContext  # or agno.workflow.context

def stateful_step(step_input: StepInput, run_context: RunContext) -> StepOutput:
    # Read session state
    count = run_context.session_state.get("counter", 0)

    # Update session state (persists across steps and runs if db configured)
    run_context.session_state["counter"] = count + 1
    run_context.session_state["last_topic"] = step_input.input

    return StepOutput(content=f"Processed item #{count + 1}")
```

---

## 8. Agents Overview — `https://docs.agno.com/agents/overview`

**Agents** in Agno are AI systems that combine a language model, tools, and instructions to process tasks autonomously. They execute through a reasoning loop:

1. Model processes context and instructions
2. Model decides whether to call tools
3. Tool results are fed back to the model
4. Loop repeats until a final response is produced

### Import Statements

```python
from agno.agent import Agent, RunOutput, RunOutputEvent, RunEvent
from agno.models.openai import OpenAIChat
from agno.models.anthropic import Claude
```

### Basic Agent

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
    instructions="Research topics thoroughly and provide detailed analysis.",
    markdown=True,
)

# Run (synchronous)
response = agent.run("What are the latest AI breakthroughs?")
print(response.content)

# Print to terminal (development helper)
agent.print_response("What are the latest AI breakthroughs?", markdown=True)
```

### Streaming Agent

```python
from typing import Iterator
from agno.agent import Agent, RunOutputEvent, RunEvent
from agno.models.openai import OpenAIChat

agent = Agent(model=OpenAIChat(id="gpt-4o"))

stream: Iterator[RunOutputEvent] = agent.run(
    "Explain quantum computing",
    stream=True,
    stream_intermediate_steps=True,
)

for chunk in stream:
    if chunk.event == RunEvent.run_content:
        print(chunk.content, end="", flush=True)
```

### Async Agent

```python
import asyncio
from agno.agent import Agent
from agno.models.anthropic import Claude

agent = Agent(model=Claude(id="claude-sonnet-4-5"))

async def main():
    response = await agent.arun("Summarize recent AI news")
    print(response.content)

asyncio.run(main())
```

### `RunOutput` (formerly `RunResponse`) — Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `content` | `Optional[str]` | The response content |
| `messages` | `Optional[List]` | Messages sent to the model |
| `metrics` | `Optional[Dict]` | Usage metrics (tokens, cost, etc.) |
| `run_id` | `Optional[str]` | Run identifier |
| `agent_id` | `Optional[str]` | Agent identifier |
| `session_id` | `Optional[str]` | Session identifier |
| `reasoning_content` | `Optional[str]` | Model's reasoning (if applicable) |

---

## 9. Building Agents — `https://docs.agno.com/agents/building-agents`

### `Agent` Class — Complete Parameter Reference

```python
from agno.agent import Agent

agent = Agent(
    # Identity
    name="Agent Name",
    id="custom-agent-id",                # str — autogenerated UUID if not set

    # Model
    model=OpenAIChat(id="gpt-4o"),       # Model object or "provider:model_id" string

    # Tools
    tools=[DuckDuckGoTools()],           # List of tools, toolkits, functions, or dicts
    show_tool_calls=False,               # bool — print tool call signatures in response
    tool_call_limit=10,                  # int — max tool calls per run
    tool_choice="auto",                  # "none" | "auto" | specific function name

    # Instructions
    instructions="Your role and behavior.", # str | List[str]
    markdown=True,                          # bool — enable markdown output formatting

    # Session & State
    user_id="user-123",                  # str — default user ID
    session_id="session-abc",            # str — autogenerated if not set
    session_state={},                    # dict — default session state in database
    add_session_state_to_context=False,  # bool
    cache_session=False,                 # bool — cache agent session in memory

    # Memory & Knowledge
    enable_agentic_memory=False,         # bool — enable agent to manage user memories
    knowledge=None,                      # KnowledgeBase — for RAG
    add_knowledge_to_context=False,      # bool — enable RAG

    # History & Context
    add_history_to_context=False,        # bool — add chat history to model messages
    num_history_runs=3,                  # int — number of historical runs to include
    num_history_messages=6,              # int — number of historical messages to include

    # Reasoning
    reasoning=False,                     # bool — enable reasoning mode

    # Output
    response_model=None,                 # Pydantic BaseModel for structured output
    structured_outputs=False,            # bool — force structured output
)
```

### Model Providers — Import Syntax

```python
# OpenAI
from agno.models.openai import OpenAIChat
agent = Agent(model=OpenAIChat(id="gpt-4o"))

# OpenAI Responses API (newer)
from agno.models.openai import OpenAIResponses
agent = Agent(model=OpenAIResponses(id="gpt-4o"))

# Anthropic Claude
from agno.models.anthropic import Claude
agent = Agent(model=Claude(id="claude-sonnet-4-5"))
# Popular Claude models:
# "claude-3-5-sonnet-20241022"    — recommended for most tasks
# "claude-opus-4-1-20250805"      — best/most capable
# "claude-3-5-haiku-20241022"     — fastest/cheapest

# Google Gemini
from agno.models.google import Gemini
agent = Agent(model=Gemini(id="gemini-2.0-flash-exp"))
```

### Structured Output with Pydantic

```python
from pydantic import BaseModel
from agno.agent import Agent
from agno.models.openai import OpenAIChat

class NewsReport(BaseModel):
    title: str
    summary: str
    key_points: list[str]
    sentiment: str

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    response_model=NewsReport,
)

response = agent.run("Summarize latest AI news")
report: NewsReport = response.content  # Typed Pydantic object
```

### Multi-Turn Conversation

```python
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    add_history_to_context=True,
    num_history_runs=5,
)

agent.print_response("My name is Alice.")
agent.print_response("What is my name?")  # Agent remembers "Alice"
```

---

## 10. Agent Tools — `https://docs.agno.com/agents/tools`

### Using Built-in Tools

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat

# Search tools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.tavily import TavilyTools
from agno.tools.exa import ExaTools
from agno.tools.serper import SerperTools
from agno.tools.wikipedia import WikipediaTools
from agno.tools.arxiv import ArxivTools
from agno.tools.hackernews import HackerNewsTools

# Finance tools
from agno.tools.yfinance import YFinanceTools

# Web scraping
from agno.tools.firecrawl import FirecrawlTools

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[
        DuckDuckGoTools(),
        YFinanceTools(),
        HackerNewsTools(),
    ],
)
```

### Python Functions as Tools

Any plain Python function can be a tool — just pass it in the `tools` list:

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat

def get_current_weather(city: str) -> str:
    """Get the current weather for a given city.
    
    Args:
        city: The name of the city.
    
    Returns:
        A string describing the weather.
    """
    # Your implementation
    return f"Sunny, 22°C in {city}"

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[get_current_weather],   # Pass the function directly
    show_tool_calls=True,
)

agent.print_response("What's the weather in Barcelona?")
```

**Important:** Always include a proper docstring — Agno uses it to describe the tool to the model.

### `@tool` Decorator — Advanced Tool Configuration

```python
from agno.tools import tool

@tool(
    name="search_web",                    # Override function name exposed to model
    description="Search the web for info", # Override docstring description
    cache_results=True,                   # Cache identical calls
    show_result=True,                     # Display result in agent response
    stop_after_tool_call=True,            # Stop agent after this tool runs
    requires_confirmation=True,           # Pause for user confirmation
    requires_user_input=True,             # Collect user input before execution
    external_execution=True,              # Execute outside agent control
)
def search_web(query: str) -> str:
    """Search the web."""
    # implementation
    return "results"
```

### Creating Custom Toolkits

```python
from typing import List
from agno.tools import Toolkit

class MyCustomTools(Toolkit):
    def __init__(self, api_key: str = None, **kwargs):
        self.api_key = api_key
        tools = [
            self.fetch_data,
            self.process_data,
        ]
        super().__init__(
            name="my_custom_tools",
            tools=tools,
            **kwargs
        )
    
    def fetch_data(self, query: str) -> str:
        """Fetch data from external API.
        
        Args:
            query: Search query string.
        
        Returns:
            Fetched data as string.
        """
        # implementation
        return f"Data for: {query}"
    
    def process_data(self, data: str) -> str:
        """Process and clean the fetched data.
        
        Args:
            data: Raw data string.
        
        Returns:
            Processed data string.
        """
        # implementation
        return data.strip()

# Usage
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[MyCustomTools(api_key="your-key")],
)
```

### Dynamic Tool Management

```python
agent = Agent(model=OpenAIChat(id="gpt-4o"))

# Add a single tool at runtime
agent.add_tool(DuckDuckGoTools())

# Replace all tools
agent.set_tools([YFinanceTools(), HackerNewsTools()])
```

---

## Complete End-to-End Example: Multi-Step Content Pipeline

```python
"""
Full production-ready workflow combining:
- Multiple agents with different roles
- A research team (multi-agent)
- Custom function steps for data shaping
- Session persistence via SQLite
"""

from agno.agent import Agent
from agno.team import Team
from agno.models.openai import OpenAIChat
from agno.models.anthropic import Claude
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools
from agno.tools.hackernews import HackerNewsTools
from agno.workflow.step import Step, StepInput, StepOutput
from agno.workflow.workflow import Workflow
from agno.db.sqlite import SqliteDb

# --- Agents ---

hackernews_agent = Agent(
    name="HackerNews Agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[HackerNewsTools()],
    instructions="Extract key insights from HackerNews. Focus on trending tech topics.",
)

finance_agent = Agent(
    name="Finance Agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[YFinanceTools()],
    instructions="Get stock prices and financial data for technology companies.",
)

writer_agent = Agent(
    name="Content Writer",
    model=Claude(id="claude-3-5-sonnet-20241022"),
    instructions=(
        "Write a compelling, well-structured article. "
        "Use the provided research. Format with clear sections and markdown."
    ),
    markdown=True,
)

# --- Research Team ---

research_team = Team(
    name="Research Team",
    members=[hackernews_agent, finance_agent],
    instructions=(
        "Collaboratively research the given topic. "
        "Combine tech news insights with financial data."
    ),
)

# --- Custom Function Steps ---

def prepare_research_query(step_input: StepInput) -> StepOutput:
    """Shape the workflow input into a focused research query."""
    topic = step_input.input
    additional = step_input.additional_data or {}
    focus_area = additional.get("focus", "general")
    
    query = (
        f"Research the following topic comprehensively: '{topic}'\n"
        f"Focus area: {focus_area}\n"
        f"Include: recent news, trends, key players, financial impact."
    )
    return StepOutput(content=query)


def prepare_writing_prompt(step_input: StepInput) -> StepOutput:
    """Shape research output into a structured writing prompt."""
    topic = step_input.input
    research = step_input.previous_step_content or "No research available."
    
    prompt = (
        f"Write a 1200-word article on: {topic}\n\n"
        f"## Research to incorporate:\n{research}\n\n"
        f"## Article structure:\n"
        f"1. Hook/Introduction\n"
        f"2. Current state of the topic\n"
        f"3. Key developments and trends\n"
        f"4. Impact and implications\n"
        f"5. Conclusion with forward-looking insights"
    )
    return StepOutput(content=prompt)


# --- Workflow ---

content_creation_workflow = Workflow(
    name="Content Creation Workflow",
    description="Automated content creation from research to polished article",
    steps=[
        Step(name="Query Preparation", executor=prepare_research_query),
        Step(name="Research Phase", team=research_team),
        Step(name="Writing Preparation", executor=prepare_writing_prompt),
        Step(name="Content Writing", agent=writer_agent),
    ],
    db=SqliteDb(
        session_table="content_workflow_sessions",
        db_file="tmp/workflows.db",
    ),
    session_state={"articles_created": 0},
)

# --- Execute ---

if __name__ == "__main__":
    content_creation_workflow.print_response(
        input="Impact of AI agents on software development in 2025",
        markdown=True,
        additional_data={"focus": "productivity and tooling"},
    )
```

---

## Quick Reference: Import Cheat Sheet

```python
# Core workflow imports
from agno.workflow.workflow import Workflow
from agno.workflow.step import Step, StepInput, StepOutput

# Workflow building blocks
from agno.workflow import Router, Condition, Parallel, Loop

# Agents & Teams
from agno.agent import Agent, RunOutput, RunOutputEvent, RunEvent
from agno.team import Team

# Models
from agno.models.openai import OpenAIChat, OpenAIResponses
from agno.models.anthropic import Claude
from agno.models.google import Gemini

# Built-in Tools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.tavily import TavilyTools
from agno.tools.yfinance import YFinanceTools
from agno.tools.hackernews import HackerNewsTools
from agno.tools.wikipedia import WikipediaTools
from agno.tools.arxiv import ArxivTools
from agno.tools.firecrawl import FirecrawlTools

# Custom Tools
from agno.tools import Toolkit, tool

# Storage
from agno.db.sqlite import SqliteDb

# Output types
from agno.run.workflow import WorkflowRunOutput

# Installation
# pip install -U agno
```
