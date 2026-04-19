# Session 1 is complete.

  ---
  What you built today:

  ┌─────────────┬───────────────────────────────────────────────────────────────────┐
  │             │                                                                   │
  ├─────────────┼───────────────────────────────────────────────────────────────────┤
  │ Project     │ thracia-agents — live at github.com/LaRux/thracia-agents          │
  ├─────────────┼───────────────────────────────────────────────────────────────────┤
  │ Environment │ conda env thracia-agents, Python 3.11                             │
  ├─────────────┼───────────────────────────────────────────────────────────────────┤
  │ CLI         │ python run.py with 9 passing tests                                │
  ├─────────────┼───────────────────────────────────────────────────────────────────┤
  │ Structure   │ Full folder scaffold, phase STATUS files, NPC schema              │
  ├─────────────┼───────────────────────────────────────────────────────────────────┤
  │ Tracking    │ PROGRESS.md, DECISIONS.md, 9 architectural decisions logged       │
  ├─────────────┼───────────────────────────────────────────────────────────────────┤
  │ Skill files │ /thracia-context, /thracia-rules, /thracia-vault, /thracia-roll20 │
  ├─────────────┼───────────────────────────────────────────────────────────────────┤
  │ Commits     │ 6 clean commits on master                                         │
  └─────────────┴───────────────────────────────────────────────────────────────────┘

  ---
  To start Session 2:

  1. Open Claude Code in C:\Users\lheur\Documents\thracia-agents\
  2. Type /thracia-context — I'll have full project awareness immediately
  3. We'll write and execute Plan 02: MonsterGen gap analysis + QAChecker — the first real agent

✻ Churned for 33s · 1 background task still running (↓ to manage)

● Agent "Save project reference memory" completed

● Memory saved — the project reference is stored so any future Claude Code session will know where to find everything.

  See you in Session 2.

  What We Built in Session 1 — Top Down

  ---
  The Point of the System

  You're a GM running a complex campaign with dozens of house rules, hundreds of monsters, and multiple players. The bottleneck isn't your creativity — it's the mechanical overhead: generating stat blocks, tracking torches, remembering that gnolls negotiate rather than fight to the death, updating XP on 15 character sheets after a session.

  The system exists to automate the mechanical overhead so you can focus on the game. Claude acts as a collaborator that knows your rules and your campaign deeply enough to do the grunt work: generate monsters that conform to your armor vector system, track dungeon turns at the table, update character sheets after a session.

  ---
  The Reasoning Behind the Relationships

  The whole system is built around one core tension: Claude is powerful but ephemeral. Every time you start a new conversation, I have no memory of what we did before. Left unaddressed, that means you'd spend the first 20 minutes of every session re-explaining your rules, your campaign state, and where the project stands.

  Everything we built today is a solution to that problem. Here's how the pieces relate:

  Your Campaign Knowledge          How Claude Accesses It
  ─────────────────────────        ──────────────────────
  Obsidian vault (rules, notes) ──→ Skill files (/thracia-rules, /thracia-vault)
  Roll20 campaign state         ──→ Skill files (/thracia-roll20) + export files
  Project progress              ──→ PROGRESS.md + /thracia-context
  Architectural decisions       ──→ DECISIONS.md

  The skill files are the bridge. They transform "Claude knows nothing" into "Claude knows your armor vector system, your faction dynamics, your map structure, and exactly where the project left off" — in the time it takes to type /thracia-context.

  The folder structure enforces the safety model: your Obsidian vault (irreplaceable) never gets touched by code. Agents only read from data/input/ (copies you put there) and only write to data/output/ (which you review before anything reaches Roll20).

  The git repository makes the whole thing recoverable. Every task ended with a commit, which means every step is a restore point. If something breaks in Session 5, you can see exactly what changed and when.

  ---
  What Each Component Does

  run.py — the switchboard
  Every agent in the system will be invoked through this one file. python run.py monster --level 1, python run.py qa, python run.py session commit — always the same pattern. Right now it just prints "not implemented" for everything. Over the next sessions, each command gets wired to a real agent. The value is that there's only one place to look when you want to know how to
  run something.

  tests/test_cli.py — the contract
  These 9 tests define what run.py is supposed to do. If you change run.py and accidentally break an argument, the tests catch it immediately. More importantly, they demonstrate TDD: we wrote the tests before the code, which forced us to think about the interface before thinking about the implementation.

  data/input/ and data/output/
  A deliberate two-stage pipeline. You drop source material into input/ (the Roll20 exports are already there). Agents process it and write to output/pending/. QAChecker validates and moves results to output/ready/ or output/flagged/. Nothing touches Roll20 until something has passed through ready/. The folders are the workflow.

  PROGRESS.md — the handoff document
  The single file that answers "where are we?" at the start of every session. Current sprint, what's done, what's next, key decisions. Updated at the end of each session. Also machine-readable — I can read it and immediately orient myself.

  DECISIONS.md — the memory of why
  Code tells you what the system does. DECISIONS.md tells you why it does it that way. Nine decisions are logged with their rationale — why Python and not JS, why QAChecker is mandatory, why MonsterGen does a gap analysis first. Without this, decisions that seemed obvious today look arbitrary in three months.

  phase*/STATUS.md — progress at a glance
  One file per phase. At any point you can open phase1-content-gen/STATUS.md and see which agents are done, in progress, or not started — without reading code.

  .claude/commands/ — Claude's working memory
  Four markdown files that load when you type a slash command:
  - /thracia-context — where we are in the project right now
  - /thracia-rules — your full homebrew ruleset (armor vectors, morale, fear, factions)
  - /thracia-vault — the Obsidian vault map (so I know where every file lives)
  - /thracia-roll20 — the Roll20 campaign state (105 existing NPCs, 24 maps, 6 sheet gaps)

  These are the difference between me being a generic assistant and being a collaborator that knows your campaign.

  docs/roll20-npc-schema.md — the Rosetta Stone
  Roll20 stores character data in specific field names (hd, ac, fort, is_npc). Without knowing these exact names, any generated monster sheet would be ignored or misread by Roll20. This document — populated from your live campaign export — is what lets MonsterGen write output that Roll20 can actually use.

  ---
  The Shape of What's Coming

  Session 1 built the foundation layer — no AI, no agents, just structure and memory. Every future session adds one agent or one tool that replaces a "not yet implemented" placeholder with real capability. By the end of Phase 1 you'll have a pipeline that reads monster source material and produces validated Roll20-ready JSON. By Phase 2 you'll have scripts running at the
  table. By Phase 3 the whole system talks to Roll20 directly.

  Each session is self-contained and leaves the project in a working, committed state. That's intentional — built for exactly the kind of weekend-sprint development you're doing.

  # Session 2 — 2026-04-04

  Plan 02 complete. Built the full MonsterGen + QAChecker pipeline: 4 modules, 134 tests, all wired into run.py.

  ---
  What was built:

  ┌─────────────────────┬───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │       Module        │                                                                                           Does                                                                                            │
  ├─────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ parse_statblocks.py │ Parses DCC + 5e stat block text → master_monsters.csv. Merges sources with DCC authoritative for mechanics.                                                                               │
  ├─────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ gap_analysis.py     │ Compares CSV against Roll20 export → gap_report.txt (names missing from Roll20).                                                                                                          │
  ├─────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ monster_gen.py      │ Reads gap report + CSV, calls Claude API for armor vectors/attacks/sp, writes Roll20-ready JSON to data/output/pending/.                                                                  │
  ├─────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ qa_checker.py       │ Two-pass validation: Pass 1 mechanical (field presence, types, HD format, armor vector), Pass 2 Claude judgment. Routes to ready/ or flagged/ with a _qa_report.txt for anything flagged. │
  └─────────────────────┴───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

  Branch plan-02-monstergen pushed to GitHub, PR ready.

  ---
  To use the pipeline:

  # Drop source material into the input directory
  cp statblocks.txt data/input/monster-source/dcc_statblocks.txt
  cp lore.txt data/input/monster-source/lore_5e_sections.txt

  python run.py monster --parse          # → data/input/master_monsters.csv
  python run.py monster --gap-analysis   # → data/output/gap_report.txt
  python run.py monster --generate --all # → data/output/pending/*.json
  python run.py qa                       # → ready/ or flagged/

  ---
  To start Session 3:

  1. Open Claude Code in C:\Users\lheur\Documents\thracia-agents\
  2. Merge or close the plan-02-monstergen PR if you haven't already
  3. Type /thracia-context — full project awareness loads instantly
  4. Next goal: Plan 03 — SheetAuditor + SheetPatcher
    - SheetAuditor reads your Roll20 character sheet export and compares against your homebrew rules
    - 6 gaps are already pre-identified in plans/2026-03-21-03-pre-notes-sheet-auditor.md
    - Start with /brainstorm to design the spec, then write the plan and execute

    # Session 3- 2026-04-11
    What we built: Plan 03 — SheetAuditor + SheetPatcher

  ┌──────────────┬───────────────────────────────────────────────────────────────────────────────────────────────────┐
  │  Component   │                                           What it does                                            │
  ├──────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ utils.py     │ Shared helpers (average_from_hd, strip_sign, build_hit_points) used by MonsterGen and the new     │
  │              │ agents                                                                                            │
  ├──────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ SheetAuditor │ Reads thracia-characters.json, filters active NPCs, runs a full quality check suite, produces     │
  │              │ audit_report.md (human review) + audit_report.json (machine input)                                │
  ├──────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ SheetPatcher │ Reads audit_report.json, writes full replacement sheets to data/output/pending/ for anything      │
  │              │ flagged as auto-patchable                                                                         │
  ├──────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ CLI wiring   │ python run.py sheet --audit and --patch flags, combinable                                         │
  └──────────────┴───────────────────────────────────────────────────────────────────────────────────────────────────┘

  Results: 66 NPCs audited, 58 auto-patched, 8 flagged for manual review.

  Bugs fixed along the way: strip_sign blank handling, build_hit_points HD fallback when hp_avg is empty.

  ---
  How to Start Session 4

  Goal: Plan 04 — RoomGen + EncounterGen

  1. Open Claude Code in C:\Users\lheur\Documents\thracia-agents\
  2. Type /thracia-context — loads full project awareness
  3. You have one uncommitted change to clean up first: .claude/commands/thracia-context.md is modified (the skill file
  itself) — commit or check that before starting Plan 04
  4. Tell me: "Let's write Plan 04 — RoomGen + EncounterGen" and we'll brainstorm the spec before touching code

  ---
  Note: No Plan 04 spec exists in the vault yet — we'll need to brainstorm and write it at the start of session 4 the
  same way we did for Plans 02 and 03.

# Session 4 — 2026-04-18

Plan 04 complete. Built RoomGen + EncounterGen — the content generation pipeline that turns the Caverns of Thracia PDF into Roll20-ready handouts and rollable encounter tables.

---
What was built:

┌────────────────┬────────────────────────────────────────────────────────────────────────────────────────────┐
│    Module      │  What it does                                                                              │
├────────────────┼────────────────────────────────────────────────────────────────────────────────────────────┤
│ parse_pdf.py   │ Extracts text from the PDF using pdfplumber. Splits rooms by header regex (primary:        │
│                │ "Area X-Y", fallback: title-case-colon). Writes staged room and wandering table files      │
│                │ to data/input/. Skips re-extraction if staged file exists (--reextract to override).       │
├────────────────┼────────────────────────────────────────────────────────────────────────────────────────────┤
│ room_gen.py    │ Reads staged room blocks, batches 3 per Claude API call, generates Roll20 handout JSON     │
│                │ with player-facing HTML in notes and full GM content in gmnotes. Writes to pending/.       │
├────────────────┼────────────────────────────────────────────────────────────────────────────────────────────┤
│ encounter_gen  │ Reads staged wandering table text, sends to Claude for parsing, generates a .js Roll20     │
│                │ API script that creates a rollable table and a GM-whisper macro button. Writes directly    │
│                │ to ready/ (no QA step — it's executable JS, not a character sheet).                        │
├────────────────┼────────────────────────────────────────────────────────────────────────────────────────────┤
│ qa_checker.py  │ Extended with pass1_handout_check — dispatches on the type field so handout JSONs bypass   │
│                │ Claude's Pass 2 and get structural validation only (type, name, notes, gmnotes present     │
│                │ and non-empty).                                                                            │
├────────────────┼────────────────────────────────────────────────────────────────────────────────────────────┤
│ run.py         │ room and encounter commands wired with --level, --pages, --all, --reextract flags.         │
│                │ --level now accepts strings (1, 2, 2a, 3a) to support the named sub-levels in the module. │
└────────────────┴────────────────────────────────────────────────────────────────────────────────────────────┘

Test count: 237 passing. Smoke test: 32 Level 1 room handouts generated and passed QA on the first real run.

---
Design decisions made this session:

- Roll20 API cannot create map pins programmatically — pivoted from map pins to handouts, which players access from the journal. Map pin linking is a one-time manual step after import (~5 seconds per room).
- Rooms sourced directly from the PDF via pdfplumber, not from Obsidian vault markdown. The vault markdown is incomplete; the PDF is authoritative.
- Encounter JS skips QAChecker entirely — it's a paste-once API script, not a data file.
- All project docs migrated from Obsidian vault into the git repo this session (docs/superpowers/).

---
How to continue:

  python run.py room --level 2       # Level 2 rooms
  python run.py room --level 2a      # Level 2A rooms
  python run.py room --all           # All levels at once
  python run.py encounter --level 1  # Level 1 wandering table → .js script

Page ranges for all levels are in data/input/pdf_sections.json — verify against the PDF table of contents before running --all.

Phase 1 content generation is complete. Next options:
- Phase 2: Roll20 API scripts (TurnTracker, ResourceManager, MoraleBot)
- Or: run the full pipeline and review output quality before moving on