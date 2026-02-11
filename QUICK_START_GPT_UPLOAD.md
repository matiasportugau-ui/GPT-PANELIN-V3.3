# 🚀 Quick Start: Uploading Files to GPT

This is a simplified guide for quickly uploading all required files to your OpenAI GPT configuration for Panelin 3.3.

## ⚡ Fast Track (3 Steps)

### Step 1: Validate Your Files (1 minute)
```bash
python validate_gpt_files.py
```

This checks that all 21 required files exist and are valid.

### Step 2: Package Your Files (1 minute)
```bash
python package_gpt_files.py
```

This creates an organized folder `GPT_Upload_Package/` with files sorted by upload phase.

### Step 3: Upload to GPT (10-15 minutes)
1. Open: https://chat.openai.com/gpts/editor
2. Create or edit your "Panelin 3.3" GPT
3. Navigate to `GPT_Upload_Package/` folder
4. Upload phases in order:
   - `Phase_1_Master_KB/` → **PAUSE 2-3 min**
   - `Phase_2_Optimized_Lookups/` → **PAUSE 2 min**
   - `Phase_3_Validation/` → **PAUSE 2 min**
   - `Phase_4_Documentation/` → **PAUSE 2 min**
   - `Phase_5_Supporting/` → **PAUSE 2 min**
   - `Phase_6_Assets/` → **Done!**

Each phase has an `INSTRUCTIONS.txt` file with specific guidance.

---

## 📂 What Files Are Uploaded?

### Essential Knowledge Base (Phase 1-3)
- **BMC_Base_Conocimiento_GPT-2.json** - Main pricing & formulas
- **accessories_catalog.json** - 70+ accessories with prices
- **bom_rules.json** - BOM calculation rules
- **bromyros_pricing_master.json** - BROMYROS master pricing
- **bromyros_pricing_gpt_optimized.json** - Fast product lookups
- **shopify_catalog_v1.json** - Product catalog
- **shopify_catalog_index_v1.csv** - Catalog index for lookups
- Plus validation and dynamic data files

### Documentation (Phase 4-5)
- All markdown guides (quotation process, training, pricing, PDF generation)
- README.md with complete system documentation
- GPT configuration files

### Assets (Phase 6)
- **bmc_logo.png** - BMC Uruguay logo for PDFs

---

## ⚙️ GPT Configuration

After uploading files, configure the GPT:

### Basic Settings
- **Name**: Panelin 3.3
- **Description**: Copy from `Panelin_GPT_config.json` → `description` field

### Instructions
Copy from: `Instrucciones GPT.rtf` or `Panelin_GPT_config.json` → `instructions` field

### Capabilities (Enable All)
- ✅ Web Browsing
- ✅ Code Interpreter (CRITICAL for PDF generation)
- ✅ Canvas
- ✅ Image Generation

### Conversation Starters
Add these 6 starters:
```
💡 Necesito una cotización para Isopanel EPS 50mm
📄 Genera un PDF para cotización de ISODEC 100mm
🔍 ¿Qué diferencia hay entre ISOROOF PIR y EPS?
📊 Evalúa mi conocimiento sobre sistemas de fijación
⚡ ¿Cuánto ahorro energético tiene el panel de 150mm vs 100mm?
🏗️ Necesito asesoramiento para un techo de 8 metros de luz
```

---

## 🔌 API / Actions Connection (OpenAI GPT Builder)

To enable real API calls (e.g. `/find_products`) from your GPT:

1. Go to **GPT Builder → Actions**
2. Import schema from `Esquema json.rtf`
3. Configure auth:
   - Type: **API Key**
   - Header: `X-API-Key`
   - Value: your Wolf API key
4. Save and test endpoints:
   - `GET /health` (should return 200)
   - `POST /find_products` (requires key)

Optional local smoke test before configuring Builder:

```bash
./test_panelin_api_connection.sh
# with key:
WOLF_API_KEY=your_key ./test_panelin_api_connection.sh
```

---

## ✅ Verification Checklist

After upload, test these queries:

- [ ] "¿Cuánto cuesta ISODEC 100mm?" → Should return price from Level 1
- [ ] "¿Cuánto cuesta un gotero frontal?" → Should return accessory price
- [ ] Request complete quotation → Should include panels + accessories + fixings
- [ ] "Genera un PDF" → Code Interpreter should activate
- [ ] Request technical diagram → Image Generation should work

---

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| **Validation fails** | Check missing files, fix JSON syntax errors |
| **Upload fails** | Wait 1-2 minutes, try again |
| **GPT gives wrong prices** | Check Phase 1 files uploaded first |
| **PDF generation fails** | Verify Code Interpreter enabled, logo uploaded |
| **GPT can't find data** | Wait 5 minutes for reindexing, try again |

---

## 📚 Detailed Documentation

For more detailed instructions, see:
- **GPT_UPLOAD_CHECKLIST.md** - Complete upload guide with troubleshooting
- **README.md** - Full system documentation
- **Panelin_GPT_config.json** - Complete configuration reference

---

## 🎯 Success Criteria

Your GPT is ready when:
- ✅ All 21 files uploaded successfully
- ✅ Code Interpreter enabled
- ✅ Knowledge base queries return correct prices
- ✅ PDF generation works
- ✅ Quotations include complete BOM (panels + accessories + fixings)

---

**Version**: 1.0  
**Last Updated**: 2026-02-10  
**Compatible with**: GPT-PANELIN v3.3

**Need Help?** Refer to the detailed `GPT_UPLOAD_CHECKLIST.md` for comprehensive instructions.
