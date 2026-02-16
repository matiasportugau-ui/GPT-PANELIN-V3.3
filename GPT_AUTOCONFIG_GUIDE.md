# GPT Autoconfiguration Guide

## ⚠️ Important Notice

**This tool does NOT automatically deploy to OpenAI.** It generates configuration files and deployment guides, but you must **manually upload files** to OpenAI GPT Builder.

**Why?** OpenAI does not provide a public API for Custom GPT management. All file uploads and configuration must be done through the web interface at https://chat.openai.com/gpts/editor.

**What this means:**
- The tool prepares everything (1 minute)
- You manually deploy to OpenAI (10-15 minutes)
- Total time: ~15-20 minutes

See [GPT_AUTOCONFIG_FAQ.md](GPT_AUTOCONFIG_FAQ.md) for detailed Q&A.

---

## Overview

The GPT Autoconfiguration Tool is a comprehensive solution for generating, validating, and preparing complete GPT configurations for manual deployment to OpenAI. It automates the preparation process but not the deployment itself.

## Features

✅ **Automatic Configuration Generation** - Generates complete GPT config from base files
✅ **Interactive Approval Workflow** - Review and approve changes before deployment
✅ **File Validation** - Validates all 21 required knowledge base files
✅ **OpenAI-Compatible Export** - Generates JSON format ready for OpenAI import
✅ **Deployment Guide** - Creates comprehensive step-by-step deployment instructions
✅ **Phase-Based Upload Sequence** - Organizes files by upload priority with pause times
✅ **Quick Reference** - One-page summary for fast deployment

---

## Quick Start

### 1. Run Autoconfiguration

```bash
python autoconfig_gpt.py
```

### 2. Review Configuration

The tool will:
- Load base configuration from `Panelin_GPT_config.json`
- Validate all required files (21 files total)
- Display configuration summary
- Request your approval

### 3. Approve Changes

Review the displayed configuration and type `yes` to approve:

```
Do you approve this configuration? (yes/no): yes
```

### 4. Deploy to OpenAI

Navigate to the generated package:

```bash
cd GPT_Deploy_Package
```

Read the deployment guide:

```bash
cat DEPLOYMENT_GUIDE.md
```

Deploy at: https://chat.openai.com/gpts/editor

---

## Generated Files

After running autoconfiguration, the following files are created in `GPT_Deploy_Package/`:

### 1. `gpt_deployment_config.json`
**Complete deployment configuration**
- Full GPT configuration
- File upload sequence with phases
- Deployment instructions
- Verification queries
- Capabilities and settings

**Use case:** Reference for all deployment details

### 2. `openai_gpt_config.json`
**OpenAI-compatible format**
- Simplified configuration for OpenAI GPT Builder
- Ready to import/paste into OpenAI interface
- Contains: name, description, instructions, starters, capabilities

**Use case:** Direct import into OpenAI (if import feature available) or copy-paste

### 3. `DEPLOYMENT_GUIDE.md`
**Comprehensive deployment instructions**
- Step-by-step deployment process
- File upload sequence with details
- Pause times between phases
- Verification queries
- Troubleshooting guide

**Use case:** Follow this guide to deploy your GPT

### 4. `QUICK_REFERENCE.txt`
**One-page quick reference**
- Essential deployment information
- Upload order summary
- Verification checklist
- Quick troubleshooting

**Use case:** Quick lookup during deployment

### 5. `validation_report.json`
**File validation results**
- List of all required files
- File sizes and locations
- Missing files report
- Total package size

**Use case:** Verify file integrity before deployment

---

## Deployment Process

### Step 1: Pre-Deployment Validation

The tool automatically validates:
- ✅ All 21 required files exist
- ✅ File sizes are reasonable
- ✅ JSON files are valid
- ✅ Configuration is complete

If files are missing, you'll see:
```
⚠️  Missing 2 files:
   - shopify_catalog_v1.json
   - bmc_logo.png
```

Fix missing files and run again.

### Step 2: Configuration Review

Review the configuration summary:

```
GPT AUTOCONFIGURATION SUMMARY
================================================================================

GPT Name: Panelin - BMC Assistant Pro
Version: 2.5 Canonical - Full Capabilities
KB Version: 7.0
Generated: 2026-02-16T22:45:00.000000

CAPABILITIES:
  - Web Browsing: ✅ Enabled
  - Code Interpreter: ✅ Enabled
  - Image Generation: ✅ Enabled
  - Canvas: ✅ Enabled

CONVERSATION STARTERS:
  1. 💡 Necesito una cotización para Isopanel EPS 50mm
  2. 📄 Genera un PDF para cotización de ISODEC 100mm
  ...

FILE UPLOAD SEQUENCE:
  Phase 1: Master Knowledge Base [CRITICAL]
  ...
```

### Step 3: Approve Configuration

Type `yes` to approve:
```
Do you approve this configuration? (yes/no): yes
✅ Configuration APPROVED
```

### Step 4: Deploy to OpenAI

Follow the generated `DEPLOYMENT_GUIDE.md`:

1. Go to https://chat.openai.com/gpts/editor
2. Click "Create" to start new GPT
3. Configure basic settings (name, description)
4. Enable all capabilities
5. Paste instructions
6. Add conversation starters
7. Upload files in phase order with pauses
8. Test with verification queries
9. Publish

---

## File Upload Sequence

**CRITICAL:** Files must be uploaded in this exact order with pauses between phases.

### Phase 1: Master Knowledge Base [CRITICAL]
**Must be uploaded first to establish source of truth**

Files:
- `BMC_Base_Conocimiento_GPT-2.json` (Primary pricing & formulas)
- `bromyros_pricing_master.json` (BROMYROS master pricing)
- `accessories_catalog.json` (70+ accessories with prices)
- `bom_rules.json` (Parametric BOM rules)

⏱️ **PAUSE 2-3 minutes** after uploading Phase 1

### Phase 2: Optimized Lookups
**Fast lookup indices and catalogs**

Files:
- `bromyros_pricing_gpt_optimized.json`
- `shopify_catalog_v1.json`
- `shopify_catalog_index_v1.csv`

⏱️ **PAUSE 2 minutes** after uploading Phase 2

### Phase 3: Validation & Dynamic Data
**Cross-reference and web pricing**

Files:
- `BMC_Base_Unificada_v4.json`
- `panelin_truth_bmcuruguay_web_only_v2.json`

⏱️ **PAUSE 2 minutes** after uploading Phase 3

### Phase 4: Documentation & Guides
**Process guides and documentation**

Files:
- `Aleros -2.rtf`
- `panelin_context_consolidacion_sin_backend.md`
- `PANELIN_KNOWLEDGE_BASE_GUIDE.md`
- `PANELIN_QUOTATION_PROCESS.md`
- `PANELIN_TRAINING_GUIDE.md`
- `GPT_INSTRUCTIONS_PRICING.md`
- `GPT_PDF_INSTRUCTIONS.md`
- `GPT_OPTIMIZATION_ANALYSIS.md`
- `README.md`

⏱️ **PAUSE 2 minutes** after uploading Phase 4

### Phase 5: Supporting Files
**Additional context and reference**

Files:
- `Instrucciones GPT.rtf`
- `Panelin_GPT_config.json`

⏱️ **PAUSE 2 minutes** after uploading Phase 5

### Phase 6: Assets
**Logo and brand assets**

Files:
- `bmc_logo.png`

✅ **Complete!**

---

## Verification Queries

After deployment, test the GPT with these queries:

1. **Pricing Test:**
   - Query: "¿Cuánto cuesta ISODEC 100mm?"
   - Expected: Should return price from Level 1 KB

2. **Accessories Test:**
   - Query: "¿Cuánto cuesta un gotero frontal?"
   - Expected: Should return accessory price from catalog

3. **Quotation Test:**
   - Query: "Necesito una cotización para Isopanel EPS 50mm de 5x10 metros"
   - Expected: Complete quotation with panels + accessories + fixings

4. **PDF Test:**
   - Query: "Genera un PDF para una cotización"
   - Expected: Code Interpreter activates and generates PDF

---

## Configuration Details

### GPT Name
**Default:** Panelin - BMC Assistant Pro

### Description
Complete technical sales assistant for BMC Uruguay panel systems with:
- Professional quotation generation
- Complete BOM calculation
- PDF generation with branding
- Technical validation
- Sales evaluation and training

### Capabilities

#### Web Browsing ✅
- **Enabled:** Yes
- **Policy:** Non-authoritative (KB is always priority)
- **Use:** General concepts, public standards, web verification

#### Code Interpreter ✅
- **Enabled:** Yes (CRITICAL)
- **Use:** PDF generation, CSV operations, batch calculations
- **Required for:** All PDF quotation features

#### Image Generation ✅
- **Enabled:** Yes
- **Use:** Educational diagrams and infographics
- **Policy:** Never claim images are real photos

#### Canvas ✅
- **Enabled:** Yes
- **Use:** Client-ready documents, training materials, proposals

### Knowledge Base

**Version:** 7.0
**Last Updated:** 2026-02-06

**Hierarchy:**
1. **Level 1 - Master KB** (highest priority)
2. **Level 1.2 - Accessories**
3. **Level 1.3 - BOM Rules**
4. **Level 1.5 - Pricing Optimized**
5. **Level 1.6 - Catalog**
6. **Level 2 - Validation**
7. **Level 3 - Dynamic**
8. **Level 4 - Support**

**Source of Truth:** Always use Level 1 for pricing and calculations

---

## Troubleshooting

### Issue: Script fails with "FileNotFoundError"

**Cause:** Base config file not found

**Solution:**
```bash
# Verify Panelin_GPT_config.json exists
ls -la Panelin_GPT_config.json

# Run from repository root
cd /path/to/GPT-PANELIN-V3.3
python autoconfig_gpt.py
```

### Issue: Missing files warning

**Cause:** Some required files are not in the repository

**Solution:**
1. Check which files are missing in the output
2. Locate or regenerate missing files
3. Run autoconfig again

### Issue: Configuration not approved

**Cause:** User typed "no" or invalid response

**Solution:**
- Review configuration summary carefully
- Type "yes" to approve
- Type "no" to cancel

### Issue: GPT gives wrong prices after deployment

**Cause:** Files uploaded in wrong order

**Solution:**
1. Delete all uploaded files in OpenAI GPT Builder
2. Re-upload files in exact phase order
3. Ensure Phase 1 files are uploaded FIRST
4. Pause between phases as indicated

### Issue: PDF generation fails

**Cause:** Code Interpreter not enabled or logo not uploaded

**Solution:**
1. Verify Code Interpreter is enabled in GPT settings
2. Verify `bmc_logo.png` was uploaded in Phase 6
3. Test PDF generation again

### Issue: GPT can't find information

**Cause:** Files not yet reindexed by OpenAI

**Solution:**
- Wait 5 minutes after final file upload
- Try query again
- If still failing, check file upload sequence

---

## Advanced Usage

### Custom Configuration

To modify the base configuration before autoconfiguration:

1. Edit `Panelin_GPT_config.json`
2. Make changes to:
   - Name, description
   - Instructions
   - Conversation starters
   - Capabilities
3. Run `python autoconfig_gpt.py`

### Automated Deployment (CI/CD)

For automated deployment (non-interactive):

```bash
# Skip approval prompt (not recommended for production)
# Modify script to add --auto-approve flag if needed
```

### Re-running Autoconfiguration

To regenerate deployment package:

1. Delete old package:
   ```bash
   rm -rf GPT_Deploy_Package
   ```

2. Run autoconfig again:
   ```bash
   python autoconfig_gpt.py
   ```

### Version Control

The `GPT_Deploy_Package/` directory should NOT be committed to git:

```bash
# Add to .gitignore
echo "GPT_Deploy_Package/" >> .gitignore
```

---

## Integration with Existing Tools

### With `validate_gpt_files.py`

Run validation before autoconfiguration:

```bash
# Validate files first
python validate_gpt_files.py

# If validation passes, run autoconfig
python autoconfig_gpt.py
```

### With `package_gpt_files.py`

The autoconfig tool replaces `package_gpt_files.py` for deployment scenarios. Use `package_gpt_files.py` for organizing files into physical directories for manual upload.

---

## Best Practices

### 1. Always Validate First

Run validation before deployment:
```bash
python validate_gpt_files.py
```

### 2. Review Configuration Carefully

Don't skip the approval step. Review:
- GPT name and description
- Instructions version
- Capabilities settings
- File upload sequence

### 3. Follow Upload Order Strictly

Phase 1 files MUST be uploaded first. Never skip phases or change order.

### 4. Pause Between Phases

The pause times are critical for GPT reindexing:
- Phase 1: 2-3 minutes
- Other phases: 2 minutes

### 5. Test After Deployment

Always run verification queries to ensure:
- Pricing is correct
- Accessories are found
- Quotations are complete
- PDF generation works

### 6. Keep Backups

Before deploying updates to existing GPT:
1. Export current GPT configuration
2. Save as backup
3. Deploy new configuration
4. Verify everything works
5. If issues, restore from backup

### 7. Document Changes

Track what changed between deployments:
- Configuration version
- KB version
- New features added
- Files added/removed

---

## FAQ

### Q: Can I deploy to multiple GPT instances?

**A:** Yes. Run autoconfig once, then use the generated package to deploy to multiple GPT instances (e.g., development, staging, production).

### Q: How do I update an existing GPT?

**A:** 
1. Run autoconfig to generate new package
2. In OpenAI GPT Builder, open existing GPT
3. Update instructions and configuration
4. Upload new/updated files
5. Test thoroughly

### Q: What if I want to change only the instructions?

**A:** 
1. Edit `Panelin_GPT_config.json` → `instructions` field
2. Run `python autoconfig_gpt.py`
3. In OpenAI, update only the instructions field
4. No need to re-upload files

### Q: Can I skip some files?

**A:** Phase 1 files are CRITICAL and must be uploaded. Phase 3-6 files are optional but recommended for full functionality.

### Q: How long does deployment take?

**A:** 
- Autoconfiguration: 1-2 minutes
- Manual deployment to OpenAI: 10-15 minutes
- Total: ~15-20 minutes

### Q: What's the difference from manual upload?

**A:** 
- **Autoconfiguration:** Automated validation, organized package, deployment guide
- **Manual:** Follow checklist step-by-step, more error-prone

---

## Support

### Getting Help

1. **Check DEPLOYMENT_GUIDE.md** in generated package
2. **Review QUICK_REFERENCE.txt** for fast lookup
3. **Check validation_report.json** for file issues
4. **See Troubleshooting section** above

### Reporting Issues

If you encounter issues:
1. Capture error messages
2. Check which step failed
3. Review validation report
4. Contact development team with details

---

## Version History

### Version 1.0 (2026-02-16)
- Initial release
- Complete autoconfiguration workflow
- Interactive approval process
- OpenAI-compatible export
- Comprehensive deployment guide
- File validation and reporting

---

## Summary

The GPT Autoconfiguration Tool streamlines the deployment of Panelin GPT by:

1. **Validating** all required files
2. **Generating** complete deployment configuration
3. **Requesting** user approval
4. **Creating** comprehensive deployment package
5. **Providing** step-by-step deployment guide

Use this tool every time you need to:
- Deploy a NEW GPT instance
- Update existing GPT configuration
- Validate GPT deployment readiness
- Generate deployment documentation

**Next Steps:**
1. Run `python autoconfig_gpt.py`
2. Review and approve configuration
3. Follow `DEPLOYMENT_GUIDE.md` to deploy
4. Test with verification queries
5. Publish your GPT!

---

**Document Version:** 1.0
**Last Updated:** 2026-02-16
**Compatible with:** GPT-PANELIN v3.3, KB v7.0
**Status:** ✅ Ready for Use
