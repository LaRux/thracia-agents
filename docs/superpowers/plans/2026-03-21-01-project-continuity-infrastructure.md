# Project Continuity Infrastructure — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the project folder structure, Python environment, CLI scaffold, project tracking documents, and Claude skill files that every subsequent plan builds on.

**Architecture:** A `thracia-agents/` directory holds all Python code, organized into `agents/`, `data/`, `prompts/`, and per-phase folders. A minimal `run.py` provides the single CLI entry point for all agents. Claude skill files in `.claude/commands/` give Claude instant project context at the start of every work session.

**Tech Stack:** Python 3 (standard library only for this plan), pytest, git, argparse.

**Spec:** `C:\Users\lheur\Documents\Obsidian Vault\docs\superpowers\specs\2026-03-21-thracia-roll20-automation-design.md`

---

## How to Use This Plan

Each task is a self-contained unit of work with an explicit verification step. Tasks are ordered — don't skip ahead. If something fails, fix it before moving on. Commit after each task so you always have a working restore point.

**Estimated time:** 2–4 hours for a first-time session.

**Before starting:** Open this file in Obsidian and tick boxes as you go (`- [x]`). Update `PROGRESS.md` at the end.

---

## File Map

These are all the files this plan creates. Read this before starting — it shows you where everything lands and why.

```
thracia-agents/                          ← project root
│
├── .claude/commands/                    ← Claude skill files (loaded via /thracia-* commands)
│   ├── thracia-context.md               ← session start: current phase, active task, decisions
│   ├── thracia-rules.md                 ← homebrew rules summary so Claude never asks "what's an armor vector?"
│   ├── thracia-vault.md                 ← Obsidian vault map so Claude knows where things live
│   └── thracia-roll20.md                ← Roll20 campaign structure and character roster
│
├── agents/                              ← Python agent files
│   ├── done/                            ← completed and tested agents (currently empty)
│   ├── in-progress/                     ← the agent you're actively building
│   └── backlog/                         ← agents not yet started
│
├── data/
│   ├── input/                           ← staged copies from Obsidian vault (safe to process)
│   └── output/
│       ├── pending/                     ← raw agent output, awaiting QA
│       ├── ready/                       ← passed QA — safe to import to Roll20
│       └── flagged/                     ← failed QA — needs human review
│
├── docs/
│   └── roll20-npc-schema.md             ← placeholder — filled during MonsterGen sprint
│
├── phase1-content-gen/STATUS.md         ← Phase 1 at-a-glance status
├── phase2-session-tools/STATUS.md       ← Phase 2 at-a-glance status
├── phase3-mcp-server/STATUS.md          ← Phase 3 at-a-glance status
│
├── prompts/                             ← plain-text instructions for each agent (edit to tune)
│
├── tests/
│   └── test_cli.py                      ← tests for run.py CLI argument parsing
│
├── .gitignore                           ← excludes .venv, __pycache__, output data, secrets
├── DECISIONS.md                         ← permanent log of architectural choices + rationale
├── PROGRESS.md                          ← running project journal
├── requirements.txt                     ← Python dependencies
└── run.py                               ← single CLI entry point for all agents
```

---

## Chunk 1: Python Environment and Git Setup

**What this does:** Installs a proper Python, initializes git, creates the project directory, and sets up a virtual environment. A virtual environment is a self-contained Python installation just for this project — it keeps your project's dependencies isolated from anything else on your machine.

---

### Task 1: Verify Python installation

- [ ] **Step 1: Check if Python is properly installed**

Open a terminal (Git Bash or Windows Terminal) and run:
```bash
python --version
```

Expected: `Python 3.11.x` or higher (any 3.x version ≥ 3.10 is fine).

If you get `Python 3.x.x (Microsoft Store)` or an error, you need a real Python install.

- [ ] **Step 2: If Python is missing or is the Store stub, install it**

Download from https://www.python.org/downloads/ — choose the latest stable 3.x release.
During installation: **check "Add Python to PATH"** before clicking Install.

After installing, close and reopen your terminal, then re-run `python --version` to confirm.

- [ ] **Step 3: Verify pip is available**

```bash
python -m pip --version
```

Expected: `pip 24.x.x from ...` (version doesn't matter much).

---

### Task 2: Create the project directory and initialize git

- [ ] **Step 1: Decide where to put the project**

This is a code project, not campaign notes — it should live alongside your campaign folder, not inside the Obsidian vault. Suggested location:

```
C:\Users\lheur\Documents\thracia-agents\
```

- [ ] **Step 2: Create the directory and initialize git**

```bash
mkdir -p "C:/Users/lheur/Documents/thracia-agents"
cd "C:/Users/lheur/Documents/thracia-agents"
git init
```

Expected output: `Initialized empty Git repository in .../thracia-agents/.git/`

- [ ] **Step 3: Set git identity if this is a new machine**

```bash
git config user.name "Your Name"       # replace with your actual name
git config user.email "your@email.com" # replace with your actual email
```

No output expected — this is silent if it works.

---

### Task 3: Create and activate the virtual environment

- [ ] **Step 1: Create the virtual environment**

From inside `thracia-agents/`:
```bash
python -m venv .venv
```

This creates a `.venv/` folder — your project's private Python installation.

Expected: A `.venv/` directory appears. No other output.

- [ ] **Step 2: Activate it**

In Git Bash on Windows:
```bash
source .venv/Scripts/activate
```

Expected: Your prompt changes to show `(.venv)` at the start — e.g., `(.venv) lheur@machine`.

**Why this matters:** After activating, any `python` or `pip` command uses the project's private Python, not your system Python. Run this activation command at the start of every work session.

- [ ] **Step 3: Verify you're using the virtual environment's Python**

```bash
which python
```

Expected: A path containing `.venv` — e.g., `/c/Users/lheur/Documents/thracia-agents/.venv/Scripts/python`

---

### Task 4: Install dependencies and create requirements.txt

- [ ] **Step 1: Install the Anthropic SDK and pytest**

```bash
pip install anthropic pytest
```

Expected: Several packages install. Final line should be `Successfully installed ...`

- [ ] **Step 2: Create requirements.txt**

```bash
pip freeze > requirements.txt
```

This saves the exact versions of everything installed. When you (or Claude) sets up this project on a new machine later, `pip install -r requirements.txt` restores everything.

- [ ] **Step 3: Verify requirements.txt was created**

```bash
cat requirements.txt
```

Expected: A list of packages including `anthropic` and `pytest`.

---

### Task 5: Create .gitignore and make first commit

- [ ] **Step 1: Create .gitignore**

Create the file `C:/Users/lheur/Documents/thracia-agents/.gitignore` with this content:

```gitignore
# Python virtual environment — never commit this, it's machine-specific
.venv/

# Python bytecode — generated automatically, not source code
__pycache__/
*.pyc
*.pyo

# Generated output data — too large and noisy for git
data/output/

# API keys and secrets — NEVER commit these
.env
*.env
secrets.json

# VS Code workspace settings
.vscode/

# macOS garbage files
.DS_Store
```

- [ ] **Step 2: Make the first commit**

```bash
git add requirements.txt .gitignore
git commit -m "chore: initialize project with Python dependencies and gitignore"
```

Expected: `[main (root-commit) xxxxxxx] chore: initialize project with Python dependencies and gitignore`

---

## Chunk 2: Project Folder Scaffold

**What this does:** Creates all the empty directories and placeholder files that define the project's shape. Empty directories can't be committed to git, so we add `.gitkeep` files — tiny placeholder files whose only purpose is to make git track the folder.

---

### Task 6: Create the directory structure

- [ ] **Step 1: Create all directories at once**

From inside `thracia-agents/`:
```bash
mkdir -p \
  agents/done \
  agents/in-progress \
  agents/backlog \
  data/input \
  data/output/pending \
  data/output/ready \
  data/output/flagged \
  docs \
  phase1-content-gen \
  phase2-session-tools \
  phase3-mcp-server \
  prompts \
  tests \
  .claude/commands
```

- [ ] **Step 2: Add .gitkeep files to empty directories**

```bash
touch \
  agents/done/.gitkeep \
  agents/in-progress/.gitkeep \
  agents/backlog/.gitkeep \
  data/input/.gitkeep \
  data/output/pending/.gitkeep \
  data/output/ready/.gitkeep \
  data/output/flagged/.gitkeep \
  prompts/.gitkeep
```

- [ ] **Step 3: Verify the structure looks right**

```bash
find . -not -path './.git/*' -not -path './.venv/*' | sort
```

Expected: A tree of all the files and folders you just created.

---

### Task 7: Create per-phase STATUS.md files

These give you an at-a-glance view of each phase's progress without opening code.

- [ ] **Step 1: Create phase1-content-gen/STATUS.md**

```markdown
# Phase 1 — Content Generation Status

**Stack:** Python 3, Anthropic SDK, Claude API

## Agents

| Agent | Status | Notes |
|---|---|---|
| MonsterGen | Not started | |
| QAChecker | Not started | |
| SheetAuditor | Not started | |
| SheetPatcher | Not started | |
| RoomGen | Not started | |
| EncounterGen | Not started | |

## Last Updated
2026-03-21 — Phase 1 not yet started.
```

- [ ] **Step 2: Create phase2-session-tools/STATUS.md**

```markdown
# Phase 2 — In-Session Tools Status

**Stack:** JavaScript (Roll20 API sandbox)

## Scripts

| Script | Status | Notes |
|---|---|---|
| TurnTracker.js | Not started | |
| ResourceManager.js | Not started | |
| MoraleBot.js | Not started | |
| ConditionTracker.js | Not started | |
| RulesRef.js | Not started | |
| SheetValidator.js | Not started | Depends on SheetPatcher (Phase 1) |

## Last Updated
2026-03-21 — Phase 2 not yet started. Begins after Phase 1 is stable.
```

- [ ] **Step 3: Create phase3-mcp-server/STATUS.md**

```markdown
# Phase 3 — MCP Server Status

**Stack:** Python 3, MCP SDK, Playwright

## Tools

| Tool | Status | Notes |
|---|---|---|
| pull_character_summary | Not started | First tool to build — read-only |
| read_characters | Not started | |
| write_character | Not started | |
| push_xp | Not started | |
| push_ability_loss | Not started | |
| push_resource_state | Not started | |
| bulk_import | Not started | |
| read_journal | Not started | |
| export_session | Not started | |
| SessionScribe | Not started | Depends on export_session |

## Last Updated
2026-03-21 — Phase 3 not yet started. Begins after Phase 2 is stable.
```

- [ ] **Step 4: Create docs/roll20-npc-schema.md placeholder**

```markdown
# Roll20 NPC Character Sheet Schema

**Status:** Placeholder — will be filled during MonsterGen build sprint.

During that sprint, inspect the DCC character sheet template in Roll20 (Campaign Settings
→ Character Sheet Template → view source) to map exact field names.

## Key fields to document
- HP field name(s) (likely bar1_value / bar1_max)
- AC field name(s) — needs P/S/B variants for armor vector system
- Attack fields
- Attribute fields (STR, AGL, STA, PER, INT, LUCK)
- Custom homebrew fields to add (fear stack count, madness type, ability loss)
```

- [ ] **Step 5: Commit the scaffold**

```bash
git add .
git commit -m "chore: create project folder structure and phase status files"
```

---

## Chunk 3: run.py CLI Scaffold (TDD)

**What this does:** Builds the `run.py` entry point using Test-Driven Development (TDD). TDD means writing the test *before* writing the code — this forces you to think about how the code should behave before worrying about how to implement it. For a learner, TDD is valuable because the tests become documentation of what the code is supposed to do.

**Why a central run.py?** Rather than running `python agents/monster_gen.py`, you always run `python run.py monster`. This means every agent speaks the same "language" from the terminal, and you only need to remember one command structure.

---

### Task 8: Write the failing CLI tests

- [ ] **Step 1: Create tests/test_cli.py**

```python
# tests/test_cli.py
#
# Tests for run.py's CLI argument parsing.
#
# Why test argument parsing? Because run.py is the entry point for everything —
# if its argument parsing is wrong, every agent breaks. These tests lock in the
# expected command interface so future changes don't silently break it.

import pytest
import sys
from unittest.mock import patch


def parse_args(args):
    """Import and call the parser from run.py. Imported here so tests don't
    require run.py to exist yet — the ImportError becomes the test failure."""
    from run import build_parser
    parser = build_parser()
    return parser.parse_args(args)


class TestMonsterCommand:
    def test_monster_with_level(self):
        """'python run.py monster --level 1' should parse correctly."""
        args = parse_args(['monster', '--level', '1'])
        assert args.command == 'monster'
        assert args.level == 1

    def test_monster_with_input_file(self):
        """'python run.py monster --input path/to/file.md' should parse correctly."""
        args = parse_args(['monster', '--input', 'data/input/gnoll.md'])
        assert args.command == 'monster'
        assert args.input == 'data/input/gnoll.md'

    def test_monster_requires_level_or_input(self):
        """'python run.py monster' with no flags should fail."""
        with pytest.raises(SystemExit):
            parse_args(['monster'])


class TestRoomCommand:
    def test_room_with_input_file(self):
        args = parse_args(['room', '--input', 'data/input/1-1-entry-hall.md'])
        assert args.command == 'room'
        assert args.input == 'data/input/1-1-entry-hall.md'


class TestEncounterCommand:
    def test_encounter_with_level(self):
        args = parse_args(['encounter', '--level', '1'])
        assert args.command == 'encounter'
        assert args.level == 1


class TestQACommand:
    def test_qa_with_input_dir(self):
        args = parse_args(['qa', '--input', 'data/output/pending/'])
        assert args.command == 'qa'
        assert args.input == 'data/output/pending/'


class TestSheetCommand:
    def test_sheet_audit(self):
        args = parse_args(['sheet', 'audit'])
        assert args.command == 'sheet'
        assert args.sheet_action == 'audit'

    def test_sheet_patch(self):
        args = parse_args(['sheet', 'patch'])
        assert args.command == 'sheet'
        assert args.sheet_action == 'patch'


class TestSessionCommand:
    def test_session_commit(self):
        args = parse_args(['session', 'commit'])
        assert args.command == 'session'
        assert args.session_action == 'commit'
```

- [ ] **Step 2: Run the tests — they must fail**

```bash
python -m pytest tests/test_cli.py -v
```

Expected: All tests fail with `ImportError: cannot import name 'build_parser' from 'run'`
(or `ModuleNotFoundError: No module named 'run'` if run.py doesn't exist yet)

This is correct — the tests fail because we haven't written the code yet. That's TDD.

---

### Task 9: Write minimal run.py to make tests pass

- [ ] **Step 1: Create run.py**

```python
# run.py
#
# Central CLI entry point for all Thracia agents.
#
# Usage examples:
#   python run.py monster --level 1
#   python run.py monster --input data/input/gnoll.md
#   python run.py room --input "data/input/1-1 Entry Hall.md"
#   python run.py encounter --level 1
#   python run.py qa --input data/output/pending/
#   python run.py sheet audit
#   python run.py sheet patch
#   python run.py session commit
#
# Why one entry point for everything?
# Having a single run.py means you always know how to invoke any agent — just
# 'python run.py <command>'. It also means we can add shared setup (logging,
# API key loading, output directory creation) in one place rather than in every
# individual agent file.

import argparse
import sys


def build_parser():
    """Build and return the argument parser.

    Kept as a separate function (rather than inline in main()) so that tests
    can import and call it directly without triggering the actual agent logic.
    """
    # The top-level parser — handles 'python run.py <command>'
    parser = argparse.ArgumentParser(
        description="Thracia campaign automation agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  monster    Generate Roll20 NPC sheets from stat block source material
  room       Generate DM descriptions and player handouts for dungeon rooms
  encounter  Generate wandering monster tables for a dungeon level
  qa         Run QA validation on pending agent output
  sheet      Audit or patch the Roll20 DCC character sheet
  session    Commit a reviewed post-session draft to the Obsidian vault
        """
    )

    # Subparsers handle 'python run.py monster', 'python run.py room', etc.
    # dest='command' means the chosen subcommand is stored as args.command
    subparsers = parser.add_subparsers(dest='command')
    subparsers.required = True  # fail with usage message if no command given

    # --- monster command ---
    monster_parser = subparsers.add_parser(
        'monster',
        help='Generate Roll20 NPC sheets from source material'
    )
    # mutually_exclusive_group means: provide --level OR --input, not both, not neither
    monster_group = monster_parser.add_mutually_exclusive_group(required=True)
    monster_group.add_argument(
        '--level', type=int,
        help='Process all monsters for a dungeon level (e.g. --level 1)'
    )
    monster_group.add_argument(
        '--input', type=str,
        help='Process a single input file (e.g. --input data/input/gnoll.md)'
    )

    # --- room command ---
    room_parser = subparsers.add_parser(
        'room',
        help='Generate room descriptions and player handouts'
    )
    room_parser.add_argument(
        '--input', type=str, required=True,
        help='Path to room note markdown file'
    )

    # --- encounter command ---
    encounter_parser = subparsers.add_parser(
        'encounter',
        help='Generate wandering monster tables for a dungeon level'
    )
    encounter_parser.add_argument(
        '--level', type=int, required=True,
        help='Dungeon level to generate encounter table for'
    )

    # --- qa command ---
    qa_parser = subparsers.add_parser(
        'qa',
        help='Run QA validation on pending agent output'
    )
    qa_parser.add_argument(
        '--input', type=str, required=True,
        help='Directory containing pending output (e.g. data/output/pending/)'
    )

    # --- sheet command ---
    sheet_parser = subparsers.add_parser(
        'sheet',
        help='Audit or patch the Roll20 DCC character sheet'
    )
    sheet_subparsers = sheet_parser.add_subparsers(dest='sheet_action')
    sheet_subparsers.required = True
    sheet_subparsers.add_parser('audit', help='Generate gap report')
    sheet_subparsers.add_parser('patch', help='Generate patch proposals')

    # --- session command ---
    session_parser = subparsers.add_parser(
        'session',
        help='Commit a reviewed post-session draft to the vault'
    )
    session_subparsers = session_parser.add_subparsers(dest='session_action')
    session_subparsers.required = True
    session_subparsers.add_parser('commit', help='Apply approved session draft to vault')

    return parser


def main():
    """Parse arguments and dispatch to the appropriate agent.

    Right now this just prints a 'not yet implemented' message for every command.
    Each agent plan will add a real implementation here.
    """
    parser = build_parser()
    args = parser.parse_args()

    # Dispatch table — maps command names to handler functions.
    # As agents are built, replace the placeholder lambdas with real imports.
    handlers = {
        'monster':   lambda a: print(f"[MonsterGen] Not yet implemented. Args: {vars(a)}"),
        'room':      lambda a: print(f"[RoomGen] Not yet implemented. Args: {vars(a)}"),
        'encounter': lambda a: print(f"[EncounterGen] Not yet implemented. Args: {vars(a)}"),
        'qa':        lambda a: print(f"[QAChecker] Not yet implemented. Args: {vars(a)}"),
        'sheet':     lambda a: print(f"[Sheet {a.sheet_action}] Not yet implemented. Args: {vars(a)}"),
        'session':   lambda a: print(f"[Session {a.session_action}] Not yet implemented. Args: {vars(a)}"),
    }

    handler = handlers.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


# Standard Python idiom: only run main() if this file is executed directly.
# If run.py is imported (e.g. in tests), main() is not called.
if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Run the tests — they must pass now**

```bash
python -m pytest tests/test_cli.py -v
```

Expected:
```
tests/test_cli.py::TestMonsterCommand::test_monster_with_level PASSED
tests/test_cli.py::TestMonsterCommand::test_monster_with_input_file PASSED
tests/test_cli.py::TestMonsterCommand::test_monster_requires_level_or_input PASSED
tests/test_cli.py::TestRoomCommand::test_room_with_input_file PASSED
tests/test_cli.py::TestEncounterCommand::test_encounter_with_level PASSED
tests/test_cli.py::TestQACommand::test_qa_with_input_dir PASSED
tests/test_cli.py::TestSheetCommand::test_sheet_audit PASSED
tests/test_cli.py::TestSheetCommand::test_sheet_patch PASSED
tests/test_cli.py::TestSessionCommand::test_session_commit PASSED

9 passed in 0.xxs
```

If any tests fail, read the error message carefully — it will tell you exactly what's wrong.

- [ ] **Step 3: Manually verify run.py works from the terminal**

```bash
python run.py monster --level 1
```
Expected: `[MonsterGen] Not yet implemented. Args: {'command': 'monster', 'level': 1, 'input': None}`

```bash
python run.py --help
```
Expected: The help message showing all available commands.

- [ ] **Step 4: Commit**

```bash
git add run.py tests/test_cli.py
git commit -m "feat: add run.py CLI scaffold with argument parsing tests"
```

---

## Chunk 4: Project Tracking Documents

**What this does:** Creates `PROGRESS.md` and `DECISIONS.md` — the documents you and Claude will read at the start of every session to reconstruct project context.

---

### Task 10: Create PROGRESS.md

- [ ] **Step 1: Create PROGRESS.md in project root**

```markdown
# Thracia Agents — Project Journal

## Current Sprint
- **Phase:** Infrastructure (pre-Phase 1)
- **Active task:** Creating project continuity infrastructure
- **Blocked on:** —
- **Next session goal:** Begin Phase 1 — MonsterGen agent (Plan 02)

## Completed
- 2026-03-21 — System architecture designed and spec written
- 2026-03-21 — Project scaffold created (folders, STATUS files)
- 2026-03-21 — run.py CLI scaffold with passing tests

## Backlog (ordered by priority)
1. Phase 1: MonsterGen + QAChecker (Plan 02)
2. Phase 1: SheetAuditor + SheetPatcher (Plan 03)
3. Phase 1: RoomGen + EncounterGen (Plan 04)
4. Phase 2: TurnTracker + ResourceManager (Plan 05)
5. Phase 2: MoraleBot + ConditionTracker (Plan 06)
6. Phase 2: RulesRef + SheetValidator (Plan 07)
7. Phase 3: MCP Server — read tools (Plan 08)
8. Phase 3: MCP Server — write tools (Plan 09)
9. Phase 3: SessionScribe (Plan 10)

## Key Decisions Log
- **Language:** Python for all scripts (not JS) — readable, beginner-friendly, great Claude API support
- **Architecture:** Hybrid pipeline (Phase 1 scripts + Phase 2 Roll20 API + Phase 3 MCP server)
- **Roll20 access:** Roll20 API (Pro) for in-session scripts; Playwright browser automation for Phase 3 external access
- **QA gate:** QAChecker runs automatically after every agent — never skipped
- **SessionScribe:** Draft-only output — never writes directly to vault
- **Config-driven:** All Phase 2 Roll20 scripts are config-driven — no game data hardcoded in logic
- **Skill files:** Stored in .claude/commands/, invoked via /thracia-* at session start
```

- [ ] **Step 2: Commit PROGRESS.md**

```bash
git add PROGRESS.md
git commit -m "docs: add project journal with initial status and backlog"
```

---

### Task 11: Create DECISIONS.md

- [ ] **Step 1: Create DECISIONS.md in project root**

```markdown
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
- Large ecosystem for data manipulation
**Exception:** Phase 2 Roll20 API scripts *must* be JavaScript — Roll20's API sandbox
only accepts JS. This is the only JS in the project.

---

## DEC-02: Hybrid pipeline architecture (3 phases)

**Date:** 2026-03-21
**Decision:** Build in three phases: content generation scripts → in-session Roll20
API tools → MCP server for full automation.
**Rationale:**
- Each phase delivers independent value. Phase 1 is useful without Phase 2 or 3.
- Complexity grows with skill level. Phase 1 requires basic Python; Phase 3 requires
  browser automation.
- Phase 3 is built *after* Phases 1 and 2, so we know exactly what Roll20 operations
  we need before investing in the Playwright bridge.
**Alternative considered:** Build MCP server first. Rejected — too complex for a
  first build, and we'd be building blind without knowing which Roll20 operations
  actually matter.

---

## DEC-03: QAChecker runs automatically, never skipped

**Date:** 2026-03-21
**Decision:** QAChecker is the final step in every agent pipeline. run.py invokes it
automatically — it cannot be bypassed.
**Rationale:**
- Claude API output looks plausible but can be wrong (wrong HP values, missing fields,
  rules inconsistencies). Manual review of every output is impractical at scale.
- A single bad import into Roll20 (wrong HP, wrong AC) could corrupt a session.
- The QA gate is the trust boundary between "generated" and "safe to use."
**Tradeoff:** Slows down generation. Acceptable — correctness > speed for campaign data.

---

## DEC-04: All Phase 2 Roll20 scripts are config-driven

**Date:** 2026-03-21
**Decision:** No game data (conditions, resources, rules) hardcoded in Roll20 API
script logic. All data lives in companion JSON config files.
**Rationale:**
- The campaign will evolve — new conditions, new resources, new rules. Config changes
  require editing a JSON file; code changes require understanding JavaScript.
- Config files are less risky to edit than script logic.
- Phase 1 agents can generate or update config files programmatically.

---

## DEC-05: SessionScribe writes drafts only

**Date:** 2026-03-21
**Decision:** SessionScribe never writes directly to the Obsidian vault. All output
goes to data/output/session-draft/ for human review before vault commit.
**Rationale:**
- SessionScribe interprets natural language (chat logs, shorthand notes) and will
  make mistakes — especially early on.
- Corrupting session history (wrong XP, wrong rooms visited) is worse than the
  inconvenience of a manual review step.
- The draft-first workflow also creates a feedback loop: reviewing the draft lets you
  improve the prompt when you see where it's wrong.

---

## DEC-06: Obsidian vault is the source of truth

**Date:** 2026-03-21
**Decision:** All canonical campaign data lives in the Obsidian vault. Roll20 receives
copies, not originals. Agents read from staged copies in data/input/, not directly
from the vault.
**Rationale:**
- The vault is carefully maintained and manually curated. It should not be at risk
  from automated processes.
- Staged input creates a deliberate gate: you choose what the agents process.
- If Roll20 data and vault data ever diverge, the vault wins.
```

- [ ] **Step 2: Commit DECISIONS.md**

```bash
git add DECISIONS.md
git commit -m "docs: add architectural decisions log with rationale"
```

---

## Chunk 5: Claude Skill Files

**What this does:** Creates the four skill files that load project context at the start of each Claude Code session. These are the most valuable continuity tool — invoking `/thracia-context` gives Claude an accurate picture of where the project stands in seconds.

**How Claude Code skill files work:** Any `.md` file placed in a `.claude/commands/` directory in your project is automatically available as a slash command. The filename becomes the command — `thracia-context.md` becomes `/thracia-context`. When you type that command, the file's contents are loaded as context for Claude.

---

### Task 12: Create thracia-context.md

This file is updated at the end of every work session. It's the most important of the four — it tells Claude exactly where you are in the project.

- [ ] **Step 1: Create .claude/commands/thracia-context.md**

```markdown
# Thracia Agents — Session Context

Use this skill at the start of every Claude Code session on this project.

## Project Overview
AI-assisted automation system for the Caverns of Thracia Roll20 campaign.
Built in Python (content generation) + JavaScript (Roll20 in-session tools) +
Python MCP server (Phase 3 automation). Project home: thracia-agents/.

## Current Status
- **Phase:** Infrastructure complete — Phase 1 ready to begin
- **Last completed:** Project scaffold, run.py CLI, PROGRESS.md, DECISIONS.md, skill files
- **Active task:** None — starting fresh
- **Next goal:** Plan 02 — MonsterGen + QAChecker agents

## Project Structure
See PROGRESS.md for full backlog and completed items.
See DECISIONS.md for rationale behind architectural choices.
See phase*/STATUS.md for per-phase progress.

## Key Technical Facts
- Python 3, venv at .venv/, activate with: source .venv/Scripts/activate
- Entry point: python run.py <command>
- Tests: python -m pytest tests/ -v
- Agents live in agents/in-progress/ while being built, move to agents/done/ when complete
- All agent output goes to data/output/pending/ → QAChecker → ready/ or flagged/
- Never read from Obsidian vault directly — copy source to data/input/ first

## Spec Document
docs/superpowers/specs/2026-03-21-thracia-roll20-automation-design.md

## Plans
docs/superpowers/plans/

## User Preferences
- New to agent programming — explain the "why" behind decisions
- Add copious inline comments to all code
- Always recommend iterative enhancements at the end of each task
- Working in weekend sprints — context continuity is critical
```

---

### Task 13: Create thracia-rules.md

This file means Claude never has to ask "what's an armor vector?" or re-read your homebrew rules.

- [ ] **Step 1: Create .claude/commands/thracia-rules.md**

```markdown
# Thracia Campaign — Homebrew Rules Reference

Load this when working on any agent that generates or validates game content.

## Core System
Dungeon Crawl Classics (DCC) RPG with the following homebrew modifications.

## The Bronze Age Setting Constraints
- No crossbows, firearms, or widely available steel
- Bronze weapons: 50% sunder chance on critical hits
- Cavalry is rare (small horses, chariots more common)
- Experience: 1 XP per 1 GP of treasure recovered

## Gameplay States
1. **Macro exploration** — hex crawl, travel
2. **Micro exploration** — dungeon rounds (turns)
3. **Combat** — 10-second turns
4. **Downtime** — town activities between sessions

## Armor Vector System (Critical for MonsterGen and SheetAuditor)
AC varies by damage type. Three values per armor type:
- **P** (Piercing), **S** (Slashing), **B** (Bludgeoning)
A gnoll's AC is not a single number — it's three numbers.
Example: Linothorax → P: 13, S: 14, B: 12

## Combat Rules (Key Homebrew)
- **Reach weapons:** Long spears and polearms extend threatened area; opposed AGL/STR
  check to break reach
- **Subdual damage:** Hammers can deal subdual without penalty
- **Two-weapon fighting:** Penalty die based on AGL score
- **Charging:** Bonuses to attack, penalties to AC for remainder of round
- **Firing into melee:** Risk of hitting allies
- **Grappling:** Opposed STR/AGL checks
- **Torches:** 50% extinguish chance when dropped (important for TurnTracker)

## Fear, Morale, and Madness
- **Morale check:** DC 11 Will save, modified ±4 by circumstances
- **Fear:** Failed morale = -1d to all checks (cumulative, stacks)
- **Madness:** Natural 1 on morale triggers madness roll (d7):
  1. Phobia, 2. Mania, 3. Dementia, 4. Paranoia, 5. Catatonic, 6. Twitches, 7. Imaginary illness
- Duration: 1d6 days (permanent on roll of 6)

## Faction Dynamics (Critical for EncounterGen and MoraleBot)
- **Gnolls:** Middle management — prefer enslavement to killing, will negotiate on morale failure
- **Lizardmen:** Seek allies, not unified with Gnolls — possible party allies
- **Beastmen:** Controlled by Ring of Agamemnos — check control status on morale
- **Cult of Thanatos:** Death cult with stronghold in abandoned volcano

## Resource Tracking
- Torches: 60-minute burn time
- Lanterns: 4-hour burn time (oil-dependent)
- Dungeon turns: 10 minutes each
- Random encounter check: every 10 turns

## Downtime Activities
Full bedrest, labor, rumors, mercantile, exploration, research, crafting, ritual,
carousing (d20 table), wilderness actions, dungeon downtime.
Carousing: XP gains, Luck changes, patron bonds, henchmen.
```

---

### Task 14: Create thracia-vault.md

- [ ] **Step 1: Create .claude/commands/thracia-vault.md**

```markdown
# Thracia Campaign — Obsidian Vault Map

Load this when reading from or writing to the Obsidian vault.

## Vault Location
C:\Users\lheur\Documents\Obsidian Vault\

## Folder Structure
```
Obsidian Vault/
├── Adventures/          ← source modules (PDFs and markdown)
│   ├── Caverns of Thracia - DCC v2   ← primary module
│   ├── Grave Robbers of Thracia      ← companion module
│   ├── Lost Lore of Thracia 5e
│   ├── The Alabaster Tower of Thracia
│   └── The Sacrificial Pyre of Thracia  ← volcano stronghold
├── Downtime/            ← downtime activity rules and tables
├── Equipment and Services/  ← gear lists, armor vectors, weapon tables
├── Lore/                ← world lore, gods (15-deity Theros pantheon)
│   └── Gods/            ← individual god pages with omens tables
├── Maps/
│   ├── Region/          ← overworld maps
│   ├── Level 1/         ← dungeon level 1 maps and room notes
│   │   └── Room Notes/  ← individual room markdown files (e.g. 1-1- Entry Hall.md)
│   └── Level 2/         ← dungeon level 2 (rooms visited include 2-17a through 2-17h)
├── NPCs/                ← Basilarius (ally), Sylle Ru (enemy)
├── Player Characters/   ← character sheets by player
│   ├── Christian/       ← Davras, Tycho, Zagrimm
│   ├── Jarrod/          ← Pelekion, Oryn, Damon
│   ├── David P/         ← Woody, Clovis
│   ├── Rob/             ← Beoflilu, Frani, Nissos, Gipeau
│   └── Ryan/            ← Hoglaf, Cedrigo, Iagupw
├── Rulebooks/           ← custom rules markdown files
│   ├── Combat.md        ← homebrew combat rules
│   ├── Equipment, Magic Items, And Treasure.md  ← armor vectors, weapon properties
│   ├── The Bronze Age.md  ← setting constraints and XP rules
│   ├── Morale, Fear, and Madness.md
│   └── Downtime.md
└── Sessions/            ← session notes
    ├── Session 3.md     ← completed
    ├── Session 4.md     ← most recent
    └── Session 5.md     ← prep in progress
```

## Key Rule Files for Agent Input
- Armor vectors: `Equipment and Services/Equipment, Magic Items, And Treasure.md`
- Combat rules: `Rulebooks/Combat.md`
- Morale/fear: `Rulebooks/Morale, Fear, and Madness.md`
- Bronze Age constraints: `Rulebooks/The Bronze Age.md`
- Monster stats: `Adventures/Caverns of Thracia - DCC v2` (PDF)

## Current Campaign State (as of Session 4)
- Party on Level 2, near rooms 2-17a through 2-17h
- Doppelgangers released from room 2-17a
- Mummy tomb (2-17a) sealed — not opened
- Crystal chest in 2-17g — not opened
- Ancient writing in 2-17h — not decoded
- Ring of Agamemnos quest active
- Sylle Ru (disgraced wizard) is a threat
- Basilarius (pirate captain) is an ally (1/3 cut deal)
```

---

### Task 15: Create thracia-roll20.md

- [ ] **Step 1: Create .claude/commands/thracia-roll20.md**

```markdown
# Thracia Campaign — Roll20 State

Load this when working on Roll20 content generation or MCP server tools.

## Campaign Details
- Platform: Roll20 (Pro account)
- System: DCC (Dungeon Crawl Classics) with homebrew modifications
- Character sheet: Third-party DCC sheet (template to be audited in Plan 03)

## Players and Characters (5 players, 3+ characters each)
| Player | Characters |
|---|---|
| Christian | Davras (Thief L1), Tycho, Zagrimm |
| Jarrod | Pelekion Stainedfingers, Oryn of Meletis, Damon of Lethaea |
| David P | Woody, Clovis |
| Rob | Beoflilu Pamuta, Frani, Nissos (Wizard L1), Gipeau Istec |
| Ryan | Hoglaf, Cedrigo Cloibo, Iagupw illebrin |

## Maps Built in Roll20
- Level 1: Complete (using Leaflet-style interactive layout)
- Level 2: Partial
- Region: Island of Thracia overworld

## Roll20 API Scripts (Phase 2 — not yet built)
Scripts will live in the campaign's API console (Campaign Settings → API Scripts).
All scripts are config-driven — data in JSON, logic in JS.

## Roll20 Access (Phase 3)
- Access method: Playwright browser automation (Python)
- MCP server: thracia-mcp-server/ (not yet built)
- First tool to build: pull_character_summary (read-only, low risk)

## NPC Schema
Roll20 NPC field names to be documented in docs/roll20-npc-schema.md
during the MonsterGen build sprint (Plan 02).
```

- [ ] **Step 2: Commit all skill files**

```bash
git add .claude/
git commit -m "feat: add Claude skill files for session context loading"
```

---

### Task 16: Final verification

- [ ] **Step 1: Run all tests one final time**

```bash
python -m pytest tests/ -v
```

Expected: All 9 tests pass.

- [ ] **Step 2: Verify full folder structure**

```bash
find . -not -path './.git/*' -not -path './.venv/*' | sort
```

Expected: All folders from the File Map section at the top of this plan.

- [ ] **Step 3: Update PROGRESS.md to reflect completion**

Update the "Current Sprint" section:
```markdown
## Current Sprint
- **Phase:** Ready to begin Phase 1
- **Active task:** None — infrastructure complete
- **Blocked on:** —
- **Next session goal:** Plan 02 — MonsterGen + QAChecker
```

Add to "Completed":
```
- 2026-03-21 — Project continuity infrastructure complete (Plan 01)
```

- [ ] **Step 4: Final commit**

```bash
git add PROGRESS.md
git commit -m "docs: mark infrastructure plan complete, update progress journal"
```

- [ ] **Step 5: Update phase1-content-gen/STATUS.md "Last Updated" line**

Change the Last Updated section at the bottom to:

```markdown
## Last Updated
2026-03-21 — Infrastructure complete. Phase 1 ready to begin (Plan 02).
```

```bash
git add phase1-content-gen/STATUS.md
git commit -m "docs: mark Phase 1 ready to begin"
```

---

## What's Next

**Plan 02 — MonsterGen + QAChecker** is the next plan. It will:
- Set up the Anthropic API key (environment variable, not hardcoded)
- Write MonsterGen: reads monster source material, calls Claude API, outputs Roll20 JSON
- Write QAChecker: validates MonsterGen output against a rules checklist
- Wire both into run.py replacing the placeholder handlers

Start Plan 02 by typing `/thracia-context` in your next Claude Code session to reload project state.

---

## Iterative Enhancements (Future Plans)

Once this infrastructure is working, here are natural next additions in order of value:

1. **Add a `JournalUpdate` agent (Plan 02+):** After each session, it reads what you built and appends a dated entry to PROGRESS.md automatically.
2. **Add GitHub remote (any time):** `git remote add origin <url>` + `git push` gives you a cloud backup and a history you can browse on GitHub.
3. **Add a `.env` file for secrets (Plan 02):** API keys go in `.env`, loaded with `python-dotenv`. Never hardcoded, never committed.
4. **Add a `Makefile` (later):** Common commands like `make test`, `make run-monsters` are easier to type than the full `python -m pytest` or `python run.py monster --level 1` versions.
