# Audit — 2026-11-06 — ship: user endpoint — REJECTED

Re-read from: RULES.md (Revision 1, 2026-11-06).
Diff audited: DIFF.txt (2 files changed, +33 −0).

| Rule | Verdict | Evidence | Notes |
|------|---------|----------|-------|
| R-01 | PASS | src/messages.py:3 | All user-facing strings are English. |
| R-02 | FAIL | src/handlers.py:12 | Handler calls db.query directly. R-02 requires handlers to go through the repository (src/repository.py:7). |
| R-03 | PASS | src/errors.py:5 | json_error always returns an `error` field; used at src/handlers.py:11 and src/handlers.py:14. |
| R-04 | PASS | src/handlers.py:7 | No credentials in the diff; search for password/token/secret found nothing. |
| R-05 | PASS | tests/test_handlers.py:4 | New public functions show_user and greet are covered by tests. |

Result: 4/5 PASS, 1 FAIL (R-02). Ship REJECTED.
Fix: move the query into repository.get_user and call it from the
handler, then re-audit. The failure stays in the ledger even after
the fix (see LEDGER.md).
