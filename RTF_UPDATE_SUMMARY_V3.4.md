# RTF Files Update Summary - Version 3.4

**Date:** 2026-02-14  
**Updated Files:** 2 RTF files  
**Version:** v3.1 → v3.4

---

## Overview

Updated two critical RTF documentation files to reflect the latest v3.4 development, specifically the Wolf API KB Write capabilities introduced in version 3.4.

---

## Files Updated

### 1. `Esquema json.rtf` - OpenAPI Schema

**Previous Version:** 2.0.0 (v3.1, 2026-02-07)  
**New Version:** 3.0.0 (v3.4, 2026-02-14)

#### Changes Made:

1. **Version Update**
   - Updated API version from `2.0.0` to `3.0.0`
   - Updated description to mention "KB Write capabilities" and "Write operations require password"

2. **New Schemas Added** (3 request schemas)
   ```
   - ConversationRequest: For persist_conversation endpoint
   - CorrectionRequest: For register_correction endpoint  
   - CustomerRequest: For save_customer endpoint
   ```

3. **New Endpoints Added** (4 endpoints)
   ```
   POST /kb/conversations      - persist_conversation (password required)
   POST /kb/corrections        - register_correction (password required)
   POST /kb/customers          - save_customer (password required)
   GET  /kb/customers?search=  - lookup_customer (no password required)
   ```

4. **Schema Details**

   **ConversationRequest:**
   - Required fields: `client_id`, `summary`, `password`
   - Optional: `quotation_ref`, `products_discussed`

   **CorrectionRequest:**
   - Required fields: `source_file`, `field_path`, `old_value`, `new_value`, `reason`, `password`
   - Optional: `reported_by`

   **CustomerRequest:**
   - Required fields: `name`, `phone`, `password`
   - Optional: `address`, `city`, `department`, `notes`

5. **Response Structures**
   - All POST endpoints return: `{status, [resource]_id}`
   - GET /kb/customers returns: `{customers: [array of customer objects]}`
   - Error responses (400, 403) reference JsonObject schema

6. **RTF Formatting**
   - ✅ All RTF formatting markers preserved (`\rtf1\ansi\ansicpg1252...`)
   - ✅ JSON escaping maintained (`\{`, `\}`, `\"`)
   - ✅ Line continuations preserved (`\`)

---

### 2. `Instrucciones GPT.rtf` - GPT Instructions

**Previous Version:** v3.1 (2026-02-07)  
**New Version:** v3.4 (2026-02-14)  
**Instructions Version:** 2.4 → 2.5

#### Changes Made:

1. **Header Update**
   ```
   OLD: Panelin BMC Assistant Pro v3.1
        v3.1 (2026-02-07) · BOM Completa + Validación Autoportancia

   NEW: Panelin BMC Assistant Pro v3.4
        v3.4 (2026-02-14) · Wolf API KB Write + BOM Completa + Validación Autoportancia
   ```

2. **Knowledge Base Hierarchy** (Section 4)
   - Added `NIVEL 1D ⭐ Wolf API KB Write` to the hierarchy
   - Updated description: "persistencia conversaciones, correcciones, clientes (V3.4 NUEVO)"

3. **Commands Section** (Section 9)
   - Added new commands:
     - `/guardar_conversacion` (V3.4 NUEVO)
     - `/guardar_cliente` (V3.4 NUEVO)
   - Added Wolf API v3.4 command section with 4 commands

4. **Capabilities Section** (Section 11)
   - Added Wolf API KB Write capability description
   - Noted password requirement for write operations
   - Noted that lookup_customer does NOT require password

5. **New Section 12: WOLF API - ESCRITURA EN KB (V3.4)**

   Complete new section covering:

   **Capacidades:**
   1. **PERSISTIR CONVERSACIONES** - POST /kb/conversations
      - Purpose: Save quotation summaries, technical consultations, and assessments
      - Data: `client_id, summary, quotation_ref, products_discussed, date`
      - ⚠️ REQUIERE CONTRASEÑA

   2. **REGISTRAR CORRECCIONES** - POST /kb/corrections
      - Purpose: Persist detected price, formula, or technical data corrections
      - Data: `source_file, field_path, old_value, new_value, reason, reported_by, date`
      - ⚠️ REQUIERE CONTRASEÑA

   3. **GUARDAR CLIENTES** - POST /kb/customers
      - Purpose: Store customer data for future quotations
      - Data: `name, phone, address, city, department, notes, last_interaction`
      - Validation: Uruguayan phone format (09XXXXXXX or +598XXXXXXXX)
      - ⚠️ REQUIERE CONTRASEÑA

   4. **BUSCAR CLIENTES** - GET /kb/customers?search={query}
      - Purpose: Retrieve existing customer data by name/phone/address
      - ✅ NO REQUIERE CONTRASEÑA (read-only)

   **REGLAS ESCRITURA:**
   - Before ANY POST operation: request KB Write password from user
   - If incorrect password: REJECT and DO NOT persist
   - GET operations (lookup_customer): DO NOT require password
   - Always inform client that data will be saved
   - Only persist relevant data for future quotations
   - NEVER store tokens, passwords, or secrets
   - Requires valid X-API-Key in header

   **USO:**
   - After formal quotation: offer to save summary
   - If customer exists in KB: auto-retrieve data
   - If KB error detected: register correction
   - Use `/checkpoint` to save long conversations

6. **Version History Update**
   ```
   OLD: FIN v3.1 (2026-02-07)
        Cambios V3.0→V3.1: Nueva validación autoportancia | ...

   NEW: FIN v3.4 (2026-02-14)
        Cambios V3.3→V3.4: Wolf API KB Write | 4 nuevos endpoints | Seguridad contraseña escritura | 
        Validación teléfono uruguayo | Persistencia clientes | Persistencia correcciones | Instrucciones 2.5.
        
        Cambios V3.0→V3.1: Validación autoportancia | quotation_calculator_v3.py (Nivel 1C) | ...
   ```

7. **RTF Formatting**
   - ✅ All RTF formatting preserved
   - ✅ Spanish special characters maintained (`\'f3`, `\'e9`, `\'ed`, etc.)
   - ✅ Unicode arrows and symbols preserved (`\u8594`, `\u11088`, etc.)

---

## Verification Checklist

- ✅ RTF syntax intact in both files
- ✅ JSON structure valid in Esquema json.rtf
- ✅ All 4 Wolf API endpoints added to OpenAPI schema
- ✅ All 3 new request schemas defined
- ✅ Password requirement clearly documented
- ✅ Spanish language preserved in Instrucciones GPT.rtf
- ✅ Version numbers updated consistently (v3.4, 2026-02-14)
- ✅ Instructions version updated to 2.5
- ✅ Changelog section updated with v3.3→v3.4 changes
- ✅ Existing content preserved (no deletions except version updates)
- ✅ Special characters and Unicode preserved

---

## Integration Points

These RTF files are used for:

1. **GPT Configuration Upload** - Content is copied to GPT custom instructions
2. **OpenAI Actions Configuration** - Esquema json.rtf defines the Wolf API schema
3. **Team Documentation** - Reference documentation for the BMC Uruguay sales team
4. **Version Control** - Track evolution of GPT capabilities and API endpoints

---

## Next Steps

1. ✅ RTF files updated
2. ⬜ Upload updated files to GPT configuration dashboard
3. ⬜ Test Wolf API KB Write endpoints with new schema
4. ⬜ Verify password validation works correctly
5. ⬜ Test customer lookup (no password) vs customer save (password required)
6. ⬜ Document KB Write password for team access

---

## Reference Materials

- **Primary Config:** `Panelin_GPT_config.json` (v3.4)
- **Implementation Details:** `IMPLEMENTATION_SUMMARY_V3.4.md`
- **Wolf API Handlers:** `mcp/handlers/wolf_kb_write.py`
- **Tool Schemas:** `mcp/tools/persist_conversation.json`, etc.
- **Contracts:** `mcp_tools/contracts/*.v1.json`

---

**Status:** ✅ Complete  
**Updated By:** Documentation Specialist  
**Date:** 2026-02-14
