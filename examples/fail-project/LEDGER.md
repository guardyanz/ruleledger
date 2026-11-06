# Ledger — example project

Newest entries first. Read the last 5 before starting work (Carry step).

## 2026-11-06 — ship: user endpoint — REJECTED, then FIXED

- R-01 PASS — src/messages.py:3
- R-02 FAIL — src/handlers.py:12 — handler called db.query directly.
  Fix: moved the query into repository.get_user and called it from the
  handler. Re-audit 2026-11-06: R-02 PASS — src/handlers.py:13.
  The original failure stays recorded here; fixing a violation does
  not erase it.
- R-03 PASS — src/errors.py:5
- R-04 PASS — src/handlers.py:7
- R-05 PASS — tests/test_handlers.py:4

## 2026-11-05 — ship: error responses — ALLOWED

- R-01 PASS — src/messages.py:3
- R-02 PASS — src/handlers.py:13
- R-03 PASS — src/errors.py:5
- R-04 PASS — src/handlers.py:7
- R-05 PASS — tests/test_handlers.py:4
