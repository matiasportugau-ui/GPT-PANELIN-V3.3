# GPT-PANELIN V3.2 — Expert Audit Prompts

> Generated: 2026-02-14
> Purpose: Structured prompts for auditing each identified attention item in the repository.
> Usage: Feed each prompt to a senior reviewer or AI agent to produce a focused, actionable audit report.

---

## Audit 1: Git History Hygiene — "Initial plan" Commits

**Scope:** Commits `14d2edc`, `506f9f5`, `7e893f0`, `5cf36b1`, `387046d`, `854c0ac`

**Prompt:**

```
You are a senior release engineer auditing the git history of the GPT-PANELIN V3.2 repository.

OBJECTIVE: Evaluate the impact of empty/boilerplate "Initial plan" commits on the project's
git history and propose a policy to prevent them going forward.

STEPS:
1. List every commit whose message is exactly "Initial plan". For each one:
   - Show the diff (files changed, lines added/removed).
   - Determine whether it introduced any meaningful code or was purely a planning artifact.
   - Check if it is reachable from the current main/default branch or only from merged PR branches.
2. Assess the impact:
   - Does git blame on any production file point to an "Initial plan" commit as the last author?
   - Do these commits break `git bisect` usefulness for any file?
3. Recommend:
   - Whether to rewrite history (interactive rebase / squash) or leave as-is, with trade-offs.
   - A CI check or branch protection rule that rejects commits with generic messages
     (e.g., regex deny-list: "^Initial plan$", "^WIP$", "^fixup$").
   - A PR merge strategy (squash-merge vs. rebase-merge) that would prevent this pattern.

OUTPUT FORMAT: Table of commits → impact assessment, followed by numbered recommendations
with implementation steps.
```

---

## Audit 2: Dual MCP Integration Paths — Divergence Risk

**Scope:** `mcp/` directory vs. `panelin_mcp_integration/` directory

**Prompt:**

```
You are a senior software architect auditing the GPT-PANELIN V3.2 repository for
architectural coherence.

OBJECTIVE: Determine whether the two MCP-related directories (`mcp/` and
`panelin_mcp_integration/`) represent intentional, complementary modules or an
accidental duplication that will drift over time.

STEPS:
1. For each directory, answer:
   - What protocol does it implement (MCP stdio/SSE, OpenAI function-calling, both)?
   - What tools/handlers does it expose? Create a feature matrix.
   - What external dependencies does it require (check requirements.txt, imports)?
   - Is there shared logic between the two? Identify any copy-pasted code blocks.
2. Map the data flow:
   - Draw the call chain from an incoming request to each handler in both paths.
   - Identify where they read from the same data files (e.g., bromyros_pricing_master.json,
     bom_rules.json, shopify_catalog_v1.json).
   - Check whether business logic (pricing formulas, BOM rules, catalog search) is
     duplicated or shared via imports.
3. Evaluate divergence risk:
   - If a pricing formula changes, how many files must be updated? Is there a single
     source of truth?
   - Are there already inconsistencies between the two implementations (different field
     names, different calculation logic, different error handling)?
4. Recommend:
   - Keep both, merge into one, or refactor into a shared core + thin adapters.
   - Provide a concrete module layout if refactoring is recommended.
   - Estimate effort (S/M/L) and risk for each option.

OUTPUT FORMAT: Feature comparison matrix, data-flow diagram (text-based), divergence
findings, and a ranked list of recommendations with effort/risk ratings.
```

---

## Audit 3: Test Coverage Gaps

**Scope:** All test files in the repository:
- `.evolucionador/tests/test_analyzer.py`
- `.evolucionador/tests/test_validator.py`
- `.evolucionador/tests/test_optimizer.py`
- `openai_ecosystem/test_client.py`
- `panelin_reports/test_pdf_generation.py`

**Prompt:**

```
You are a senior QA engineer auditing test coverage for the GPT-PANELIN V3.2 repository.

OBJECTIVE: Assess whether critical business logic is adequately tested and identify
the most dangerous gaps.

STEPS:
1. Inventory existing tests:
   - For each test file, list every test function/method and what it covers.
   - Determine if the tests can actually run (check imports, fixtures, dependencies).
   - Run `pytest --collect-only` (or equivalent) to verify test discoverability.
2. Map critical business logic that MUST be tested:
   - `quotation_calculator_v3.py` — the core quoting engine (986 lines, 0 tests found).
   - `mcp/handlers/bom.py` — BOM calculation (recently had multiple bug fixes for
     thickness conversion, support calculation, producto_ref).
   - `mcp/handlers/pricing.py` — pricing logic (recently had type-hint fixes).
   - `mcp/handlers/catalog.py` — catalog search correctness.
   - `mcp/handlers/errors.py` — error reporting paths.
   - `panelin_mcp_integration/panelin_mcp_server.py` — MCP server request handling.
3. For each untested critical module, define:
   - Minimum viable test cases (happy path, edge cases, error cases).
   - Specific edge cases derived from recent bug fixes:
     * Thickness = 0 or missing
     * Support calculation with length_m vs. width_m
     * producto_ref missing or malformed
     * Price list returning a list vs. a single value
   - Mock/fixture requirements (which JSON data files are needed).
4. Prioritize:
   - Rank modules by risk (business impact × likelihood of regression).
   - Recommend a testing roadmap: what to test first, what framework to use,
     and a target coverage percentage.

OUTPUT FORMAT: Coverage matrix (module → test status → risk level), followed by
a prioritized test backlog with specific test case descriptions.
```

---

## Audit 4: `corrections_log.json` — Version Control Appropriateness

**Scope:** `/corrections_log.json` (root-level tracked file)

**Prompt:**

```
You are a senior data engineer auditing the data management practices of the
GPT-PANELIN V3.2 repository.

OBJECTIVE: Determine whether `corrections_log.json` should be tracked in git,
and if not, recommend the correct storage and workflow.

STEPS:
1. Analyze the file:
   - Read its schema, current contents (currently empty corrections array with
     schema definition and one example).
   - Determine its lifecycle: Is it written to at runtime by the GPT? Is it
     manually edited? Is it consumed by any script?
2. Search for references:
   - Grep the entire codebase for "corrections_log" to find any code that reads
     or writes this file.
   - Check if any GPT instructions reference it (search .json config files and
     markdown instruction files).
3. Evaluate storage options:
   | Option | Pros | Cons |
   |--------|------|------|
   | Keep in git | Single source of truth, versioned | Merge conflicts, grows unbounded |
   | .gitignore + template | Clean history | Need separate distribution of template |
   | External store (DB/API) | Scalable, queryable | Infrastructure overhead |
   | Git-tracked schema + .gitignored data | Best of both | Slightly more complex setup |
4. Recommend:
   - The best storage strategy given that this is a GPT-based system without a backend.
   - If keeping in git: a rotation/archival policy to prevent unbounded growth.
   - If removing from git: exact .gitignore entry and migration steps.

OUTPUT FORMAT: Decision matrix, final recommendation with implementation commands.
```

---

## Audit 5: Documentation Sprawl at Root Level

**Scope:** 23 markdown files at the repository root

**Prompt:**

```
You are a senior technical writer auditing the documentation structure of the
GPT-PANELIN V3.2 repository.

OBJECTIVE: Reduce documentation sprawl, eliminate redundancy, and create a clear
information architecture that serves three audiences: (1) GPT operators uploading
files, (2) developers extending the MCP server, (3) end users of the quotation system.

STEPS:
1. Catalog every .md file at the root and in docs/:
   For each file, record:
   - Title and stated purpose (first 5 lines).
   - Word count and last-modified date.
   - Primary audience (operator / developer / user / internal-only).
   - Whether it duplicates content found in another file (flag overlaps).
2. Identify redundancy:
   - Compare README.md sections against standalone files (e.g., does README.md
     duplicate MCP_QUICK_START.md content?).
   - Check for contradictions between files (e.g., different setup commands,
     different module paths after the review fix in commit 6dd52aa).
   - Flag any file that is purely a "prompt" or "agent instruction" that shouldn't
     be user-facing documentation (e.g., MCP_RESEARCH_PROMPT.md,
     MCP_AGENT_ARCHITECT_PROMPT.md).
3. Propose a new structure:
   ```
   docs/
   ├── getting-started/
   │   ├── quick-start.md
   │   └── gpt-upload-guide.md
   ├── architecture/
   │   ├── mcp-server.md
   │   └── knowledge-base.md
   ├── guides/
   │   ├── quotation-process.md
   │   ├── pricing-instructions.md
   │   └── pdf-reports.md
   ├── reference/
   │   ├── api-examples.md
   │   └── configuration.md
   └── internal/
       ├── audit-reports/
       └── evolution-plans/
   ```
4. For each current file, map it to the new location or mark it for deletion/merge.
5. Recommend:
   - A documentation linting tool (e.g., markdownlint, vale) and CI integration.
   - A CODEOWNERS rule for docs/ to ensure reviews.
   - A maximum of 3 files at the repo root (README.md, LICENSE, CONTRIBUTING.md).

OUTPUT FORMAT: Current file → proposed destination mapping table, redundancy report,
and a migration script outline (bash commands to move files and update cross-references).
```

---

## Audit 6: BOM Calculation Correctness & Regression Safety

**Scope:** `mcp/handlers/bom.py`, related JSON data files, recent bug-fix commits

**Prompt:**

```
You are a senior domain engineer specializing in construction/building-material
BOM (Bill of Materials) calculations, auditing the GPT-PANELIN V3.2 system.

OBJECTIVE: Verify the correctness of BOM calculations after recent bug fixes and
identify remaining risks.

STEPS:
1. Read `mcp/handlers/bom.py` line by line. For each calculation:
   - Document the formula in mathematical notation.
   - Identify the input fields and their expected units (meters, millimeters, USD, etc.).
   - Verify unit consistency (e.g., thickness in mm converted to m before area calc).
   - Cross-reference with `bom_rules.json` to confirm rule application is correct.
2. Replay recent bug fixes:
   - Commit `8a8aee2`: thickness conversion fix — verify the fix is complete and no
     other thickness references remain unconverted.
   - Commit `e4144e6`: support calculation using length_m + autoportancia — verify
     the formula matches domain requirements (what is "autoportancia"? Is it
     self-supporting span? Confirm the engineering definition).
   - Commit `8a8aee2`: producto_ref usage — verify all product lookups use the
     correct reference field consistently.
3. Edge case analysis:
   - What happens with: thickness = 0, negative dimensions, missing producto_ref,
     extremely large dimensions (>100m), non-numeric inputs?
   - Does the code handle partial BOM requests (e.g., only panels, no accessories)?
   - What happens if bom_rules.json is malformed or missing a rule?
4. Data validation:
   - Read `bom_rules.json` and verify every rule has the required fields.
   - Check for orphaned rules (rules that reference products not in the catalog).
   - Check for missing rules (common product combinations without BOM rules).
5. Recommend:
   - Specific assertions or validation checks to add at function entry points.
   - A set of golden-file test cases (input → expected output) derived from real
     quotation scenarios.
   - Whether a domain-expert review of the formulas is needed before production use.

OUTPUT FORMAT: Formula documentation table, bug-fix verification checklist (pass/fail),
edge-case risk matrix, and prioritized recommendations.
```
