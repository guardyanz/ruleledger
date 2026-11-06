#!/usr/bin/env python3
"""RuleLedger completeness checker.

Mechanically verifies that an AUDIT.md table covers *every* rule in a
RULES.md file -- nothing skipped silently, no unknown rule IDs, and every
row carries a verdict (PASS/FAIL) plus file:line evidence.

What this script does NOT do: judge whether a PASS verdict is *true*.
That judgement is the agent's job (RuleLedger step 5). This script only
checks completeness, so a forgotten rule cannot hide inside a long audit.

RULES.md format (one rule per line):

    R-01 - All user-facing copy in English.
    R-02: No direct database access in request handlers.

Optional header lines (parsed when present):

    Revision: 3
    Date: 2026-11-06
    Source: AGENTS.md
    Hash: <sha256 of the rule lines, see compute_rules_hash>

If a Hash line is present and does not match the rule lines, the check
fails: the rules changed without a revision bump (RuleLedger step 2).

AUDIT.md format: a Markdown table whose header contains the words
Rule, Verdict, and Evidence (case-insensitive), for example:

    | Rule | Verdict | Evidence | Notes |
    |------|---------|----------|-------|
    | R-01 | PASS | src/messages.py:12 | Copy is English. |
    | R-02 | FAIL | src/handlers.py:31 | Handler calls db.query directly. |

Usage:
    python scripts/ruleledger_check.py --rules RULES.md --audit AUDIT.md
    python scripts/ruleledger_check.py --rules RULES.md --audit AUDIT.md --format json

Exit code 0 means the audit is COMPLETE (every rule audited). A FAIL
verdict inside a complete audit still exits 0 -- the audit did its job;
the *ship* is what is rejected, and the agent must say so. Exit code 1
means the audit is incomplete or malformed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

RULE_RE = re.compile(r"^\s*(R-\d{2,})\s*[-:.\u2013\u2014]\s*(.+?)\s*$")
HEADER_RE = re.compile(r"^(Revision|Date|Source|Hash):\s*(.+?)\s*$", re.IGNORECASE)
RULE_ID_RE = re.compile(r"R-\d{2,}")
# file:line evidence, e.g. src/handlers.py:31 or tests/test_x.py:12-18
EVIDENCE_RE = re.compile(r"[A-Za-z0-9_.\-/]+\.[A-Za-z0-9]+:\d+(?:-\d+)?")


@dataclass
class Rule:
    rule_id: str
    text: str


@dataclass
class AuditRow:
    rule_id: str
    verdict: str  # "PASS" or "FAIL"
    evidence: str
    notes: str = ""


@dataclass
class ValidationResult:
    rules: list[Rule] = field(default_factory=list)
    rows: list[AuditRow] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors and not self.missing and not self.unknown

    @property
    def passed(self) -> list[str]:
        return [r.rule_id for r in self.rows if r.verdict == "PASS"]

    @property
    def failed(self) -> list[str]:
        return [r.rule_id for r in self.rows if r.verdict == "FAIL"]

    @property
    def ship_rejected(self) -> bool:
        """A complete audit with any FAIL means: do not ship."""
        return self.ok and bool(self.failed)


def compute_rules_hash(rules: list[Rule]) -> str:
    """SHA-256 over the normalised rule lines, one per line.

    Normalisation is deliberately boring: ``R-01 <text>`` with single
    spaces and surrounding whitespace stripped. Any edit to a rule's
    wording changes the hash, which is the point of the Freeze step.
    """
    payload = "\n".join(f"{r.rule_id} {r.text}" for r in rules)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_rules(text: str) -> tuple[list[Rule], dict[str, str]]:
    """Parse RULES.md. Returns (rules, header dict)."""
    rules: list[Rule] = []
    header: dict[str, str] = {}
    for line in text.splitlines():
        hm = HEADER_RE.match(line)
        if hm:
            header[hm.group(1).lower()] = hm.group(2)
            continue
        m = RULE_RE.match(line)
        if m:
            rules.append(Rule(rule_id=m.group(1), text=m.group(2)))
    return rules, header


def parse_audit(text: str) -> tuple[list[AuditRow], list[str]]:
    """Parse the first Rule/Verdict/Evidence table in AUDIT.md.

    Returns (rows, errors). A missing or header-less table is an error,
    not an empty result: an audit with no table audited nothing.
    """
    lines = text.splitlines()
    errors: list[str] = []
    header_idx: int | None = None
    col: dict[str, int] = {}

    for i, line in enumerate(lines):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        lowered = [c.lower() for c in cells]
        if "rule" in lowered and "verdict" in lowered and "evidence" in lowered:
            header_idx = i
            col = {name: idx for idx, name in enumerate(lowered)}
            break

    if header_idx is None:
        return [], ["no audit table found: expected a header row with "
                    "Rule, Verdict, and Evidence columns"]

    rows: list[AuditRow] = []
    seen: set[str] = set()
    # Skip the separator row directly under the header.
    for line in lines[header_idx + 1:]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            if rows:
                break  # table ended
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if all(set(c) <= set("-: ") and c for c in cells):
            continue  # |---|---| separator
        if len(cells) <= max(col[name] for name in ("rule", "verdict", "evidence")):
            errors.append(f"malformed audit row (too few columns): {stripped}")
            continue
        rule_cell = cells[col["rule"]]
        verdict_cell = cells[col["verdict"]].upper()
        evidence_cell = cells[col["evidence"]]
        notes_cell = cells[col["notes"]] if "notes" in col and len(cells) > col["notes"] else ""

        m = RULE_ID_RE.fullmatch(rule_cell)
        if not m:
            errors.append(f"audit row must contain exactly one rule ID: {stripped}")
            continue
        rule_id = m.group(0)
        if rule_id in seen:
            errors.append(f"duplicate audit row for {rule_id}")
            continue
        seen.add(rule_id)

        if verdict_cell not in {"PASS", "FAIL"}:
            errors.append(f"{rule_id}: missing or invalid verdict "
                          f"(expected PASS or FAIL): {cells[col['verdict']]!r}")
            continue
        if not EVIDENCE_RE.search(evidence_cell):
            errors.append(f"{rule_id}: missing file:line evidence: "
                          f"{evidence_cell!r}")
            continue
        rows.append(AuditRow(rule_id=rule_id,
                             verdict=verdict_cell,
                             evidence=evidence_cell,
                             notes=notes_cell))
    if not rows and not errors:
        errors.append("audit table has no data rows")
    return rows, errors


def validate(rules_path: str | Path, audit_path: str | Path) -> ValidationResult:
    """Validate an audit file against a rules file. Pure and testable."""
    result = ValidationResult()
    try:
        rules_text = Path(rules_path).read_text(encoding="utf-8")
    except OSError as exc:
        result.errors.append(f"cannot read rules file {rules_path}: {exc}")
        return result
    try:
        audit_text = Path(audit_path).read_text(encoding="utf-8")
    except OSError as exc:
        result.errors.append(f"cannot read audit file {audit_path}: {exc}")
        return result

    rules, header = parse_rules(rules_text)
    result.rules = rules
    if not rules:
        result.errors.append("no rules found in rules file "
                             "(expected lines like 'R-01 - <rule>')")
        return result

    seen_rules: set[str] = set()
    for rule in rules:
        if rule.rule_id in seen_rules:
            result.errors.append(f"duplicate rule definition for {rule.rule_id}")
        seen_rules.add(rule.rule_id)

    declared_hash = header.get("hash", "")
    if declared_hash:
        actual = compute_rules_hash(rules)
        if declared_hash.lower() != actual.lower():
            result.errors.append(
                "rules hash mismatch: the rule lines changed without a "
                "revision bump (Freeze step). Declared hash "
                f"{declared_hash[:12]}..., computed {actual[:12]}.... "
                "Update the Hash line only together with a new Revision "
                "and an explicit user instruction.")

    rows, parse_errors = parse_audit(audit_text)
    result.rows = rows
    result.errors.extend(parse_errors)

    audited = {r.rule_id for r in rows}
    declared = {r.rule_id for r in rules}
    result.missing = [r.rule_id for r in rules if r.rule_id not in audited]
    result.unknown = sorted(audited - declared)
    if result.missing:
        result.errors.append(
            "rules missing from the audit: " + ", ".join(result.missing))
    if result.unknown:
        result.errors.append(
            "audit mentions unknown rule IDs: " + ", ".join(result.unknown))
    return result


def format_text(result: ValidationResult) -> str:
    lines = [
        "RuleLedger check",
        f"Rules: {len(result.rules)}"
        + (f" ({', '.join(r.rule_id for r in result.rules)})" if result.rules else ""),
        f"Audit rows: {len(result.rows)}",
        f"PASS: {len(result.passed)}  FAIL: {len(result.failed)}",
        "Missing rules: " + (", ".join(result.missing) if result.missing else "none"),
        "Unknown rule IDs: " + (", ".join(result.unknown) if result.unknown else "none"),
    ]
    for err in result.errors:
        lines.append(f"ERROR: {err}")
    if result.ok:
        lines.append("Result: COMPLETE - every rule was audited.")
        if result.failed:
            lines.append("Ship: REJECTED - "
                         + ", ".join(result.failed)
                         + " failed. Fix and re-audit; the failure stays "
                           "in the ledger (Record step).")
        else:
            lines.append("Ship: ALLOWED - all rules passed.")
    else:
        lines.append("Result: INCOMPLETE - audit is not trustworthy. "
                     "Fix the errors above and re-run.")
    return "\n".join(lines)


def format_json(result: ValidationResult) -> str:
    return json.dumps({
        "ok": result.ok,
        "rules": [r.rule_id for r in result.rules],
        "audited": [r.rule_id for r in result.rows],
        "pass": result.passed,
        "fail": result.failed,
        "missing": result.missing,
        "unknown": result.unknown,
        "ship_rejected": result.ship_rejected,
        "errors": result.errors,
    }, indent=2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check that an AUDIT.md covers every rule in RULES.md.")
    parser.add_argument("--rules", required=True, help="path to RULES.md")
    parser.add_argument("--audit", required=True, help="path to AUDIT.md")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="output format (default: text)")
    args = parser.parse_args(argv)

    result = validate(args.rules, args.audit)
    print(format_json(result) if args.format == "json" else format_text(result))
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
