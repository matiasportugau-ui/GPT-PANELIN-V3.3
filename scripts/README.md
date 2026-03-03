# Scripts

## Morning Audit (`morning_audit.py`)

Checks all four customer touchpoints (WhatsApp, Facebook, MercadoLibre, Email) and
optionally writes a summary row to a Google Sheets "Daily Audit" worksheet.

### How to run locally

```bash
# 1. Install dependencies (only needed once)
pip install -r requirements.txt

# 2. (Optional) set Google Sheets credentials
export GOOGLE_SHEETS_ID="<your-spreadsheet-id>"
export GOOGLE_SHEETS_CREDENTIALS_PATH="./scripts/credentials/service_account.json"

# 3. Run the audit
python scripts/morning_audit.py
```

The script runs without Google Sheets credentials – it will log a warning and skip
the Sheets write step.  Audit logs are saved to `scripts/logs/audit_YYYYMMDD_HHMMSS.log`.

### How to run via GitHub Actions

Trigger the **Manual Morning Audit** workflow from the Actions tab:

```
Actions → 🌅 Manual Morning Audit → Run workflow
```

Required repository configuration:
| Type | Name | Value |
|------|------|-------|
| Secret | `GOOGLE_SHEETS_CREDS` | JSON content of the service-account file |
| Variable | `GOOGLE_SHEETS_ID` | Spreadsheet ID |

### How to run the tests

```bash
# From the repository root
pytest scripts/tests/test_morning_audit.py -v
```

The test suite (16 tests) covers:
- Initialisation with and without credentials
- All four channel audit methods
- `run_audit()` aggregation
- `write_to_sheets()` – skips gracefully, writes rows, deduplicates
- `send_summary_email()` Phase-2 placeholder
- `main()` entry-point exit code

---

# PR Cleanup Scripts

This directory contains scripts to facilitate the cleanup of stale, duplicate, and empty pull requests.

## Scripts

### close_stale_prs.sh
**Purpose**: Automated closure of 15 PRs identified in PR_CLEANUP_ANALYSIS.md

**Usage**:
```bash
./scripts/close_stale_prs.sh
```

**Requirements**:
- GitHub CLI (`gh`) must be installed
- User must be authenticated (`gh auth login`)
- User must have permission to close PRs in the repository

**What it does**:
1. Closes 4 empty PRs (#87, #86, #85, #84)
2. Closes 11 stale/superseded PRs (#81, #80, #79, #76, #70, #69, #58, #49, #44, #37)
3. Adds detailed explanatory comments to each closed PR
4. Displays summary of actions taken

**Safety**:
- Prompts for confirmation before proceeding
- Continues execution even if a PR is already closed
- Does not modify repository code

---

### verify_cleanup_status.sh
**Purpose**: Verify current PR status and repository code health

**Usage**:
```bash
./scripts/verify_cleanup_status.sh
```

**Requirements**:
- Python 3.x (for code compilation checks)
- GitHub CLI (`gh`) optional (for PR list)

**What it checks**:
- Lists current open PRs
- Compiles all Python files in panelin_mcp_integration/
- Compiles all Python files in mcp/handlers/
- Reports overall code health status

**When to use**:
- Before running close_stale_prs.sh (to verify current state)
- After running close_stale_prs.sh (to verify cleanup completed)
- Anytime to check repository health

---

## Related Documentation

- **PR_CLEANUP_ANALYSIS.md** — Original analysis identifying PRs to close
- **PR_CLOSURE_GUIDE.md** — Detailed guide with manual closure commands
- **PR_CLEANUP_IMPLEMENTATION_SUMMARY.md** — Complete implementation summary

---

## Quick Start

```bash
# 1. Verify current state
./scripts/verify_cleanup_status.sh

# 2. Review the closure guide (optional)
cat PR_CLOSURE_GUIDE.md

# 3. Execute cleanup
./scripts/close_stale_prs.sh

# 4. Verify cleanup completed
./scripts/verify_cleanup_status.sh
```

---

## Expected Outcome

After running `close_stale_prs.sh`:
- ✅ 15 PRs closed (4 empty + 11 stale/superseded)
- ✅ 4 PRs remain open (#82, #74, #71, #68)
- ✅ All closed PRs have explanatory comments
- ✅ Python files continue to compile without errors

---

## Troubleshooting

### "gh: command not found"
Install GitHub CLI: https://cli.github.com/

### "HTTP 403: 403 Forbidden"
Run `gh auth login` to authenticate

### "PR already closed"
This is normal - the script will continue with remaining PRs

### Python compilation errors
Run `./scripts/verify_cleanup_status.sh` to see which files have errors

---

**Generated**: 2026-02-14  
**Related PR**: Analysis and implementation of PR cleanup strategy
