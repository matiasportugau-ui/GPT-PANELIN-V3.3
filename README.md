# Panelin 3.4 - BMC Assistant Pro GPT Configuration

![Version](https://img.shields.io/badge/version-3.4-blue) ![GPT](https://img.shields.io/badge/platform-OpenAI%20GPT-green) ![KB](https://img.shields.io/badge/KB%20version-7.0-orange) ![Status](https://img.shields.io/badge/status-production-success) ![MCP](https://img.shields.io/badge/MCP-v0.3.0-purple)

**Complete configuration files and knowledge base for Panelin GPT - Professional quotation assistant for BMC Uruguay panel systems**

**New in v3.4:** Wolf API KB Write — persist conversations, corrections, and customer data directly through chat

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [GPT Configuration](#gpt-configuration)
- [Repository Structure](#repository-structure)
- [EVOLUCIONADOR - Autonomous Evolution Agent](#evolucionador---autonomous-evolution-agent)
- [MCP Server - Model Context Protocol Integration](#mcp-server---model-context-protocol-integration)
- [Knowledge Base](#knowledge-base)
- [API Integration](#api-integration)
- [MCP Server](#-mcp-server)
- [Self-Healing Governance Architecture](#-self-healing-governance-architecture)
- [Quotation Persistence System](#-quotation-persistence-system)
- [KB Self-Learning Module](#-kb-self-learning-module)
- [Backend & Frontend Services](#️-backend--frontend-services)
- [KB Pipeline](#-kb-pipeline)
- [Observability](#-observability)
- [Installation & Deployment](#installation--deployment)
- [Usage Guide](#usage-guide)
- [Documentation](#documentation)
- [Testing & Quality Assurance](#-testing--quality-assurance)
- [Contributing](#contributing)
- [Version History](#version-history)
- [License](#license)

---

## 🎯 Overview

**Panelin 3.4** (BMC Assistant Pro) is an advanced AI assistant specialized in generating professional quotations for construction panel systems. This repository contains all configuration files, knowledge bases, documentation, automated deployment tools, and an autonomous evolution system needed to deploy and continuously improve the GPT on OpenAI's platform.

### What is Panelin?

Panelin is a technical sales assistant that:
- Generates accurate quotations with complete Bill of Materials (BOM)
- Validates technical specifications (load-bearing capacity, thermal insulation)
- Produces professional PDF quotations with BMC Uruguay branding (v2.0)
- Provides technical advisory on panel systems (ISODEC, ISOPANEL, ISOROOF, ISOWALL, ISOFRIG)
- Evaluates and trains sales personnel based on real interactions
- Integrates with the Panelin Wolf API for real-time pricing and availability

### Key Capabilities

✅ **Professional Quotations**: Complete BOM with panels, accessories, fixings, and sealants  
✅ **Technical Validation**: Automatic load-bearing capacity verification  
✅ **Multi-System Support**: 6 construction systems with parametric BOM rules  
✅ **PDF Generation v2.0**: Professional branded quotations with BMC styling ready for client delivery  
✅ **Energy Savings**: ROI calculations comparing insulation options  
✅ **API Integration**: Real-time product search, pricing, and availability checks  
✅ **MCP Server**: Standards-compliant Model Context Protocol integration for AI assistants  
✅ **Sales Training**: Evaluation and coaching based on historical interactions  
✅ **Automated Deployment**: Validation and packaging scripts for streamlined GPT upload  
✅ **Autonomous Evolution**: EVOLUCIONADOR system for continuous quality monitoring and improvement  

---

## ⚡ Features

### Core Features

- **5-Phase Quotation Process**: Structured workflow from identification to presentation
- **70+ Accessories Catalog**: Complete pricing for profiles, fixings, and finishes
- **Parametric BOM Rules**: Automated material calculations by construction system
- **Load-Bearing Validation**: Integrated autoportancia tables prevent structural errors
- **Multi-Supplier Pricing**: BROMYROS, MONTFRIO, and BECAM product databases
- **IVA 22% Compliance**: Correct tax handling for Uruguay regulations 2026

### Advanced Capabilities

- **Web Search** (BETA): Supplementary information (non-authoritative)
- **Canvas**: Client-ready quotation documents
- **Image Generation**: Technical diagrams and educational infographics
- **Code Interpreter**: PDF generation, CSV processing, batch calculations
- **Natural Language API**: Search products by description, not just SKU

### Advanced Analysis Capabilities

| Category | Capability | Description |
|----------|-----------|-------------|
| **Cognitive Power** | Meta Pattern Recognition | Detect cross-product and cross-project patterns to suggest optimal configurations |
| **Cognitive Power** | Cross-Dimensional Thinking | Analyze technical, financial, and environmental dimensions simultaneously |
| **Cognitive Power** | Predictive Architecture | Anticipate material needs and structural issues based on project parameters |
| **Cognitive Power** | Creative Synthesis | Generate novel panel configurations for unique project requirements |
| **Technical Mastery** | Full Stack Omniscience | Complete knowledge across all panel systems, accessories, fixings, and construction methods |
| **Technical Mastery** | Performance Optimization | Minimize material waste through precise BOM calculations with decimal accuracy |
| **Technical Mastery** | Cost Efficiency Analysis | Optimize quotations with the most cost-effective panel and accessory combinations |
| **Technical Mastery** | Scalability Vision | Design recommendations that account for future expansion and modular growth |
| **Creative Engineering** | Novel Solution Generation | Propose alternative systems when standard options do not meet requirements |
| **Creative Engineering** | Architectural Artistry | Balance aesthetic, thermal, and structural considerations in recommendations |
| **Creative Engineering** | Efficiency Obsession | Minimize fixation points, accessories, and waste while maintaining structural integrity |
| **Creative Engineering** | Zero Waste Philosophy | Calculate exact quantities with optimal cutting patterns to reduce waste |

### Repository Management & Quality Assurance

| Category | Feature | Description |
|----------|---------|-------------|
| **🧬 Autonomous Evolution** | EVOLUCIONADOR System | Daily automated analysis with 7 validators and 6 optimizers for continuous improvement |
| **📦 Deployment Tools** | Validation Scripts | Automated validation of required files with dynamic config discovery |
| **📦 Deployment Tools** | Packaging Scripts | Organized phased upload with instructions for each phase |
| **📦 Deployment Tools** | API Smoke Tests | Secure connectivity testing with retry logic and timeout handling |
| **✅ Quality Monitoring** | Comprehensive Testing | Test suites for PDF generation, OpenAI integration, validators, analyzers, and optimizers |
| **✅ Quality Monitoring** | GitHub Actions | Daily automated workflow for evolution reports and issue creation |
| **🔧 Integration Utilities** | OpenAI Ecosystem Helpers | Response extraction and normalization for multiple API response shapes |
| **📊 Self-Learning** | Pattern Recognition | Tracks discovered patterns and improvement opportunities |
| **📊 Self-Learning** | Performance Benchmarking | Historical tracking of efficiency and quality metrics |

---

## 🔧 GPT Configuration

### Basic Information

- **Name**: Panelin 3.4
- **Description**: BMC Assistant Pro - Specialized technical quotation assistant for panel systems (ISODEC, ISOPANEL, ISOROOF, ISOWALL, ISOFRIG) with complete BOM calculation, enhanced PDF generation (v2.0), Wolf API KB write capabilities, and professional advisory. Knowledge Base v7.0 with 70+ accessories catalog and parametric rules for 6 construction systems.
- **Instructions**: See [Instrucciones GPT.rtf](Instrucciones%20GPT.rtf) for complete system instructions
- **Version**: 3.4 (KB v7.0, PDF Template v2.0, MCP v0.3.0)
- **Last Updated**: 2026-02-16

### Conversation Starters

```
💡 "Necesito una cotización para Isopanel EPS 50mm"
📄 "Genera un PDF para cotización de ISODEC 100mm"
🔍 "¿Qué diferencia hay entre ISOROOF PIR y EPS?"
📊 "Evalúa mi conocimiento sobre sistemas de fijación"
⚡ "¿Cuánto ahorro energético tiene el panel de 150mm vs 100mm?"
🏗️ "Necesito asesoramiento para un techo de 8 metros de luz"
```

### Enabled Capabilities

| Capability | Status | Purpose |
|------------|--------|---------|
| Web Browsing | ✅ BETA | Supplementary information only (non-authoritative) |
| Canvas | ✅ Enabled | Client-ready documents and structured proposals |
| Image Generation | ✅ Enabled | Educational diagrams only |
| Code Interpreter | ✅ Enabled | **CRITICAL** - PDF generation, data analysis, calculations |

---

## 📁 Repository Structure

```
GPT-PANELIN-V3.3/
├── README.md                                    # This file - Complete project overview
├── LICENSE                                      # MIT License
├── .gitignore                                   # Git exclusions
├── requirements.txt                             # Python dependencies (reportlab, pillow)
│
├── CORE CONFIGURATION
│   ├── Instrucciones GPT.rtf                    # Main GPT system instructions (v3.1)
│   ├── Panelin_GPT_config.json                  # Complete GPT configuration (v2.3)
│   ├── Esquema json.rtf                         # OpenAPI 3.1 schema for Panelin Wolf API
│   └── llms.txt                                 # LLM-optimized documentation index
│
├── KNOWLEDGE BASE - LEVEL 1 (Master Sources)
│   ├── BMC_Base_Conocimiento_GPT-2.json         # PRIMARY - Panel prices, formulas, specs
│   ├── accessories_catalog.json                 # 70+ accessories with real prices
│   ├── bom_rules.json                           # Parametric BOM rules (6 systems)
│   ├── bromyros_pricing_gpt_optimized.json      # Fast product lookups
│   └── shopify_catalog_v1.json                  # Product descriptions & images
│
├── KNOWLEDGE BASE - LEVEL 2-3 (Validation & Dynamic)
│   ├── BMC_Base_Unificada_v4.json               # Cross-reference validation
│   ├── panelin_truth_bmcuruguay_web_only_v2.json # Web pricing snapshot
│   └── corrections_log.json                     # KB error corrections tracking system
│
├── DOCUMENTATION (Guides & Processes)
│   ├── PANELIN_KNOWLEDGE_BASE_GUIDE.md          # KB hierarchy & usage guide
│   ├── PANELIN_QUOTATION_PROCESS.md             # 5-phase quotation workflow
│   ├── PANELIN_TRAINING_GUIDE.md                # Sales evaluation & training
│   ├── GPT_INSTRUCTIONS_PRICING.md              # Fast pricing lookups guide
│   ├── GPT_PDF_INSTRUCTIONS.md                  # PDF generation workflow v2.0
│   ├── GPT_OPTIMIZATION_ANALYSIS.md             # System analysis & improvements
│   ├── QUICK_START_GPT_UPLOAD.md                # Quick 3-step upload guide
│   ├── GPT_UPLOAD_CHECKLIST.md                  # Complete upload checklist
│   ├── GPT_UPLOAD_IMPLEMENTATION_SUMMARY.md     # Upload tools technical details
│   ├── USER_GUIDE.md                            # End-user upload guide
│   ├── IMPLEMENTATION_SUMMARY_V3.3.md           # V3.3 implementation details
│   ├── EVOLUCIONADOR_FINAL_REPORT.md            # EVOLUCIONADOR completion report
│   ├── KB_ARCHITECTURE_AUDIT.md                 # KB files MCP migration analysis
│   ├── KB_MCP_MIGRATION_PROMPT.md               # KB restructuring prompt
│   ├── MCP_SERVER_COMPARATIVE_ANALYSIS.md       # Top 10 MCP servers comparison
│   ├── MCP_AGENT_ARCHITECT_PROMPT.md            # MCP architecture AI agent prompt
│   ├── MCP_RESEARCH_PROMPT.md                   # MCP market research prompt
│   ├── MCP_CROSSCHECK_EVOLUTION_PLAN.md         # MCP gap analysis & execution plan
│   └── panelin_context_consolidacion_sin_backend.md # SOP commands reference
│
├── PDF GENERATION MODULE (v3.3)
│   ├── panelin_reports/
│   │   ├── __init__.py                          # Package initialization (v2.0)
│   │   ├── pdf_generator.py                     # Enhanced PDF generator v2.0
│   │   ├── pdf_styles.py                        # BMC branding and styles
│   │   ├── test_pdf_generation.py               # Comprehensive test suite
│   │   └── assets/
│   │       └── bmc_logo.png                     # BMC logo for PDF headers
│
├── DEPLOYMENT TOOLS
│   ├── validate_gpt_files.py                    # Dynamically discovers and validates required config files
│   ├── package_gpt_files.py                     # Organizes files for phased upload
│   └── test_panelin_api_connection.sh           # API smoke test script
│
├── MCP SERVER (Model Context Protocol)
│   └── mcp/                                     # MCP server implementation
│       ├── server.py                            # Main MCP server (stdio & SSE transports)
│       ├── requirements.txt                     # MCP dependencies (mcp>=1.0.0, uvicorn, starlette)
│       ├── config/                              # Configuration files
│       ├── handlers/                            # Tool handler implementations (18 tools)
│       │   ├── pricing.py                       # price_check tool handler
│       │   ├── catalog.py                       # catalog_search tool handler
│       │   ├── bom.py                           # bom_calculate tool handler
│       │   ├── errors.py                        # report_error tool handler
│       │   ├── tasks.py                         # Background task tool handlers (7 tools)
│       │   ├── wolf_kb_write.py                 # Wolf API KB write handlers (4 tools)
│       │   ├── governance.py                    # Self-healing governance handlers (2 tools)
│       │   └── quotation.py                     # Quotation persistence handler (1 tool)
│       ├── storage/                             # Backend-agnostic storage layer
│       │   └── memory_store.py                  # Memory-based quotation storage
│       ├── tasks/                               # Background task processing engine
│       │   ├── models.py                        # Task lifecycle models and data classes
│       │   ├── manager.py                       # Async task manager with concurrency control
│       │   ├── workers.py                       # Worker functions for batch/bulk operations
│       │   └── tests/                           # 55 comprehensive tests
│       │       ├── test_models.py
│       │       ├── test_manager.py
│       │       ├── test_workers.py
│       │       └── test_handlers.py
│       └── tools/                               # JSON tool schemas (18 tools)
│           ├── price_check.json                 # Pricing lookup schema
│           ├── catalog_search.json              # Catalog search schema
│           ├── bom_calculate.json               # BOM calculator schema
│           ├── report_error.json                # Error reporting schema
│           ├── batch_bom_calculate.json         # Batch BOM background task schema
│           ├── bulk_price_check.json            # Bulk pricing background task schema
│           ├── full_quotation.json              # Full quotation background task schema
│           ├── task_status.json                 # Task status query schema
│           ├── task_result.json                 # Task result retrieval schema
│           ├── task_list.json                   # Task listing schema
│           ├── task_cancel.json                 # Task cancellation schema
│           ├── persist_conversation.json        # Wolf API conversation persistence
│           ├── register_correction.json         # Wolf API correction registration
│           ├── save_customer.json               # Wolf API customer data storage
│           ├── lookup_customer.json             # Wolf API customer lookup
│           ├── validate_correction.json         # Governance validation schema
│           ├── commit_correction.json           # Governance commit schema
│           └── quotation_store.json             # Quotation persistence schema
│
├── WOLF API (Knowledge Base Backend) — NEW in v3.4
│   └── wolf_api/                                # FastAPI backend for KB operations
│       ├── main.py                              # FastAPI app with /kb/conversations endpoint
│       ├── requirements.txt                     # FastAPI, uvicorn, google-cloud-storage
│       ├── requirements-test.txt                # pytest, httpx for testing
│       ├── Dockerfile                           # Production-ready Docker image (Python 3.11)
│       ├── .dockerignore                        # Docker build exclusions
│       ├── README.md                            # Quick start and API documentation
│       ├── DEPLOYMENT.md                        # Complete deployment guide (Cloud Run)
│       ├── IAM_SETUP.md                         # IAM permissions and service account setup
│       └── tests/                               # Unit tests (10 tests, all passing)
│           ├── __init__.py
│           └── test_kb_conversations.py         # /kb/conversations endpoint tests
│
├── CALCULATION ENGINE
│   ├── quotation_calculator_v3.py               # Python calculation engine v3.1
│   └── quotation_calculator_v3.cpython-314.pyc  # Compiled bytecode
│
├── KB SELF-LEARNING MODULE (v3.4)
│   └── kb_self_learning/                        # Knowledge base self-learning system
│       ├── kb_writer_service.py                 # FastAPI service for KB entry creation
│       ├── approval_workflow.py                 # Human approval workflow engine
│       ├── config_v3.4.yaml                     # Module configuration
│       ├── DEPLOYMENT_V3.4.md                   # Deployment guide
│       ├── ARCHITECTURAL_LIMITATIONS.md         # Known limitations and roadmap
│       └── tests/                               # Test suite (336 lines)
│           ├── test_kb_writer_service.py
│           └── test_approval_workflow.py
│
├── BACKEND SERVICE
│   └── backend/                                 # Flask backend for chat storage (Cloud Run)
│       ├── main.py                              # Flask app with /chat endpoint
│       ├── kb_manager.py                        # Knowledge base management utilities
│       ├── init_db.sql                          # Database migration script (PostgreSQL)
│       ├── Dockerfile                           # Production Docker image (Python 3.11)
│       ├── .dockerignore                        # Docker build exclusions
│       ├── requirements.txt                     # Flask, psycopg2, google-cloud-secretmanager
│       ├── models/                              # SQLAlchemy data models
│       └── tests/                              # Backend tests with mocked dependencies
│
├── FRONTEND SERVICE
│   └── frontend/                               # Web chat interface (Flask)
│       ├── main.py                             # Flask app serving chat UI
│       ├── Dockerfile                          # Production Docker image (Python 3.11)
│       ├── .dockerignore                       # Docker build exclusions
│       ├── requirements.txt                    # Flask dependencies
│       └── templates/                          # HTML/JS templates
│           └── chat.html                       # Chat interface (XSS-safe rendering)
│
├── KB PIPELINE
│   └── kb_pipeline/                            # Knowledge base index builder
│       ├── build_indexes.py                    # Builds hot artifacts from source catalogs
│       └── README.md                           # Pipeline documentation
│
├── OBSERVABILITY
│   └── observability/                          # Metrics, cost tracking, and alerts
│       ├── daily_cost_report.py                # GCP daily cost report generator
│       ├── metrics_schema.json                 # Prometheus/GCP metrics schema
│       └── threshold_alerts.md                 # Alert threshold configuration guide
│
├── OPENAI ECOSYSTEM HELPERS
│   └── openai_ecosystem/                        # OpenAI API integration utilities
│       ├── __init__.py
│       ├── client.py                            # Response extraction and normalization
│       ├── test_client.py                       # Comprehensive test suite (33 tests)
│       └── README.md                            # Module documentation
│
├── DATA FILES
│   ├── normalized_full_cleaned.csv              # Raw product data (515 rows)
│   ├── perfileria_index.json                    # Profile product index
│   ├── bromyros_pricing_master.json             # Complete supplier pricing data
│   └── shopify_catalog_index_v1.csv             # Product catalog index
│
├── ASSETS
│   └── bmc_logo.png                             # BMC Uruguay logo (root copy)
│
├── .evolucionador/                              # 🧬 AUTONOMOUS EVOLUTION AGENT
│   ├── agent.yaml                               # Agent configuration
│   ├── requirements.txt                         # Python dependencies (none - stdlib only)
│   ├── README.md                                # EVOLUCIONADOR documentation
│   ├── COMPLETION_REPORT.md                     # Implementation completion report
│   ├── IMPLEMENTATION_SUMMARY.md                # Technical implementation details
│   ├── README_VALIDATOR.md                      # Validator system documentation
│   ├── VALIDATOR_GUIDE.md                       # Validator usage guide
│   ├── VALIDATOR_IMPLEMENTATION.md              # Validator implementation details
│   ├── examples_validator.py                    # Validator usage examples
│   │
│   ├── core/                                    # Core analysis engines
│   │   ├── __init__.py
│   │   ├── analyzer.py                          # Main analysis engine (850+ lines)
│   │   ├── validator.py                         # 7 specialized validators (1,246 lines)
│   │   ├── optimizer.py                         # 6 optimization algorithms
│   │   └── utils.py                             # Utility functions
│   │
│   ├── reports/                                 # Report generation system
│   │   ├── __init__.py
│   │   ├── template.md                          # Report template
│   │   ├── generator.py                         # Report generator (50+ variables)
│   │   ├── GENERATOR_README.md                  # Generator documentation
│   │   ├── latest.md                            # Most recent report
│   │   ├── latest.json                          # Latest results in JSON format
│   │   └── analysis_results.json                # Complete analysis data
│   │
│   ├── knowledge/                               # Self-learning knowledge base
│   │   ├── patterns.json                        # Learned patterns database
│   │   ├── benchmarks.json                      # Performance benchmarks
│   │   └── improvements.json                    # Tracked improvements
│   │
│   └── tests/                                   # Test suites
│       ├── test_analyzer.py
│       ├── test_validator.py
│       └── test_optimizer.py
│
├── mcp/                                         # 🔌 MCP SERVER IMPLEMENTATION
│   ├── server.py                                # Main MCP server with stdio/SSE transport
│   ├── requirements.txt                         # MCP SDK dependencies
│   │
│   ├── config/
│   │   └── mcp_server_config.json               # Server configuration & KB paths
│   │
│   ├── handlers/                                # Tool implementation handlers
│   │   ├── __init__.py
│   │   ├── pricing.py                           # price_check handler
│   │   ├── catalog.py                           # catalog_search handler
│   │   ├── bom.py                               # bom_calculate handler
│   │   └── errors.py                            # report_error handler
│   │
│   └── tools/                                   # MCP tool schemas (JSON)
│       ├── price_check.json                     # Pricing lookup tool schema
│       ├── catalog_search.json                  # Catalog search tool schema
│       ├── bom_calculate.json                   # BOM calculation tool schema
│       └── report_error.json                    # Error reporting tool schema
│
├── panelin_mcp_integration/                     # 🔗 MCP INTEGRATION CLIENTS
│   ├── panelin_mcp_server.py                    # Wolf API MCP wrapper for OpenAI
│   └── panelin_openai_integration.py            # OpenAI Responses API + MCP tools
│
├── .github/
│   └── workflows/
│       └── evolucionador-daily.yml              # Daily automated evolution workflow
│
├── docs/                                        # 📚 DOCUMENTATION HUB
│   └── README.md                                # Complete documentation index
│
├── archive/                                     # 📦 ARCHIVED REVIEW ARTIFACTS
│   ├── BOOT_PRS_COMPARISON.md                   # PR comparison analysis
│   ├── BRANCH_REVIEW_REPORT.md                  # Branch review report
│   ├── PULL_REQUESTS_REVIEW.md                  # 9-PR overview
│   ├── PR_REVIEW_README.md                      # Review navigation
│   ├── PR_CONSOLIDATION_ACTION_PLAN.md          # Consolidation plan
│   └── README_REVIEW_SUMMARY.md                 # README audit results
│
```

---

## 🧬 EVOLUCIONADOR - Autonomous Evolution Agent

**Version:** 1.0.0 | **Status:** ✅ Production Ready | **Mission:** Continuous evolution towards 100% perfection

### What is EVOLUCIONADOR?

EVOLUCIONADOR is an autonomous AI agent system that continuously analyzes, validates, optimizes, and evolves this repository. It runs daily via GitHub Actions, generating comprehensive evolution reports and actionable recommendations to improve functionality, efficiency, speed, and cost-effectiveness.

### Key Capabilities

| Category | Capability | Description |
|----------|-----------|-------------|
| **🔍 Analysis** | Deep Repository Scanning | Scans all files, validates README compliance, analyzes KB consistency |
| **✅ Validation** | 7 Specialized Validators | JSON schemas, formulas, pricing, load-bearing, API, documentation, cross-references |
| **⚡ Optimization** | 6 Optimization Algorithms | File sizes, formula efficiency, API calls, calculations, memory, costs |
| **📊 Reporting** | Comprehensive Reports | Daily reports with scores, issues, recommendations, and code patches |
| **🧠 Self-Learning** | Pattern Recognition | Tracks patterns, benchmarks performance, learns improvements |

### Core Components

#### 1. Analyzer Engine (`.evolucionador/core/analyzer.py`)
**850+ lines** - Main analysis engine that:
- Scans entire workspace (22+ files detected)
- Validates README compliance (100/100 score)
- Analyzes knowledge base (8 JSON files)
- Checks file compatibility
- Generates performance data
- Calculates multi-dimensional efficiency scores

#### 2. Validator Engine (`.evolucionador/core/validator.py`)
**1,246 lines** - Seven specialized validators:
1. **JSONValidator** - Schema validation for all KB files
2. **FormulaValidator** - Quotation calculation correctness
3. **PricingValidator** - Cross-file price consistency (±5% tolerance)
4. **LoadBearingValidator** - Autoportancia table accuracy
5. **APIValidator** - Endpoint compatibility checks
6. **DocumentationValidator** - Completeness verification
7. **CrossReferenceValidator** - Data integrity validation

#### 3. Optimizer Engine (`core/optimizer.py`)
Six optimization algorithms for:
- File size reduction
- Formula efficiency improvements
- API call optimization
- Calculation performance
- Memory usage optimization
- Cost reduction strategies

#### 4. Report Generator (`.evolucionador/reports/generator.py`)
Generates comprehensive markdown reports with:
- Executive summaries with efficiency scores
- Detailed validation results
- Actionable recommendations with priority levels
- Ready-to-apply code patches
- Historical trend analysis
- 50+ template variables for complete reporting

### Workflow Automation

**Daily Execution** (via `.github/workflows/evolucionador-daily.yml`):
1. **00:00 UTC** - Automatic daily run
2. Runs complete analysis pipeline
3. Generates evolution report
4. Creates GitHub issue with findings
5. Commits report history to repository

**Manual Trigger**: Can be run on-demand via GitHub Actions workflow dispatch

### Self-Learning Knowledge Base

EVOLUCIONADOR maintains three knowledge files:
- **`.evolucionador/knowledge/patterns.json`** - Discovered patterns and best practices
- **`.evolucionador/knowledge/benchmarks.json`** - Performance benchmarks across versions
- **`.evolucionador/knowledge/improvements.json`** - Tracked improvements and their impact

### Output & Reports

**Latest Report**: `.evolucionador/reports/latest.md`  
**Historical Reports**: `.evolucionador/reports/history/` (daily Markdown files named by date)  
**Analysis Data**: `.evolucionador/reports/analysis_results.json`

Each report includes:
- ✅ Overall efficiency score (target: 100%)
- 🎯 Priority-based recommendations
- 📊 Validation results by category
- 🔧 Ready-to-apply code patches
- 📈 Historical trend comparison
- ⚠️ Critical issues requiring attention

### Testing Infrastructure

Comprehensive test suites ensure reliability:
- `.evolucionador/tests/test_analyzer.py` - Analysis engine tests
- `.evolucionador/tests/test_validator.py` - All 7 validators
- `.evolucionador/tests/test_optimizer.py` - Optimization algorithms
- `.evolucionador/examples_validator.py` - Usage examples

### Usage

```bash
# Install dependencies (none required - uses Python stdlib only)

# Run complete analysis
python .evolucionador/core/analyzer.py

# Generate evolution report
python .evolucionador/reports/generator.py

# View latest report
cat .evolucionador/reports/latest.md
```

### Documentation

- **[.evolucionador/README.md](.evolucionador/README.md)** - Complete EVOLUCIONADOR guide
- **[EVOLUCIONADOR_FINAL_REPORT.md](EVOLUCIONADOR_FINAL_REPORT.md)** - Implementation completion report
- **[.evolucionador/VALIDATOR_GUIDE.md](.evolucionador/VALIDATOR_GUIDE.md)** - Validator usage guide
- **[.evolucionador/reports/GENERATOR_README.md](.evolucionador/reports/GENERATOR_README.md)** - Report generator documentation

---

## 🔌 MCP Server - Model Context Protocol Integration

**Version:** 0.3.0 | **Status:** ✅ Production Ready | **Mission:** Persistent tools for quotation workflows with self-healing governance

### What is the MCP Server?

The MCP (Model Context Protocol) Server is a new architectural component that exposes GPT-PANELIN's core capabilities as persistent, callable tools through the Model Context Protocol. This enables:

- **Persistent tool access** without uploading large KB files to GPT context
- **Real-time data access** via API-backed tools
- **Session memory** through error correction logging
- **Planned: GitHub integration** for KB version control and automated updates (roadmap)

### MCP Server Architecture

The implementation consists of three main components:

#### 1. Core MCP Server (`mcp/`)

A production-ready MCP server built on the MCP SDK that provides **18 specialized tools** across five categories:

**Core Tools (4):**
| Tool | Purpose | Handler |
|------|---------|---------|
| `price_check` | Product pricing lookup from master KB | `handlers/pricing.py` |
| `catalog_search` | Product catalog search with filters | `handlers/catalog.py` |
| `bom_calculate` | Complete BOM calculation using parametric rules | `handlers/bom.py` |
| `report_error` | Log KB errors to corrections_log.json | `handlers/errors.py` |

**Background Task Tools (7):**
| Tool | Purpose | Handler |
|------|---------|---------|
| `batch_bom_calculate` | Process multiple BOMs asynchronously | `handlers/tasks.py` |
| `bulk_price_check` | Bulk pricing lookups | `handlers/tasks.py` |
| `full_quotation` | Complete quotation with BOM + pricing | `handlers/tasks.py` |
| `task_status` | Check task progress | `handlers/tasks.py` |
| `task_result` | Retrieve completed task results | `handlers/tasks.py` |
| `task_list` | List recent tasks | `handlers/tasks.py` |
| `task_cancel` | Cancel pending/running tasks | `handlers/tasks.py` |

**Wolf API KB Write Tools (4):**
| Tool | Purpose | Handler |
|------|---------|---------|
| `persist_conversation` | Save conversation history to KB | `handlers/wolf_kb_write.py` |
| `register_correction` | Register KB corrections (prices, weights, specs) | `handlers/wolf_kb_write.py` |
| `save_customer` | Store customer data | `handlers/wolf_kb_write.py` |
| `lookup_customer` | Retrieve customer data | `handlers/wolf_kb_write.py` |

> 📝 **New Feature:** The GPT can modify product weights (kg) in the catalog through `register_correction` tool. See [GPT_WEIGHT_MODIFICATION_GUIDE.md](GPT_WEIGHT_MODIFICATION_GUIDE.md) for complete documentation.

**Self-Healing Governance Tools (2):**
| Tool | Purpose | Handler |
|------|---------|---------|
| `validate_correction` | Validate KB corrections with impact analysis | `handlers/governance.py` |
| `commit_correction` | Apply validated corrections | `handlers/governance.py` |

**Quotation Persistence (1):**
| Tool | Purpose | Handler |
|------|---------|---------|
| `quotation_store` | Store quotations with vector search | `handlers/quotation.py` |

**Key Features:**
- Dual transport support: `stdio` (local/OpenAI Custom GPT Actions) and `sse` (remote hosting)
- 18 production-ready tools across 5 categories
- JSON tool schemas in `tools/` directory
- Direct KB file access (no duplication in GPT context)
- Self-healing governance with two-step approval workflow
- Backend-agnostic quotation storage
- Thread-safe handlers with `threading.Lock` patterns
- Comprehensive error codes via `mcp_tools.contracts`

**Usage:**
```bash
# Install dependencies
cd mcp
pip install -r requirements.txt

# Run with stdio transport (for local testing / OpenAI)
python server.py

# Run with SSE transport (for remote hosting)
python server.py --transport sse --port 8000
```

#### 2. MCP Integration Clients (`panelin_mcp_integration/`)

Two integration patterns for connecting the MCP server to OpenAI:

**A. Wolf API MCP Wrapper (`panelin_mcp_server.py`)**
- Wraps the existing Panelin Wolf API as MCP-compatible tools
- Handles authentication, validation, and error handling
- Returns MCP-compliant tool registry for OpenAI integration
- Supports: `find_products`, `get_product_price`, `check_availability`

**B. OpenAI Responses API Integration (`panelin_openai_integration.py`)**
- Full implementation using OpenAI Responses API with MCP tools
- Auto-approved tool calls (no user confirmation needed)
- Direct API integration without Custom GPT Actions configuration
- Pattern for future GPT-5 MCP integration

**Usage Example:**
```python
from panelin_mcp_integration.panelin_mcp_server import PanelinMCPServer

# Initialize MCP server wrapper
server = PanelinMCPServer(api_key="YOUR_WOLF_API_KEY")

# Get tool registry for OpenAI
tools = server.tools_registry()

# Tools can now be registered with OpenAI Custom GPT Actions
```

#### 3. Configuration & Documentation

**Configuration:**
- `mcp/config/mcp_server_config.json` - Server config with KB paths, OpenAI integration settings, and GitHub MCP capabilities
- Tool schemas in `mcp/tools/*.json` - MCP-compliant tool definitions

**Research & Analysis:**
- [MCP_SERVER_COMPARATIVE_ANALYSIS.md](MCP_SERVER_COMPARATIVE_ANALYSIS.md) - Top 10 MCP server comparison with cost analysis
- [MCP_AGENT_ARCHITECT_PROMPT.md](MCP_AGENT_ARCHITECT_PROMPT.md) - AI agent prompt for MCP architecture design
- [KB_ARCHITECTURE_AUDIT.md](KB_ARCHITECTURE_AUDIT.md) - KB restructuring analysis for MCP migration
- [MCP_CROSSCHECK_EVOLUTION_PLAN.md](MCP_CROSSCHECK_EVOLUTION_PLAN.md) - MCP gap analysis & execution plan

### MCP vs. Traditional Architecture

| Aspect | Traditional (v3.3) | MCP-Enhanced (v3.4) |
|--------|-------------------|---------------------|
| **KB Upload** | All files uploaded to GPT | Tools access KB directly |
| **Context Usage** | ~122K tokens/session | ~40K tokens/session |
| **Data Updates** | Manual re-upload required | Automatic via GitHub MCP |
| **Error Corrections** | Lost between sessions | Persisted + governed workflow |
| **API Access** | Via Custom GPT Actions | Native MCP tools |
| **Session Memory** | Limited to conversation | Persistent quotation store |
| **Governance** | Manual review process | Automated impact analysis |
| **Cost** | $22.50–$40.50/mo | $15–$57/mo (with GitHub MCP) |

### Current Status & Roadmap

**✅ Completed:**
- MCP server v0.3.0 with 18 production-ready tools
- Core tools (pricing, catalog, BOM, errors)
- Background task processing with async manager
- Wolf API KB write capabilities (4 tools)
- Self-healing governance system (2 tools)
- Quotation persistence with vector search
- Tool schemas and contracts
- MCP integration client implementations
- Comprehensive test coverage (100+ tests)
- Thread-safe handlers with proper locking

**🚧 In Progress:**
- Production deployment on Cloud Run
- Full GitHub MCP sync workflow
- Qdrant integration for enhanced vector search

**📋 Planned:**
- Automated KB updates via MCP
- Real-time quotation analytics dashboard
- Machine learning-based price prediction

### Integration Guide

For detailed integration instructions, see:
- [MCP Server Comparative Analysis](MCP_SERVER_COMPARATIVE_ANALYSIS.md) - Cost analysis and provider comparison
- [MCP Agent Architect Prompt](MCP_AGENT_ARCHITECT_PROMPT.md) - Architecture design guide
- [KB Architecture Audit](KB_ARCHITECTURE_AUDIT.md) - Migration strategy

---

## 📚 Knowledge Base

The knowledge base follows a strict **hierarchical priority system** to ensure accuracy and consistency.

### Hierarchy Overview

| Level | Priority | Purpose | Files |
|-------|----------|---------|-------|
| **Level 1 - Master** | 🔴 Highest | Authoritative pricing, formulas, specs | `BMC_Base_Conocimiento_GPT-2.json` |
| **Level 1.2 - Accessories** | 🔴 High | Accessories pricing catalog | `accessories_catalog.json` |
| **Level 1.3 - BOM Rules** | 🔴 High | Parametric material calculations | `bom_rules.json` |
| **Level 1.5 - Pricing Optimized** | 🟡 Medium | Fast product lookups | `bromyros_pricing_gpt_optimized.json` |
| **Level 1.6 - Catalog** | 🟡 Medium | Descriptions, images (NOT prices) | `shopify_catalog_v1.json` |
| **Level 2 - Validation** | 🟢 Low | Cross-reference only | `BMC_Base_Unificada_v4.json` |
| **Level 3 - Dynamic** | 🟢 Low | Web snapshot (validate vs Level 1) | `panelin_truth_bmcuruguay_web_only_v2.json` |

### Level 1 - Master Knowledge Base

#### `BMC_Base_Conocimiento_GPT-2.json` (PRIMARY)

**Content:**
- Complete panel products (ISODEC, ISOPANEL, ISOROOF, ISOWALL, ISOFRIG, HM_RUBBER)
- Validated Shopify pricing (price_per_m2)
- Exact quotation formulas (including v6.0: tortugas_pvc, arandelas_carrocero, fijaciones_perfileria)
- Technical specifications (load-bearing capacity, thermal coefficients, thermal resistance)
- Business rules (IVA 22%, minimum roof slope 7%, shipping costs)
- Energy savings calculation formulas

**When to use:**
- ✅ ALWAYS for panel pricing
- ✅ ALWAYS for calculation formulas
- ✅ ALWAYS for technical specifications
- ✅ ALWAYS for load-bearing validation

**Golden Rule:** If there's a conflict with other files, Level 1 wins.

#### `accessories_catalog.json` (NEW in v7.0)

**Content:**
- 70+ accessory items with real pricing (IVA included)
- Front and lateral gutters by thickness
- Babetas (attach, embed, lateral types)
- Ridge caps, channels, U profiles
- Fixings (rods, nuts, screws, washers, PVC turtles)
- Sealants (silicone, butyl tape)
- Indices by SKU, type, compatibility, and usage
- Multi-supplier support (BROMYROS, MONTFRIO, BECAM)

**Categories covered:**
- Goteros Frontales (Front gutters): 15+ items
- Goteros Laterales (Lateral gutters): 12+ items
- Babetas (Flashing): 10+ items
- Cumbreras (Ridge caps): 3+ items
- Canalones (Channels): 6+ items
- Perfiles U (U profiles): 8+ items
- Fijaciones (Fixings): 15+ items
- Selladores (Sealants): 6+ items

#### `bom_rules.json` (NEW in v7.0)

**Content:**
- Parametric formulas by construction system
- Unified load-bearing capacity table
- SKU-to-thickness mapping
- Detailed fixing kits (metal, concrete, wood)
- Complete calculation example (step-by-step)

**Six construction systems:**
1. `techo_isoroof_3g` - Lightweight roof (ISOROOF 3G / FOIL / PLUS)
2. `techo_isodec_eps` - Heavy roof EPS (ISODEC EPS 100-250mm)
3. `techo_isodec_pir` - Heavy roof PIR (ISODEC PIR 50-120mm)
4. `pared_isopanel_eps` - Wall/facade (ISOPANEL EPS 50-250mm)
5. `pared_isowall_pir` - Fire-resistant wall (ISOWALL PIR 50-80mm)
6. `pared_isofrig_pir` - Cold storage (ISOFRIG PIR 40-150mm)

### Level 1.5-1.6 - Optimized Lookups

#### `bromyros_pricing_gpt_optimized.json`

Fast product lookups with multi-level indexing:
- Index by SKU: Direct product access
- Index by familia: Browse related products
- Index by subfamilia: Filter by material (EPS/PIR)
- Familia groups: Complete family context

See [GPT_INSTRUCTIONS_PRICING.md](GPT_INSTRUCTIONS_PRICING.md) for detailed usage.

#### `shopify_catalog_v1.json`

Product catalog for presentation:
- Product descriptions
- Variant information
- Product images
- **⚠️ DO NOT use for pricing** (use Level 1 instead)

### Knowledge Base Usage Rules

**Rule #1: Source of Truth**
- Level 1 always wins in conflicts
- Never invent data not in KB
- If not in KB, respond: "No tengo esa información"

**Rule #2: Query Priority**
1. Query Level 1 first (panels) or Level 1.2 (accessories)
2. If not found, check Level 2 (but report discrepancy)
3. If not found, check Level 3 (but validate against Level 1)
4. If not found, check Level 4 for context
5. If nowhere, respond: "No tengo esa información"

**Rule #3: Cross-Validation**
- Use Level 2 to detect inconsistencies
- Report differences but use Level 1
- Never use Level 2 for direct responses

**Rule #4: Updates**
- Level 3 may have more recent pricing
- Always validate against Level 1 before using
- If different, use Level 1 and report discrepancy

For complete KB guidance, see [PANELIN_KNOWLEDGE_BASE_GUIDE.md](PANELIN_KNOWLEDGE_BASE_GUIDE.md).

### KB Error Correction System

**File:** `corrections_log.json`

A persistent error tracking system for identifying and correcting KB inconsistencies:

**Purpose:**
- Log pricing errors discovered during quotation sessions
- Track corrections with source attribution
- Persist fixes across GPT sessions
- Enable automated KB updates via MCP

**Schema:**
```json
{
  "id": "COR-NNN",
  "date": "2026-02-11",
  "kb_file": "accessories_catalog.json",
  "field": "items[32].price_usd",
  "wrong_value": 15.50,
  "correct_value": 18.75,
  "source": "User correction in quotation session",
  "status": "pending | applied | rejected",
  "applied_date": null
}
```

**Integration:**
- MCP `report_error` tool writes to this file
- EVOLUCIONADOR validates corrections during analysis
- Future: Automated PR creation for approved corrections

---

## 🔌 API Integration

### Panelin Wolf API

**Base URL:** `https://panelin-api-642127786762.us-central1.run.app`  
**Version:** 2.0.0  
**Platform:** Google Cloud Run (Production)

### Authentication

All authenticated endpoints require an `X-API-Key` header:

```bash
curl -H "X-API-Key: YOUR_WOLF_API_KEY" \
  https://panelin-api-642127786762.us-central1.run.app/
```

### Available Endpoints

#### Health & Status

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | ❌ No | Liveness check |
| `/ready` | GET | ❌ No | Readiness check |
| `/` | GET | ✅ Yes | API status & version |

#### Quotation Services

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/calculate_quote` | POST | ✅ Yes | Calculate complete panel quotation |
| `/find_products` | POST | ✅ Yes | Natural language product search |
| `/product_price` | POST | ✅ Yes | Get price for product by ID |
| `/check_availability` | POST | ✅ Yes | Check product availability & stock |

#### Knowledge Base Services (v3.4)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/kb/conversations` | POST | ✅ Yes | Persist conversation summaries to GCS |

**New in v3.4:** The Wolf API now includes Knowledge Base write operations that allow the GPT to persist conversation data, corrections, and customer information directly through chat interactions. Data is stored in Google Cloud Storage as JSONL for downstream analysis and training.

**Implementation:** See [`wolf_api/`](./wolf_api/) for the FastAPI backend implementation with GCS persistence, including deployment guides and IAM setup instructions.

### Request Examples

#### Calculate Quote

```json
POST /calculate_quote
{
  "product_id": "ISOPANEL_EPS_50mm",
  "length_m": 5.5,
  "width_m": 12.0,
  "quantity": 1,
  "discount_percent": 0,
  "include_accessories": true,
  "include_tax": true,
  "installation_type": "techo"
}
```

**Response:**
```json
{
  "quotation_id": "QT-2026-02-10-001",
  "product_id": "ISOPANEL_EPS_50mm",
  "total_usd": 2456.80,
  "currency": "USD"
}
```

#### Find Products (Natural Language)

```json
POST /find_products
{
  "query": "panel aislante para techo industrial 100mm",
  "max_results": 5
}
```

**Response:**
```json
{
  "results": [
    {
      "product_id": "ISODEC_EPS_100",
      "name": "Isodec EPS 100mm",
      "family": "ISODEC",
      "price_per_m2": 46.07
    },
    ...
  ]
}
```

### API Schema

The complete OpenAPI 3.1.0 schema is integrated into the GPT configuration. Key schemas:

- **QuoteRequest**: Complete quotation request with dimensions, quantity, discounts
- **ProductSearchRequest**: Natural language product search
- **ProductPriceRequest**: Direct price lookup by product ID
- **FindProductsResponse**: Search results with pricing

### Response Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | Success | Request processed successfully |
| 400 | Bad Request | Invalid parameters or missing required fields |
| 403 | Forbidden | Invalid or missing API key |
| 404 | Not Found | Product not found |
| 503 | Service Unavailable | API temporarily unavailable |

### LLM-Optimized Documentation

The repository includes `llms.txt` — an LLM-optimized documentation index that provides quick navigation for AI assistants. This file follows the emerging convention for LLM-readable documentation, enabling better context discovery for AI coding assistants and documentation tools.

---

## 🔧 MCP Server

### Model Context Protocol Integration

**Panelin MCP Server** provides a standards-compliant [Model Context Protocol](https://modelcontextprotocol.io) interface for integrating Panelin's quotation tools with any MCP-compatible AI assistant, including OpenAI's GPTs, Claude Desktop, and other MCP clients.

**Status:** ✅ Production Ready | **Version:** 0.3.0 | **Transport:** stdio, SSE

### What is MCP?

The Model Context Protocol (MCP) is an open standard for connecting AI assistants to external tools and data sources. Panelin's MCP server exposes specialized tools for construction panel quotations, including background task processing for long-running operations:

#### Core Tools (Synchronous)

| Tool | Description | Use Case |
|------|-------------|----------|
| 🏷️ **price_check** | Product pricing lookup by SKU or search | Real-time price queries for BMC/BROMYROS products |
| 🔍 **catalog_search** | Product catalog search with filtering | Find products by description, category, or keywords |
| 📋 **bom_calculate** | Bill of Materials calculator | Complete BOM generation for panel installations |
| 🐛 **report_error** | Knowledge Base error logger | Report and track KB inconsistencies |

#### Background Task Tools (Async)

| Tool | Description | Use Case |
|------|-------------|----------|
| 📦 **batch_bom_calculate** | Batch BOM for multiple panels | Multi-zone projects needing BOMs for several panel types |
| 💰 **bulk_price_check** | Bulk pricing for multiple products | Compare prices across families, build multi-product quotes |
| 📄 **full_quotation** | Combined BOM + pricing + catalog | Complete quotation in one pass (BOM, pricing, accessories) |
| 📊 **task_status** | Check background task progress | Poll running tasks for completion percentage |
| 📥 **task_result** | Retrieve completed task output | Get the full result data when a task finishes |
| 📋 **task_list** | List recent background tasks | Monitor and review task history with optional filters |
| ❌ **task_cancel** | Cancel a pending/running task | Stop tasks that are no longer needed |

### Quick Start

#### Install Dependencies

```bash
# Install MCP server dependencies from the repository root
pip install -r mcp/requirements.txt
```

**Required packages:**
- `mcp>=1.0.0` - Model Context Protocol SDK
- `uvicorn>=0.30.0` - ASGI server (for SSE transport)
- `starlette>=0.40.0` - Web framework (for SSE transport)
- `httpx>=0.27.0` - HTTP client
- `pydantic>=2.0.0` - Data validation

#### Run with stdio Transport (Local MCP Clients)

For local MCP clients like Claude Desktop:

```bash
# Run from the repository root
python -m mcp.server

# The server will communicate via standard input/output
# Perfect for local MCP clients
```

#### Run with SSE Transport (Remote Hosting)

For remote deployments and HTTP-based integrations:

```bash
# Run from the repository root
python -m mcp.server --transport sse --port 8000

# Server will be available at:
# - SSE endpoint: http://localhost:8000/sse
# - POST messages: http://localhost:8000/messages
```

### MCP Tools Reference

#### 1. price_check

**Purpose:** Look up current product pricing by SKU, family, or natural language search.

**Input Schema:**
```json
{
  "query": "ISODEC-100-1000",           // Required: SKU, family, or search term
  "filter_type": "sku",                  // Optional: "sku", "family", "type", "search"
  "thickness_mm": 100                    // Optional: filter by thickness
}
```

**Example Usage:**
```json
// Search by SKU
{
  "query": "ISODEC-100-1000",
  "filter_type": "sku"
}

// Search by family
{
  "query": "ISODEC",
  "filter_type": "family"
}

// Free-text search
{
  "query": "panel aislante para techo",
  "filter_type": "search"
}
```

**Response:** Returns price in USD with IVA 22% included, sourced from `bromyros_pricing_master.json`.

#### 2. catalog_search

**Purpose:** Search the BMC product catalog for details, variants, and images.

**Input Schema:**
```json
{
  "query": "panel industrial",           // Required: search keywords
  "category": "techo",                   // Optional: "techo", "pared", "camara", "accesorio", "all"
  "limit": 5                             // Optional: max results (default: 5)
}
```

**Example Usage:**
```json
{
  "query": "isodec",
  "category": "techo",
  "limit": 10
}
```

**Response:** Returns lightweight product index results. Use product ID for full details.

#### 3. bom_calculate

**Purpose:** Calculate complete Bill of Materials for panel installations using parametric rules.

**Input Schema:**
```json
{
  "product_family": "ISODEC",            // Required: panel family
  "thickness_mm": 100,                   // Required: panel thickness
  "core_type": "EPS",                    // Required: "EPS" or "PIR"
  "usage": "techo",                      // Required: "techo", "pared", "camara"
  "length_m": 12.0,                      // Required: installation length
  "width_m": 6.0,                        // Required: installation width/span
  "quantity_panels": 10                  // Optional: if known
}
```

**Example Usage:**
```json
{
  "product_family": "ISODEC",
  "thickness_mm": 100,
  "core_type": "EPS",
  "usage": "techo",
  "length_m": 12.0,
  "width_m": 6.0
}
```

**Response:** Returns complete BOM with:
- Panel quantities
- Fixation requirements (screws, washers, turtles)
- Accessories (gutters, flashing, sealants)
- Load-bearing validation results
- Quantity calculations and subtotals

**Data Source:** Uses parametric rules from `bom_rules.json` with unified load-bearing capacity tables.

#### 4. report_error

**Purpose:** Log Knowledge Base errors for tracking and correction.

**Input Schema:**
```json
{
  "kb_file": "accessories_catalog.json", // Required: KB file name
  "field": "items[32].price_usd",        // Required: JSON path to field
  "wrong_value": "45.00",                // Required: incorrect value found
  "correct_value": "47.50",              // Required: correct value
  "source": "user_correction",           // Required: discovery source
  "notes": "Verified with supplier"      // Optional: additional context
}
```

**Source options:**
- `user_correction` - Reported by end user
- `validation_check` - Found by automated validation
- `audit` - Discovered during manual audit
- `web_verification` - Verified against external source

**Response:** Persists error to `corrections_log.json` for tracking and potential future automation (e.g., generating GitHub PRs via external tools; not implemented in this repository).

#### 5. batch_bom_calculate (Background Task)

**Purpose:** Submit multiple BOM calculations as a single background task. Ideal for multi-zone projects.

**Input Schema:**
```json
{
  "items": [
    {
      "product_family": "ISODEC",
      "thickness_mm": 100,
      "core_type": "EPS",
      "usage": "techo",
      "length_m": 12.0,
      "width_m": 6.0
    },
    {
      "product_family": "ISOPANEL",
      "thickness_mm": 50,
      "core_type": "EPS",
      "usage": "pared",
      "length_m": 8.0,
      "width_m": 4.0
    }
  ]
}
```

**Response:** Returns a `task_id` for polling with `task_status` and retrieval with `task_result`.

#### 6. bulk_price_check (Background Task)

**Purpose:** Look up pricing for multiple products at once.

**Input Schema:**
```json
{
  "queries": [
    {"query": "ISODEC", "filter_type": "family"},
    {"query": "ISOROOF", "filter_type": "family"},
    {"query": "panel techo 100mm", "filter_type": "search"}
  ]
}
```

**Response:** Returns a `task_id` for status polling and result retrieval.

#### 7. full_quotation (Background Task)

**Purpose:** Generate a complete quotation combining BOM + pricing + catalog in one pass.

**Input Schema:**
```json
{
  "product_family": "ISODEC",
  "thickness_mm": 100,
  "core_type": "EPS",
  "usage": "techo",
  "length_m": 12.0,
  "width_m": 6.0,
  "client_name": "Empresa Constructora ABC",
  "project_name": "Galpon Industrial",
  "discount_percent": 5
}
```

**Response:** Returns a `task_id`. The completed result includes BOM, pricing, catalog matches, and a quotation summary.

#### 8. task_status / task_result / task_list / task_cancel

**Purpose:** Manage background tasks.

```json
// Check status
{"task_id": "TASK-A1B2C3D4"}

// Retrieve result (only for completed tasks)
{"task_id": "TASK-A1B2C3D4"}

// List tasks (all filters optional)
{"status": "running", "task_type": "batch_bom_calculate", "limit": 10}

// Cancel a task
{"task_id": "TASK-A1B2C3D4"}
```

**Task States:** `pending` -> `running` -> `completed` | `failed` | `cancelled`

**Progress Tracking:** Running tasks include progress data (percentage, current item, items completed/total).

### Integration Paths

There are two distinct integration paths in this project:

#### 1. MCP-compatible Clients (Model Context Protocol)

**For local MCP clients (e.g., Claude Desktop, IDE extensions):**

- Run the MCP server using the stdio transport (default): `python -m mcp.server` from repo root
- Point your MCP client at the server executable
- The client will discover available tools from the MCP protocol

**For remote MCP clients:**

- Run with SSE transport: `python -m mcp.server --transport sse --port 8000` from repo root
- Configure your MCP client to connect to the SSE endpoint
- Tools will be available via the MCP protocol over HTTP

**MCP tool schemas are available at:**
- `mcp/tools/price_check.json`
- `mcp/tools/catalog_search.json`
- `mcp/tools/bom_calculate.json`
- `mcp/tools/report_error.json`
- `mcp/tools/batch_bom_calculate.json`
- `mcp/tools/bulk_price_check.json`
- `mcp/tools/full_quotation.json`
- `mcp/tools/task_status.json`
- `mcp/tools/task_result.json`
- `mcp/tools/task_list.json`
- `mcp/tools/task_cancel.json`

These JSON files describe MCP tools and are consumed by MCP-aware clients, not directly by OpenAI Custom GPT Actions.

#### 2. OpenAI Custom GPT Actions (HTTP / OpenAPI-based)

**Note:** OpenAI Custom GPT Actions use HTTP endpoints defined by OpenAPI schemas, which is a different integration approach than MCP.

To integrate with OpenAI Custom GPT Actions:

1. Deploy the SSE transport server: `python -m mcp.server --transport sse --port 8000` from repo root
2. Implement HTTP API wrappers that expose the MCP tools as REST endpoints
3. Generate an OpenAPI specification for those HTTP endpoints
4. In the OpenAI GPT Builder, create a new Action and import the OpenAPI specification
5. Configure any required authentication for your deployed HTTP endpoint

The MCP server's stdio transport cannot be used directly with OpenAI Custom GPT Actions, as Actions require HTTP endpoints accessible over the internet.

### Architecture

```
mcp/
├── server.py              # Main MCP server implementation
├── requirements.txt       # Python dependencies
├── config/                # Configuration files
├── handlers/              # Tool handler implementations
│   ├── pricing.py        # price_check handler
│   ├── catalog.py        # catalog_search handler
│   ├── bom.py            # bom_calculate handler
│   ├── errors.py         # report_error handler
│   └── tasks.py          # Background task tool handlers (7 tools)
├── tasks/                 # Background task processing engine
│   ├── models.py         # Task, TaskProgress, TaskStatus, TaskType
│   ├── manager.py        # Async task manager (submit, cancel, query)
│   ├── workers.py        # Worker functions (batch BOM, bulk pricing, quotation)
│   └── tests/            # 55 comprehensive tests
│       ├── test_models.py
│       ├── test_manager.py
│       ├── test_workers.py
│       └── test_handlers.py
├── handlers/              # Tool handler implementations (18 tools)
│   ├── pricing.py        # price_check handler
│   ├── catalog.py        # catalog_search handler
│   ├── bom.py            # bom_calculate handler
│   ├── errors.py         # report_error handler
│   ├── tasks.py          # Background task tool handlers (7 tools)
│   ├── wolf_kb_write.py  # Wolf API KB write handlers (4 tools)
│   ├── governance.py     # Self-healing governance handlers (2 tools)
│   └── quotation.py      # Quotation persistence handler (1 tool)
├── storage/               # Backend-agnostic storage layer
│   └── memory_store.py   # Memory-based quotation storage
└── tools/                 # JSON tool schemas (18 tools)
    ├── price_check.json
    ├── catalog_search.json
    ├── bom_calculate.json
    ├── report_error.json
    ├── batch_bom_calculate.json
    ├── bulk_price_check.json
    ├── full_quotation.json
    ├── task_status.json
    ├── task_result.json
    ├── task_list.json
    ├── task_cancel.json
    ├── persist_conversation.json
    ├── register_correction.json
    ├── save_customer.json
    ├── lookup_customer.json
    ├── validate_correction.json
    ├── commit_correction.json
    └── quotation_store.json
```

---

## 🔒 Self-Healing Governance Architecture

**Version:** 1.0 | **Status:** ✅ Production Ready | **Handler:** `mcp/handlers/governance.py` (524 lines)

### Overview

The self-healing governance system provides enterprise-grade change management for Knowledge Base corrections with automatic impact analysis and two-step approval workflow.

### Core Features

- **Two-step approval workflow**: validate → review → commit
- **Automatic impact analysis**: Simulates corrections on last 50 quotations
- **Thread-safe**: Uses `threading.Lock` for pending changes cache
- **Whitelist-based**: Only allowed KB files can be modified
- **Audit trail**: All corrections logged to `corrections_log.json`
- **Deterministic IDs**: SHA-256 based change IDs for uniqueness

### Governance Tools

#### 9. validate_correction

**Purpose:** Validate proposed KB corrections and simulate impact on recent quotations

**Input Schema:**
```json
{
  "kb_file": "bromyros_pricing_master.json",
  "field": "data.products[0].pricing.web_iva_inc",
  "proposed_value": "47.50",
  "reason": "Price updated per supplier notification"
}
```

**Response:** Returns comprehensive change report with:
- Current vs proposed values
- Impact analysis (affected quotations, price deltas)
- Risk assessment
- `change_id` for commit step

**Error Codes:** Via `VALIDATE_CORRECTION_ERROR_CODES`

#### 10. commit_correction

**Purpose:** Apply validated corrections after review and approval

**Input Schema:**
```json
{
  "change_id": "CHG-A1B2C3D4E5F6",
  "approved_by": "admin_user"
}
```

**Response:** Confirmation with applied changes and affected files

**Error Codes:** Via `COMMIT_CORRECTION_ERROR_CODES`

### Workflow

```
User proposes correction
   ↓
validate_correction
   ↓ [validates against pricing index]
   ↓ [simulates impact on quotations]
   ↓ [generates change report]
   ↓
Returns change_id + impact report
   ↓
User reviews impact
   ↓
commit_correction (if approved)
   ↓ [applies changes to KB]
   ↓ [logs to corrections_log.json]
   ↓
Confirmation returned
```

### Allowed KB Files

Only these files can be modified through governance:
- `bromyros_pricing_master.json`
- `bromyros_pricing_gpt_optimized.json`
- `accessories_catalog.json`
- `bom_rules.json`
- `shopify_catalog_v1.json`
- `BMC_Base_Conocimiento_GPT-2.json`
- `perfileria_index.json`

---

## 💾 Quotation Persistence System

**Version:** 1.0 | **Status:** ✅ Production Ready | **Handler:** `mcp/handlers/quotation.py` (155 lines)

### Overview

Backend-agnostic quotation storage with optional vector similarity search for building quotation history and pattern analysis.

### Core Features

- **Backend-agnostic design**: Currently Memory Store, extensible to Qdrant/PostgreSQL
- **Vector similarity search**: Optional retrieval of similar past quotations
- **Analytics tracking**: Structured logging with event data
- **Size limits**: 1MB JSON payload limit for safety
- **JSON validation**: Serialization checks before storage
- **Configuration**: Injectable via `configure_quotation_store()`

### Quotation Store Tool

#### 11. quotation_store

**Purpose:** Store quotations with embeddings for future retrieval and analysis

**Input Schema:**
```json
{
  "quotation": {
    "client_name": "Empresa ABC",
    "product_family": "ISODEC",
    "thickness_mm": 100,
    "area_m2": 66.0,
    "total_usd": 2500.00,
    "items": [...]
  },
  "embedding": [0.123, 0.456, 0.789, ...],
  "include_similar": true,
  "limit": 3
}
```

**Parameters:**
- `quotation` (required): Complete quotation object
- `embedding` (required): Vector embedding (non-empty number array)
- `include_similar` (optional): Return similar past quotations (default: false)
- `limit` (optional): Max similar quotations to return (default: 3)

**Response:**
```json
{
  "quotation_id": "QT-2026-02-16-001",
  "stored_at": "2026-02-16T20:45:00Z",
  "backend": "memory_store",
  "similar_quotations": [
    {
      "quotation_id": "QT-2026-02-14-003",
      "similarity": 0.94,
      "client_name": "Empresa XYZ",
      "total_usd": 2450.00
    }
  ]
}
```

### Storage Architecture

```
quotation_store handler
   ↓
MemoryStore (current) / Qdrant (planned)
   ↓
JSON persistence (quotation_memory.json)
   ↓
Optional vector similarity search
```

### Configuration

```python
from mcp.storage.memory_store import MemoryStore
from mcp.handlers.quotation import configure_quotation_store

# Initialize storage
store = MemoryStore(persist_path="quotation_memory.json")
configure_quotation_store(
    store=store,
    enable_vector_retrieval=True,
    backend_metadata={"active_backend": "memory_store"}
)
```

### Use Cases

- **Quotation history**: Track all quotations over time
- **Pattern analysis**: Identify common configurations
- **Price trending**: Monitor pricing evolution
- **Similar project lookup**: Find comparable past quotations
- **Analytics**: Structured event logging for dashboards

---

## 🧠 KB Self-Learning Module

**Version:** 3.4 | **Status:** ✅ Production Ready (with [known limitations](kb_self_learning/ARCHITECTURAL_LIMITATIONS.md)) | **Location:** `kb_self_learning/`

### Overview

The KB Self-Learning module allows the AI model to **propose new knowledge base entries** through chat interactions, with a human approval workflow before any changes are persisted. It bridges continuous learning with human oversight.

### Core Components

#### KB Writer Service (`kb_self_learning/kb_writer_service.py`)

FastAPI-based service that exposes endpoints for submitting KB entries:

- Accepts structured `KBEntry` payloads (topic, content, confidence score, tags, metadata)
- Validates entry completeness before queuing for review
- Uses Pydantic v2 models with strict field constraints
- Integrates with SQLAlchemy for entry persistence

```python
# Example KB entry structure
{
    "topic": "ISODEC EPS 150mm load-bearing update",
    "content": "Max autoportancia corrected to 7.5m per supplier bulletin 2026-02",
    "confidence_score": 0.95,
    "source": "self_learning",
    "tags": ["autoportancia", "ISODEC", "EPS"]
}
```

#### Approval Workflow (`kb_self_learning/approval_workflow.py`)

Manages the human review pipeline:

- **Status flow**: `pending_approval` → `approved` | `rejected` | `needs_revision`
- In-memory queue (`pending_queue`) with approval history tracking
- Per-entry audit trail with reviewer, timestamp, and notes

> ⚠️ **Limitation:** The current implementation uses in-memory state, making it incompatible with multi-replica Kubernetes deployments. See [ARCHITECTURAL_LIMITATIONS.md](kb_self_learning/ARCHITECTURAL_LIMITATIONS.md) for full details and migration path.

### Configuration

`kb_self_learning/config_v3.4.yaml` controls approval thresholds, confidence requirements, and allowed entry types.

### Testing

```bash
# Run KB self-learning tests
pytest kb_self_learning/tests/ -v
```

**Coverage:** `test_kb_writer_service.py` + `test_approval_workflow.py` (336 lines total)

---

## 🖥️ Backend & Frontend Services

### Backend Service (`backend/`)

**Flask application** deployed on Google Cloud Run. Provides chat conversation storage backed by Cloud SQL (PostgreSQL), with secrets managed via Google Cloud Secret Manager.

**Key endpoints:**
- `POST /chat` — Store and process user messages (5000 character limit enforced)
- `GET /health` — Health check
- Database schema managed via `backend/init_db.sql` migration script

**Security features:**
- Server-side message length validation (400 error for >5000 chars)
- Credentials injected at runtime from Secret Manager (never hardcoded)
- Database schema via migration scripts, not application startup

**Running locally:**
```bash
cd backend
pip install -r requirements.txt
# Requires environment variables: PORT, PROJECT_ID, DB_CONNECTION_NAME, DB_USER, DB_PASSWORD, DB_NAME
python main.py
```

**Tests:**
```bash
pytest backend/tests/ -v
```

### Frontend Service (`frontend/`)

**Flask web application** serving the chat interface. Implements the Panelin chat UI with XSS-safe message rendering.

**Security features:**
- All user-generated content rendered via `textContent` (never `innerHTML`)
- Message input enforces `maxlength="5000"` on the frontend
- Matching server-side validation in the backend

**Running locally:**
```bash
cd frontend
pip install -r requirements.txt
python main.py
```

---

## 🔁 KB Pipeline

**Location:** `kb_pipeline/` | **Script:** `kb_pipeline/build_indexes.py`

The KB Pipeline builds lightweight **hot artifacts** and provenance metadata from source catalogs, enabling fast MCP tool lookups without loading full catalog files into memory.

### Source Catalogs

- `shopify_catalog_v1.json`
- `bromyros_pricing_master.json`
- `bromyros_pricing_gpt_optimized.json`

### Output Artifacts

```
artifacts/
├── hot/
│   ├── shopify_catalog_v1.hot.json            (~470 bytes, 1 row)
│   ├── bromyros_pricing_master.hot.json        (~32 KB, 96 rows)
│   └── bromyros_pricing_gpt_optimized.hot.json (~32 KB, 96 rows)
└── source_manifest.json                        (~1.5 KB)
```

Each hot record preserves immutable source references (`source_file`, `source_key`, `checksum`) for traceability.

### Rebuild

```bash
python kb_pipeline/build_indexes.py
```

The build fails if required fields are missing, duplicate SKUs exist within a catalog, or duplicate source references are detected across catalogs.

---

## 📊 Observability

**Location:** `observability/`

Cost monitoring and alerting infrastructure for the Panelin GCP deployment.

### Components

| File | Description |
|------|-------------|
| `daily_cost_report.py` | Generates daily GCP cost summary reports by service |
| `metrics_schema.json` | Prometheus/GCP Monitoring metrics schema definition |
| `threshold_alerts.md` | Alert threshold configuration guide and escalation procedures |

### Cost Monitoring

The daily cost report tracks:
- Cloud Run invocations (backend, frontend, Wolf API)
- Cloud SQL usage
- GCS storage and operations
- Secret Manager access

---

### Additional Resources

- **Quick Start Guide:** [MCP_QUICK_START.md](MCP_QUICK_START.md) - Get the server running in 3 steps
- **Usage Examples:** [MCP_USAGE_EXAMPLES.md](MCP_USAGE_EXAMPLES.md) - Practical examples for each tool
- **MCP Specification:** [modelcontextprotocol.io](https://modelcontextprotocol.io)
- **Comparative Analysis:** [MCP_SERVER_COMPARATIVE_ANALYSIS.md](MCP_SERVER_COMPARATIVE_ANALYSIS.md)
- **Migration Guide:** [KB_MCP_MIGRATION_PROMPT.md](KB_MCP_MIGRATION_PROMPT.md)
- **Architecture Audit:** [KB_ARCHITECTURE_AUDIT.md](KB_ARCHITECTURE_AUDIT.md)

### Benefits of MCP Integration

| Benefit | Impact |
|---------|--------|
| **Reduced Token Usage** | 77% reduction in tokens/session (149K → 34K) |
| **Real-time Data** | Dynamic pricing and catalog queries instead of static KB |
| **Error Tracking** | Persistent logging with governance workflow |
| **Self-Healing** | Automated impact analysis for KB corrections |
| **Quotation Memory** | Persistent storage with similarity search |
| **Standard Protocol** | Works with any MCP-compatible AI assistant |
| **Scalability** | External data sources don't consume GPT context window |
| **Version Control** | KB updates via GitHub without GPT redeployment |
| **Thread Safety** | Production-ready with proper locking patterns |

---

## 🚀 Installation & Deployment

### Quick Start

**🚀 For fast deployment, we provide automated helper tools:**

#### Option 1: Claude Desktop with Auto-Start (Maximum Automation) ⭐ NEWEST

**Fully automated - Claude starts deployment when you open it:**

**Setup (one-time, 5 minutes):**
```bash
# Install MCP server for Claude Desktop
python setup_claude_mcp.py
```

**Usage (every time):**
```
1. Open Claude Desktop
2. Say: "Deploy the GPT"
3. Claude handles everything automatically
4. Approve final publication
5. Done! (~5 minutes total)
```

**What happens automatically:**
- ✅ Claude has deployment tools loaded on startup
- ✅ Checks configuration status automatically
- ✅ Generates config if needed
- ✅ Uses Computer Use to deploy
- ✅ No manual file management needed

**Time:** ~5 minutes (one command + supervision)
**Cost:** ~$0.45 per deployment (Claude API)
**Prerequisites:** Claude Desktop

See [CLAUDE_MCP_SETUP_GUIDE.md](CLAUDE_MCP_SETUP_GUIDE.md) for complete setup instructions and [CLAUDE_COMPUTER_USE_AUTOMATION.md](CLAUDE_COMPUTER_USE_AUTOMATION.md) for advanced usage.

#### Option 2: GitHub Actions + Claude Computer Use (High Automation)

**Most automated approach using AI-powered browser automation:**

**What's Automated:**
- ✅ Config generation via GitHub Actions (~1 min)
- ✅ Browser-based deployment via Claude Computer Use (~5 min supervised)
- ✅ File uploads, settings, verification
- ✅ 65% time savings vs. manual

**How it works:**
```
1. Push changes → GitHub Actions generates config
2. Open Claude Desktop with Computer Use enabled
3. Give Claude the deployment task
4. Claude downloads artifacts, navigates OpenAI, uploads files
5. You supervise and approve actions
6. GPT is published
```

**Total time:** ~6 minutes (1 min automated + 5 min supervised)
**Cost:** ~$0.45 per deployment (Claude API)
**Prerequisites:** Claude Desktop with Computer Use enabled

See [CLAUDE_COMPUTER_USE_AUTOMATION.md](CLAUDE_COMPUTER_USE_AUTOMATION.md) for complete setup guide, prompts, security considerations, and troubleshooting.

#### Option 2: GitHub Actions Automation (Partial Automation)

**Automates configuration generation via GitHub Actions:**

**⚠️ Note:** This automates config generation but NOT deployment to OpenAI (no API exists). Manual upload to OpenAI GPT Builder still required (~15 minutes).

**Automatic Triggers:**
- Runs on push to main when GPT files change
- Validates files automatically
- Generates config package automatically
- Uploads artifacts for download

**Manual Trigger:**
```
1. Go to Actions tab → Generate GPT Configuration
2. Click "Run workflow"
3. Wait ~1 minute for completion
4. Download "gpt-deployment-package" artifact
5. Follow DEPLOYMENT_GUIDE.md to upload to OpenAI
```

**Time:** 1 min automated + 15 min manual upload = 16 min total

See [GITHUB_ACTIONS_GPT_CONFIG.md](GITHUB_ACTIONS_GPT_CONFIG.md) for details or [AUTOMATED_GPT_CREATION_LIMITATIONS.md](AUTOMATED_GPT_CREATION_LIMITATIONS.md) for why full automation is impossible.

#### Option 2: Local Autoconfiguration (Recommended for Testing)

**Generate complete deployment-ready configuration with approval workflow:**

**⚠️ Note:** This tool generates configuration files but does NOT automatically upload to OpenAI. Manual deployment through OpenAI GPT Builder is still required (no public API available).

```bash
# Run autoconfiguration tool
python autoconfig_gpt.py

# Review configuration summary
# Type 'yes' to approve

# Navigate to generated package
cd GPT_Deploy_Package

# Follow deployment guide for manual upload
cat DEPLOYMENT_GUIDE.md
```

The autoconfiguration tool:
- ✅ Validates all 21 required files
- ✅ Generates complete GPT configuration
- ✅ Creates OpenAI-compatible export
- ✅ Provides step-by-step deployment guide
- ✅ Includes interactive approval workflow
- ⚠️ Manual upload to OpenAI still required (10-15 min)

See [AUTOCONFIG_QUICK_START.md](AUTOCONFIG_QUICK_START.md) for details, [GPT_AUTOCONFIG_GUIDE.md](GPT_AUTOCONFIG_GUIDE.md) for comprehensive documentation, or [GPT_AUTOCONFIG_FAQ.md](GPT_AUTOCONFIG_FAQ.md) for common questions.

#### Option 2.5: **Complete ZIP Package (Recommended for Sharing)** 🆕

**For a complete, downloadable package with everything:**

```bash
# Quick method (recommended)
./generate_gpt_package.sh

# Or run Python script directly
python create_gpt_zip_package.py

# Output: GPT_Complete_Package/Panelin_GPT_Config_Package_[timestamp].zip
# Contains: All 38 files (KB, configs, docs) in organized folders
```

This creates a **single ZIP file** (~290 KB) containing:
- ✅ All 21 knowledge base files (organized by upload phase)
- ✅ GPT configuration files (auto-generated)
- ✅ All instruction and schema files
- ✅ Deployment guides and documentation
- ✅ README with quick start instructions
- ✅ Complete file manifest

**Perfect for:**
- 📦 Sharing complete GPT configuration with team members
- 💾 Archiving deployment-ready packages
- 🚀 Fast deployment (extract and follow README)
- 📤 Uploading to cloud storage for distribution

See [GPT_ZIP_PACKAGE_GUIDE.md](GPT_ZIP_PACKAGE_GUIDE.md) for complete documentation.

#### Option 3: Manual Packaging

**For traditional file organization and manual upload:**

```bash
# Step 1: Validate all required files exist
python validate_gpt_files.py

# Step 2: Package files for easy upload
python package_gpt_files.py

# Step 3: Follow instructions in GPT_Upload_Package/
```

See [QUICK_START_GPT_UPLOAD.md](QUICK_START_GPT_UPLOAD.md) for streamlined deployment guide, or [GPT_UPLOAD_CHECKLIST.md](GPT_UPLOAD_CHECKLIST.md) for comprehensive instructions.

### Prerequisites

**For GPT Deployment:**
- OpenAI GPT Builder account
- Access to OpenAI Custom GPTs (ChatGPT Plus or Enterprise)
- All knowledge base files from this repository
- Python 3.7+ (for validation and packaging scripts)

**For Local Development & Testing:**
```bash
# Install Python dependencies for PDF generation
pip install -r requirements.txt
# Includes: reportlab>=4.0.0, pillow>=9.0.0

# For EVOLUCIONADOR (optional - uses stdlib only)
cd .evolucionador
# No external dependencies required
```

**For Running Tests:**
```bash
# Test PDF generation module
python panelin_reports/test_pdf_generation.py

# Test EVOLUCIONADOR components
python .evolucionador/tests/test_analyzer.py
python .evolucionador/tests/test_validator.py
python .evolucionador/tests/test_optimizer.py
```

### Docker Deployment (Production)

**For production deployments, use Docker for containerized deployment:**

#### Prerequisites
- Docker 20.10+ and Docker Compose v2+
- 2+ CPU cores, 2GB+ RAM, 5GB+ disk space
- OpenAI API key

#### Quick Start with Docker

```bash
# 1. Clone repository
git clone https://github.com/matiasportugau-ui/GPT-PANELIN-V3.3.git
cd GPT-PANELIN-V3.3

# 2. Create environment file
cp .env.example .env
# Edit .env and set OPENAI_API_KEY and other variables

# 3. Build and start services
docker-compose up -d --build

# 4. View logs
docker-compose logs -f panelin-bot

# 5. Check health
./scripts/health_check.sh production
```

#### Production Deployment Script

```bash
# Run pre-deployment checks
./scripts/pre_deploy_check.sh

# Deploy to production
./scripts/deploy.sh production

# Verify deployment
./scripts/health_check.sh production
```

**See [DEPLOYMENT.md](DEPLOYMENT.md) for comprehensive deployment guide including:**
- Architecture overview
- Environment setup
- Health checks and monitoring
- Troubleshooting
- Rollback procedures
- Security considerations

### CI/CD Pipeline

This project includes automated CI/CD workflows using GitHub Actions:

#### Workflows

- **CI/CD Pipeline** (`.github/workflows/ci-cd.yml`)
  - Runs tests, linting, and knowledge base validation
  - Builds Docker image
  - Auto-deploys to staging on main branch
  - Manual approval required for production

- **Test Suite** (`.github/workflows/test.yml`)
  - Matrix testing: Python 3.10, 3.11, 3.12
  - Unit tests, integration tests
  - Knowledge base validation

- **Health Checks** (`.github/workflows/health-check.yml`)
  - Runs every 6 hours
  - Validates system health
  - Manual trigger available

#### Required GitHub Secrets

Configure in repository Settings → Secrets:

```
OPENAI_API_KEY           # Required for OpenAI integration
DOCKER_USERNAME          # Optional: Docker Hub username
DOCKER_PASSWORD          # Optional: Docker Hub password
SENTRY_DSN               # Optional: Error tracking
```

#### Monitoring

- **Health endpoint**: `http://localhost:8000/health`
- **Metrics endpoint**: `http://localhost:9090/metrics` (Prometheus format)
- **Logs**: `logs/panelin.log` (rotated, max 10MB × 5 backups)

### GPT Builder Deployment

For deploying to OpenAI's GPT Builder platform:

#### 1. Prepare Knowledge Base Files

**Option A: Use the Helper Scripts (Recommended)**

The repository includes two Python scripts to streamline deployment:

**1. Validation Script (`validate_gpt_files.py`)**
```bash
python \
  validate_gpt_files.py
```
- ✅ Validates all 21 required files exist
- ✅ Checks JSON syntax for all knowledge base files
- ✅ Verifies file sizes are within expected ranges
- ✅ Reports any missing or invalid files
- Exit code 0 = all valid, non-zero = issues found

**2. Packaging Script (`package_gpt_files.py`)**
```bash
python package_gpt_files.py
```
- 📦 Creates organized `GPT_Upload_Package/` directory
- 📁 Sorts files into 6 upload phases
- 📝 Generates an INSTRUCTIONS.txt guide for each phase
- ⏱️ Specifies pause times between phases
- 📊 Shows file counts and sizes per phase

**Output Structure:**
```
GPT_Upload_Package/
├── Phase_1_Master_KB/           # 3 files - Upload FIRST
├── Phase_2_Optimized_Lookups/   # 2 files
├── Phase_3_Validation/          # 2 files
├── Phase_4_Documentation/       # 7 files
├── Phase_5_Supporting/          # 2 files
└── Phase_6_Assets/              # 1 file
```

Each phase includes an instructions file (INSTRUCTIONS.txt) with:
- File listing and descriptions
- Upload order requirements
- Recommended pause time before next phase
- Specific guidance for that phase

**Quick Start Guides:**
- [QUICK_START_GPT_UPLOAD.md](QUICK_START_GPT_UPLOAD.md) - 3-step fast track guide
- [USER_GUIDE.md](USER_GUIDE.md) - Detailed user-friendly guide
- [GPT_UPLOAD_CHECKLIST.md](GPT_UPLOAD_CHECKLIST.md) - Comprehensive checklist

**Option B: Manual Preparation**

Ensure all required files are ready for upload:

**Level 1 (Mandatory):**
- [ ] `BMC_Base_Conocimiento_GPT-2.json`
- [ ] `accessories_catalog.json`
- [ ] `bom_rules.json`
- [ ] `bromyros_pricing_gpt_optimized.json`
- [ ] `shopify_catalog_v1.json`

**Level 2-3 (Recommended):**
- [ ] `BMC_Base_Unificada_v4.json`
- [ ] `panelin_truth_bmcuruguay_web_only_v2.json`

**Documentation (Recommended):**
- [ ] `PANELIN_KNOWLEDGE_BASE_GUIDE.md`
- [ ] `PANELIN_QUOTATION_PROCESS.md`
- [ ] `PANELIN_TRAINING_GUIDE.md`
- [ ] `GPT_INSTRUCTIONS_PRICING.md`
- [ ] `GPT_PDF_INSTRUCTIONS.md`

**Validation:**
Run `validate_gpt_files.py` with Python to verify all files exist and are valid before upload.

#### 2. Configure GPT in OpenAI

1. Go to OpenAI GPT Builder: https://chat.openai.com/gpts/editor
2. Create new GPT or edit existing "Panelin 3.4"
3. **Configure basic info:**
   - Name: `Panelin 3.4`
   - Description: Use description from [Panelin_GPT_config.json](Panelin_GPT_config.json)
   - Profile image: Upload `bmc_logo.png` (optional)

4. **Configure instructions:**
   - Copy full instructions from `Instrucciones GPT.rtf`
   - OR use the instructions section from `Panelin_GPT_config.json`

5. **Configure conversation starters:**
   - Add the 6 conversation starters from the configuration file

6. **Enable capabilities:**
   - ✅ Web Browsing (mark as non-authoritative in instructions)
   - ✅ Canvas
   - ✅ Image Generation
   - ✅ Code Interpreter (CRITICAL for PDF generation)

#### 3. Upload Knowledge Base

**Important:** Upload in this specific order to maintain hierarchy:

1. **First:** `BMC_Base_Conocimiento_GPT-2.json` (establishes Level 1 priority)
2. **Then:** `accessories_catalog.json` and `bom_rules.json`
3. **Then:** Optimized indices and catalogs
4. **Then:** Validation and dynamic data
5. **Finally:** Documentation files

Wait a few minutes between uploads for reindexing.

#### 4. Configure Actions (API Integration)

1. In GPT Builder, go to "Actions" section
2. Import the OpenAPI schema from the problem statement
3. Configure authentication:
   - Type: API Key
   - Header name: `X-API-Key`
   - Key value: `YOUR_WOLF_API_KEY` (obtain from system administrator)

4. Test each endpoint:
   - Test `/health` (should return 200 OK)
   - Test `/` with API key (should return status)
   - Test `/find_products` with a sample query

#### 5. Verify Configuration

Use this checklist to ensure everything works:

**Knowledge Base Verification:**
- [ ] Ask "¿Cuánto cuesta ISODEC 100mm?" (should return price from Level 1)
- [ ] Ask "¿Cuánto cuesta un gotero frontal?" (should return price from accessories catalog)
- [ ] Request a complete quotation with BOM (should include all accessories)
- [ ] Check that autoportancia validation works correctly

**API Verification:**
- [ ] Test product search through natural language
- [ ] Test quotation calculation through API
- [ ] Verify API key authentication works

**Capabilities Verification:**
- [ ] Request PDF generation (Code Interpreter should activate)
- [ ] Ask for a technical diagram (Image Generation should work)
- [ ] Verify Canvas opens for formal quotations

### Updating the GPT

When updating files:

1. **Remove** the old file from the GPT's knowledge
2. **Upload** the new file
3. **Wait** 5-10 minutes for reindexing
4. **Test** that the GPT reads the new data correctly
5. **Verify** that Level 1 hierarchy is maintained

---

## 📖 Usage Guide

### Basic Quotation Workflow

#### Step 1: Initiate Conversation

The GPT will greet you and ask for your name:

```
User: "Hola"
Panelin: "Hola! Soy Panelin, BMC Assistant Pro. ¿Cuál es tu nombre?"
User: "Martin"
Panelin: "Perfecto Martin. Estoy aquí para hacer tu vida más fácil..."
```

#### Step 2: Request Quotation

```
User: "Necesito cotización para ISODEC EPS 100mm, techo de 5m x 11m"
```

#### Step 3: GPT Asks Critical Questions

Panelin will collect required information:
- Luz (distance between supports) - CRITICAL for load-bearing validation
- Structure type (concrete, metal, wood)
- Client name, phone, and project address (for formal quotations)

#### Step 4: Validation

Panelin automatically validates:
- **Load-bearing capacity**: Compares requested span vs maximum safe span
- **Thickness adequacy**: Suggests alternatives if needed
- **Technical feasibility**: Warns about structural requirements

Example validation:
```
⚠️ ADVERTENCIA: ISODEC EPS 100mm tiene autoportancia máxima de 5.5m.
Para tu luz de 6m, te recomiendo:
1. ISODEC EPS 150mm (autoportancia 7.5m)
2. O agregar un apoyo intermedio a los 3m
```

#### Step 5: Complete BOM Calculation

Panelin calculates:
- **Panels**: Based on area and panel width
- **Supports**: Based on load-bearing capacity
- **Fixing points**: Per formula (includes all fixing rows)
- **Accessories**:
  - Front gutters
  - Lateral gutters
  - Babetas
  - Ridge caps (if applicable)
  - Channels (if applicable)
- **Fixings**:
  - Rods (threaded 3/8")
  - Nuts
  - Washers (carrocero type)
  - PVC turtles
  - Screws/rivets
- **Sealants**:
  - Silicone
  - Butyl tape

#### Step 6: Presentation

Panelin presents the quotation with:
- **Detailed line items** (product, SKU, quantity, unit price, total)
- **Subtotals** by category (panels, accessories, fixings, sealants)
- **IVA 22%** (correctly applied - prices already include IVA, not added)
- **Total** (includes shipping estimate if applicable)
- **Technical recommendations**
- **Long-term value analysis** (energy savings, ROI comparison)

### Advanced Features

#### PDF Generation

Request a professional PDF quotation:

```
User: "Genera PDF para esta cotización"
```

Panelin will:
1. Validate all data is complete
2. Use Code Interpreter to generate PDF
3. Apply BMC Uruguay branding
4. Include all line items with correct calculations
5. Add terms & conditions
6. Provide downloadable PDF

See [GPT_PDF_INSTRUCTIONS.md](GPT_PDF_INSTRUCTIONS.md) for technical details.

#### Product Search via API

Use natural language to search products:

```
User: "¿Qué paneles tienes para cámaras frigoríficas?"
```

Panelin uses the `/find_products` API endpoint to search and present options.

#### Energy Savings Comparison

When comparing thicknesses:

```
User: "Compara ISODEC 100mm vs 150mm para ahorro energético"
```

Panelin provides:
- Thermal resistance comparison (m²K/W)
- Estimated annual energy savings (kWh and USD)
- ROI analysis considering initial cost vs long-term savings
- Comfort improvement explanation

#### Sales Training Mode

Activate with command:

```
User: "/entrenar"
```

Panelin provides:
- Knowledge assessment
- Practice scenarios
- Feedback on responses
- Best practices examples

See [PANELIN_TRAINING_GUIDE.md](PANELIN_TRAINING_GUIDE.md) for details.

### Commands Reference

| Command | Purpose |
|---------|---------|
| `/estado` | Show conversation state and context risk |
| `/checkpoint` | Create snapshot of current conversation |
| `/consolidar` | Complete consolidation (MD + JSON) |
| `/evaluar_ventas` | Evaluate sales personnel competencies |
| `/entrenar` | Start guided training session |
| `/pdf` | Guide for generating PDF quotation |

---

## 📚 Documentation

> 📂 **Looking for documentation?** Visit the **[Documentation Index](docs/README.md)** for a complete navigation guide to all project documentation.

### Core Documentation

| Document | Description | Status |
|----------|-------------|--------|
| [README.md](README.md) | This file - Complete project overview | ✅ Current |
| [Instrucciones GPT.rtf](Instrucciones%20GPT.rtf) | Full GPT system instructions (v3.1) | ✅ Production |
| [Panelin_GPT_config.json](Panelin_GPT_config.json) | Complete GPT configuration (v2.3) | ✅ Production |

### Knowledge Base Guides

| Document | Description | Version |
|----------|-------------|---------|
| [PANELIN_KNOWLEDGE_BASE_GUIDE.md](PANELIN_KNOWLEDGE_BASE_GUIDE.md) | Complete KB hierarchy and usage rules | 3.0 (KB v7.0) |
| [PANELIN_QUOTATION_PROCESS.md](PANELIN_QUOTATION_PROCESS.md) | 5-phase quotation workflow with formulas | 3.0 |
| [PANELIN_TRAINING_GUIDE.md](PANELIN_TRAINING_GUIDE.md) | Sales evaluation and training procedures | 2.0 |

### Technical Instructions

| Document | Description | Version |
|----------|-------------|---------|
| [GPT_INSTRUCTIONS_PRICING.md](GPT_INSTRUCTIONS_PRICING.md) | Fast pricing lookups with optimized JSON | 1.0 |
| [GPT_PDF_INSTRUCTIONS.md](GPT_PDF_INSTRUCTIONS.md) | PDF generation workflow and requirements | 2.0 |
| [GPT_OPTIMIZATION_ANALYSIS.md](GPT_OPTIMIZATION_ANALYSIS.md) | System analysis and improvement plan | 1.0 |

### Deployment & Upload Guides

| Document | Description | Audience |
|----------|-------------|----------|
| [QUICK_START_GPT_UPLOAD.md](QUICK_START_GPT_UPLOAD.md) | Fast 3-step upload guide | Quick deployers |
| [USER_GUIDE.md](USER_GUIDE.md) | User-friendly upload walkthrough | Non-technical users |
| [GPT_UPLOAD_CHECKLIST.md](GPT_UPLOAD_CHECKLIST.md) | Comprehensive deployment checklist | Thorough deployers |
| [GPT_UPLOAD_IMPLEMENTATION_SUMMARY.md](GPT_UPLOAD_IMPLEMENTATION_SUMMARY.md) | Technical implementation details | Developers |

### MCP Server Documentation

| Document | Description | Purpose |
|----------|-------------|---------|
| [MCP_QUICK_START.md](MCP_QUICK_START.md) | Get MCP server running in 3 steps | Quick deployment |
| [MCP_USAGE_EXAMPLES.md](MCP_USAGE_EXAMPLES.md) | Practical examples for all 18 tools | Learning & testing |
| [MCP_SERVER_COMPARATIVE_ANALYSIS.md](MCP_SERVER_COMPARATIVE_ANALYSIS.md) | Analysis of 10 MCP server options | Architecture decisions |
| [KB_MCP_MIGRATION_PROMPT.md](KB_MCP_MIGRATION_PROMPT.md) | KB migration to MCP architecture | Migration planning |
| [KB_ARCHITECTURE_AUDIT.md](KB_ARCHITECTURE_AUDIT.md) | KB optimization audit | Token reduction strategy |

### Implementation & Version Documentation

| Document | Description | Version |
|----------|-------------|---------|
| [IMPLEMENTATION_SUMMARY_V3.4.md](IMPLEMENTATION_SUMMARY_V3.4.md) | V3.4 changes (Wolf API write, governance, storage) | 3.4 |
| [IMPLEMENTATION_SUMMARY_V3.3.md](IMPLEMENTATION_SUMMARY_V3.3.md) | V3.3 changes and new features | 3.3 |
| [EVOLUCIONADOR_FINAL_REPORT.md](EVOLUCIONADOR_FINAL_REPORT.md) | EVOLUCIONADOR completion report | 1.0.0 |
| [WOLF_KB_WRITE_ACCESS_VERIFICATION.md](WOLF_KB_WRITE_ACCESS_VERIFICATION.md) | Wolf API write access verification guide | 3.4 |
| [WOLF_WRITE_ACCESS_QUICK_GUIDE.md](WOLF_WRITE_ACCESS_QUICK_GUIDE.md) | Quick guide for Wolf API write capabilities | 3.4 |
| [GPT_WEIGHT_MODIFICATION_GUIDE.md](GPT_WEIGHT_MODIFICATION_GUIDE.md) | Complete guide for modifying product weights (kg) via GPT | 3.4 |

### MCP Integration Documentation

| Document | Description | Version |
|----------|-------------|---------|
| [MCP_SERVER_COMPARATIVE_ANALYSIS.md](MCP_SERVER_COMPARATIVE_ANALYSIS.md) | Top 10 MCP server comparison with cost analysis | 1.0 |
| [MCP_AGENT_ARCHITECT_PROMPT.md](MCP_AGENT_ARCHITECT_PROMPT.md) | AI agent for MCP architecture design | 1.0 |
| [MCP_RESEARCH_PROMPT.md](MCP_RESEARCH_PROMPT.md) | Structured MCP market research prompt | 1.0 |
| [KB_ARCHITECTURE_AUDIT.md](KB_ARCHITECTURE_AUDIT.md) | KB files audit for MCP migration | 1.0 |
| [KB_MCP_MIGRATION_PROMPT.md](KB_MCP_MIGRATION_PROMPT.md) | KB restructuring execution prompt | 1.0 |
| [MCP_CROSSCHECK_EVOLUTION_PLAN.md](MCP_CROSSCHECK_EVOLUTION_PLAN.md) | MCP gap analysis & execution plan | 1.0 |

### Module-Specific Documentation

| Document | Description | Module |
|----------|-------------|--------|
| [openai_ecosystem/README.md](openai_ecosystem/README.md) | OpenAI API helpers usage guide | openai_ecosystem |
| [panelin_reports/test_pdf_generation.py](panelin_reports/test_pdf_generation.py) | PDF generation test suite | panelin_reports |
| [.evolucionador/README.md](.evolucionador/README.md) | EVOLUCIONADOR system guide | .evolucionador |
| [docs/README.md](docs/README.md) | Complete documentation hub and index | docs |
| [mcp/config/mcp_server_config.json](mcp/config/mcp_server_config.json) | MCP server configuration | mcp |
| [kb_self_learning/ARCHITECTURAL_LIMITATIONS.md](kb_self_learning/ARCHITECTURAL_LIMITATIONS.md) | KB self-learning module limitations and roadmap | kb_self_learning |
| [kb_self_learning/DEPLOYMENT_V3.4.md](kb_self_learning/DEPLOYMENT_V3.4.md) | KB self-learning deployment guide | kb_self_learning |
| [background_tasks/README.md](background_tasks/README.md) | Background task processing guide with examples | background_tasks |
| [kb_pipeline/README.md](kb_pipeline/README.md) | KB pipeline usage and artifact reference | kb_pipeline |
| [wolf_api/README.md](wolf_api/README.md) | Wolf API quick start and endpoint reference | wolf_api |
| [wolf_api/DEPLOYMENT.md](wolf_api/DEPLOYMENT.md) | Wolf API complete deployment guide (Cloud Run) | wolf_api |
| [wolf_api/IAM_SETUP.md](wolf_api/IAM_SETUP.md) | Wolf API IAM permissions and service account setup | wolf_api |

### Python Modules Documentation

| Module | Description | Version |
|--------|-------------|---------|
| `quotation_calculator_v3.py` | Core calculation engine with Decimal precision, autoportancia validation, 6 construction systems | 3.1 |
| `panelin_reports/` | Professional PDF generation with BMC branding, ReportLab-based | 2.0 |
| `openai_ecosystem/` | OpenAI API response extraction and normalization utilities | 1.0 |
| `.evolucionador/` | Autonomous evolution agent with 7 validators, 6 optimizers, report generator | 1.0.0 |
| `mcp/` | MCP server with 18 tools (4 core, 7 background, 4 Wolf API, 2 governance, 1 storage) | 0.3.0 |
| `panelin_mcp_integration/` | MCP integration clients for OpenAI Responses API and Wolf API wrapper | 0.3.0 |
| `kb_self_learning/` | Knowledge base self-learning service with human approval workflow (FastAPI) | 3.4 |
| `backend/` | Flask chat backend for Cloud Run with Cloud SQL and Secret Manager integration | 1.0 |
| `frontend/` | Flask chat frontend with XSS-safe rendering and input validation | 1.0 |
| `background_tasks/` | Standalone async task queue with priority, retry, scheduler, and REST API | 1.0.0 |
| `kb_pipeline/` | KB index builder producing hot artifacts with provenance metadata | 1.0 |
| `observability/` | GCP cost reporting, Prometheus metrics schema, and alert thresholds | 1.0 |

#### OpenAI Ecosystem Module

The `openai_ecosystem/` module provides utilities for working with OpenAI API responses:

**Key Features:**
- **`extract_text(response)`** - Normalizes text from multiple OpenAI response shapes
  - Responses API style (`response.output_text`)
  - Chat Completions (`response.choices[].message.content`)
  - Message-oriented variants with structured/tool call fallbacks
- **`extract_primary_output(response)`** - Classifies output as text/structured/tool_call/unknown
- Handles edge cases: empty responses, missing fields, mixed content types
- Compact diagnostic summaries when no text is available
- Comprehensive test coverage: 33 tests across 5 categories

**Use Cases:**
- Normalizing responses from different OpenAI API endpoints
- Extracting text from complex response structures
- Handling tool calls and structured outputs
- Deduplicating repeated content in multi-part responses

**Documentation:** See [openai_ecosystem/README.md](openai_ecosystem/README.md) for detailed usage examples.

### API Documentation

The API schema is embedded in the GPT Actions configuration. Key endpoints:
- Health checks: `/health`, `/ready`
- Quotations: `/calculate_quote`
- Product search: `/find_products`, `/product_price`
- Availability: `/check_availability`

---

## 🧪 Testing & Quality Assurance

### Testing Infrastructure

The repository includes comprehensive test suites to ensure quality and reliability:

#### 1. PDF Generation Tests
**Location:** `panelin_reports/test_pdf_generation.py`

```bash
# Run PDF generation tests
python panelin_reports/test_pdf_generation.py
```

**Test Coverage:**
- ✅ Basic quotation PDF generation
- ✅ Multiple products with accessories
- ✅ Comments formatting (bold/red styling)
- ✅ Bank transfer footer rendering
- ✅ Logo detection and fallback handling

**Test Output:** 5 test PDFs with different scenarios

#### 2. EVOLUCIONADOR Tests
**Location:** `.evolucionador/tests/`

```bash
# Test analysis engine
python .evolucionador/tests/test_analyzer.py

# Test validation system
python .evolucionador/tests/test_validator.py

# Test optimization algorithms
python .evolucionador/tests/test_optimizer.py
```

**Test Coverage:**
- ✅ Workspace scanning and file detection
- ✅ All 7 validators (JSON, formulas, pricing, load-bearing, API, docs, cross-refs)
- ✅ Optimization algorithm correctness
- ✅ Report generation
- ✅ Error handling and edge cases

#### 3. File Validation
**Location:** `validate_gpt_files.py`

```bash
# Validate all GPT upload files
python \
  validate_gpt_files.py
```

**Validation Checks:**
- ✅ All 21 required files exist
- ✅ JSON syntax validation
- ✅ File size within expected ranges
- ✅ File readability and accessibility

#### 4. API Connection Tests
**Location:** `test_panelin_api_connection.sh`

```bash
# Test Panelin API connectivity and authentication
export WOLF_API_KEY="your_api_key_here"
./test_panelin_api_connection.sh
```

**Test Coverage:**
- ✅ Health check endpoint (no authentication)
- ✅ Readiness check endpoint (no authentication)
- ✅ Authenticated endpoints with API key
- ✅ Product search functionality
- ✅ Connection reliability with retries and timeouts
- ✅ Secure handling of API keys (no exposure in process listings)

**Security Features:**
- Secure temporary file handling with `mktemp`
- Automatic cleanup with `trap`
- API key passed via curl config file (not command line)
- Connection timeout and retry logic to prevent hanging

#### 5. MCP Handler Tests
**Location:** `mcp/tests/`

```bash
# Run all MCP tests (from repository root)
pytest mcp/tests/ -v

# Run specific handler tests
pytest mcp/tests/test_wolf_kb_write.py -v
```

**Test Coverage (100+ tests):**
- ✅ Core tool handlers (pricing, catalog, BOM, errors)
- ✅ Background task handlers (55 tests)
- ✅ Wolf API KB write handlers (20+ tests)
- ✅ Governance handlers (validate/commit corrections)
- ✅ Quotation persistence handler

#### 6. Wolf API Tests
**Location:** `wolf_api/tests/`

```bash
# Run Wolf API tests (from repository root)
pytest wolf_api/tests/ -v
```

**Test Coverage (10 tests):**
- ✅ POST /kb/conversations endpoint
- ✅ GCS persistence (daily_jsonl and per_event_jsonl modes)
- ✅ X-API-Key authentication
- ✅ Error handling and edge cases

#### 7. KB Self-Learning Tests
**Location:** `kb_self_learning/tests/`

```bash
# Run KB self-learning tests
pytest kb_self_learning/tests/ -v
```

**Test Coverage (336 lines):**
- ✅ KB writer service entry creation and validation
- ✅ Approval workflow status transitions
- ✅ Reviewer notes and audit trail

#### 8. Backend Tests
**Location:** `backend/tests/`

```bash
# Run backend tests
pytest backend/tests/ -v
```

**Test Coverage (15 tests):**
- ✅ Chat endpoint validation (5000 char limit)
- ✅ Keyword extraction
- ✅ Error cases and edge conditions
- ✅ Mocked psycopg2/secretmanager (no DB required)

#### 9. Background Task Tests
**Location:** `background_tasks/tests/`

```bash
# Run background task tests
pytest background_tasks/tests/ -v
```

**Test Coverage:**
- ✅ Task queue operations (enqueue, dequeue, priority)
- ✅ Task persistence and recovery
- ✅ Worker execution and retry logic
- ✅ Scheduler (interval and daily tasks)
- ✅ Task cancellation and concurrent execution

### Continuous Integration

**GitHub Actions Workflow:** `.github/workflows/evolucionador-daily.yml`

**Automated Daily Tasks:**
1. Complete repository analysis
2. Validation of all KB files
3. Performance benchmarking
4. Evolution report generation
5. Automatic issue creation for findings
6. Report history archival

**Schedule:** Daily at 00:00 UTC  
**Manual Trigger:** Available via workflow dispatch

### Quality Metrics

EVOLUCIONADOR tracks these quality dimensions:
- **Functionality Score:** Target 95%+ (comprehensive feature completeness)
- **Efficiency Score:** Target 90%+ (file sizes, calculation speed)
- **Documentation Quality:** README compliance, guide completeness
- **Code Quality:** Pattern recognition, best practices adherence
- **API Performance:** Response times, reliability
- **Cost Optimization:** Resource usage, API call efficiency

---

## 🤝 Contributing

### How to Contribute

This repository contains the configuration for a production GPT system. Contributions should focus on:

1. **Knowledge Base Updates**
   - New product additions
   - Price updates
   - Formula corrections
   - Technical specification improvements

2. **Documentation Improvements**
   - Clarifications in guides
   - New examples
   - Troubleshooting tips
   - Translation improvements

3. **BOM Rules Enhancement**
   - New construction systems
   - Formula refinements
   - Edge case handling

### Contribution Guidelines

1. **Do NOT modify** production files directly without review
2. **Test thoroughly** any KB updates before deploying
3. **Maintain hierarchy** - Level 1 must remain authoritative
4. **Document changes** in commit messages and relevant guides
5. **Validate pricing** against official sources (Shopify, suppliers)

### Testing Changes

Before deploying KB updates:

1. **Local validation**: Verify JSON syntax and structure
2. **Content review**: Check for pricing accuracy, formula correctness
3. **Hierarchy check**: Ensure Level 1 priority is maintained
4. **Integration test**: Upload to test GPT instance first
5. **User acceptance**: Test with real quotation scenarios

### Reporting Issues

When reporting issues with the GPT or KB:

1. **Provide context**: What were you trying to do?
2. **Include conversation**: Copy relevant parts of the dialogue
3. **Expected vs actual**: What should have happened vs what did happen?
4. **KB source**: Which file should contain the correct data?
5. **Priority**: Is this a critical pricing error or minor inconsistency?

---

## 📜 Version History

### v3.4 / KB v7.0 / MCP v0.3.0 (2026-02-14) - Current

**Major Features:**

**1. Wolf API KB Write Capabilities (4 Tools)**
- **persist_conversation**: Save conversation summaries and quotation history to KB via Wolf API
- **register_correction**: Register KB corrections detected during conversations for continuous improvement
- **save_customer**: Store customer data (name, phone, address) for seamless repeat quotations
- **lookup_customer**: Auto-retrieve returning customer info without re-asking
- Password protection on all write operations (configurable via environment variable)
- Uruguayan phone format validation (09XXXXXXX or +598XXXXXXXX)
- 4 new MCP tool contracts (v1 envelope format with error codes)
- OpenAI approval workflow for write operations
- See `IMPLEMENTATION_SUMMARY_V3.4.md` for full details

**2. Self-Healing Governance Architecture (2 Tools)**
- **validate_correction**: Enterprise-grade validation with automatic impact analysis
- **commit_correction**: Two-step approval workflow for KB corrections
- Simulates impact on last 50 quotations before applying changes
- Thread-safe with `threading.Lock` for pending changes cache
- Whitelist-based security (only allowed KB files can be modified)
- Complete audit trail in `corrections_log.json`
- Deterministic SHA-256 based change IDs

**3. Quotation Persistence System (1 Tool)**
- **quotation_store**: Backend-agnostic quotation storage with vector similarity search
- Memory Store implementation with extensibility to Qdrant/PostgreSQL
- 1MB payload size limit for safety
- Analytics tracking with structured logging
- Optional retrieval of similar past quotations
- Pattern analysis and history tracking capabilities

**4. Production Readiness**
- MCP Server bumped to v0.3.0
- 18 total production-ready tools (4 core + 7 background + 4 Wolf API + 2 governance + 1 storage)
- Comprehensive test coverage (100+ tests across all handlers)
- Thread-safe implementations throughout
- Standardized error codes via `mcp_tools.contracts`

**Version Matrix:**
| Component | v3.3 | v3.4 |
|-----------|------|------|
| Panelin Version | 3.3 | 3.4 |
| Instructions Version | 2.4 | 2.5 |
| MCP Server Version | 0.2.0 | 0.3.0 |
| KB Version | 7.0 | 7.0 (unchanged) |
| PDF Template Version | 2.0 | 2.0 (unchanged) |
| Total MCP Tools | 12 | 18 (+4 Wolf, +2 Governance, +1 Storage) |

---

### v3.3 / KB v7.0 / PDF Template v2.0 (2026-02-10, Updated 2026-02-11)

**Major Features:**

**1. Enhanced PDF Generation Template v2.0** (from PR #215)
- Professional BMC logo header with 2-column layout
- Styled tables with alternating row colors (#EDEDED header, #FAFAFA rows)
- Right-aligned numeric columns for better readability
- Formatted comments section with per-line bold/red styling
- Bank transfer footer with grid/borders
- 1-page optimization (shrinks comments before other content)
- ReportLab-based implementation

**2. 🧬 EVOLUCIONADOR - Autonomous Evolution Agent v1.0.0**
- Complete autonomous repository evolution system
- Daily automated analysis via GitHub Actions
- 7 specialized validators (JSON, formulas, pricing, load-bearing, API, docs, cross-refs)
- 6 optimization algorithms (file size, formula efficiency, API, calculations, memory, cost)
- Comprehensive evolution reports with actionable recommendations
- Self-learning pattern recognition and benchmarking
- 44 files, 4,300+ lines of production code
- Zero external dependencies (Python stdlib only)

**3. Deployment Tools**
- `validate_gpt_files.py` - Validates all 21 required files with dynamic config discovery
- `package_gpt_files.py` - Organizes files for phased upload
- `test_panelin_api_connection.sh` - API smoke test with secure key handling
- Comprehensive upload guides (Quick Start, User Guide, Checklist)
- Automated file validation with JSON syntax checking

**4. OpenAI Ecosystem Helpers** (New)
- `openai_ecosystem/` - Response extraction and normalization utilities
- Handles multiple OpenAI API response shapes (Responses API, Chat Completions, Messages)
- `extract_text()` function with structured/tool call fallbacks
- Comprehensive test coverage (33 tests across 5 categories)
- SDK-agnostic utilities: compatible with OpenAI SDK responses but does not require the SDK (Python stdlib only)

**New Modules & Files:**
- `openai_ecosystem/` - OpenAI API integration utilities
  - `openai_ecosystem/client.py` - Response extraction and normalization (349 lines)
  - `openai_ecosystem/test_client.py` - Comprehensive test suite (449 lines, 33 tests)
  - `openai_ecosystem/README.md` - Module documentation with examples
- `panelin_reports/` - Complete PDF generation package
  - `panelin_reports/pdf_generator.py` - Enhanced PDF generator v2.0
  - `panelin_reports/pdf_styles.py` - BMC branding and style definitions
  - `panelin_reports/test_pdf_generation.py` - Comprehensive testing suite
- `.evolucionador/` - Complete autonomous evolution system
  - `.evolucionador/core/analyzer.py` - Analysis engine (850+ lines)
  - `.evolucionador/core/validator.py` - 7 validators (1,246 lines)
  - `.evolucionador/core/optimizer.py` - Optimization algorithms
  - `.evolucionador/reports/generator.py` - Report generator (50+ variables)
- `test_panelin_api_connection.sh` - Secure API connectivity smoke test
- `.github/workflows/evolucionador-daily.yml` - Daily automation
- `requirements.txt` - Python dependencies (reportlab, pillow)
- `.gitignore` - Proper exclusions

**Documentation Updates:**
- Updated README with complete repository overview
- Added EVOLUCIONADOR documentation (README, guides, reports)
- Added deployment tool documentation
- Enhanced PDF generation workflow documentation
- Added implementation summary for v3.3

**Updates:**
- All existing v3.2 features retained
- PDF generation now matches official BMC quotation template
- Enhanced professional presentation for client delivery
- Automated testing suite with 5 test cases
- Daily automated quality monitoring and improvement tracking

### v3.2 / KB v7.0 (2026-02-07)

**Major Features:**
- ✅ Complete BOM validation with autoportancia v3.1
- ✅ 70+ accessories catalog with real prices
- ✅ Parametric BOM rules for 6 construction systems
- ✅ Unified load-bearing capacity table
- ✅ Multi-supplier pricing (BROMYROS, MONTFRIO, BECAM)
- ✅ Advanced analysis capabilities (pattern recognition, cost optimization, zero-waste calculations)

**New Files:**
- `accessories_catalog.json` - Complete accessories with pricing
- `bom_rules.json` - Parametric BOM rules
- `quotation_calculator_v3.py` - Enhanced calculator with validation

**Updates:**
- Enhanced autoportancia validation with 15% safety margin
- New formulas: `tortugas_pvc`, `arandelas_carrocero`, `fijaciones_perfileria`
- Updated business rules for 2026 (IVA 22% confirmed)
- Improved energy savings calculations

### v3.1 (2026-02-06)

**Features:**
- Enhanced load-bearing validation
- New validation commands: `/autoportancia`, `/validar`
- Code Interpreter marked as CRITICAL capability
- Improved personalization for users (Mauro, Martin, Rami, Carolina)

### v2.3 / KB v6.0 (2026-01-27)

**Features:**
- Professional PDF generation
- New accessories: ANGULO_ALUMINIO, TORTUGAS_PVC, ARANDELA_CARROCERO
- Shopify catalog integration
- BROMYROS pricing optimization
- Fast product lookup indices

### v2.0 / KB v5.0 (2026-01-20)

**Features:**
- Initial production release
- 5-phase quotation process
- Basic knowledge base hierarchy
- API integration (Panelin Wolf API)
- Sales evaluation and training capabilities

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

**Copyright:** © 2026 MatPrompt

The MIT License allows:
- ✅ Commercial use
- ✅ Modification
- ✅ Distribution
- ✅ Private use

**Attribution Required:** Please include the original copyright notice and license in any copy or substantial portion of the software.

**BMC Uruguay Business Data:**  
While the code is MIT licensed, the proprietary business data (prices, formulas, product information) belongs to BMC Uruguay and should be used in accordance with BMC Uruguay's terms and conditions.

For BMC Uruguay business inquiries, contact: [BMC Uruguay](https://bmcuruguay.com.uy)

---

## 🔗 Links & Resources

- **Official Website**: https://bmcuruguay.com.uy
- **API Base URL**: https://panelin-api-642127786762.us-central1.run.app
- **OpenAI GPT Platform**: https://chat.openai.com/gpts
- **Documentation Hub**: [docs/README.md](docs/README.md)

### Archived Documentation

Historical review artifacts have been moved to the `archive/` directory. These documents served their purpose during PR review and consolidation processes:

- `BOOT_PRS_COMPARISON.md` - PR #15/18/19 comparison analysis
- `BRANCH_REVIEW_REPORT.md` - Branch analysis for PR #27
- `PULL_REQUESTS_REVIEW.md` - 9-PR overview analysis
- `PR_REVIEW_README.md` - Navigation for review documents
- `PR_CONSOLIDATION_ACTION_PLAN.md` - Consolidation plan
- `README_REVIEW_SUMMARY.md` - README audit results

These files are retained for historical reference but are not part of the active documentation.

---

## 📞 Support & Contact

For technical support or questions about this GPT configuration:

1. **Check documentation first**: Most questions are answered in the guides
2. **Review troubleshooting**: See [PANELIN_KNOWLEDGE_BASE_GUIDE.md](PANELIN_KNOWLEDGE_BASE_GUIDE.md) § Troubleshooting
3. **Test in isolation**: Verify if the issue is with KB data or GPT instructions
4. **Contact administrators**: Provide detailed information and context

---

**Version:** 3.4  
**Knowledge Base Version:** 7.0  
**PDF Template Version:** 2.0  
**MCP Server Version:** 0.3.0  
**Last Updated:** 2026-02-16  
**Maintained by:** BMC Uruguay Development Team  

---

*This README provides complete documentation for deploying and operating the Panelin 3.4 GPT with MCP Server integration, self-healing governance, and Wolf API KB write capabilities. For detailed technical specifications, consult the individual documentation files referenced throughout this document.* 
