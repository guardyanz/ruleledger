# Audit — 2026-11-06 — ship: user endpoint

Re-read from: RULES.md (Revision 1, 2026-11-06).
Diff audited: DIFF.txt (5 files changed, +54 −0).

| Rule | Verdict | Evidence | Notes |
|------|---------|----------|-------|
| R-01 | PASS | src/messages.py:3 | All user-facing strings are English. |
| R-02 | PASS | src/handlers.py:13 | Handler calls repository.get_user; the only query lives in src/repository.py:9. |
| R-03 | PASS | src/errors.py:5 | json_error always returns an `error` field; used at src/handlers.py:12 and src/handlers.py:15. |
| R-04 | PASS | src/handlers.py:8 | No credentials in the diff; search for password/token/secret found nothing. |
| R-05 | PASS | tests/test_handlers.py:4 | New public functions show_user and greet are covered by tests. |

Result: 5/5 PASS. Ship allowed.
