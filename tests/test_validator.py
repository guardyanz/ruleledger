"""Tests for scripts/ruleledger_check.py.

Run from the repo root:  python -m pytest -q
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from ruleledger_check import (  # noqa: E402
    compute_rules_hash,
    main,
    parse_audit,
    parse_rules,
    validate,
)

ROOT = Path(__file__).resolve().parents[1]
PASS_RULES = ROOT / "examples" / "pass-project" / "RULES.md"
PASS_AUDIT = ROOT / "examples" / "pass-project" / "AUDIT.md"
FAIL_RULES = ROOT / "examples" / "fail-project" / "RULES.md"
FAIL_AUDIT = ROOT / "examples" / "fail-project" / "AUDIT.md"
CHECK = ROOT / "scripts" / "ruleledger_check.py"

SAMPLE_RULES = """# Rules
Revision: 1
Date: 2026-11-06
Source: AGENTS.md

R-01 - All user-facing copy in English.
R-02: No direct database access in request handlers.
R-03 - All API errors return a JSON body with an `error` field.
"""

SAMPLE_AUDIT = """# Audit

| Rule | Verdict | Evidence | Notes |
|------|---------|----------|-------|
| R-01 | PASS | src/messages.py:3 | English. |
| R-02 | PASS | src/handlers.py:13 | Via repository. |
| R-03 | PASS | src/errors.py:5 | Always has error field. |
"""


def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


# --- parsing RULES.md -------------------------------------------------

def test_parse_rules_extracts_ids_in_order():
    rules, header = parse_rules(SAMPLE_RULES)
    assert [r.rule_id for r in rules] == ["R-01", "R-02", "R-03"]
    assert rules[0].text == "All user-facing copy in English."


def test_parse_rules_accepts_dash_and_colon_separators():
    rules, _ = parse_rules("R-01 - first rule.\nR-02: second rule.\n")
    assert len(rules) == 2
    assert rules[1].text == "second rule."


def test_parse_rules_ignores_non_rule_lines():
    rules, header = parse_rules("# Title\nSome prose.\nRevision: 2\nR-01 - real rule.\n")
    assert len(rules) == 1
    assert header["revision"] == "2"


def test_parse_rules_empty_file_has_no_rules():
    rules, _ = parse_rules("# Nothing here\n")
    assert rules == []


def test_compute_hash_is_stable_and_sensitive_to_wording():
    rules, _ = parse_rules(SAMPLE_RULES)
    h1 = compute_rules_hash(rules)
    h2 = compute_rules_hash(rules)
    assert h1 == h2 and len(h1) == 64
    rules[0].text = "All user-facing copy in Indonesian."
    assert compute_rules_hash(rules) != h1


# --- validating the shipped fixtures ----------------------------------

def test_pass_fixture_is_complete_and_allowed():
    result = validate(PASS_RULES, PASS_AUDIT)
    assert result.ok
    assert result.missing == []
    assert result.unknown == []
    assert result.failed == []
    assert not result.ship_rejected


def test_fail_fixture_is_complete_but_ship_rejected():
    result = validate(FAIL_RULES, FAIL_AUDIT)
    assert result.ok  # complete audit: every rule was judged
    assert result.failed == ["R-02"]
    assert result.ship_rejected


def test_fixture_rules_hash_matches_declared_hash():
    for rules_path in (PASS_RULES, FAIL_RULES):
        rules, header = parse_rules(rules_path.read_text(encoding="utf-8"))
        assert header["hash"] == compute_rules_hash(rules)


# --- failure modes ------------------------------------------------------

def test_missing_rule_is_reported(tmp_path):
    rules = write(tmp_path, "RULES.md", SAMPLE_RULES)
    audit = write(tmp_path, "AUDIT.md", SAMPLE_AUDIT.replace(
        "| R-03 | PASS | src/errors.py:5 | Always has error field. |\n", ""))
    result = validate(rules, audit)
    assert not result.ok
    assert result.missing == ["R-03"]


def test_unknown_rule_id_is_reported(tmp_path):
    rules = write(tmp_path, "RULES.md", SAMPLE_RULES)
    audit = write(tmp_path, "AUDIT.md", SAMPLE_AUDIT.replace(
        "| R-03 |", "| R-99 |"))
    result = validate(rules, audit)
    assert not result.ok
    assert result.unknown == ["R-99"]
    assert result.missing == ["R-03"]


@pytest.mark.parametrize("rule_cell", ["R-01 / R-99", "R-01 extra text"])
def test_rule_cell_must_contain_one_exact_id(tmp_path, rule_cell):
    rules = write(tmp_path, "RULES.md", SAMPLE_RULES)
    audit = write(tmp_path, "AUDIT.md", SAMPLE_AUDIT.replace(
        "| R-01 |", f"| {rule_cell} |"))
    result = validate(rules, audit)
    assert not result.ok
    assert "R-01" in result.missing


def test_missing_verdict_fails(tmp_path):
    rules = write(tmp_path, "RULES.md", SAMPLE_RULES)
    audit = write(tmp_path, "AUDIT.md", SAMPLE_AUDIT.replace(
        "| R-02 | PASS |", "| R-02 | MAYBE |"))
    result = validate(rules, audit)
    assert not result.ok
    assert any("R-02" in e and "verdict" in e for e in result.errors)


@pytest.mark.parametrize("verdict", ["not PASS", "PASS pending review", "FAIL resolved", "PASS/FAIL"])
def test_ambiguous_verdict_is_rejected(tmp_path, verdict):
    rules = write(tmp_path, "RULES.md", SAMPLE_RULES)
    audit = write(tmp_path, "AUDIT.md", SAMPLE_AUDIT.replace(
        "| R-01 | PASS |", f"| R-01 | {verdict} |"))
    result = validate(rules, audit)
    assert not result.ok
    assert any("R-01" in e and "verdict" in e for e in result.errors)


def test_missing_evidence_fails(tmp_path):
    rules = write(tmp_path, "RULES.md", SAMPLE_RULES)
    audit = write(tmp_path, "AUDIT.md", SAMPLE_AUDIT.replace(
        "| R-01 | PASS | src/messages.py:3 |", "| R-01 | PASS | - |"))
    result = validate(rules, audit)
    assert not result.ok
    assert any("R-01" in e and "evidence" in e for e in result.errors)


def test_evidence_without_line_number_fails(tmp_path):
    rules = write(tmp_path, "RULES.md", SAMPLE_RULES)
    audit = write(tmp_path, "AUDIT.md", SAMPLE_AUDIT.replace(
        "src/messages.py:3", "src/messages.py"))
    result = validate(rules, audit)
    assert not result.ok


def test_empty_audit_fails(tmp_path):
    rules = write(tmp_path, "RULES.md", SAMPLE_RULES)
    audit = write(tmp_path, "AUDIT.md", "# Audit\n\nNo table here.\n")
    result = validate(rules, audit)
    assert not result.ok
    assert any("no audit table" in e for e in result.errors)


def test_duplicate_rule_row_fails(tmp_path):
    rules = write(tmp_path, "RULES.md", SAMPLE_RULES)
    audit = write(tmp_path, "AUDIT.md", SAMPLE_AUDIT +
                  "| R-01 | PASS | src/other.py:1 | Again. |\n")
    result = validate(rules, audit)
    assert not result.ok
    assert any("duplicate" in e for e in result.errors)


def test_duplicate_rule_definitions_are_rejected(tmp_path):
    rules = write(tmp_path, "RULES.md", SAMPLE_RULES + "R-01 - Another rule.\n")
    audit = write(tmp_path, "AUDIT.md", SAMPLE_AUDIT)
    result = validate(rules, audit)
    assert not result.ok
    assert any("duplicate" in e and "R-01" in e for e in result.errors)


def test_short_row_with_reordered_columns_is_reported(tmp_path):
    rules = write(tmp_path, "RULES.md", SAMPLE_RULES)
    audit = write(tmp_path, "AUDIT.md", """| Notes | Rule | Verdict | Evidence |
|-------|------|---------|----------|
| Note | R-01 | PASS |
""")
    result = validate(rules, audit)
    assert not result.ok
    assert any("too few columns" in e for e in result.errors)


def test_hash_mismatch_fails(tmp_path):
    rules, _ = parse_rules(SAMPLE_RULES)
    bad_hash = "0" * 64
    rules_text = SAMPLE_RULES.replace(
        "Source: AGENTS.md", f"Source: AGENTS.md\nHash: {bad_hash}")
    rules_path = write(tmp_path, "RULES.md", rules_text)
    audit = write(tmp_path, "AUDIT.md", SAMPLE_AUDIT)
    result = validate(rules_path, audit)
    assert not result.ok
    assert any("hash mismatch" in e for e in result.errors)


def test_correct_hash_passes(tmp_path):
    rules, _ = parse_rules(SAMPLE_RULES)
    good_hash = compute_rules_hash(rules)
    rules_text = SAMPLE_RULES.replace(
        "Source: AGENTS.md", f"Source: AGENTS.md\nHash: {good_hash}")
    rules_path = write(tmp_path, "RULES.md", rules_text)
    audit = write(tmp_path, "AUDIT.md", SAMPLE_AUDIT)
    result = validate(rules_path, audit)
    assert result.ok


# --- CLI ----------------------------------------------------------------

def test_cli_pass_fixture_exits_zero():
    proc = subprocess.run(
        [sys.executable, str(CHECK), "--rules", str(PASS_RULES),
         "--audit", str(PASS_AUDIT)],
        capture_output=True, text=True)
    assert proc.returncode == 0
    assert "Ship: ALLOWED" in proc.stdout


def test_cli_fail_fixture_exits_zero_but_rejects_ship():
    proc = subprocess.run(
        [sys.executable, str(CHECK), "--rules", str(FAIL_RULES),
         "--audit", str(FAIL_AUDIT)],
        capture_output=True, text=True)
    assert proc.returncode == 0  # audit complete; the ship is rejected
    assert "Ship: REJECTED - R-02 failed." in proc.stdout


def test_cli_missing_rule_exits_one(tmp_path):
    rules = write(tmp_path, "RULES.md", SAMPLE_RULES)
    audit = write(tmp_path, "AUDIT.md", SAMPLE_AUDIT.replace(
        "| R-03 | PASS | src/errors.py:5 | Always has error field. |\n", ""))
    proc = subprocess.run(
        [sys.executable, str(CHECK), "--rules", str(rules),
         "--audit", str(audit)],
        capture_output=True, text=True)
    assert proc.returncode == 1
    assert "R-03" in proc.stdout


def test_cli_json_format_parses(tmp_path):
    rules = write(tmp_path, "RULES.md", SAMPLE_RULES)
    audit = write(tmp_path, "AUDIT.md", SAMPLE_AUDIT)
    proc = subprocess.run(
        [sys.executable, str(CHECK), "--rules", str(rules),
         "--audit", str(audit), "--format", "json"],
        capture_output=True, text=True)
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["ok"] is True
    assert data["rules"] == ["R-01", "R-02", "R-03"]


def test_main_returns_int_directly(tmp_path):
    rules = write(tmp_path, "RULES.md", SAMPLE_RULES)
    audit = write(tmp_path, "AUDIT.md", SAMPLE_AUDIT)
    assert main(["--rules", str(rules), "--audit", str(audit)]) == 0
    assert main(["--rules", str(FAIL_RULES),
                 "--audit", str(FAIL_AUDIT)]) == 0
