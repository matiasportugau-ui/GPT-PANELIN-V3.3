# Agno Framework Research: Secondary Topics

Comprehensive research notes with exact imports, constructor syntax, and working code examples for each topic.

---

## 1. Memory v2

### Overview

Memory v2 became the default memory system starting with Agno v1.4.0 and continues in v2.0. It provides persistent storage for user preferences, context, and past interactions across conversations. Unlike session history (which stores conversation messages), Memory stores **extracted facts and insights** about users.

### Memory Modes

| Mode | Flag | Description |
|------|------|-------------|
| **Automatic Memory** | `update_memory_on_run=True` | Agno auto-extracts and stores memories after each run |
| **Agentic Memory** | `enable_agentic_memory=True` | Agent decides when to create/update/delete memories via built-in tools |

> **Warning:** Do not enable both simultaneously — `enable_agentic_memory` takes precedence.

### PostgreSQL Configuration

**Install:**
```bash
pip install -U agno openai sqlalchemy 'psycopg[binary]'
```

**Agent with PostgreSQL Memory:**
```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.db.postgres import PostgresDb

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"
db = PostgresDb(db_url=db_url)

agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    db=db,
    enable_user_memories=True,        # enable memory storage
    update_memory_on_run=True,         # auto-extract memories
    add_memories_to_context=True,      # inject memories into context
)

# Memories are auto-extracted from conversation
agent.print_response(
    "My name is John Doe and I like to play basketball on the weekends.",
    user_id="john"
)
# Next run will recall John's preferences
agent.print_response("What do I do on weekends?", user_id="john")
```

**Low-Level Memory v2 API (v1.x style, still available):**
```python
from agno.memory.v2.memory import Memory
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.schema import UserMemory

memory_db = PostgresMemoryDb(
    table_name="user_memories",
    connection_string="postgresql://user:password@localhost:5432/mydb"
)

memory = Memory(db=memory_db)

memory.add_user_memory(
    memory=UserMemory(
        memory="The user has a premium subscription",
        topics=["subscription", "account"]
    ),
    user_id="user@example.com"
)
```

### Custom Memory Manager

For advanced control over what gets stored:

```python
from agno.agent import Agent
from agno.memory import MemoryManager
from agno.models.openai import OpenAIResponses
from agno.db.postgres import PostgresDb

db = PostgresDb(db_url="postgresql+psycopg://ai:ai@localhost:5532/ai")

memory_manager = MemoryManager(
    db=db,
    model=OpenAIResponses(id="gpt-4o-mini"),
    additional_instructions="Don't store the user's real name or PII",
)

agent = Agent(
    db=db,
    memory_manager=memory_manager,
    update_memory_on_run=True,
)
```

### Memory Optimization (for users with many memories)

```python
from agno.memory.strategies.types import MemoryOptimizationStrategyType

optimized = agent.memory_manager.optimize_memories(
    user_id="user_123",
    strategy=MemoryOptimizationStrategyType.SUMMARIZE,
    apply=True,
)
```

### Supported Storage Backends

| Backend | Import |
|---------|--------|
| PostgreSQL | `from agno.db.postgres import PostgresDb` |
| SQLite | `from agno.db.sqlite import SqliteDb` |
| MongoDB | `from agno.memory.v2.db.mongodb import MongoMemoryDb` |
| Redis | `from agno.memory.v2.db.redis import RedisMemoryDb` |

---

## 2. Knowledge Bases

### Architecture

Agno's knowledge system has three layers:
1. **Readers** — ingest documents (JSON, PDF, CSV, etc.)
2. **Embedders** — convert text to vector representations
3. **Vector DBs** — store and search embeddings

### JSONKnowledgeBase / JSON Reader

**Import path:**
```python
from agno.knowledge.knowledge import Knowledge
from agno.knowledge.reader.json_reader import JSONReader
```

**Product catalog example:**
```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.knowledge.knowledge import Knowledge
from agno.knowledge.reader.json_reader import JSONReader
from agno.vectordb.pgvector import PgVector, SearchType
from agno.knowledge.embedder.openai import OpenAIEmbedder

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

# Create knowledge base with PgVector backend
knowledge = Knowledge(
    vector_db=PgVector(
        table_name="product_catalog",
        db_url=db_url,
        search_type=SearchType.hybrid,
        embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    ),
)

# Insert JSON product catalog
knowledge.insert(
    path="./data/products.json",
    reader=JSONReader(),
)

# Or async insert
# await knowledge.ainsert(path="./data/products.json", reader=JSONReader())

# Auto-detection also works (reader inferred from file extension)
# knowledge.insert(path="./data/products.json")

# Create agent with knowledge
agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    knowledge=knowledge,
    search_knowledge=True,  # enables RAG search
)

agent.print_response("What products do you have for residential walls?")
```

### PgVector Configuration

**Import:**
```python
from agno.vectordb.pgvector import PgVector, SearchType
```

**Constructor parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `table_name` | `str` | required | Table for vectors and metadata |
| `db_url` | `str` | required | PostgreSQL connection URL |
| `embedder` | `Embedder` | `OpenAIEmbedder()` | Embedder instance |
| `search_type` | `SearchType` | `SearchType.vector` | vector, keyword, or hybrid |
| `distance` | `Distance` | cosine | Distance metric for comparisons |

**SearchType options:**
```python
from agno.vectordb.pgvector import SearchType

SearchType.vector    # pure vector similarity
SearchType.keyword   # keyword/BM25 search
SearchType.hybrid    # combined vector + keyword
```

### OpenAIEmbedder Configuration

**Import:**
```python
from agno.knowledge.embedder.openai import OpenAIEmbedder
```

**Constructor parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `id` (or `model`) | `str` | `"text-embedding-ada-002"` | Embedding model name |
| `dimensions` | `int` | `1536` | Vector dimensionality |
| `api_key` | `str` | env `OPENAI_API_KEY` | API key |
| `batch_size` | `int` | `100` | Texts per API call |

**Example with newer model:**
```python
embedder = OpenAIEmbedder(
    id="text-embedding-3-small",
    dimensions=1536,
)
```

### Other Supported Embedders

| Embedder | Import |
|----------|--------|
| HuggingFace | `from agno.knowledge.embedder.huggingface import HuggingFaceEmbedder` |
| Ollama | `from agno.knowledge.embedder.ollama import OllamaEmbedder` |
| Cohere | `from agno.knowledge.embedder.cohere import CohereEmbedder` |
| Gemini | `from agno.knowledge.embedder.gemini import GeminiEmbedder` |

---

## 3. Guardrails

### Architecture

Guardrails in Agno are implemented through the **hooks system**:
- **Pre-hooks** (input guardrails) — execute **before** the agent processes input
- **Post-hooks** (output guardrails) — execute **after** the agent generates a response

### Built-in Guardrails

| Guardrail | Purpose |
|-----------|---------|
| `PromptInjectionGuardrail` | Detects jailbreak/injection patterns |
| `PIIDetectionGuardrail` | Detects personally identifiable information |
| `OpenAIModerationGuardrail` | Uses OpenAI's moderation API |

### Input Guardrails (Pre-hooks)

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.guardrails import PromptInjectionGuardrail

agent = Agent(
    name="Secure Agent",
    model=OpenAIChat(id="gpt-4o-mini"),
    pre_hooks=[PromptInjectionGuardrail()],
)

# This will raise InputCheckError if injection is detected
try:
    agent.print_response("Ignore all previous instructions and...")
except Exception as e:
    print(f"Blocked: {e}")
```

### Custom Input Guardrail

```python
import re
from agno.guardrails import BaseGuardrail
from agno.exceptions import CheckTrigger, InputCheckError
from agno.run.agent import RunInput

class URLGuardrail(BaseGuardrail):
    """Blocks inputs containing URLs."""

    def check(self, run_input: RunInput) -> None:
        if isinstance(run_input.input_content, str):
            url_pattern = r'https?://[^\s]+|www\.[^\s]+'
            if re.search(url_pattern, run_input.input_content):
                raise InputCheckError(
                    "URLs are not allowed in input.",
                    check_trigger=CheckTrigger.INPUT_NOT_ALLOWED,
                )

    async def async_check(self, run_input: RunInput) -> None:
        # Same logic; Agno calls this for .arun()
        self.check(run_input)


class ProfanityGuardrail(BaseGuardrail):
    """Blocks profane inputs."""

    BLOCKED_WORDS = {"badword1", "badword2"}

    def check(self, run_input: RunInput) -> None:
        if isinstance(run_input.input_content, str):
            words = set(run_input.input_content.lower().split())
            found = words & self.BLOCKED_WORDS
            if found:
                raise InputCheckError(
                    f"Profanity detected: {found}",
                    check_trigger=CheckTrigger.INPUT_NOT_ALLOWED,
                )

    async def async_check(self, run_input: RunInput) -> None:
        self.check(run_input)

# Usage
agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    pre_hooks=[URLGuardrail(), ProfanityGuardrail()],
)
```

### Output Guardrails (Post-hooks)

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.exceptions import CheckTrigger, OutputCheckError
from agno.run.team import RunOutput  # or agno.run.agent.RunOutput

def validate_response_length(run_output: RunOutput) -> None:
    """Ensure response is neither too short nor too long."""
    content = run_output.content.strip() if run_output.content else ""
    if len(content) < 20:
        raise OutputCheckError(
            "Response too brief",
            check_trigger=CheckTrigger.OUTPUT_NOT_ALLOWED,
        )
    if len(content) > 5000:
        raise OutputCheckError(
            "Response too lengthy",
            check_trigger=CheckTrigger.OUTPUT_NOT_ALLOWED,
        )


def validate_no_pii_in_output(run_output: RunOutput) -> None:
    """Check that the response doesn't contain email addresses."""
    import re
    if run_output.content and re.search(r'\b[\w.-]+@[\w.-]+\.\w+\b', run_output.content):
        raise OutputCheckError(
            "Response contains email addresses (PII leak)",
            check_trigger=CheckTrigger.OUTPUT_NOT_ALLOWED,
        )

agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    post_hooks=[validate_response_length, validate_no_pii_in_output],
)
```

### LLM-Based Output Validation

```python
from pydantic import BaseModel
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.exceptions import CheckTrigger, OutputCheckError
from agno.run.team import RunOutput

class OutputValidationResult(BaseModel):
    is_complete: bool
    is_professional: bool
    is_safe: bool
    concerns: list[str]
    confidence_score: float

def validate_response_quality(run_output: RunOutput) -> None:
    validator = Agent(
        name="Output Validator",
        model=OpenAIChat(id="gpt-4o-mini"),
        instructions=[
            "Evaluate if the response is complete, professional, and safe.",
            "Flag any concerns about quality or safety."
        ],
        output_schema=OutputValidationResult,
    )
    result = validator.run(
        input=f"Validate this response: '{run_output.content}'"
    )
    validation = result.content
    if not validation.is_safe:
        raise OutputCheckError(
            f"Unsafe content: {validation.concerns}",
            check_trigger=CheckTrigger.OUTPUT_NOT_ALLOWED,
        )
```

---

## 4. Context & Instructions

### Static Instructions

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    instructions=[
        "You are a helpful construction quotation assistant.",
        "Always respond in Spanish.",
        "Use metric units.",
    ],
)
```

### Dynamic Instructions with RunContext

Pass a **function** instead of a string/list. The function receives `RunContext` and returns a personalized instruction string.

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.run import RunContext

def get_instructions(run_context: RunContext) -> str:
    if not run_context.session_state:
        run_context.session_state = {}

    user_id = run_context.session_state.get("current_user_id", "guest")
    role = run_context.session_state.get("user_role", "customer")
    language = run_context.session_state.get("language", "en")

    return (
        f"You are assisting user '{user_id}' who has role '{role}'. "
        f"Respond in language: {language}. "
        f"If role is 'admin', you may discuss pricing details. "
        f"If role is 'customer', focus on product recommendations."
    )

agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    instructions=get_instructions,
    session_state={
        "current_user_id": "john.doe",
        "user_role": "admin",
        "language": "es",
    },
)

agent.print_response("Show me pricing for wall panels")
```

### Session State in Instructions (Template Substitution)

A simpler approach using `{variable}` placeholders:

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    session_state={
        "user_name": "Carlos",
        "company": "Panelin BMC",
        "role": "Sales Engineer",
    },
    instructions=(
        "You are helping {user_name} from {company}. "
        "Their role is {role}. Personalize all responses accordingly."
    ),
)
```

### Dynamic State via Tool Hooks

State can be updated reactively during tool execution:

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.run import RunContext

def track_query_count(run_context: RunContext, **kwargs):
    if not run_context.session_state:
        run_context.session_state = {}
    count = run_context.session_state.get("query_count", 0)
    run_context.session_state["query_count"] = count + 1

agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    tool_hooks=[track_query_count],
)
```

### Built-in Context Enrichment

```python
agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    add_datetime_to_context=True,    # injects current date/time
    add_history_to_context=True,     # injects recent conversation history
    num_history_runs=3,              # how many past runs to include
    add_memories_to_context=True,    # injects user memories
)
```

---

## 5. Agent OS / Playground

### What is AgentOS?

AgentOS is a **production runtime and control plane** for multi-agent systems. It wraps your agents, teams, and workflows in a FastAPI application with **50+ ready-to-use endpoints** and SSE-compatible streaming.

### Basic Setup

**Install:**
```bash
uv pip install -U 'agno[os]' openai
```

**Create and serve an agent:**
```python
# agents.py
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.db.sqlite import SqliteDb
from agno.os import AgentOS

support_agent = Agent(
    id="support-agent",
    name="Support Agent",
    model=OpenAIChat(id="gpt-4o-mini"),
    db=SqliteDb(db_file="agno.db"),
    instructions=["You are a helpful support agent."],
    add_datetime_to_context=True,
    add_history_to_context=True,
    num_history_runs=3,
    markdown=True,
)

agent_os = AgentOS(agents=[support_agent])
app = agent_os.get_app()
```

**Run:**
```bash
fastapi dev agents.py
```

**Access points:**
| URL | Description |
|-----|-------------|
| `http://localhost:8000` | Control plane UI |
| `http://localhost:8000/docs` | Swagger API documentation |
| `http://localhost:8000/config` | AgentOS configuration |

### Playground

The Playground is a web UI at **`app.agno.com/playground`** that connects to your local AgentOS at `localhost:7777/v1`.

**Features:**
- Multi-agent testing interface
- Multimodal input (text, images, audio)
- Human-in-the-loop workflows
- Reasoning traces visualization
- Real-time streaming

### Core API Endpoints

AgentOS automatically exposes these REST endpoints:

**Agent endpoints:**
- `POST /agents/{agent_id}/runs` — Run an agent
- `GET /agents` — List all agents
- `GET /agents/{agent_id}` — Get agent details

**Team endpoints:**
- `POST /teams/{team_id}/runs` — Run a team
- `GET /teams` — List all teams

**Workflow endpoints:**
- `POST /workflows/{workflow_id}/runs` — Run a workflow
- `GET /workflows` — List all workflows

**Session/Memory endpoints:**
- Session management (create, list, get, delete)
- Memory management (list, search, optimize)
- Knowledge base management (insert, search)
- Evaluation endpoints

**Run parameters (form-based):**

| Parameter | Type | Description |
|-----------|------|-------------|
| `message` | `str` | Input message |
| `stream` | `bool` | Enable SSE streaming |
| `user_id` | `str` | User identifier |
| `session_id` | `str` | Session identifier |
| `dependencies` | `dict` | External dependencies |
| `session_state` | `dict` | Session state override |
| `metadata` | `dict` | Custom metadata |
| `output_schema` | `dict` | Pydantic schema for structured output |

### AgentOS with Teams and Workflows

```python
from agno.agent import Agent
from agno.team import Team
from agno.models.openai import OpenAIChat
from agno.os import AgentOS

researcher = Agent(id="researcher", name="Researcher", model=OpenAIChat(id="gpt-4o-mini"))
writer = Agent(id="writer", name="Writer", model=OpenAIChat(id="gpt-4o-mini"))

content_team = Team(
    id="content-team",
    name="Content Team",
    agents=[researcher, writer],
    model=OpenAIChat(id="gpt-4o-mini"),
)

agent_os = AgentOS(
    agents=[researcher, writer],
    teams=[content_team],
)
app = agent_os.get_app()
```

### Bring Your Own FastAPI App

```python
from fastapi import FastAPI
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.os import AgentOS

custom_app = FastAPI(title="Panelin API")

@custom_app.get("/health")
async def health():
    return {"status": "ok"}

@custom_app.get("/api/v1/products")
async def list_products():
    return {"products": [...]}

agent_os = AgentOS(
    agents=[Agent(id="panelin-agent", model=OpenAIChat(id="gpt-4o-mini"))],
    base_app=custom_app,           # your existing FastAPI app
    on_route_conflict="preserve_base_app",  # your routes take priority
)

app = agent_os.get_app()
```

### Key AgentOS Properties

- **Private by design**: all data stored in your database
- **JWT-based RBAC**: hierarchical scopes for security
- **Request isolation**: no state bleed between users/agents/sessions
- **Hot reload**: changes to agents reflect without rebuilding

---

## 6. Deployment

### Docker Deployment (Official Template)

**Create project from template:**
```bash
uv pip install -U 'agno[infra]'
ag infra create --template agentos-docker --name my-agentos
cd my-agentos
```

**Project structure:**
```
my-agentos/
├── agents/           # Agent definitions
├── teams/            # Team definitions
├── workflows/        # Workflow definitions
├── compose.yml       # Docker Compose (AgentOS + PostgreSQL/pgvector)
├── Dockerfile        # Application container
└── pyproject.toml
```

**Deploy locally:**
```bash
export OPENAI_API_KEY=sk-***
docker compose up -d --build
```

**Access:** `http://localhost:8000/docs`

**Commands:**

| Action | Command |
|--------|---------|
| Start | `ag infra up` or `docker compose up -d --build` |
| Stop | `ag infra down` or `docker compose down` |
| Restart | `ag infra restart` or `docker compose restart` |
| Logs | `docker compose logs -f` |

### Docker Compose Structure

```yaml
# compose.yml (reference structure)
services:
  agentos:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DATABASE_URL=postgresql+psycopg://ai:ai@db:5432/ai
    depends_on:
      - db

  db:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_USER: ai
      POSTGRES_PASSWORD: ai
      POSTGRES_DB: ai
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

### FastAPI Integration

AgentOS is built on FastAPI. For custom deployments:

```python
# app.py
from fastapi import FastAPI
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.db.postgres import PostgresDb
from agno.os import AgentOS

db = PostgresDb(db_url="postgresql+psycopg://ai:ai@db:5432/ai")

panelin_agent = Agent(
    id="panelin-quotation",
    name="Panelin Quotation Agent",
    model=OpenAIChat(id="gpt-4o-mini"),
    db=db,
    enable_user_memories=True,
    instructions=["You are the Panelin quotation engine."],
)

agent_os = AgentOS(agents=[panelin_agent])
app = agent_os.get_app()

# Run with: uvicorn app:app --host 0.0.0.0 --port 8000
# Or:       fastapi dev app.py
```

**Dockerfile:**
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install uv && uv pip install --system -r pyproject.toml

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Cloud Deployment Targets

The Docker template is compatible with:
- **Hosted PaaS**: Railway, Render, Fly.io, Modal
- **Cloud IaaS**: AWS ECS, Google Cloud Run, Azure VMs
- **Other**: DigitalOcean App Platform

For AWS specifically, Agno provides an **AWS ECS template**:
```bash
ag infra create --template agentos-aws --name my-aws-deploy
```

This includes security groups, RDS database, load balancers, and ECS task definitions.

---

## 7. Tracing / Observability

### Architecture

Agno uses **OpenTelemetry (OTEL)** as the tracing backbone, with the `AgnoInstrumentor` from the `openinference-instrumentation-agno` package. This enables integration with any OTEL-compatible backend.

### Install Dependencies

```bash
pip install agno opentelemetry-sdk opentelemetry-exporter-otlp openinference-instrumentation-agno
```

### Langfuse Integration

**Additional install:**
```bash
pip install langfuse
```

**Full example:**
```python
import base64
import os
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools
from openinference.instrumentation.agno import AgnoInstrumentor
from opentelemetry import trace as trace_api
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

# Langfuse authentication
LANGFUSE_AUTH = base64.b64encode(
    f"{os.environ['LANGFUSE_PUBLIC_KEY']}:{os.environ['LANGFUSE_SECRET_KEY']}".encode()
).decode()

os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "https://us.cloud.langfuse.com/api/public/otel"
os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {LANGFUSE_AUTH}"

# Configure OpenTelemetry
tracer_provider = TracerProvider()
tracer_provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter()))
trace_api.set_tracer_provider(tracer_provider)

# Instrument Agno — call this BEFORE creating agents
AgnoInstrumentor().instrument()

# Create and use agent (traces are sent automatically)
agent = Agent(
    name="Traced Agent",
    model=OpenAIChat(id="gpt-4o-mini"),
    tools=[DuckDuckGoTools(search=True, news=True)],
    debug_mode=True,
)

agent.print_response("What is the current price of Tesla?")
```

**Langfuse data regions:**

| Region | Endpoint |
|--------|----------|
| US | `https://us.cloud.langfuse.com/api/public/otel` |
| EU | `https://cloud.langfuse.com/api/public/otel` |
| Self-hosted | `http://localhost:3000/api/public/otel` (v3.22.0+) |

### LangSmith Integration

```python
import os
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from openinference.instrumentation.agno import AgnoInstrumentor
from opentelemetry import trace as trace_api
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

# LangSmith configuration
endpoint = "https://api.smith.langchain.com/otel/v1/traces"  # US region
# endpoint = "https://eu.api.smith.langchain.com/otel/v1/traces"  # EU region
headers = {
    "x-api-key": os.environ["LANGSMITH_API_KEY"],
    "Langsmith-Project": os.environ.get("LANGSMITH_PROJECT", "default"),
}

tracer_provider = TracerProvider()
tracer_provider.add_span_processor(
    SimpleSpanProcessor(OTLPSpanExporter(endpoint=endpoint, headers=headers))
)
trace_api.set_tracer_provider(tracer_provider)

AgnoInstrumentor().instrument()

agent = Agent(
    name="LangSmith Traced Agent",
    model=OpenAIChat(id="gpt-4o-mini"),
    debug_mode=True,
)

agent.print_response("Summarize recent AI news")
```

### Alternative: OpenLIT Method (for Langfuse)

```python
import openlit

openlit.init()  # auto-instruments Agno

agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    debug_mode=True,
)
```

### What Gets Traced

The `AgnoInstrumentor` captures:
- **Agent execution flows**: full call chains through agents and teams
- **Tool invocations**: each tool call with inputs/outputs
- **LLM calls**: model requests with token usage
- **Knowledge searches**: RAG retrieval operations
- **Memory operations**: read/write to memory stores
- **Errors and exceptions**: with full stack traces

### Environment Variables Summary

```bash
# Langfuse
export LANGFUSE_PUBLIC_KEY=pk-***
export LANGFUSE_SECRET_KEY=sk-***

# LangSmith
export LANGSMITH_API_KEY=ls-***
export LANGSMITH_TRACING=true
export LANGSMITH_PROJECT=my-project
export LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

---

## Quick Reference: All Key Imports

```python
# Core
from agno.agent import Agent
from agno.team import Team
from agno.models.openai import OpenAIChat, OpenAIResponses
from agno.models.anthropic import Claude
from agno.run import RunContext

# Database backends
from agno.db.postgres import PostgresDb
from agno.db.sqlite import SqliteDb

# Memory
from agno.memory import MemoryManager
from agno.memory.v2.memory import Memory
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.schema import UserMemory

# Knowledge
from agno.knowledge.knowledge import Knowledge
from agno.knowledge.reader.json_reader import JSONReader
from agno.knowledge.embedder.openai import OpenAIEmbedder

# Vector DB
from agno.vectordb.pgvector import PgVector, SearchType

# Guardrails
from agno.guardrails import BaseGuardrail, PromptInjectionGuardrail
from agno.exceptions import CheckTrigger, InputCheckError, OutputCheckError
from agno.run.agent import RunInput
from agno.run.team import RunOutput

# AgentOS
from agno.os import AgentOS

# Tracing
from openinference.instrumentation.agno import AgnoInstrumentor

# Tools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.mcp import MCPTools
```
