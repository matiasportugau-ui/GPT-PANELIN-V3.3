# KB Modification Quick Reference

**For Developers and GPT Integrators**

---

## Quick Tool Selection

| Scenario | Tool | Password? |
|----------|------|-----------|
| User reports error during chat | `report_error` | No |
| Need to validate price change | `validate_correction` | No |
| Apply validated correction | `commit_correction` | No |
| Multiple errors at once | `batch_validate_corrections` | No |
| View pending corrections | `list_corrections` | No |
| Mark correction as applied | `update_correction_status` | **Yes** |
| Save conversation context | `persist_conversation` (Wolf API) | **Yes** |
| Register via Wolf API | `register_correction` (Wolf API) | **Yes** |

---

## Minimal Examples

### Report Error (Simplest)
```json
{
  "kb_file": "accessories_catalog.json",
  "field": "items[32].price_usd",
  "wrong_value": "15.50",
  "correct_value": "18.75",
  "source": "conversation"
}
```

### Validate Correction
```json
{
  "kb_file": "bromyros_pricing_master.json",
  "field": "data.products[5].pricing.web_iva_inc",
  "proposed_value": "165.00"
}
```

### Commit Correction
```json
{
  "change_id": "CHG-A3B4C5D6E7F8",
  "confirm": true
}
```

### Batch Validate
```json
{
  "corrections": [
    {
      "kb_file": "accessories_catalog.json",
      "field": "items[10].price_usd",
      "proposed_value": "25.00"
    },
    {
      "kb_file": "accessories_catalog.json",
      "field": "items[12].price_usd",
      "proposed_value": "18.50"
    }
  ]
}
```

### List Corrections
```json
{
  "status": "pending",
  "limit": 10
}
```

### Update Status (Requires Password)
```json
{
  "correction_id": "COR-001",
  "new_status": "applied",
  "password": "YOUR_PASSWORD"
}
```

---

## Allowed KB Files

```
bromyros_pricing_master.json
bromyros_pricing_gpt_optimized.json
accessories_catalog.json
bom_rules.json
shopify_catalog_v1.json
BMC_Base_Conocimiento_GPT-2.json
perfileria_index.json
```

---

## Valid Sources

```
conversation       - Error detected during verbal interaction
user_correction    - User explicitly provides correction
validation_check   - Automated validation detected error
audit             - Manual audit process
web_verification  - Verified against web source
```

---

## Status Values

```
pending   - Awaiting review/application
applied   - Correction has been applied to KB
rejected  - Correction deemed invalid
```

---

## Error Codes

```
MISSING_REQUIRED_FIELDS - Missing kb_file, field, value, etc.
INVALID_KB_FILE        - KB file not in allowed list
INVALID_FIELD          - Field path is malformed
PASSWORD_REQUIRED      - Operation requires password
INVALID_PASSWORD       - Wrong password
CORRECTION_NOT_FOUND   - Correction ID doesn't exist
VALUE_MISMATCH         - Current value doesn't match expected
EMPTY_BATCH            - No corrections in batch
BATCH_TOO_LARGE        - More than 20 corrections
INVALID_LIMIT          - Limit must be 1-500
INVALID_OFFSET         - Offset must be >= 0
INVALID_STATUS         - Status must be pending/applied/rejected
```

---

## Password Configuration

Default password: `mywolfy`

Override with environment variable:
```bash
export WOLF_KB_WRITE_PASSWORD="your_secure_password"
```

**Required for:**
- `update_correction_status`
- `persist_conversation` (Wolf API)
- `register_correction` (Wolf API)
- `save_customer` (Wolf API)

**Not required for:**
- `report_error`
- `validate_correction`
- `commit_correction`
- `batch_validate_corrections`
- `list_corrections`
- `lookup_customer` (Wolf API)

---

## Workflow Patterns

### Pattern 1: Immediate Logging
```
User reports error → report_error → Continue conversation
```

### Pattern 2: Validated Change
```
User suggests change → validate_correction → Review impact → commit_correction
```

### Pattern 3: Batch Processing
```
Collect multiple errors → batch_validate_corrections → Review summary → Commit individually
```

---

## Testing

Run all KB interaction tests:
```bash
pytest mcp/tests/test_kb_interaction.py -v
```

Run specific test:
```bash
pytest mcp/tests/test_kb_interaction.py::TestListCorrections::test_pagination -v
```

---

## Files Modified

- `mcp/handlers/errors.py` - Enhanced report_error
- `mcp/handlers/governance.py` - Added 3 new handlers
- `mcp/server.py` - Registered new tools
- `mcp/tools/*.json` - 3 new tool schemas
- `mcp/tests/test_kb_interaction.py` - 18 new tests

---

## Contract Version

All tools return v1 contract envelopes:
```json
{
  "ok": true|false,
  "contract_version": "v1",
  ...
}
```

Legacy format supported in `report_error` for backward compatibility.

---

*Quick Reference v1.0*
