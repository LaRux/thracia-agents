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
**Spec:** docs/superpowers/specs/2026-03-21-thracia-roll20-automation-design.md (in vault)
**Plans:** docs/superpowers/plans/ (in vault)

## Current Status
- **Phase:** Infrastructure complete — Phase 1 ready to begin
- **Last completed:** Plan 01 — full project scaffold, run.py CLI, tracking docs, skill files
- **Active task:** None — starting fresh
- **Next goal:** Plan 02 — MonsterGen gap analysis + QAChecker

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
- 6 sheet gaps pre-identified — see plans/2026-03-21-03-pre-notes-sheet-auditor.md

## Git Log (as of Plan 01 completion)
1. chore: initialize project with Python dependencies and gitignore
2. chore: create project folder structure and phase status files
3. feat: add run.py CLI scaffold with 9 passing argument parsing tests
4. docs: add project journal and architectural decisions log
5. feat: add Claude skill files for session context loading

## Update Instructions
Update this file at the end of every session:
- Change "Current Status" to reflect what was completed
- Update "Next goal" to the next plan/task
- Add the new commit to "Git Log"
