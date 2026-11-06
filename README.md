# RuleLedger

**In a long session, an agent obeys your standing rules for the first five turns and breaks them on the twentieth — because the rules are buried in a context that has grown past the point where the model reliably uses them.**

RuleLedger is a portable [Agent Skill](https://agentskills.io) that stops that from happening silently. It turns standing rules into numbered, frozen, auditable artefacts: extract the rules, freeze them with a hash, re-read them from disk before shipping, audit every rule against the diff with file-and-line evidence, and record the verdict in a ledger that the next session reads first.

No dependencies. No server. No account. One `SKILL.md`, one small Python checker, two worked examples.

## Why this happens

This is not a guess about model behaviour — it is measured:

- **Context rot is real.** Chroma Research (Hong, Troynikov, Huber, 14 July 2025) tested 18 frontier models and found that every one degraded as its input grew, even on simple retrieval tasks, long before the context window filled. On LongMemEval, a conversational-memory benchmark, the same questions scored consistently worse when buried in ~113,000 tokens of conversation than in a focused ~300-token version. The size of the drop varies by model and task — there is no single percentage to quote, and this repo does not invent one. Source: <https://research.trychroma.com/context-rot>
- **Skills do not survive compaction intact.** Anthropic's Claude Code documentation states that after auto-compaction, only the first 5,000 tokens of each invoked skill are re-attached, inside a shared 25,000-token budget. A long skill — or a rule sitting on page nine of one — can silently disappear from the next turn. That is why `SKILL.md` in this repo puts the seven steps first and keeps the file short.

The failure RuleLedger targets is therefore specific: not "the agent is bad at coding", but "the agent can no longer *see* the rule it is supposed to follow, and nobody notices until the ship".

## Install (30 seconds)

The repo lives under the GitHub account `guardyanz`.

**Agent Skills CLI (works across agents):**

```bash
npx skills add guardyanz/ruleledger
```

**Claude Code (plugin marketplace):**

```text
/plugin marketplace add guardyanz/ruleledger
/plugin install ruleledger@ruleledger-marketplace
```

**Manual (any agent that reads `SKILL.md`):**

```bash
git clone https://github.com/guardyanz/ruleledger.git ~/.claude/skills/ruleledger
```

## Quick start

```bash
# 1. In your project, extract your standing rules (Step 1–2).
#    The agent writes RULES.md from AGENTS.md / CLAUDE.md and freezes it.
# 2. Work as usual. Before shipping, the agent re-reads RULES.md,
#    maps the diff to the rules, and audits every rule (Steps 3–5).
# 3. Check the audit mechanically — no rule skipped, no unknown ID:
python scripts/ruleledger_check.py --rules RULES.md --audit AUDIT.md
```

## The seven steps

| Step | What happens | Output |
|------|--------------|--------|
| 1. Extract | Standing rules from `AGENTS.md` / `CLAUDE.md` / session instructions become numbered lines `R-01`, `R-02`, … — one rule, one line, no meaning-changing paraphrase. Zero rules → the skill skips, it does not fail. | `RULES.md` |
| 2. Freeze | SHA-256 hash + revision + date. Rules change only on an explicit user instruction, with a new revision. Contradictory rules → STOP and ask the user. | Frozen `RULES.md` |
| 3. Re-read | The agent reads `RULES.md` from disk again and states it did so, listing `R-01`–`R-n`, before writing any file that ships. No statement, no ship. | Re-read statement |
| 4. Map | Every changed hunk in `git diff` is mapped to a rule or explicitly marked "no rule applies". Unmapped hunks may not ship silently. | Hunk → rule map |
| 5. Audit | One PASS/FAIL row per rule, each with `file:line` evidence. One FAIL rejects the ship. The checker verifies completeness. | `AUDIT.md` + ship decision |
| 6. Record | The verdicts are appended to the ledger. A violation that was fixed stays recorded, with the fix and the re-audit. | `LEDGER.md` entry |
| 7. Carry | Next session — and right after any compaction — the agent reads the 5 most recent ledger entries before writing code. If the ledger cannot be read, it says so. | Recent-violations summary |

Full instructions, file templates, and worked PASS/FAIL examples are in [`SKILL.md`](SKILL.md).

## The checker

The checker requires Python 3.10 or newer. It has no runtime dependencies.

`scripts/ruleledger_check.py` uses only the Python standard library. It checks *completeness*, not truth: every rule in `RULES.md` must appear exactly once in `AUDIT.md`, with a PASS/FAIL verdict and `file:line` evidence, and no unknown rule IDs may appear. Judging whether a PASS is deserved is still the agent's job — the checker makes a silently skipped rule impossible.

Real output from the shipped examples (run 6 November 2026):

```text
$ python scripts/ruleledger_check.py --rules examples/pass-project/RULES.md --audit examples/pass-project/AUDIT.md
RuleLedger check
Rules: 5 (R-01, R-02, R-03, R-04, R-05)
Audit rows: 5
PASS: 5  FAIL: 0
Missing rules: none
Unknown rule IDs: none
Result: COMPLETE - every rule was audited.
Ship: ALLOWED - all rules passed.
```

```text
$ python scripts/ruleledger_check.py --rules examples/fail-project/RULES.md --audit examples/fail-project/AUDIT.md
RuleLedger check
Rules: 5 (R-01, R-02, R-03, R-04, R-05)
Audit rows: 5
PASS: 4  FAIL: 1
Missing rules: none
Unknown rule IDs: none
Result: COMPLETE - every rule was audited.
Ship: REJECTED - R-02 failed. Fix and re-audit; the failure stays in the ledger (Record step).
```

Note the second case exits `0`: the *audit* is complete, so the checker passes — it is the *ship* that is rejected. A FAIL verdict is the audit working, not the checker failing.

```bash
# Machine-readable output for CI:
python scripts/ruleledger_check.py --rules RULES.md --audit AUDIT.md --format json
```

## Worked examples

- [`examples/pass-project/`](examples/pass-project/) — a small project with 5 rules, a diff, a PASS audit, and a ledger. The handler delegates database access to a repository (`src/handlers.py:13`); the only query lives in `src/repository.py:9`.
- [`examples/fail-project/`](examples/fail-project/) — the same 5 rules with one violation: the handler calls `db.query` directly (`src/handlers.py:12`), so `R-02` FAILs, the ship is rejected, and the ledger records the failure, the fix, and the re-audit.

Both examples use the same generic rules — "All user-facing copy in English" and "No direct database access in request handlers" among them — so you can see the mechanism without any project-specific context.

## How this differs from the nearest neighbours

| Approach | What it protects | What it does not do |
|----------|------------------|---------------------|
| **RuleLedger** | Standing rules from being forgotten: extract → freeze → re-read → map → audit → record → carry, plus a mechanical completeness check. | It does not judge whether a PASS verdict is honest (see Limitations). |
| File-locking tools such as gstack's `/freeze` and `/guard` | Files from concurrent or conflicting edits. | They guard *files*, not *rules*. A frozen file can still be edited in a way that breaks a standing rule. Different problem. |
| Post-compaction summary ledgers (e.g. the Riyan ledger pattern) | Memory recovery: a summary written after compaction so the next session can catch up. | A summary helps you recover, but it does not gate the ship. RuleLedger's audit runs *before* shipping and one FAIL blocks it. |
| A plain `SKILL.md` with the rules pasted in | Nothing, structurally: the rules are in context until they rot. | No freeze, no re-read gate, no per-rule audit, no ledger, no completeness check. |

No standalone portable skill was found that combines all four: numbered extraction, a freeze hash, a pre-ship per-rule audit, and a carry-forward ledger. That combination — not any single step — is RuleLedger's claim. Each step on its own is deliberately unoriginal.

## Limitations — read before trusting this

- **The self-check paradox.** The agent that forgot a rule is the same agent asked to audit itself. RuleLedger shrinks the failure mode — a re-read from disk, a rule-by-rule table, a mechanical completeness check — but it cannot eliminate it. The checker proves no rule was *skipped*; it cannot prove a PASS verdict is *honest*. For high-stakes ships, have a second agent or a human read the audit table against the diff.
- **Rules must be checkable.** "Write clean code" cannot be audited; "All user-facing copy in English" can. Vague rules should be sharpened in Step 1, not silently passed in Step 5.
- **The ledger is a memory aid, not a proof.** The hash protects the rules from silent drift. It does not protect the audit from a careless author.
- **Scope.** This skill governs standing rules for code that ships. It does not review security, performance, or correctness beyond the rules you wrote.
- **No star or adoption claims.** This repo makes no promise about GitHub stars, forks, or downloads. Those depend on whether the mechanism earns trust in real sessions.

## Roadmap

- [ ] Pre-commit hook wrapper around the checker (`--staged` mode).
- [ ] GitHub Action that fails the PR check on an incomplete audit.
- [ ] Optional `--strict` mode: refuse an audit whose evidence lines fall outside the diff.
- [ ] Multi-file rules (`RULES/` directory) for projects with more than ~30 rules.
- [ ] A second-opinion mode: a different agent re-audits FAIL/PASS rows the first agent marked.

## Repository layout

```text
ruleledger/
├── SKILL.md                  # the skill: frontmatter + 7 steps + examples
├── .claude-plugin/
│   ├── marketplace.json      # Claude Code plugin marketplace manifest
│   └── plugin.json           # plain plugin metadata manifest
├── scripts/
│   └── ruleledger_check.py   # mechanical audit completeness checker (stdlib only)
├── tests/
│   └── test_validator.py     # validator and CLI regression tests, pytest
├── examples/
│   ├── pass-project/         # 5 rules, diff, PASS audit, ledger
│   └── fail-project/         # same rules, one violation, FAIL audit, ledger
├── README.md
├── CONTRIBUTING.md
├── SECURITY.md
├── CHANGELOG.md
└── LICENSE                   # MIT
```

## Contributing

To set up an isolated development environment and run the checks:

```bash
python -m venv .venv
# macOS / Linux:
source .venv/bin/activate
# Windows PowerShell:
# .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

GitHub Actions runs the validator tests on Linux and Windows with Python 3.10
and 3.14. The example projects are illustrative audit fixtures; their handler
snippets are not standalone applications and are excluded from test collection.

See [CONTRIBUTING.md](CONTRIBUTING.md). Bug reports should include the `RULES.md` and `AUDIT.md` that reproduce the problem (with secrets removed).

## License

MIT — see [LICENSE](LICENSE).
