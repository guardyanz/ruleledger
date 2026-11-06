---
name: ruleledger
description: Keep standing rules from rotting in long AI agent sessions. Extract numbered rules from AGENTS.md, CLAUDE.md, or session instructions, freeze them with a hash, re-read them from the file before shipping, audit every rule against the diff with file and line evidence, and record the verdict in a ledger. Use when a project has standing rules and the agent will ship code in a long session, after compaction, or across multiple sessions. Do not use for one-off tasks with no standing rules.
---

# RuleLedger

## The problem in one sentence

In a long session, an agent obeys your standing rules for the first five turns and breaks them on the twentieth, because the rules are buried in a context that has grown past the point where the model reliably uses it.

## How this skill works

Seven steps, in order. Each step reads the output of the previous step — never skip ahead, and never audit from memory. The three files this skill owns are:

- `RULES.md` — the frozen, numbered rules (Step 1–2).
- `AUDIT.md` — one PASS/FAIL row per rule, with evidence, for the current ship (Step 5).
- `LEDGER.md` — the append-only record of every ship's verdicts (Step 6).

Keep this file short on purpose: after compaction only the first 5,000 tokens of a skill are re-attached, so the steps below are the part that must survive.

## Step 1 — Extract

**Input:** `AGENTS.md`, `CLAUDE.md`, and any standing instructions given in this session.
**Action:** Copy each standing rule into `RULES.md`, one rule per line, numbered `R-01`, `R-02`, and so on. One rule, one line, one idea. Do not paraphrase in a way that changes the meaning; if a sentence contains two rules, split it into two numbered lines. Preserve the source next to the header (`Source: AGENTS.md`).
**Output:** `RULES.md` with a header (`Revision`, `Date`, `Source`) and the numbered rules.
**Edge case:** If there are zero standing rules, stop here. The skill skips; that is a success, not a failure. Write nothing to the ledger.

## Step 2 — Freeze

**Input:** the `RULES.md` from Step 1.
**Action:** Compute the SHA-256 hash of the rule lines (see "Hash" below) and write it in the header with the revision number and date. From now on the rules are frozen: they change only when the user explicitly says so, and every change gets a new revision number, a new date, and a new hash, recorded in `LEDGER.md`.
**Output:** a frozen `RULES.md`.
**Conflict:** If two extracted rules contradict each other, STOP. Do not pick a winner. Ask the user which one stands, and record the answer as a revision.
**Hash:** SHA-256 over the lines `R-01 <text>`, `R-02 <text>`, … joined with `\n`, UTF-8 encoded. The bundled checker (`scripts/ruleledger_check.py`) computes it; a mismatch means the rules changed without a revision bump.

## Step 3 — Re-read

**Input:** the frozen `RULES.md`.
**Action:** Before writing any file that will ship, read `RULES.md` from disk again and state, in your reply, that you have re-read rules `R-01` through `R-n`. Do not rely on the copy in your context: the file is the source of truth, and the whole point of this skill is that context copies rot.
**Output:** an explicit re-read statement listing the rule IDs.
**Gate:** No re-read statement, no shipping. If you cannot read the file (it was deleted, the path is wrong), say so explicitly instead of proceeding from memory.

## Step 4 — Map

**Input:** `git diff --stat` plus the changed files, and the frozen `RULES.md`.
**Action:** Build a table mapping every changed hunk to the rule it touches, or to "no rule applies". A hunk with no mapping is **unmapped**: either map it to a rule or explicitly exclude it with a reason (for example, "generated file, no rule applies"). Unmapped hunks are not allowed to ship silently.
**Output:** the hunk→rule map, as part of `AUDIT.md` or alongside it.

## Step 5 — Audit

**Input:** the map from Step 4 and the changed files.
**Action:** For **every** rule `R-01` through `R-n`, write one row in `AUDIT.md`:

| Rule | Verdict | Evidence | Notes |
|------|---------|----------|-------|
| R-01 | PASS | src/messages.py:3 | All user-facing strings are English. |

- **Verdict** is `PASS` or `FAIL` only. There is no "mostly fine" and no blank.
- **Evidence** is a real `file:line` in the diff. A claim without evidence is not a PASS.
- **One FAIL rejects the ship.** Fix the violation, then re-audit from Step 3. A fixed violation is recorded, not erased (Step 6).
- Then run the mechanical checker: `python scripts/ruleledger_check.py --rules RULES.md --audit AUDIT.md`. It verifies that every rule ID appears exactly once, that no unknown ID appears, and that every row has a verdict and evidence. It cannot judge whether a PASS is true — that judgement is yours — but it makes a silently skipped rule impossible.

**Output:** a complete `AUDIT.md` (checker exit code 0) and a ship decision: ALLOWED or REJECTED.

## Step 6 — Record

**Input:** the completed `AUDIT.md`.
**Action:** Append one entry to `LEDGER.md`: date, what shipped, and one line per rule with its verdict and evidence. A violation that was found and fixed stays in the ledger, with the fix and the re-audit result noted next to it. The ledger is append-only: never rewrite history to make a ship look clean.
**Output:** the new ledger entry.

## Step 7 — Carry

**Input:** `LEDGER.md`.
**Action:** At the start of the next session — and immediately after any compaction — read the 5 most recent ledger entries **before** writing code. They tell you which rules this project has actually broken before, and those are the rules most likely to break again.
**Output:** a one-line summary of the recent violations, stated before work begins.
**Gate:** If the ledger cannot be read (missing file, wrong path), say so explicitly. Never silently assume "no recent violations".

## Worked example

Rules (generic, from a fictional project):

```text
R-01 - All user-facing copy in English.
R-02 - No direct database access in request handlers.
```

### PASS — before and after

Before: the handler called the database directly.

```python
# src/handlers.py (BEFORE)
from db import query

def show_user(request):
    rows = query("SELECT id, name FROM users WHERE id = ?", (request.params["id"],))
```

After: the query moved to the repository; the handler calls the repository.

```python
# src/handlers.py (AFTER)
from repository import get_user

def show_user(request):
    user = get_user(request.params["id"])
```

Audit row: `| R-02 | PASS | src/handlers.py:13 | Handler calls repository.get_user; the only query is in src/repository.py:9. |`

### FAIL — same rules, one violation

The diff adds a greeting in another language:

```python
# src/messages.py
WELCOME_MESSAGE = "Selamat datang kembali!"
```

Audit row: `| R-01 | FAIL | src/messages.py:3 | User-facing copy is not English. |`

Ship: **REJECTED**. Fix the string to `"Welcome back!"`, re-audit from Step 3, and record both the failure and the fix in `LEDGER.md`.

## File templates

`RULES.md`:

```text
# Rules — <project>

Revision: 1
Date: 2026-11-06
Source: AGENTS.md
Hash: <sha256 of the rule lines>

R-01 - <rule, one line>
R-02 - <rule, one line>
```

`LEDGER.md` (newest first):

```text
# Ledger — <project>

## 2026-11-06 — ship: <what shipped> — ALLOWED / REJECTED

- R-01 PASS — src/messages.py:3
- R-02 FAIL — src/handlers.py:12 — <what broke>. Fix: <what changed>.
  Re-audit: R-02 PASS — src/handlers.py:13.
```

## Limitations — read before trusting this skill

- **The self-check paradox.** The agent that forgot a rule is the same agent asked to audit itself. RuleLedger reduces the failure mode — it forces a re-read from disk, a rule-by-rule table, and a mechanical completeness check — but it cannot eliminate it. The checker proves no rule was *skipped*; it cannot prove a PASS verdict is *honest*. For high-stakes ships, have a second agent or a human read the audit table against the diff.
- **Rules must be checkable.** "Write clean code" cannot be audited; "All user-facing copy in English" can. If a rule is vague, Step 1 should flag it and ask the user to sharpen it, not silently pass it.
- **The ledger is only as honest as the agent writing it.** It is a memory aid, not a cryptographic proof. The hash in Step 2 protects the rules from silent drift; it does not protect the audit from a careless author.
- **Scope.** This skill governs standing rules for code that ships. It does not review security, performance, or correctness beyond the rules you wrote.
## References

- `scripts/ruleledger_check.py` — the mechanical completeness checker (Python standard library only, no dependencies). Run it with `python scripts/ruleledger_check.py --rules RULES.md --audit AUDIT.md`.
- `examples/pass-project/` — a small project with 5 rules, a diff, a PASS audit, and a ledger.
- `examples/fail-project/` — the same rules with one violation: a FAIL audit and a ledger entry showing the fix and re-audit.
