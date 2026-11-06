# Contributing to RuleLedger

## How to contribute

1. Fork the repo and create a branch from `main`.
2. For changes to the skill itself (`SKILL.md`), keep the seven steps first and the file short: after compaction only the first 5,000 tokens of a skill are re-attached, so anything that must survive a long session belongs at the top.
3. For changes to the checker (`scripts/ruleledger_check.py`), add or update tests in `tests/test_validator.py` and keep the checker dependency-free (Python standard library only).
4. Run the tests before opening a pull request:

```bash
python -m pytest -q
python scripts/ruleledger_check.py --rules examples/pass-project/RULES.md --audit examples/pass-project/AUDIT.md
python scripts/ruleledger_check.py --rules examples/fail-project/RULES.md --audit examples/fail-project/AUDIT.md
```

Use Python 3.10 or newer and install the test dependency first with
`python -m pip install -r requirements-dev.txt` (preferably in a virtual environment).

The test suite must pass. The second command must end with `Ship: ALLOWED`. The third must end with `Ship: REJECTED - R-02 failed.` — that is the expected behaviour for the fail example, not a broken test.

## What makes a good pull request

- **One mechanism per PR.** A new step, a new checker flag, or a new example — not all three.
- **Examples must be real.** If you add an example audit, the evidence lines must point at lines that exist in the example files, and the validator output quoted in the PR description must come from an actual run.
- **No unproven claims.** Do not add benchmark numbers, star counts, or "first ever" language without a source you can link to. If a claim cannot be sourced, leave it out.

## Reporting bugs

Open an issue with:

- the `RULES.md` and `AUDIT.md` that reproduce the problem (remove secrets first),
- the exact command you ran and its full output,
- your Python version (`python --version`).

## Code of conduct

Be direct and be kind. Disagree with the mechanism, not the person. Maintainers may close issues that ask for features outside the skill's scope — governing standing rules for code that ships — with a short reason.
