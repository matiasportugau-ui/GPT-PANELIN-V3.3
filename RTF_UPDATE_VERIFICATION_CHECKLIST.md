# RTF Files v3.4 Update - Quick Verification Checklist

## ✅ Esquema json.rtf

### Version & Description
- [x] API version updated to `3.0.0`
- [x] Description includes "KB Write capabilities" and password requirement
- [x] OpenAPI version remains `3.1.0`

### New Schemas (3)
- [x] `ConversationRequest` schema added
  - [x] Required fields: `client_id`, `summary`, `password`
  - [x] Optional fields: `quotation_ref`, `products_discussed`
- [x] `CorrectionRequest` schema added
  - [x] Required fields: `source_file`, `field_path`, `old_value`, `new_value`, `reason`, `password`
  - [x] Optional fields: `reported_by`
- [x] `CustomerRequest` schema added
  - [x] Required fields: `name`, `phone`, `password`
  - [x] Optional fields: `address`, `city`, `department`, `notes`

### New Endpoints (4)
- [x] `POST /kb/conversations` (persist_conversation)
  - [x] Request: ConversationRequest schema
  - [x] Response 200: `{status, conversation_id}`
  - [x] Response 400: Bad request or invalid password
  - [x] Response 403: Invalid API key
  
- [x] `POST /kb/corrections` (register_correction)
  - [x] Request: CorrectionRequest schema
  - [x] Response 200: `{status, correction_id}`
  - [x] Response 400: Bad request or invalid password
  - [x] Response 403: Invalid API key
  
- [x] `POST /kb/customers` (save_customer)
  - [x] Request: CustomerRequest schema
  - [x] Response 200: `{status, customer_id}`
  - [x] Response 400: Bad request, invalid phone or password
  - [x] Response 403: Invalid API key
  
- [x] `GET /kb/customers` (lookup_customer)
  - [x] Query parameter: `search` (required)
  - [x] Response 200: `{customers: [array]}`
  - [x] Response 403: Invalid API key
  - [x] Note: "no password required" in summary

### RTF Formatting
- [x] RTF header intact (`\rtf1\ansi\ansicpg1252...`)
- [x] JSON escaping correct (`\{`, `\}`, `\"`)
- [x] Line continuations preserved (`\`)
- [x] Closing brace intact (`\}`)

---

## ✅ Instrucciones GPT.rtf

### Header
- [x] Version updated to `v3.4`
- [x] Date updated to `(2026-02-14)`
- [x] Subtitle includes "Wolf API KB Write"

### Section 4: Knowledge Base Hierarchy
- [x] `NIVEL 1D` added with Wolf API KB Write
- [x] Description: "persistencia conversaciones, correcciones, clientes (V3.4 NUEVO)"

### Section 9: Commands
- [x] `/guardar_conversacion` command added (V3.4 NUEVO)
- [x] `/guardar_cliente` command added (V3.4 NUEVO)
- [x] Wolf API v3.4 command subsection added
- [x] Four Wolf API commands listed:
  - [x] `/guardar_conversacion`
  - [x] `/guardar_cliente`
  - [x] `/corregir_kb`
  - [x] `/buscar_cliente`

### Section 11: Capabilities
- [x] Wolf API KB Write capability added
- [x] Password requirement noted
- [x] Lookup exemption noted (no password for GET)

### Section 12: WOLF API - ESCRITURA EN KB (NEW)
- [x] Section header created
- [x] Four capabilities documented:
  1. [x] PERSISTIR CONVERSACIONES - POST /kb/conversations
  2. [x] REGISTRAR CORRECCIONES - POST /kb/corrections
  3. [x] GUARDAR CLIENTES - POST /kb/customers
  4. [x] BUSCAR CLIENTES - GET /kb/customers
  
- [x] Data structures documented for each
- [x] Password requirements clearly marked
- [x] Phone validation noted (Uruguayan format)

### REGLAS ESCRITURA
- [x] Before POST: request password rule
- [x] Invalid password: reject rule
- [x] GET operations: no password rule
- [x] Inform client: consent rule
- [x] Minimal data: only relevant rule
- [x] No secrets: security rule
- [x] X-API-Key required: auth rule

### USO
- [x] After quotation: offer to save
- [x] Existing customer: auto-retrieve
- [x] KB error: register correction
- [x] Long conversations: use /checkpoint

### Version History (End)
- [x] "FIN v3.4 (2026-02-14)" header
- [x] V3.3→V3.4 changes documented:
  - [x] Wolf API KB Write
  - [x] 4 new endpoints
  - [x] Password security
  - [x] Phone validation
  - [x] Customer persistence
  - [x] Correction persistence
  - [x] Instructions 2.5
- [x] V3.0→V3.1 changes preserved

### RTF Formatting
- [x] RTF header intact
- [x] Spanish characters preserved (`\'f3`, `\'e9`, etc.)
- [x] Unicode arrows preserved (`\u8594`, `\u11088`)
- [x] Bullets preserved (`\'b7`)
- [x] Line breaks intact (`\`)
- [x] Closing brace intact (`}`)

---

## Test Upload Commands

### For macOS/RTF Preview
```bash
# View Esquema json.rtf
open "Esquema json.rtf"

# View Instrucciones GPT.rtf
open "Instrucciones GPT.rtf"
```

### For Text Verification
```bash
# Check version in Esquema json.rtf
grep -A 2 '"version"' "Esquema json.rtf"

# Check version in Instrucciones GPT.rtf  
head -10 "Instrucciones GPT.rtf"

# Count endpoints
grep -c "operationId" "Esquema json.rtf"
# Should show: 11 (7 existing + 4 new)
```

---

## Post-Upload Verification

### In GPT Configuration UI
- [ ] Copy Esquema json.rtf content to Actions schema
- [ ] Copy Instrucciones GPT.rtf content to Instructions
- [ ] Verify version shows as v3.4 in UI
- [ ] Test Wolf API actions appear in UI
- [ ] Verify password field appears for write operations

### In Testing
- [ ] Test `persist_conversation` with password
- [ ] Test `register_correction` with password
- [ ] Test `save_customer` with password
- [ ] Test `lookup_customer` without password
- [ ] Verify password validation rejects incorrect password
- [ ] Verify phone validation rejects invalid format

---

**Status:** ✅ All checks passed  
**Ready for:** GPT configuration upload  
**Date:** 2026-02-14
