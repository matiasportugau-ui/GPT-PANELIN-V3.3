# DEPLOYMENT STATUS — Phase 1 Production Fix

## 1) Endpoint status

### New v4 endpoints added in `app.py`

| Endpoint | Method | Engine used | Status |
|---|---|---|---|
| `/api/quote` | POST | `panelin_v4/engine/quotation_engine.py` (`process_quotation`) | ✅ Implemented |
| `/api/validate` | POST | `panelin_v4/engine/validation_engine.py` (`validate_quotation`) | ✅ Implemented |
| `/api/sai-score` | POST | `panelin_v4/evaluator/sai_engine.py` (`calculate_sai`) | ✅ Implemented |

### Existing endpoints preserved

Legacy endpoints are preserved by reusing the existing FastAPI app from `wolf_api/main.py` and keeping operation IDs used by clients.

| Legacy name | Method | Path | Status |
|---|---|---|---|
| `getSheetStats` | GET | `/sheets/stats` | ✅ Preserved |
| `searchClients` | GET | `/sheets/search` | ✅ Preserved |
| `getRow` | GET | `/sheets/row/{row_number}` | ✅ Preserved |
| `readConsultations` | GET | `/sheets/consultations` | ✅ Preserved |
| `addConsultation` | POST | `/sheets/consultations` | ✅ Preserved |
| `addQuotationLine` | POST | `/sheets/quotation_line` | ✅ Preserved |
| `updateRow` | PATCH | `/sheets/update_row` | ✅ Preserved |
| `persistConversation` | POST | `/kb/conversations` | ✅ Preserved |
| `saveCustomer` | POST | `/kb/customers` | ✅ Preserved |
| `registerCorrection` | POST | `/kb/corrections` | ✅ Preserved |

---

## 2) Deploy failure diagnosis and fix

### Root cause found

- `app.py` had no Cloud Run-compatible runtime entrypoint block.
- The previous file was Vercel-oriented and did not include explicit `uvicorn.run(...)` with Cloud Run host/port semantics.

### Applied fix

- Added Cloud Run-compatible startup block in `app.py`:

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
```

- This ensures Cloud Run compatibility (`0.0.0.0` + env `PORT` defaulting to `8080`).

---

## 3) Files changed

- `app.py`
  - Reworked as Cloud Run entrypoint.
  - Reused existing API app from `wolf_api.main` to preserve legacy endpoints.
  - Added `/api/quote`, `/api/validate`, `/api/sai-score`.
  - Added legacy operation ID mapping for existing client integrations.
- `requirements.txt`
  - Added missing runtime dependencies for legacy endpoints:
    - `google-cloud-storage>=2.10.0`
    - `gspread>=6.0.0`
    - `google-auth>=2.0.0`

---

## 4) Regression execution result

Command executed:

```bash
python3 -c "import json; from panelin_v4.evaluator.regression_suite import run_regression_suite; r=run_regression_suite(); fails=[{'test_id':x['test_id'],'failures':x['failures']} for x in r['results'] if not x['passed']]; print(json.dumps({'total':r['total'],'passed':r['passed'],'failed':r['failed'],'pass_rate':r['pass_rate'],'failed_tests':fails}, ensure_ascii=False, indent=2))"
```

Result:

- Total: **19**
- Passed: **19**
- Failed: **0**
- Pass rate: **100.0%**

---

## 5) Manual deploy instructions (Cloud Run)

If a manual deploy is required from repository root:

1. Ensure dependencies and env vars are available:
   - `WOLF_API_KEY`
   - `KB_GCS_BUCKET`
   - `SHEETS_SPREADSHEET_ID`
   - Optional sheets tab vars (`SHEETS_TAB_2026`, `SHEETS_TAB_2025`, `SHEETS_TAB_ADMIN`)
2. Deploy to Cloud Run (example):

```bash
gcloud run deploy panelin-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars WOLF_API_KEY=...,KB_GCS_BUCKET=...,SHEETS_SPREADSHEET_ID=...
```

3. Validate runtime:

```bash
curl -s https://panelin-api-642127786762.us-central1.run.app/health
curl -s https://panelin-api-642127786762.us-central1.run.app/api/health
```

