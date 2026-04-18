# Thracia Agents — Session Context

Use this skill at the start of every Claude Code session on this project.
It gives you full project awareness instantly — no reconstruction needed.

## Project Overview
AI-assisted automation system for the Caverns of Thracia Roll20 campaign.
Built in Python (content generation) + JavaScript (Roll20 in-session tools) +
Python MCP server (Phase 3 automation).

**Project root:** C:\Users\lheur\Documents\thracia-agents\
**GitHub:** https://github.com/LaRux/thracia-agents
**Obsidian vault:** C:\Users\lheur\Documents\Obsidian Vault\
**Spec:** docs/superpowers/specs/2026-03-21-thracia-roll20-automation-design.md
**Plans:** docs/superpowers/plans/

## Current Status
- **Phase:** Phase 1 — Content Generation (in progress)
- **Last completed:** Plan 04 — RoomGen + EncounterGen (PDF extraction → Roll20 handout JSONs + wandering table API scripts)
- **Active task:** None — starting fresh
- **Next goal:** Plan 05 (TBD) — Phase 1 complete; consider Phase 2 (Roll20 API scripts) or smoke-testing the full pipeline

## Environment
- Python: conda environment named thracia-agents
- Activate with: conda activate thracia-agents
- Run tests: python -m pytest tests/ -v
- CLI entry point: python run.py <command>
- Windows note: use 'type' instead of 'cat' in Anaconda Prompt

## Key Technical Facts
- All agent output goes to data/output/pending/ → QAChecker → ready/ or flagged/
- Never read from Obsidian vault directly — copy source to data/input/ first
- Agents live in agents/in-progress/ while building, move to agents/done/ when complete
- Roll20 NPC field schema documented in docs/roll20-npc-schema.md
- 105 NPCs already exist in Roll20 — MonsterGen does gap analysis first
- Roll20 export files staged in data/input/thracia-exports/ (characters + maps JSON)
- SheetAuditor reads thracia-characters.json, audits all active NPCs (is_npc="1", archived=false)
- SheetAuditor produces audit_report.md (human review) + audit_report.json (machine input)
- SheetPatcher reads audit_report.json, writes full replacement sheets to data/output/pending/
- average_from_hd helper lives in agents/in-progress/utils.py (shared by MonsterGen + SheetAuditor)
- strip_sign returns 0 for blank strings; build_hit_points falls back to hd average if hp_avg empty

## Git Log (as of Plan 04 completion)
1. chore: initialize project with Python dependencies and gitignore
2. chore: create project folder structure and phase status files
3. feat: add run.py CLI scaffold with 9 passing argument parsing tests
4. docs: add project journal and architectural decisions log
5. feat: add Claude skill files for session context loading
— Plan 02 (MonsterGen + QAChecker) —
6. feat: add DCC stat block parser with 22 passing tests
7. feat: add 5e stat block parser with CR->HD table and alignment mapping
8. feat: add merge logic and CSV writer to parse_statblocks
9. feat: add gap_analysis module with 10 passing tests
10. feat: add monster_gen deterministic transforms with 19 passing tests
11. feat: add Claude API integration for monster sheet generation, 13 passing tests
12. feat: add monster_gen CLI dispatch and file I/O
13. feat: add qa_checker Pass 1 mechanical validation with 10 passing tests
14. feat: add qa_checker Pass 2 and file routing with 6 new tests
15. feat: wire all Plan 02 modules into run.py — MonsterGen + QAChecker complete
16. fix: improve crit parsing — extract table/die separately from threat range
— Plan 03 (SheetAuditor + SheetPatcher) —
17. fix: port session bugfixes — strip_sign blank handling, build_hit_points hd fallback
18. feat: update sheet CLI to --audit/--patch flags (combinable)
19. feat: add sheet_auditor NPC filter and character loading
20. feat: add check_sheet with full quality check suite
21. feat: add assemble_full_sheet and audit_characters
22. feat: add audit report generation (md + json)
23. feat: wire SheetAuditor into run.py sheet --audit command
24. feat: add SheetPatcher and wire sheet --patch command
25. chore: mark Plan 03 complete in PROGRESS.md
— Plan 04 (RoomGen + EncounterGen) —
26. chore: move all docs from Obsidian vault into project repo
27. docs: add Plan 04 RoomGen + EncounterGen implementation plan
28. chore: install pdfplumber and add pdf_sections.json config
29. feat: add parse_pdf extraction module with room splitting and 9 passing tests
30. feat: add encounter_gen prompt template
31. feat: add room_gen prompt template
32. feat: add room_gen agent with handout JSON generation and 12 passing tests
33. feat: add encounter_gen agent with JS table generation and 12 passing tests
34. fix: anchor encounter_gen paths to project root, raise on validation failure
35. feat: extend QAChecker with handout validation pass and 7 new tests
36. feat: wire room and encounter commands into run.py with full CLI and handler dispatch
37. fix: correct level None check and add config KeyError guard in run.py

## Update Instructions
Update this file at the end of every session:
- Change "Current Status" to reflect what was completed
- Update "Next goal" to the next plan/task
- Add the new commit to "Git Log"
