# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## What this project is — and is not

RuleLedger is a process skill and a small local file checker. It makes no network requests, reads only the files you point it at, and writes nothing except what you ask it to print. It is **not** a security scanner and **not** a substitute for code review: a PASS verdict in an audit is only as honest as the agent that wrote it (see "Limitations" in the README).

## Reporting a vulnerability

If you find a security issue in `scripts/ruleledger_check.py` — for example, a way for a crafted `AUDIT.md` or `RULES.md` to execute arbitrary code or to exfiltrate data — please report it privately instead of opening a public issue:

- Open a GitHub Security Advisory on this repository, or
- Email the maintainer via the address listed on their GitHub profile.

Please include a minimal `RULES.md` / `AUDIT.md` pair that reproduces the issue and the exact command you ran. Do not include secrets, credentials, or production data in the report.

## Response

Reports are acknowledged within 7 days. If the issue is confirmed, a fix and a patched release are published, and the reporter is credited in `CHANGELOG.md` unless they ask not to be.

## Scope notes

- The example projects under `examples/` contain no real credentials. Any string that looks like a secret there is a made-up value in a fictional project.
- RuleLedger never sends your rules, audits, or ledgers anywhere. If a future version adds any network behaviour, it will be opt-in, documented, and listed here first.
