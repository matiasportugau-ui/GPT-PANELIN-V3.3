# Knowledge Base Modification Guide for Verbal Interactions

**Version:** 1.0  
**Date:** 2026-02-17  
**Purpose:** Complete guide for modifying the knowledge base during GPT verbal interactions

---

## Overview

Panelin GPT now supports comprehensive knowledge base modification capabilities during verbal interactions with users. When errors or corrections are identified during conversations, they can be immediately captured, validated, and persisted back to the knowledge base.

This guide covers all available tools for KB modification and best practices for handling errors during verbal interactions.

---

## Available Tools

### 1. **report_error** - Simple Error Logging

**Use Case:** Quick error reporting during conversations when the GPT detects or the user identifies incorrect data.

**When to Use:**
- User says "that price is wrong"
- GPT provides an incorrect quotation
- Data inconsistency detected mid-conversation

**Tool Schema:**
```json
{
  "kb_file": "accessories_catalog.json",
  "field": "items[32].price_usd",
  "wrong_value": "15.50",
  "correct_value": "18.75",
  "source": "conversation",
  "notes": "User reported incorrect price during quotation"
}
```

**Response:**
```json
{
  "ok": true,
  "contract_version": "v1",
  "correction": {
    "id": "COR-001",
    "date": "2026-02-17T17:00:00Z",
    "kb_file": "accessories_catalog.json",
    "field": "items[32].price_usd",
    "wrong_value": "15.50",
    "correct_value": "18.75",
    "source": "conversation",
    "notes": "User reported incorrect price during quotation",
    "status": "pending",
    "applied_date": null
  },
  "message": "Correction COR-001 logged successfully. Error reported during conversation and queued for review.",
  "total_pending": 5
}
```

**Valid Sources:**
- `conversation` - Error detected during verbal interaction
- `user_correction` - User explicitly provides correction
- `validation_check` - Automated validation detected error
- `audit` - Manual audit process
- `web_verification` - Verified against web source

---

### 2. **validate_correction** - Pre-Flight Validation

**Use Case:** Validate a proposed correction before committing it. Provides impact analysis on recent quotations.

**When to Use:**
- Before applying critical price changes
- When assessing impact of data corrections
- To generate change reports for approval

**Tool Schema:**
```json
{
  "kb_file": "bromyros_pricing_master.json",
  "field": "data.products[5].pricing.web_iva_inc",
  "current_value": "150.00",
  "proposed_value": "165.00",
  "source": "conversation",
  "notes": "User reported updated pricing from BMC website"
}
```

**Response:**
```json
{
  "ok": true,
  "contract_version": "v1",
  "validation": {
    "field_exists": true,
    "current_value": "150.00",
    "proposed_value": "165.00",
    "value_match": true
  },
  "impact_analysis": {
    "quotations_analyzed": 50,
    "quotations_affected": 3,
    "total_impact_usd": "45.00",
    "affected_quotations": [
      {
        "quotation_id": "Q-2026-001",
        "item": "ISOPANEL EPS 50mm",
        "original_line_total": "300.00",
        "revised_line_total": "315.00",
        "impact_usd": "15.00"
      }
    ]
  },
  "change_report": {
    "change_id": "CHG-A3B4C5D6E7F8",
    "timestamp": "2026-02-17T17:05:00Z",
    "severity": "low",
    "summary": "Change to bromyros_pricing_master.json:data.products[5].pricing.web_iva_inc — from '150.00' to '165.00'. 3/50 quotations affected (total impact: USD 45.00)"
  },
  "change_id": "CHG-A3B4C5D6E7F8"
}
```

---

### 3. **commit_correction** - Apply Validated Correction

**Use Case:** Commit a previously validated correction to the corrections log.

**When to Use:**
- After validating a correction with validate_correction
- When impact is acceptable and change is approved
- Requires explicit confirmation flag

**Tool Schema:**
```json
{
  "change_id": "CHG-A3B4C5D6E7F8",
  "confirm": true
}
```

**Response:**
```json
{
  "ok": true,
  "contract_version": "v1",
  "correction": {
    "id": "COR-002",
    "date": "2026-02-17T17:06:00Z",
    "kb_file": "bromyros_pricing_master.json",
    "field": "data.products[5].pricing.web_iva_inc",
    "wrong_value": "150.00",
    "correct_value": "165.00",
    "source": "conversation",
    "status": "pending",
    "change_id": "CHG-A3B4C5D6E7F8",
    "impact_summary": {
      "quotations_affected": 3,
      "total_impact_usd": "45.00",
      "severity": "low"
    }
  },
  "message": "Correction COR-002 committed successfully. 3 quotation(s) affected.",
  "total_pending": 6
}
```

---

### 4. **batch_validate_corrections** - Validate Multiple Errors

**Use Case:** When multiple errors are detected in a single conversation, validate them all at once.

**When to Use:**
- Multiple price corrections identified
- Batch updates from user feedback
- Systematic data review sessions

**Tool Schema:**
```json
{
  "corrections": [
    {
      "kb_file": "accessories_catalog.json",
      "field": "items[10].price_usd",
      "proposed_value": "25.00",
      "source": "conversation",
      "notes": "User correction during quotation"
    },
    {
      "kb_file": "accessories_catalog.json",
      "field": "items[12].price_usd",
      "proposed_value": "18.50",
      "source": "conversation",
      "notes": "User correction during quotation"
    }
  ]
}
```

**Limits:**
- Maximum 20 corrections per batch
- Each correction validated independently
- Results include batch_index for identification

**Response:**
```json
{
  "ok": true,
  "contract_version": "v1",
  "results": [
    {
      "ok": true,
      "batch_index": 0,
      "correction_input": {
        "kb_file": "accessories_catalog.json",
        "field": "items[10].price_usd",
        "proposed_value": "25.00"
      },
      "validation": { ... },
      "impact_analysis": { ... },
      "change_report": { ... }
    },
    {
      "ok": true,
      "batch_index": 1,
      ...
    }
  ],
  "summary": {
    "total_corrections": 2,
    "successful_validations": 2,
    "failed_validations": 0,
    "total_quotations_affected": 5,
    "total_impact_usd": "78.00"
  }
}
```

---

### 5. **list_corrections** - Retrieve Correction History

**Use Case:** View pending, applied, or rejected corrections with filtering.

**When to Use:**
- Check what corrections are pending
- Review correction history
- Monitor correction status

**Tool Schema:**
```json
{
  "status": "pending",
  "kb_file": "accessories_catalog.json",
  "limit": 10,
  "offset": 0
}
```

**Parameters:**
- `status`: `"pending"`, `"applied"`, `"rejected"`, or `"all"` (default: `"all"`)
- `kb_file`: Optional filter by specific file
- `limit`: Results per page (1-500, default: 50)
- `offset`: Pagination offset (default: 0)

**Response:**
```json
{
  "ok": true,
  "contract_version": "v1",
  "corrections": [
    {
      "id": "COR-001",
      "date": "2026-02-17T17:00:00Z",
      "kb_file": "accessories_catalog.json",
      "field": "items[32].price_usd",
      "wrong_value": "15.50",
      "correct_value": "18.75",
      "source": "conversation",
      "status": "pending"
    }
  ],
  "pagination": {
    "total": 15,
    "limit": 10,
    "offset": 0,
    "has_more": true
  }
}
```

---

### 6. **update_correction_status** - Manage Correction Lifecycle

**Use Case:** Update the status of corrections (requires password).

**When to Use:**
- Mark corrections as applied after manual fix
- Reject invalid corrections
- Revert corrections to pending status

**Tool Schema:**
```json
{
  "correction_id": "COR-001",
  "new_status": "applied",
  "notes": "Applied manually via GitHub PR #123",
  "password": "mywolfy"
}
```

**Valid Statuses:**
- `pending` - Awaiting review/application
- `applied` - Correction has been applied to KB
- `rejected` - Correction deemed invalid

**Response:**
```json
{
  "ok": true,
  "contract_version": "v1",
  "correction": {
    "id": "COR-001",
    "status": "applied",
    "applied_date": "2026-02-17T17:15:00Z",
    "status_history": [
      {
        "timestamp": "2026-02-17T17:15:00Z",
        "from_status": "pending",
        "to_status": "applied",
        "notes": "Applied manually via GitHub PR #123"
      }
    ]
  },
  "message": "Correction COR-001 status updated from 'pending' to 'applied'",
  "total_pending": 4
}
```

---

## Workflow Examples

### Example 1: Simple Error During Conversation

**User:** "The price for the 50mm EPS panel seems wrong. It should be $145 not $135."

**GPT Action:**
1. Call `report_error` with the correction details
2. Acknowledge the error and thank the user
3. Continue conversation with corrected information

**GPT Response:**
"Thank you for catching that! I've logged a correction for the 50mm EPS panel price (from $135 to $145). The correction is now queued for review and will be applied to future quotations. Let me recalculate your quotation with the correct price..."

---

### Example 2: Critical Price Change with Validation

**User:** "BMC just updated the pricing for ISODEC 100mm panels to $185/m²."

**GPT Action:**
1. Call `validate_correction` to check impact
2. Review impact analysis (quotations affected, total impact)
3. If impact is acceptable, call `commit_correction`
4. Inform user of the change and its impact

**GPT Response:**
"I've validated that price change. The update would affect 7 recent quotations with a total impact of $210 USD. I've committed this correction (COR-003) to the queue. The pricing team will review and apply it to the knowledge base within 24 hours."

---

### Example 3: Multiple Errors in One Session

**User:** "I need to correct several accessory prices based on the latest supplier list."

**GPT Action:**
1. Collect all corrections from the conversation
2. Call `batch_validate_corrections` with all corrections
3. Review summary and present to user
4. Ask for confirmation before committing each

**GPT Response:**
"I've validated all 5 corrections. Here's the summary:
- 2 affected existing quotations
- Total impact: $45 USD
- All validations passed

Would you like me to commit these corrections to the review queue?"

---

## Best Practices

### For Verbal Interactions

1. **Acknowledge Immediately**
   - Thank users for reporting errors
   - Confirm the correction has been logged
   - Provide the correction ID for reference

2. **Explain Impact**
   - If using `validate_correction`, share impact analysis
   - Mention how many quotations are affected
   - Explain severity level (low/medium/high)

3. **Use Appropriate Tool**
   - Simple errors → `report_error`
   - Critical changes → `validate_correction` + `commit_correction`
   - Multiple errors → `batch_validate_corrections`

4. **Maintain Context**
   - Include relevant notes from the conversation
   - Use "conversation" as source
   - Reference quotation IDs if applicable

5. **Follow Up**
   - Mention that corrections are queued for review
   - Explain typical review timeframe
   - Offer to use corrected value immediately in current quotation

### Security

- **Password Required:** Only `update_correction_status` requires password
- **Whitelist Validation:** All KB files validated against allowed list
- **Path Traversal Protection:** File paths sanitized
- **Input Validation:** All fields validated before processing

---

## Error Handling

### Common Error Codes

| Code | Meaning | Resolution |
|------|---------|------------|
| `MISSING_REQUIRED_FIELDS` | Missing kb_file, field, value, etc. | Provide all required parameters |
| `INVALID_KB_FILE` | KB file not in allowed list | Use one of the allowed KB files |
| `INVALID_FIELD` | Field path is malformed | Check JSON path syntax |
| `PASSWORD_REQUIRED` | Operation requires password | Provide KB write password |
| `INVALID_PASSWORD` | Wrong password | Check password and retry |
| `CORRECTION_NOT_FOUND` | Correction ID doesn't exist | Verify correction ID |
| `VALUE_MISMATCH` | Current value doesn't match expected | Re-validate with actual value |
| `EMPTY_BATCH` | No corrections in batch | Provide at least one correction |
| `BATCH_TOO_LARGE` | More than 20 corrections | Split into multiple batches |

### Graceful Degradation

If a tool fails:
1. Log the error with `logger.exception()`
2. Return error envelope with details
3. Continue conversation with fallback behavior
4. Inform user of the issue

---

## Integration with Wolf API

The enhanced KB modification tools integrate with the Wolf API for persistence:

- **persist_conversation** - Save conversation context (requires password)
- **register_correction** - Register via Wolf API (requires password)
- **lookup_customer** - No password needed (read-only)

---

## Future Enhancements

Planned additions:
- Real-time correction notification to admin dashboard
- Confidence scoring for corrections
- Automatic correction application for low-impact changes
- Correction preview before commit
- Rollback functionality for applied corrections

---

## Support

For issues or questions about KB modification:
- Check the corrections log: `corrections_log.json`
- Review test cases: `mcp/tests/test_kb_interaction.py`
- Consult: `KB_ARCHITECTURE_AUDIT.md` for architectural context

---

*Last updated: 2026-02-17*
*Version: 1.0*
