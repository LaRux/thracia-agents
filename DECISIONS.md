# Architectural Decisions

This document records *why* each major decision was made. When a choice seems
arbitrary or you're tempted to change it, check here first.

---

## DEC-01: Python for all automation scripts (not JavaScript)

**Date:** 2026-03-21
**Decision:** Use Python 3 for all Phase 1 content generation and Phase 3 MCP server.
**Rationale:**
- Most beginner-friendly syntax for someone new to agent programming
- Anthropic's Python SDK is mature and well-documented
- Excellent libraries for reading PDFs, markdown, and structured data
**Exception:** Phase 2 Roll20 API scripts *must* be JavaScript — Roll20's API sandbox
only accepts JS. This is the only JS in the project.

---

## DEC-02: Hybrid pipeline architecture (3 phases)

**Date:** 2026-03-21
**Decision:** Build in three phases: content generation scripts → in-session Roll20
API tools → MCP server for full automation.
**Rationale:**
- Each phase delivers independent value. Phase 1 is useful without Phase 2 or 3.
- Complexity grows with skill level — Phase 1 requires basic Python; Phase 3 requires
  browser automation.
- Phase 3 is built *after* Phases 1 and 2, so we know exactly what Roll20 operations
  we need before investing in the Playwright bridge.
**Alternative considered:** Build MCP server first. Rejected — too complex upfront,
and we'd be building blind without knowing which operations actually matter.

---

## DEC-03: QAChecker runs automatically, never skipped

**Date:** 2026-03-21
**Decision:** QAChecker is the final step in every agent pipeline, invoked
automatically by run.py — it cannot be bypassed.
**Rationale:**
- Claude API output looks plausible but can be wrong (wrong HP, missing fields).
- Manual review of every output is impractical at scale.
- A single bad import into Roll20 could corrupt a session.
**Tradeoff:** Slows down generation slightly. Acceptable — correctness > speed.

---

## DEC-04: All Phase 2 Roll20 scripts are config-driven

**Date:** 2026-03-21
**Decision:** No game data (conditions, resources, rules) hardcoded in Roll20 API
script logic. All data lives in companion JSON config files.
**Rationale:**
- Adding a new condition or resource should mean editing a JSON file, not JS code.
- Phase 1 agents can generate or update config files programmatically.
- Reduces the risk of breaking script logic when extending the campaign.

---

## DEC-05: SessionScribe writes drafts only

**Date:** 2026-03-21
**Decision:** SessionScribe never writes directly to the Obsidian vault. All output
goes to data/output/session-draft/ for human review before vault commit.
**Rationale:**
- SessionScribe interprets natural language and will make mistakes early on.
- Corrupting session history is worse than the inconvenience of a review step.
- The draft workflow creates a feedback loop for improving the prompt over time.

---

## DEC-06: Obsidian vault is the source of truth

**Date:** 2026-03-21
**Decision:** All canonical campaign data lives in the vault. Roll20 receives copies.
Agents read from staged copies in data/input/, never directly from the vault.
**Rationale:**
- The vault is carefully maintained. It should not be at risk from automated processes.
- Staged input creates a deliberate gate: you choose what the agents process.
- If Roll20 and vault data ever diverge, the vault wins.

---

## DEC-07: MonsterGen does gap analysis first

**Date:** 2026-03-21
**Decision:** MonsterGen's first task is to identify which Thracia monsters are
*missing* from Roll20, then generate only those. It does not regenerate existing NPCs.
**Rationale:**
- Live Roll20 export revealed 105 NPCs already built. Regenerating them would waste
  time and risk overwriting work already done.
- Gap analysis output (monster-gaps.json) also serves as a QA artifact — a record
  of what was generated and why.

---

## DEC-08: Armor vectors stored as text until SheetPatcher

**Date:** 2026-03-21
**Decision:** Until SheetPatcher (Plan 03) adds proper P/S/B AC fields to the sheet,
MonsterGen stores armor vectors in the NPC description field as plain text
(e.g. "AC: P14/S14/B12"). No new fields are invented.
**Rationale:**
- Inventing field names that don't exist in the sheet would create invisible data —
  stored but never displayed.
- Text in description is visible immediately and can be read by RulesRef.js.
- Keeps MonsterGen simple until the sheet is fixed.

---

## DEC-09: conda for Python environment management

**Date:** 2026-03-21
**Decision:** Use conda environments (conda activate thracia-agents) rather than
Python venv.
**Rationale:**
- User already has Anaconda installed — no additional tooling needed.
- conda environments work identically to venv for this project's purposes.
**Note:** Use 'type' instead of 'cat' in Anaconda Prompt (Windows CMD).
