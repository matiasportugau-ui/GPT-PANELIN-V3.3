# Agno Framework - Comprehensive Research Document

> Validated information from docs.agno.com (researched March 2026)

---

## 1. Workflows

### Imports

```python
from agno.workflow.workflow import Workflow
from agno.workflow.step import Step, StepInput, StepOutput
from agno.workflow.router import Router
```

### Creating Workflows with Sequential Steps

Steps are the fundamental unit of work. Each Step encapsulates exactly one executor — an Agent, Team, or custom Python function.

```python
from agno.workflow.step import Step
from agno.workflow.workflow import Workflow

research_step = Step(name="Research Step", team=research_team)
content_planning_step = Step(name="Content Planning Step", agent=content_planner)
writing_step = Step(name="Writing Step", agent=writer_agent)

workflow = Workflow(
    name="Content Creation Workflow",
    steps=[research_step, content_planning_step, writing_step],
)
```

### Step Constructor Parameters

| Parameter | Description |
|-----------|-------------|
| `name` | Step identification string |
| `agent` | An Agent executor for the step |
| `team` | A Team executor for the step |
| `executor` | Custom Python function to execute |
| `max_retries` | Default 3 retry attempts on failure |
| `timeout_seconds` | Execution timeout |
| `skip_on_failure` | Skip step if it fails after retries |
| `requires_confirmation` | Pause for user confirmation before execution |
| `requires_user_input` | Collect user input before execution |

### Steps with Pure Python Functions (No LLM)

Define a `Step` with a custom function as the `executor`. The function must accept a `StepInput` and return a `StepOutput`:

```python
from agno.workflow.step import Step, StepInput, StepOutput

def custom_function(step_input: StepInput) -> StepOutput:
    message = step_input.input
    previous_step_content = step_input.previous_step_content

    result = process_data(message, previous_step_content)

    return StepOutput(content=result)

custom_step = Step(
    name="Custom Step",
    executor=custom_function,
)
```

**Class-based executor alternative:**

```python
class CustomExecutor:
    def __call__(self, step_input: StepInput) -> StepOutput:
        return StepOutput(content="result")

step = Step(name="Custom Step", executor=CustomExecutor())
```

**Fully Python workflow (single function replaces all steps):**

```python
from agno.workflow.workflow import Workflow

def custom_workflow_function(workflow: Workflow, execution_input):
    # Complete control over execution flow
    return final_result

workflow = Workflow(name="Function-Based Workflow", steps=custom_workflow_function)
```

### Router / Conditional Steps

A `Router` selects exactly one execution path based on a `selector` function. The selector receives `StepInput` and returns a step name (string), a `Step` object, or a `List[Step]`.

```python
from agno.workflow.step import Step, StepInput
from agno.workflow.router import Router
from typing import Union, List

def route_by_topic(step_input: StepInput) -> Union[str, Step, List[Step]]:
    topic = step_input.input.lower()
    if "tech" in topic or "ai" in topic:
        return "Tech Research"
    elif "business" in topic:
        return "Business Research"
    else:
        return "General Research"

router = Router(
    selector=route_by_topic,
    choices=[tech_step, business_step, general_step],
)
```

**With session state access:**

```python
from agno.run import RunContext

def route_based_on_state(step_input: StepInput, run_context: RunContext) -> Step:
    preference = run_context.session_state.get("agent_preference", "general")
    run_context.session_state["interaction_count"] = (
        run_context.session_state.get("interaction_count", 0) + 1
    )
    if preference == "technical":
        return technical_step
    return general_step
```

**With dynamic step_choices:**

```python
def dynamic_selector(step_input: StepInput, step_choices: list) -> Union[str, Step, List[Step]]:
    step_map = {s.name: s for s in step_choices if hasattr(s, "name")}
    if "full" in step_input.input.lower():
        return [step_map["researcher"], step_map["writer"]]
    return step_choices[0]
```

### Running Workflows

**Synchronous:**

```python
response = workflow.run(message="AI trends in 2024", markdown=True)
# response is a WorkflowRunResponse with .content, .run_id, .status, etc.
```

**Asynchronous:**

```python
response = await workflow.arun(message="AI trends in 2024")
```

**Streaming (async):**

```python
async for event in workflow.arun(message="topic", stream=True):
    # event is a WorkflowRunOutputEvent (step_started, step_completed, etc.)
    pass
```

**Background execution:**

```python
run_id = await workflow.arun(message="topic", background=True)
# Poll status using run_id
```

**Event filtering:**

```python
workflow = Workflow(
    name="My Workflow",
    steps=[...],
    store_events=True,
    events_to_skip=["step_started"],  # skip verbose events
)
```

---

## 2. Agents

### Imports

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
```

### Creating an Agent

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat

agent = Agent(
    name="My Agent",
    model=OpenAIChat(id="gpt-4o"),
    instructions="You are a helpful assistant.",
    tools=[my_tool_1, my_tool_2],
    markdown=True,
)

agent.print_response("Hello!", stream=True)
```

### Core Constructor Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `model` | Model or str | Model object or `"provider:model_id"` string |
| `name` | str | Agent name |
| `id` | str | Agent ID (auto-generated UUID if not set) |
| `instructions` | str/list | Instructions for the agent |
| `tools` | list | Tools available to the agent |
| `markdown` | bool | Enable markdown formatting |

### Session Management Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `user_id` | None | Default user ID |
| `session_id` | auto | Session ID (auto-generated if not set) |
| `session_state` | None | Default session state dictionary |
| `add_session_state_to_context` | False | Add session state to context |
| `enable_agentic_state` | False | Allow agent to update session state |
| `cache_session` | False | Cache current session in memory |
| `search_session_history` | False | Search through previous sessions |
| `num_history_sessions` | None | Number of past sessions to include |

### History/Context Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `add_history_to_context` | False | Add chat history to messages |
| `num_history_runs` | None | Number of historical runs |
| `num_history_messages` | None | Number of historical messages |

### Knowledge & Memory Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `knowledge` | None | Knowledge base object |
| `knowledge_filters` | None | Filters for knowledge base |
| `add_knowledge_to_context` | False | Enable RAG |
| `db` | None | Database for session storage |
| `memory_manager` | None | Custom MemoryManager |
| `enable_agentic_memory` | False | Agent manages its own memories |
| `update_memory_on_run` | False | Auto-update memories after each run |

### Adding Tools to Agents

Tools can be Python functions or toolkit instances:

```python
from agno.tools.duckduckgo import DuckDuckGoTools

def my_custom_tool(query: str) -> str:
    """Search for information."""
    return f"Result for {query}"

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools(), my_custom_tool],
)
```

---

## 3. MCP Integration

### Imports

```python
from agno.tools.mcp import MCPTools
```

### MCPTools with SSE Transport

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.mcp import MCPTools

server_url = "http://localhost:8000/sse"

mcp_tools = MCPTools(url=server_url, transport="sse")

agent = Agent(
    name="MCP Agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[mcp_tools],
)
```

> **Note:** SSE transport is deprecated. The recommended transport is `"streamable-http"`:

```python
mcp_tools = MCPTools(transport="streamable-http", url="https://your-mcp-server.com")
```

### SSE Configuration with SSEClientParams

```python
from agno.tools.mcp import MCPTools

mcp_tools = MCPTools(
    transport="sse",
    url="http://localhost:8000/sse",
    server_params={
        "sse_read_timeout": 30,
        "timeout": 10,
        "headers": {"Authorization": "Bearer token"},
    },
)
```

### Tool Filtering

**Include only specific tools:**

```python
mcp_tools = MCPTools(
    url="http://localhost:8000/sse",
    transport="sse",
    include_tools=["write_file"],
)
```

**Exclude specific tools:**

```python
mcp_tools = MCPTools(
    url="http://localhost:8000/sse",
    transport="sse",
    exclude_tools=["create_draft_email"],
)
```

### MCPToolbox (Advanced Filtering by Toolset)

```python
from agno.tools.mcp import MCPToolbox

async with MCPToolbox(
    url="http://127.0.0.1:5001",
    toolsets=["hotel-management"],
) as toolbox:
    agent = Agent(tools=[toolbox])
```

---

## 4. Storage

### Imports

```python
from agno.db.postgres import PostgresDb
```

### PostgresStorage / PostgresDb Configuration

```python
from agno.db.postgres import PostgresDb

db = PostgresDb(
    db_url="postgresql+psycopg://user:password@localhost:5432/mydb",
)

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    db=db,
    session_id="user_123",  # Same ID = same conversation
)
```

**Connection string format:**

```
postgresql+psycopg://user:password@host:port/database
```

**Custom session table:**

```python
db = PostgresDb(
    db_url="postgresql+psycopg://user:password@localhost:5432/mydb",
    session_table="my_agent_sessions",
)
```

**What gets stored:** session_id, session_type, agent_id, user_id, session_data, runs, messages, metadata, timestamps.

### Other Storage Backends

**SQLite:**

```python
from agno.db.sqlite import SqliteDb

db = SqliteDb(db_file="tmp/agent.db")
```

**JSON (demo/testing only):**

```python
from agno.db.json import JsonDb

db = JsonDb(db_path="tmp/json_db")
```

### Docker Setup for Local Postgres

```bash
docker run -d \
  -e POSTGRES_DB=ai \
  -e POSTGRES_USER=ai \
  -e POSTGRES_PASSWORD=ai \
  -p 5532:5432 \
  agno/pgvector:16
```

Connection: `db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"`

---

## 5. Models

### OpenAI

```python
from agno.models.openai import OpenAIChat

model = OpenAIChat(id="gpt-4o", temperature=0.5)
# Requires: OPENAI_API_KEY env var
```

Key parameters: `id` (default `"gpt-4o"`), `temperature`, `max_completion_tokens`, `reasoning_effort` (for o1 models).

There is also `OpenAIResponses` for the Responses API:

```python
from agno.models.openai import OpenAIResponses

model = OpenAIResponses(id="gpt-5-mini")
```

### Anthropic Claude

```python
from agno.models.anthropic import Claude

model = Claude(id="claude-sonnet-4-20250514")
# Requires: ANTHROPIC_API_KEY env var
```

Key models: `claude-3-5-haiku-20241022` (fastest), `claude-sonnet-4-20250514` (balanced), `claude-opus-4-1-20250805` (best).

Supports: `cache_system_prompt=True`, structured outputs via Pydantic, `betas` parameter.

### Google Gemini

```python
from agno.models.google import Gemini

model = Gemini(id="gemini-2.0-flash")
# Requires: GOOGLE_API_KEY env var
# Install: pip install google-genai agno
```

Key parameters: `id`, `api_key`, `generation_config`, `system_instruction`, `thinking_enabled`.

### Model Swapping

Models can be swapped via string notation `"provider:model_id"`:

```python
agent = Agent(model="openai:gpt-4o")
# or
agent = Agent(model="anthropic:claude-sonnet-4")
```

> **Note:** Cross-provider switching (OpenAI ↔ Anthropic ↔ Google) can cause issues due to incompatible message formats. Same-provider swaps are recommended.

---

## 6. Knowledge & Memory

### Knowledge with PgVector

```python
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector, SearchType

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

knowledge_base = Knowledge(
    vector_db=PgVector(
        table_name="recipes",
        db_url=db_url,
        search_type=SearchType.hybrid,
    )
)

# Load data
knowledge_base.insert(url="https://example.com/data.pdf")

# Use with agent
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    knowledge=knowledge_base,
    search_knowledge=True,
)
```

### Knowledge Tools (Agentic RAG)

```python
from agno.knowledge.knowledge import Knowledge
from agno.tools.knowledge import KnowledgeTools

knowledge = Knowledge(vector_db=PgVector(...))
agent = Agent(
    knowledge=knowledge,
    tools=[KnowledgeTools()],
)
```

### JSON as Database (for testing/demos)

```python
from agno.db.json import JsonDb

db = JsonDb(
    db_path="tmp/json_db",
    session_table="sessions",
    memory_table="memories",
    knowledge_table="knowledge",
)
```

### Memory V2 (default since v1.4.0)

```python
from agno.memory.v2.memory import Memory
from agno.memory.v2.db.sqlite import SqliteMemoryDb

memory_db = SqliteMemoryDb(table_name="memories", db_file="path/to/memory.db")
memory = Memory(db=memory_db)
```

**Agent-level memory configuration:**

```python
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    db=SqliteDb(db_file="tmp/agent.db"),
    enable_agentic_memory=True,      # Agent can manage memories via tool
    update_memory_on_run=True,        # Auto-update after each run
    add_history_to_context=True,
)
```

**Custom MemoryManager:**

```python
from agno.memory.manager import MemoryManager

memory = Memory(
    model=OpenAIChat(id="gpt-4o"),
    memory_manager=MemoryManager(
        model=OpenAIChat(id="gpt-4o"),
        memory_capture_instructions="Focus on user preferences and facts.",
    ),
    db=memory_db,
)
```

**MemoryTools toolkit:**

```python
from agno.tools.memory import MemoryTools

memory_tools = MemoryTools(
    db=my_database,
    enable_think=True,
    enable_get_memories=True,
)
# Operations: add_memory, update_memory, delete_memory, get_memories, think, analyze
```

**Manual memory creation:**

```python
memory.create_user_memories(
    message="User likes dark mode and Python.",
    user_id="user_123",
)
```

---

## 7. Guardrails

### Input Guardrails (Pre-Hooks)

```python
from agno.guardrails import BaseGuardrail
from agno.exceptions import CheckTrigger, InputCheckError
from agno.run.agent import RunInput

class URLGuardrail(BaseGuardrail):
    """Block inputs containing URLs."""

    def check(self, run_input: RunInput) -> None:
        import re
        if isinstance(run_input.input_content, str):
            url_pattern = r'https?://[^\s]+|www\.[^\s]+'
            if re.search(url_pattern, run_input.input_content):
                raise InputCheckError(
                    "URLs are not allowed.",
                    check_trigger=CheckTrigger.INPUT_NOT_ALLOWED,
                )

    async def async_check(self, run_input: RunInput) -> None:
        self.check(run_input)

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    pre_hooks=[URLGuardrail()],
)
```

### Built-in Guardrails

- **OpenAI Moderation Guardrail** — detects content policy violations
- **Prompt Injection Guardrail** — detects prompt injection attempts
- **PII Detection Guardrail** — detects personally identifiable information

### Output Validation (Post-Hooks)

For validating agent/team outputs before returning to users:

```python
from agno.exceptions import CheckTrigger, OutputCheckError
from agno.run.team import RunOutput

def validate_output(run_output: RunOutput) -> None:
    content = run_output.content or ""
    if len(content) < 20:
        raise OutputCheckError(
            "Response too brief.",
            check_trigger=CheckTrigger.OUTPUT_NOT_ALLOWED,
        )

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    post_hooks=[validate_output],
)
```

**Preventing hallucinated prices (example pattern):**

```python
from pydantic import BaseModel

class ValidationResult(BaseModel):
    is_complete: bool
    is_professional: bool
    is_safe: bool
    concerns: list[str]
    confidence_score: float

def validate_no_hallucinated_prices(run_output: RunOutput) -> None:
    content = run_output.content or ""
    # Check for price patterns that shouldn't be there
    import re
    price_pattern = r'\$\d+\.?\d*'
    if re.search(price_pattern, content):
        raise OutputCheckError(
            "Output contains prices that may be hallucinated. "
            "Prices should only come from verified data sources.",
            check_trigger=CheckTrigger.OUTPUT_NOT_ALLOWED,
        )
```

---

## 8. AgentOS & Playground

### Playground Setup

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.playground import Playground

agent = Agent(
    name="My Agent",
    model=OpenAIChat(id="gpt-4o"),
    markdown=True,
)

playground = Playground(agents=[agent])
app = playground.get_app()

if __name__ == "__main__":
    playground.serve(app="my_file:app", reload=True)
```

Access UI at `http://localhost:7777`, API docs at `http://localhost:7777/docs`.

### Playground Constructor Parameters

| Parameter | Description |
|-----------|-------------|
| `agents` | List of Agent instances to serve |
| `teams` | List of Team instances to serve |
| `workflows` | List of Workflow instances to serve |
| `app_id` | Application ID |
| `name` | Application name |
| `description` | Application description |
| `settings` | PlaygroundSettings configuration |
| `api_app` | Custom FastAPI app (optional) |
| `router` | Custom APIRouter (optional) |

### Auto-Exposed API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/agents/{agent_id}/runs` | POST | Run an agent |
| `/teams/{team_id}/runs` | POST | Run a team |
| `/workflows/{workflow_id}/runs` | POST | Run a workflow |

Run endpoints accept: `message`, `stream`, `user_id`, `session_id`, `dependencies`, `output_schema`.

### Key Methods

- `playground.get_app()` — returns configured FastAPI application
- `playground.serve(app=..., reload=True)` — launches Uvicorn server
- `playground.get_router()` — returns the APIRouter

### AgentOS (Production)

```python
from agno.os import AgentOS

agent_os = AgentOS(agents=[agent])
app = agent_os.get_app()
```

---

## 9. Deployment

### Docker Template

Agno provides a production-ready Docker template:

```bash
# Install
uv pip install -U 'agno[infra]'

# Create from template
ag infra create --template agentos-docker --name my-app

# Or clone directly
git clone https://github.com/agno-agi/agentos-docker-template.git
```

**Docker Compose commands:**

| Command | Purpose |
|---------|---------|
| `docker compose up -d --build` | Start containers |
| `docker compose down` | Stop containers |
| `docker compose restart` | Restart (e.g., after env var changes) |
| `docker compose logs -f` | View logs |

The template includes AgentOS + PostgreSQL with pgvector. Access API at `http://localhost:8000/docs`.

### PgVector Docker Setup

```bash
docker run -d \
  -e POSTGRES_DB=ai \
  -e POSTGRES_USER=ai \
  -e POSTGRES_PASSWORD=ai \
  -e PGDATA=/var/lib/postgresql/data/pgdata \
  -v pgvolume:/var/lib/postgresql/data \
  -p 5532:5432 \
  --name pgvector \
  agnohq/pgvector:16
```

### AWS Deployment

```bash
ag infra up prd:aws
```

Deploys to ECS Fargate with RDS PostgreSQL and Application Load Balancer. Estimated cost: $65-100/month.

### Deployment Options Summary

| Template | Target | Best For |
|----------|--------|----------|
| `agentos-docker` | Docker (local/any cloud) | Self-hosted, development |
| Railway | Railway PaaS | Quick MVPs |
| AWS | ECS Fargate + RDS | Enterprise scale |

### Environment Variables

Key environment variables needed:

- `OPENAI_API_KEY` — for OpenAI models
- `ANTHROPIC_API_KEY` — for Claude models
- `GOOGLE_API_KEY` — for Gemini models
- Database connection strings as needed

---

## Quick Reference: All Key Imports

```python
# Agent
from agno.agent import Agent

# Models
from agno.models.openai import OpenAIChat, OpenAIResponses
from agno.models.anthropic import Claude
from agno.models.google import Gemini

# Workflows
from agno.workflow.workflow import Workflow
from agno.workflow.step import Step, StepInput, StepOutput
from agno.workflow.router import Router
from agno.run import RunContext

# Storage
from agno.db.postgres import PostgresDb
from agno.db.sqlite import SqliteDb
from agno.db.json import JsonDb

# Knowledge
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector, SearchType
from agno.tools.knowledge import KnowledgeTools

# Memory
from agno.memory.v2.memory import Memory
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.manager import MemoryManager
from agno.tools.memory import MemoryTools

# MCP
from agno.tools.mcp import MCPTools, MCPToolbox

# Guardrails
from agno.guardrails import BaseGuardrail
from agno.exceptions import CheckTrigger, InputCheckError, OutputCheckError
from agno.run.agent import RunInput
from agno.run.team import RunOutput

# Playground & AgentOS
from agno.playground import Playground
from agno.os import AgentOS
```
