# Panelin 3.3 - BMC Assistant Pro GPT Configuration

![Version](https://img.shields.io/badge/version-3.3-blue) ![GPT](https://img.shields.io/badge/platform-OpenAI%20GPT-green) ![KB](https://img.shields.io/badge/KB%20version-7.0-orange) ![Status](https://img.shields.io/badge/status-production-success)

**Complete configuration files and knowledge base for Panelin GPT - Professional quotation assistant for BMC Uruguay panel systems**

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [GPT Configuration](#gpt-configuration)
- [Repository Structure](#repository-structure)
- [Knowledge Base](#knowledge-base)
- [API Integration](#api-integration)
- [Installation & Deployment](#installation--deployment)
- [Usage Guide](#usage-guide)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [Version History](#version-history)
- [License](#license)

---

## 🎯 Overview

**Panelin 3.3** (BMC Assistant Pro) is an advanced AI assistant specialized in generating professional quotations for construction panel systems. This repository contains all configuration files, knowledge bases, and documentation needed to deploy and operate the GPT on OpenAI's platform.

### What is Panelin?

Panelin is a technical sales assistant that:
- Generates accurate quotations with complete Bill of Materials (BOM)
- Validates technical specifications (load-bearing capacity, thermal insulation)
- Produces professional PDF quotations with BMC Uruguay branding
- Provides technical advisory on panel systems (ISODEC, ISOPANEL, ISOROOF, ISOWALL, ISOFRIG)
- Evaluates and trains sales personnel based on real interactions
- Integrates with the Panelin Wolf API for real-time pricing and availability

### Key Capabilities

✅ **Professional Quotations**: Complete BOM with panels, accessories, fixings, and sealants  
✅ **Technical Validation**: Automatic load-bearing capacity verification  
✅ **Multi-System Support**: 6 construction systems with parametric BOM rules  
✅ **PDF Generation**: Professional branded quotations ready for client delivery  
✅ **Energy Savings**: ROI calculations comparing insulation options  
✅ **API Integration**: Real-time product search, pricing, and availability checks  
✅ **Sales Training**: Evaluation and coaching based on historical interactions  

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

---

## 🔧 GPT Configuration

### Basic Information

- **Name**: Panelin 3.3
- **Description**: BMC Assistant Pro - Specialized technical quotation assistant for panel systems (ISODEC, ISOPANEL, ISOROOF, ISOWALL, ISOFRIG) with complete BOM calculation, enhanced PDF generation (v2.0), and professional advisory. Knowledge Base v7.0 with 70+ accessories catalog and parametric rules for 6 construction systems.
- **Instructions**: See [Instrucciones GPT.rtf](Instrucciones%20GPT.rtf) for complete system instructions
- **Version**: 3.3 (KB v7.0, PDF Template v2.0)
- **Last Updated**: 2026-02-10

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

### 🚀 Auto-Boot System (NEW in v3.3)

Panelin 3.3 includes an **automatic knowledge base indexing system** that executes at the start of every conversation:

**What it does:**
- 🔍 Scans all uploaded knowledge files automatically
- 📊 Generates structured index table showing all available files
- ✅ Displays operational log (4 phases: scan → index → validate → ready)
- 🎯 Provides file-specific conversation starters
- 🔒 Maintains security (hides internal reasoning, shows only operational logs)

**Key files:**
- **GPT_BOOT_INSTRUCTIONS_COMPACT.md** - Ready-to-use boot directive (prepend to instructions)
- **GPT_BOOT_IMPLEMENTATION_GUIDE.md** - Detailed deployment guide
- **GPT_SYSTEM_PROMPT_AUTOBOOT.md** - Complete technical specification
- **GPT_BOOT_QUICK_REFERENCE.md** - Quick reference card

**Quick deployment:** Copy `GPT_BOOT_INSTRUCTIONS_COMPACT.md` and paste at the **TOP** of the GPT instructions field.

**Benefits:**
- ✅ Users see exactly what files the GPT has access to
- ✅ All files are easily referenceable by name during conversations
- ✅ Transparent initialization process builds user trust
- ✅ Consistent experience across all sessions

See [GPT_BOOT_IMPLEMENTATION_GUIDE.md](GPT_BOOT_IMPLEMENTATION_GUIDE.md) for complete deployment instructions.

---

## 📁 Repository Structure

```
GPT-PANELIN-V3.3/
├── README.md                                    # This file
├── LICENSE                                      # Repository license
│
├── Instrucciones GPT.rtf                        # Main GPT system instructions (v3.1)
├── Panelin_GPT_config.json                      # Complete GPT configuration (v2.3)
│
├── KNOWLEDGE BASE - LEVEL 1 (Master Sources)
│   ├── BMC_Base_Conocimiento_GPT-2.json         # PRIMARY - Panel prices, formulas, specs
│   ├── accessories_catalog.json                  # 70+ accessories with real prices
│   ├── bom_rules.json                           # Parametric BOM rules (6 systems)
│   ├── bromyros_pricing_gpt_optimized.json      # Fast product lookups
│   └── shopify_catalog_v1.json                  # Product descriptions & images
│
├── KNOWLEDGE BASE - LEVEL 2-3 (Validation & Dynamic)
│   ├── BMC_Base_Unificada_v4.json               # Cross-reference validation
│   └── panelin_truth_bmcuruguay_web_only_v2.json # Web pricing snapshot
│
├── DOCUMENTATION (Guides & Processes)
│   ├── PANELIN_KNOWLEDGE_BASE_GUIDE.md          # KB hierarchy & usage guide
│   ├── PANELIN_QUOTATION_PROCESS.md             # 5-phase quotation workflow
│   ├── PANELIN_TRAINING_GUIDE.md                # Sales evaluation & training
│   ├── GPT_INSTRUCTIONS_PRICING.md              # Fast pricing lookups guide
│   ├── GPT_PDF_INSTRUCTIONS.md                  # PDF generation workflow
│   └── GPT_OPTIMIZATION_ANALYSIS.md             # System analysis & improvements
│
├── AUTO-BOOT SYSTEM (NEW in v3.3)
│   ├── GPT_BOOT_INSTRUCTIONS_COMPACT.md         # Ready-to-use boot directive
│   ├── GPT_BOOT_IMPLEMENTATION_GUIDE.md         # Detailed deployment guide
│   ├── GPT_SYSTEM_PROMPT_AUTOBOOT.md            # Complete technical specification
│   └── GPT_BOOT_QUICK_REFERENCE.md              # Quick reference card
│
├── PDF GENERATION MODULE (NEW in v3.3)
│   ├── panelin_reports/__init__.py              # Package initialization
│   ├── panelin_reports/pdf_generator.py         # Enhanced PDF generator v2.0
│   ├── panelin_reports/pdf_styles.py            # BMC branding and styles
│   ├── panelin_reports/test_pdf_generation.py   # Testing suite
│   └── panelin_reports/assets/bmc_logo.png      # BMC logo for PDFs
│
├── DATA FILES
│   ├── normalized_full_cleaned.csv              # Raw product data (515 rows)
│   ├── perfileria_index.json                    # Profile product index
│   └── quotation_calculator_v3.py               # Python calculation engine
│
└── ASSETS
    └── bmc_logo.png                             # BMC Uruguay logo for PDFs
```

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

---

## 🚀 Installation & Deployment

### Quick Start

**🚀 For fast deployment, we provide automated helper tools:**

```bash
# Step 1: Validate all required files exist
python validate_gpt_files.py

# Step 2: Package files for easy upload
python package_gpt_files.py

# Step 3: Follow instructions in GPT_Upload_Package/
```

See [QUICK_START_GPT_UPLOAD.md](QUICK_START_GPT_UPLOAD.md) for streamlined deployment guide, or [GPT_UPLOAD_CHECKLIST.md](GPT_UPLOAD_CHECKLIST.md) for comprehensive instructions.

### Prerequisites

- OpenAI GPT Builder account
- Access to OpenAI Custom GPTs (ChatGPT Plus or Enterprise)
- All knowledge base files from this repository
- Python 3.7+ (for helper scripts)

### Deployment Steps

#### 1. Prepare Knowledge Base Files

**Option A: Use the Helper Scripts (Recommended)**

Run the packaging script to organize all files:
```bash
python package_gpt_files.py
```

This creates `GPT_Upload_Package/` with files organized by upload phase. Each phase includes an INSTRUCTIONS.txt file.

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
Run `python validate_gpt_files.py` to verify all files exist and are valid before upload.

#### 2. Configure GPT in OpenAI

1. Go to OpenAI GPT Builder: https://chat.openai.com/gpts/editor
2. Create new GPT or edit existing "Panelin 3.3"
3. **Configure basic info:**
   - Name: `Panelin 3.3`
   - Description: Use description from [Panelin_GPT_config.json](Panelin_GPT_config.json)
   - Profile image: Upload `bmc_logo.png` (optional)

4. **Configure instructions:**
   - **NEW in v3.3:** For automatic file indexing at session start, prepend `GPT_BOOT_INSTRUCTIONS_COMPACT.md` to the instructions
   - Then copy full instructions from `Instrucciones GPT.rtf`
   - OR use the instructions section from `Panelin_GPT_config.json`
   - See [GPT_BOOT_IMPLEMENTATION_GUIDE.md](GPT_BOOT_IMPLEMENTATION_GUIDE.md) for detailed auto-boot setup

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
| [GPT_PDF_INSTRUCTIONS.md](GPT_PDF_INSTRUCTIONS.md) | PDF generation workflow and requirements | 1.0 |
| [GPT_OPTIMIZATION_ANALYSIS.md](GPT_OPTIMIZATION_ANALYSIS.md) | System analysis and improvement plan | 1.0 |

### API Documentation

The API schema is embedded in the GPT Actions configuration. Key endpoints:
- Health checks: `/health`, `/ready`
- Quotations: `/calculate_quote`
- Product search: `/find_products`, `/product_price`
- Availability: `/check_availability`

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

### v3.3 / KB v7.0 / PDF Template v2.0 (2026-02-10) - Current

**Major Features:**
- ✅ **Enhanced PDF Generation Template v2.0** (from PR #215)
  - Professional BMC logo header with 2-column layout
  - Styled tables with alternating row colors (#EDEDED header, #FAFAFA rows)
  - Right-aligned numeric columns for better readability
  - Formatted comments section with per-line bold/red styling
  - Bank transfer footer with grid/borders
  - 1-page optimization (shrinks comments before other content)
  - ReportLab-based implementation

**New Module:**
- `panelin_reports/` - Complete PDF generation package
  - `pdf_generator.py` - Enhanced PDF generator v2.0
  - `pdf_styles.py` - BMC branding and style definitions
  - `test_pdf_generation.py` - Comprehensive testing suite

**Updates:**
- All existing v3.2 features retained
- PDF generation now matches official BMC quotation template
- Enhanced professional presentation for client delivery
- Automated testing suite with 5 test cases

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

This project is proprietary and confidential. All rights reserved to BMC Uruguay.

**Restrictions:**
- ❌ No public distribution
- ❌ No commercial use without authorization
- ❌ No modification without approval
- ❌ Authorized users only

For licensing inquiries, contact: [BMC Uruguay](https://bmcuruguay.com.uy)

---

## 🔗 Links & Resources

- **Official Website**: https://bmcuruguay.com.uy
- **API Base URL**: https://panelin-api-642127786762.us-central1.run.app
- **OpenAI GPT Platform**: https://chat.openai.com/gpts

---

## 📞 Support & Contact

For technical support or questions about this GPT configuration:

1. **Check documentation first**: Most questions are answered in the guides
2. **Review troubleshooting**: See [PANELIN_KNOWLEDGE_BASE_GUIDE.md](PANELIN_KNOWLEDGE_BASE_GUIDE.md) § Troubleshooting
3. **Test in isolation**: Verify if the issue is with KB data or GPT instructions
4. **Contact administrators**: Provide detailed information and context

---

**Version:** 3.3  
**Knowledge Base Version:** 7.0  
**PDF Template Version:** 2.0  
**Last Updated:** 2026-02-10  
**Maintained by:** BMC Uruguay Development Team  

---

*This README provides complete documentation for deploying and operating the Panelin 3.3 GPT. For detailed technical specifications, consult the individual documentation files referenced throughout this document.* 
