# GPT Upload Checklist - Panelin 3.3

This document provides a comprehensive checklist and guide for uploading all required files to the OpenAI GPT configuration.

## 📋 Quick Start

**Total Files to Upload**: 21 files  
**Total Size**: Approximately 1.3 MB  
**Upload Time**: 10-15 minutes (with pauses for reindexing)

---

## 🎯 Upload Order (CRITICAL - Follow This Sequence)

Upload files in this specific order to maintain the knowledge base hierarchy:

### Phase 1: Master Knowledge Base (Level 1) - UPLOAD FIRST
These are the most important files and must be uploaded first to establish the source of truth.

- [ ] **1. BMC_Base_Conocimiento_GPT-2.json** (PRIMARY - Panel prices, formulas, specs)
- [ ] **2. bromyros_pricing_master.json** (BROMYROS master pricing source)
- [ ] **3. accessories_catalog.json** (70+ accessories with real prices)
- [ ] **4. bom_rules.json** (Parametric BOM rules for 6 construction systems)

⏱️ **PAUSE 2-3 minutes** after Phase 1 for GPT to reindex

### Phase 2: Optimized Lookups (Level 1.5-1.6)
Fast lookup indices and product catalogs.

- [ ] **5. bromyros_pricing_gpt_optimized.json** (Fast product lookups)
- [ ] **6. shopify_catalog_v1.json** (Product descriptions & images - NOT for pricing)
- [ ] **7. shopify_catalog_index_v1.csv** (Catalog index for fast lookups)

⏱️ **PAUSE 2 minutes** after Phase 2

### Phase 3: Validation & Dynamic Data (Level 2-3)
Cross-reference and web pricing snapshots.

- [ ] **8. BMC_Base_Unificada_v4.json** (Cross-reference validation)
- [ ] **9. panelin_truth_bmcuruguay_web_only_v2.json** (Web pricing snapshot)

⏱️ **PAUSE 2 minutes** after Phase 3

### Phase 4: Documentation & Guides (Level 4)
Process guides and usage documentation.

- [ ] **10. Aleros -2.rtf** (Technical rules for aleros/voladizos)
- [ ] **11. panelin_context_consolidacion_sin_backend.md** (SOP commands and context flow)
- [ ] **12. PANELIN_KNOWLEDGE_BASE_GUIDE.md** (KB hierarchy & usage rules)
- [ ] **13. PANELIN_QUOTATION_PROCESS.md** (5-phase quotation workflow)
- [ ] **14. PANELIN_TRAINING_GUIDE.md** (Sales evaluation & training)
- [ ] **15. GPT_INSTRUCTIONS_PRICING.md** (Fast pricing lookups guide)
- [ ] **16. GPT_PDF_INSTRUCTIONS.md** (PDF generation workflow)
- [ ] **17. GPT_OPTIMIZATION_ANALYSIS.md** (System analysis)
- [ ] **18. README.md** (Complete project overview)

⏱️ **PAUSE 2 minutes** after Phase 4

### Phase 5: Supporting Files
Additional context and reference files.

- [ ] **19. Instrucciones GPT.rtf** (Full GPT system instructions - Optional, can paste in instructions field)
- [ ] **20. Panelin_GPT_config.json** (Complete GPT configuration reference)

⏱️ **PAUSE 2 minutes** after Phase 5

### Phase 6: Assets
Logo and brand assets.

- [ ] **21. bmc_logo.png** (BMC Uruguay logo for PDFs)

---

## 📊 File Details & Descriptions

### Level 1 - Master Knowledge Base (CRITICAL)

#### 1. BMC_Base_Conocimiento_GPT-2.json
- **Purpose**: Primary source of truth for all panel pricing, formulas, and specifications
- **Size**: ~500 KB
- **Contains**:
  - Complete panel products (ISODEC, ISOPANEL, ISOROOF, ISOWALL, ISOFRIG)
  - Validated Shopify pricing (price_per_m2)
  - Exact quotation formulas v6.0
  - Technical specifications (load-bearing, thermal coefficients)
  - Business rules (IVA 22%, shipping costs)
- **Usage**: ALWAYS use for panel pricing and calculations

#### 2. accessories_catalog.json
- **Purpose**: Complete accessories pricing catalog (NEW in v7.0)
- **Size**: ~150 KB
- **Contains**:
  - 70+ accessory items with real prices (IVA included)
  - Gutters, babetas, ridge caps, channels, profiles
  - Fixings (rods, nuts, screws, washers, PVC turtles)
  - Sealants (silicone, butyl tape)
  - Multi-supplier support (BROMYROS, MONTFRIO, BECAM)
- **Usage**: ALWAYS use for accessory pricing in quotations

#### 3. bom_rules.json
- **Purpose**: Parametric BOM calculation rules (NEW in v7.0)
- **Size**: ~100 KB
- **Contains**:
  - Formulas for 6 construction systems
  - Unified load-bearing capacity table (autoportancia)
  - SKU-to-thickness mapping
  - Detailed fixing kits by structure type
  - Complete calculation examples
- **Usage**: Use for BOM calculations and autoportancia validation

### Level 1.5 - Optimized Lookups

#### 4. bromyros_pricing_gpt_optimized.json
- **Purpose**: Fast product lookups with multi-level indexing
- **Size**: ~400 KB
- **Contains**:
  - Index by SKU (direct product access)
  - Index by familia (browse related products)
  - Index by subfamilia (filter by EPS/PIR)
  - Familia groups (complete family context)
- **Usage**: Use for fast product searches and lookups

#### 5. shopify_catalog_v1.json
- **Purpose**: Product catalog for presentation
- **Size**: ~800 KB
- **Contains**:
  - Product descriptions
  - Variant information
  - Product images URLs
- **⚠️ WARNING**: DO NOT use for pricing - use Level 1 instead

### Level 2-3 - Validation & Dynamic

#### 6. BMC_Base_Unificada_v4.json
- **Purpose**: Cross-reference validation
- **Size**: ~300 KB
- **Usage**: Detect inconsistencies, NOT for direct responses

#### 7. panelin_truth_bmcuruguay_web_only_v2.json
- **Purpose**: Web pricing snapshot (dynamic data)
- **Size**: ~200 KB
- **Usage**: Validate against Level 1, report discrepancies

### Level 4 - Documentation

#### 8-14. Documentation Files
All markdown documentation files that guide the GPT's behavior:
- Knowledge base hierarchy and usage
- Quotation processes and workflows
- Training and evaluation procedures
- PDF generation instructions
- Optimization analysis

### Supporting Files

#### 15. Instrucciones GPT.rtf
- **Purpose**: Full system instructions for the GPT
- **Size**: ~50 KB
- **Note**: Can be pasted directly in GPT Builder instructions field instead of uploading

#### 16. Panelin_GPT_config.json
- **Purpose**: Complete GPT configuration reference
- **Size**: ~30 KB
- **Note**: Reference file, not strictly required to upload

#### 17. bmc_logo.png
- **Purpose**: BMC Uruguay logo for PDF headers
- **Size**: ~48 KB
- **Usage**: Used by Code Interpreter for PDF generation

---

## 🚀 Step-by-Step Upload Process

### Step 1: Access GPT Builder
1. Go to: https://chat.openai.com/gpts/editor
2. Either create new GPT or edit existing "Panelin 3.3"

### Step 2: Configure Basic Information
1. **Name**: `Panelin 3.3`
2. **Description**: Copy from `Panelin_GPT_config.json` → `description` field
3. **Profile Image**: Upload `bmc_logo.png` (optional)

### Step 3: Configure Instructions
**Option A**: Upload `Instrucciones GPT.rtf` as a knowledge file  
**Option B**: Copy instructions from `Panelin_GPT_config.json` → `instructions` field and paste in Instructions box

### Step 4: Enable Capabilities
In GPT Builder, enable these capabilities:
- ✅ **Web Browsing** (mark as non-authoritative in instructions)
- ✅ **Canvas** (for client-ready documents)
- ✅ **Image Generation** (for educational diagrams)
- ✅ **Code Interpreter** (CRITICAL for PDF generation)

### Step 5: Upload Knowledge Base Files
Follow the upload order above (Phases 1-6), with pauses between phases.

**Important Notes:**
- Wait 2-3 minutes between phases for GPT to reindex
- Upload one file at a time (don't batch upload)
- Verify file size after upload (should match expected size)
- If upload fails, try again after 1 minute

### Step 6: Configure Conversation Starters
Add these 6 starters from `Panelin_GPT_config.json`:
```
💡 Necesito una cotización para Isopanel EPS 50mm
📄 Genera un PDF para cotización de ISODEC 100mm
🔍 ¿Qué diferencia hay entre ISOROOF PIR y EPS?
📊 Evalúa mi conocimiento sobre sistemas de fijación
⚡ ¿Cuánto ahorro energético tiene el panel de 150mm vs 100mm?
🏗️ Necesito asesoramiento para un techo de 8 metros de luz
```

### Step 7: Configure Actions (API Integration)
If using the Panelin Wolf API:
1. Go to "Actions" section
2. Import OpenAPI schema from `Esquema json.rtf`
3. Configure API Key authentication (header: `X-API-Key`)
4. Test endpoints: `/health`, `/find_products`

### Step 8: Verification
Test the GPT with these queries:

**Knowledge Base Test:**
- "¿Cuánto cuesta ISODEC 100mm?" → Should return price from Level 1
- "¿Cuánto cuesta un gotero frontal?" → Should return price from accessories catalog
- Request complete quotation with BOM → Should include all accessories

**Capabilities Test:**
- Request PDF generation → Code Interpreter should activate
- Ask for technical diagram → Image Generation should work
- Request formal quotation → Canvas should open

---

## ✅ Post-Upload Verification Checklist

After completing the upload, verify:

- [ ] GPT can find panel prices from `BMC_Base_Conocimiento_GPT-2.json`
- [ ] GPT can find accessory prices from `accessories_catalog.json`
- [ ] GPT uses correct formulas from KB (not inventing calculations)
- [ ] GPT validates autoportancia correctly
- [ ] Code Interpreter activates for PDF generation
- [ ] Canvas opens for formal documents
- [ ] Web Browsing is marked as non-authoritative
- [ ] IVA handling is correct (22% already included in prices)
- [ ] Derivation policy is enforced (internal only, not external installers)

---

## 🔧 Troubleshooting

### Issue: File upload fails
**Solution**: Wait 1-2 minutes and try again. Check file size (max 512 MB per file).

### Issue: GPT gives wrong prices
**Solution**: Verify Level 1 files were uploaded first. Check upload order.

### Issue: GPT says "I don't have that information"
**Solution**: File may not have reindexed yet. Wait 5 minutes and try again.

### Issue: PDF generation fails
**Solution**: Verify Code Interpreter is enabled. Check that `bmc_logo.png` was uploaded.

### Issue: GPT uses external sources instead of KB
**Solution**: Reinforce in instructions that KB is authoritative. May need to rephrase instructions.

---

## 📦 Using the Helper Script

We've provided a validation script to check all files before upload:

```bash
python validate_gpt_files.py
```

This will:
- ✅ Verify all 21 required files exist
- ✅ Check file sizes are reasonable
- ✅ Validate JSON syntax
- ✅ Report any missing or invalid files
- ✅ Generate upload order list

---

## 🎓 Tips for Success

1. **Follow the upload order** - Level 1 must be uploaded first to establish hierarchy
2. **Pause between phases** - Give GPT time to reindex (2-3 minutes)
3. **Upload one file at a time** - Don't batch upload to avoid indexing conflicts
4. **Test after each phase** - Quick test to ensure files are accessible
5. **Keep a backup** - Save a copy of all files before uploading
6. **Document your configuration** - Note which files were uploaded and when
7. **Version control** - If updating, remove old file before uploading new version

---

## 📞 Support

If you encounter issues:
1. Check this document's troubleshooting section
2. Review `PANELIN_KNOWLEDGE_BASE_GUIDE.md` for detailed KB information
3. Verify file integrity with `validate_gpt_files.py`
4. Contact BMC Uruguay development team with detailed error information

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-10  
**Compatible with**: GPT-PANELIN v3.3, KB v7.0  
**Status**: ✅ Ready for Use

---

*This checklist ensures proper configuration and upload of all required files for the Panelin 3.3 GPT.*
