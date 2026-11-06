# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2026-11-06

### Fixed

- Reject ambiguous verdicts, multiple IDs in an audit cell, and duplicate rule definitions.
- Report short audit rows with reordered columns as validation errors instead of crashing.
- Correct the Claude Code marketplace install command and an unmatched Markdown fence in the skill.

### Added

- `SKILL.md`: the RuleLedger skill — seven steps (Extract, Freeze, Re-read, Map, Audit, Record, Carry), file templates for `RULES.md` and `LEDGER.md`, and worked PASS/FAIL examples using the generic rules "All user-facing copy in English" and "No direct database access in request handlers".
- `scripts/ruleledger_check.py`: mechanical audit completeness checker (Python standard library only). Verifies that every rule in `RULES.md` appears exactly once in `AUDIT.md` with a PASS/FAIL verdict and `file:line` evidence, rejects unknown rule IDs, and verifies the rules hash when one is declared. Text and JSON output; exit 0 for a complete audit (even one containing FAIL verdicts), exit 1 for an incomplete or malformed audit.
- `tests/test_validator.py`: 30 pytest tests covering rule parsing, hash stability, both shipped fixtures, malformed input, and the CLI (text and JSON output).
- `requirements-dev.txt` and GitHub Actions CI for Python 3.10 and 3.14 on Linux and Windows.
- `examples/pass-project/`: 5 rules, a diff, a PASS audit, and a ledger.
- `examples/fail-project/`: the same 5 rules with one violation (`R-02`), a FAIL audit, and a ledger entry showing the fix and re-audit.
- `.claude-plugin/marketplace.json` and `.claude-plugin/plugin.json`: Claude Code plugin manifests.
- `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, MIT `LICENSE`.
