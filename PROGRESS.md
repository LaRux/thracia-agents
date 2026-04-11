# Thracia Agents — Project Journal

## Current Sprint
- **Phase:** Phase 1 — Plan 03 complete
- **Active task:** None
- **Blocked on:** —
- **Next session goal:** Plan 04 — RoomGen + EncounterGen

## Completed
- 2026-03-21 — System architecture designed and spec written
- 2026-03-21 — Live Roll20 export analyzed (110 characters, 24 maps)
- 2026-03-21 — roll20-npc-schema.md populated with exact field names
- 2026-03-21 — SheetAuditor gaps pre-identified (6 gaps documented)
- 2026-03-21 — Project scaffold created (folders, STATUS files, .gitignore)
- 2026-03-21 — run.py CLI scaffold with 9 passing tests
- 2026-03-21 — PROGRESS.md, DECISIONS.md, skill files created
- 2026-03-21 — Plan 01 (Project Continuity Infrastructure) complete
- 2026-04-04 — Plan 02 complete: parse_statblocks, gap_analysis, monster_gen, qa_checker
- 2026-04-11 — Plan 03 complete: utils, sheet_auditor, sheet_patcher — 66 NPCs audited, 58 patched, 8 manual

## Backlog (ordered by priority)
1. ~~Phase 1: MonsterGen + QAChecker (Plan 02)~~ ✓
2. ~~Phase 1: SheetAuditor + SheetPatcher (Plan 03)~~ ✓
3. Phase 1: RoomGen + EncounterGen (Plan 04)
4. Phase 2: TurnTracker + ResourceManager (Plan 05)
5. Phase 2: MoraleBot + ConditionTracker (Plan 06)
6. Phase 2: RulesRef + SheetValidator (Plan 07)
7. Phase 3: MCP Server — read tools (Plan 08)
8. Phase 3: MCP Server — write tools (Plan 09)
9. Phase 3: SessionScribe (Plan 10)

## Key Decisions Log
- **Language:** Python for all scripts — readable, beginner-friendly, great Claude API support
- **Architecture:** Hybrid pipeline (Phase 1 scripts + Phase 2 Roll20 API + Phase 3 MCP server)
- **Roll20 access:** Roll20 API (Pro) for in-session scripts; Playwright for Phase 3 external access
- **QA gate:** QAChecker runs automatically after every agent — never skipped
- **SessionScribe:** Draft-only output — never writes directly to vault
- **Config-driven:** All Phase 2 Roll20 scripts are config-driven — no game data in logic
- **Skill files:** Stored in .claude/commands/, invoked via /thracia-* at session start
- **Python env:** conda environment named thracia-agents (activate: conda activate thracia-agents)
- **MonsterGen scope:** Gap analysis first — 105 NPCs already exist in Roll20
- **Windows note:** Use 'type' instead of 'cat' in Anaconda Prompt

## Session Notes
### Session 1 (2026-03-21)
- Completed full architecture brainstorm and spec
- Ran live Roll20 export — discovered 105 existing NPCs, 24 maps
- Pre-populated NPC schema and SheetAuditor findings from export data
- Completed Plan 01: project scaffold, run.py with TDD, all tracking docs
