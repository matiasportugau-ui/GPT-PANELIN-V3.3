# PANELIN Morning Audit — Full Explanation

> **Quick answer: to run the audit right now** →
> ```bash
> python scripts/morning_audit.py
> ```
> Full setup and run instructions are in [scripts/README.md](../scripts/README.md).

---

## What is the Morning Audit?

The **Morning Audit** is a lightweight daily routine that checks all four customer-facing communication channels for PANELIN / BMC Uruguay and records the results to a Google Sheets tracking spreadsheet.

The goal is simple: every morning, before the work day starts, confirm that no customer message has been missed overnight on any platform.

### The four channels checked

| Emoji | Platform | What to look for |
|-------|----------|-----------------|
| 📱 | **WhatsApp Web** | Unread messages from customers asking about panels, pricing, or orders |
| 📘 | **Facebook Page** | Unread messages in the Page inbox and Messenger |
| 🛍️ | **MercadoLibre** | New questions on listings, unread messages, and new orders |
| 📧 | **Email / Gmail** | Customer inquiries in the inbox and spam folder |

---

## Phase 1 vs Phase 2

The script is designed in two phases:

### Phase 1 (current — manual prompts)

Phase 1 does **not** connect to external APIs for WhatsApp, Facebook, MercadoLibre, or Gmail. Instead, it:

1. Prints a reminder for each platform telling you what to check manually.
2. Logs a timestamped entry to `scripts/logs/audit_YYYYMMDD_HHMMSS.log`.
3. Writes one row per channel to the Google Sheets "Daily Audit" worksheet (if configured).

This means you still open each platform yourself and count messages — the script's job is to act as your structured checklist and audit trail.

### Phase 2 (planned — automated collection)

Phase 2 will replace the manual prompts with real API integrations so message counts are fetched automatically. The `send_summary_email()` method (currently a no-op placeholder) will send a daily summary email once Phase 2 is complete.

---

## Step-by-step walkthrough

When you run `python scripts/morning_audit.py`, the following happens in order:

```
1.  load_dotenv()
    └─ Reads GOOGLE_SHEETS_ID and GOOGLE_SHEETS_CREDENTIALS_PATH from .env (if present)

2.  PanelinAudit()
    └─ _connect_sheets()
        ├─ If credentials are missing → logs a warning, continues without Sheets
        └─ If credentials are present → opens the Google Sheets spreadsheet

3.  run_audit()
    ├─ _audit_whatsapp()     → logs reminder, returns {platform, status, message, count}
    ├─ _audit_facebook()     → logs reminder, returns {platform, status, message, count}
    ├─ _audit_mercadolibre() → logs reminder, returns {platform, status, message, count}
    └─ _audit_email()        → logs reminder, returns {platform, status, message, count}

4.  write_to_sheets()
    ├─ If no sheet connection → logs "Skipping" warning, stops
    ├─ Opens (or creates) the "Daily Audit" worksheet
    ├─ Reads existing rows and builds a de-duplication key set
    │   key = (cliente.casefold(), "DD-MM", origin_code)
    ├─ Skips rows whose key already exists (safe to re-run the same day)
    └─ Appends new rows (one per channel) at the next empty row

5.  send_summary_email()
    └─ Phase 2 placeholder — logs a message, does nothing yet

6.  Logs "MORNING AUDIT COMPLETE" and the path to the log file
    Exit code 0 = success, 1 = audit failed to complete
```

---

## Google Sheets integration

### Worksheet structure — "Daily Audit"

Each row added by the script maps to columns **A through H**:

| Col | Header | Value written by script | Description |
|-----|--------|------------------------|-------------|
| A | Asig. | *(blank)* | Who the row is assigned to (fill in manually) |
| B | Estado | `Pendiente` | Status — set to "Pendiente" on creation |
| C | Fecha | `DD-MM` | Today's date, e.g. `03-03` |
| D | Cliente | `Audit WhatsApp` / `Audit Facebook` / `Audit MercadoLibre` / `Audit Email` | Platform label |
| E | Orig. | `WA` / `FB` / `ML` / `EM` | Origin code |
| F | Telefono-Contacto | *(blank)* | Contact phone (fill in manually if needed) |
| G | Direccion/Zona | *(blank)* | Address/zone (fill in manually if needed) |
| H | Consulta | The platform's check reminder text | Short description of what was audited |

### Origin codes

| Code | Platform |
|------|----------|
| `WA` | WhatsApp |
| `FB` | Facebook |
| `ML` | MercadoLibre |
| `EM` | Email |

### Deduplication

The script checks for duplicate rows before writing. A row is considered a duplicate if the combination of **Cliente** (column D, case-insensitive) + **Fecha** (column C) + **Orig.** (column E) already exists in the worksheet.

This means you can safely re-run the script on the same day without creating duplicate rows.

### Setting up Google Sheets from scratch

1. **Create (or open) your tracking spreadsheet** in Google Sheets.  
   Copy the spreadsheet ID from the URL:  
   `https://docs.google.com/spreadsheets/d/**<SPREADSHEET_ID>**/edit`

2. **Create a Service Account** in [Google Cloud Console](https://console.cloud.google.com/):
   - Navigate to *IAM & Admin → Service Accounts → Create Service Account*
   - Give it a name, e.g. `panelin-audit`
   - After creation, go to the *Keys* tab → *Add Key → Create new key → JSON*
   - Download the JSON file

3. **Share your spreadsheet** with the service account email  
   (looks like `panelin-audit@<project>.iam.gserviceaccount.com`)  
   and give it **Editor** access.

4. **Configure the environment variables**:
   ```bash
   export GOOGLE_SHEETS_ID="<your-spreadsheet-id>"
   export GOOGLE_SHEETS_CREDENTIALS_PATH="/path/to/service_account.json"
   ```
   Or put them in a `.env` file at the repository root:
   ```ini
   GOOGLE_SHEETS_ID=<your-spreadsheet-id>
   GOOGLE_SHEETS_CREDENTIALS_PATH=./scripts/credentials/service_account.json
   ```

5. **Run the audit** — the "Daily Audit" worksheet is created automatically on first run if it does not already exist.

---

## Reading the log output

A successful run prints output like this:

```
2026-03-03 07:00:01,234 - INFO  - ============================================================
2026-03-03 07:00:01,235 - INFO  - 🌅 PANELIN MORNING AUDIT STARTED
2026-03-03 07:00:01,236 - INFO  - ============================================================
2026-03-03 07:00:01,237 - WARNING - ⚠️ Google Sheets ID missing. Set GOOGLE_SHEETS_ID to …
2026-03-03 07:00:01,238 - INFO  - 🔄 Running all channel audits...
2026-03-03 07:00:01,239 - INFO  - 📱 Checking WhatsApp Web...
2026-03-03 07:00:01,240 - WARNING - ⚠️  Phase 1 manual step: open WhatsApp Web and count …
2026-03-03 07:00:01,241 - INFO  - 📘 Checking Facebook Page...
2026-03-03 07:00:01,242 - WARNING - ⚠️  Phase 1 manual step: check Facebook Page inbox …
2026-03-03 07:00:01,243 - INFO  - 🛍️ Checking MercadoLibre...
2026-03-03 07:00:01,244 - WARNING - ⚠️  Phase 1 manual step: review MercadoLibre questions …
2026-03-03 07:00:01,245 - INFO  - 📧 Checking Email...
2026-03-03 07:00:01,246 - WARNING - ⚠️  Phase 1 manual step: review Gmail inbox and spam …
2026-03-03 07:00:01,247 - INFO  - ✅ All channel audits completed
2026-03-03 07:00:01,248 - WARNING - ⚠️ Skipping Google Sheets write (no sheet connection).
2026-03-03 07:00:01,249 - INFO  - 📬 Email summary placeholder (Phase 2)
2026-03-03 07:00:01,250 - INFO  - ============================================================
2026-03-03 07:00:01,251 - INFO  - 🎉 MORNING AUDIT COMPLETE
2026-03-03 07:00:01,252 - INFO  - 📝 Logs saved to: scripts/logs/audit_20260303_070001.log
2026-03-03 07:00:01,253 - INFO  - ============================================================
```

### What the messages mean

| Message | Meaning |
|---------|---------|
| `⚠️ Google Sheets ID missing` | The `GOOGLE_SHEETS_ID` env var is not set. Sheets write is skipped. This is normal for a local run without credentials. |
| `⚠️ Phase 1 manual step: …` | Reminder to manually check this platform. No action is taken automatically. |
| `✅ All channel audits completed` | All four channel checks ran without errors. |
| `⚠️ Skipping Google Sheets write` | No sheet connection — write is skipped safely. |
| `✅ Inserted N row(s) into worksheet 'Daily Audit'` | Rows were written to Sheets successfully. |
| `ℹ️ Skipping duplicate row for …` | Today's row for this channel already exists in Sheets — not written again. |
| `🎉 MORNING AUDIT COMPLETE` | The script finished successfully (exit code 0). |
| `❌ Morning audit did not complete` | An unexpected exception stopped the audit (exit code 1). Check the log for the error. |

---

## Troubleshooting

### ❌ `ModuleNotFoundError: No module named 'dotenv'`
Install the dependencies:
```bash
pip install -r requirements.txt
```

### ⚠️ `Google Sheets ID missing` (and you do want Sheets)
Set the environment variable before running:
```bash
export GOOGLE_SHEETS_ID="<your-spreadsheet-id>"
```
or add it to a `.env` file in the repository root.

### ⚠️ `Google credentials file not found`
Check that the path in `GOOGLE_SHEETS_CREDENTIALS_PATH` points to an existing JSON file.

### ❌ `Google Sheets connection failed: 403`
The service-account email has not been granted access to the spreadsheet.  
Open the spreadsheet in Google Sheets → Share → add the service-account email as Editor.

### ❌ `Google Sheets connection failed: invalid_grant`
The service-account JSON key has expired or been revoked.  
Regenerate the key in Google Cloud Console (IAM & Admin → Service Accounts → Keys).

### ❌ `Missing dependencies. Install with: pip install -r requirements.txt`
The `gspread` or `google-auth` packages are not installed. Run:
```bash
pip install -r requirements.txt
```

### Rows are not appearing in Sheets
Run the audit with `GOOGLE_SHEETS_ID` set and check whether the log shows
`✅ Inserted` or `ℹ️ Skipping duplicate`. If it shows `⚠️ Skipping Google Sheets write`,
the sheet connection failed — look earlier in the log for the error.

---

## Running the tests

```bash
# From the repository root
pytest scripts/tests/test_morning_audit.py -v
```

The 16-test suite covers all key behaviours without requiring real Google credentials.

---

## File locations

| File | Purpose |
|------|---------|
| `scripts/morning_audit.py` | The audit script |
| `scripts/logs/audit_YYYYMMDD_HHMMSS.log` | Per-run log files |
| `scripts/credentials/service_account.json` | Google service-account key (not committed) |
| `scripts/tests/test_morning_audit.py` | Unit tests |
| `.github/workflows/manual_audit.yml` | GitHub Actions workflow for on-demand runs |
| `.env` | Local environment variables (not committed) |
