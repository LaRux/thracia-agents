# Thracia Roll20 Automation System — Architecture Design

**Date:** 2026-03-21
**Status:** Approved
**Author:** Brainstorming session with Claude Code
**Project home:** `C:\Users\lheur\Documents\Obsidian Vault` (source of truth)
**Target campaign:** Caverns of Thracia (DCC ruleset, Roll20 Pro)

---

## Overview

An AI-assisted automation system to transform the Caverns of Thracia campaign into a
fully operational Roll20 campaign. The system uses Python scripts and the Anthropic
Claude API to generate and validate content, JavaScript Roll20 API scripts for
real-time in-session tools, and (in a later phase) a Python MCP server that gives
Claude Code direct programmatic access to Roll20.

The system is designed for a single GM running a 5-player Dungeon Crawl Classics
campaign. It is built incrementally over weekend sprints, with explicit project
continuity infrastructure to support long gaps between sessions. The guiding
philosophy is that each phase delivers independent, usable value — nothing in Phase 2
blocks on Phase 1, and Phase 3 is an enhancement layer, not a foundation.

---

## Core Architectural Principles

These decisions were made deliberately and should not be changed without updating this
document and `DECISIONS.md`.

1. **Obsidian vault is the source of truth.** Roll20 is the presentation layer, not
   the database. All canonical campaign data (rules, monsters, characters, session
   notes) lives in the vault. Roll20 receives copies, not originals.

2. **Agents read from staged input, write to reviewed output.** Scripts never read
   directly from vault markdown files (a bug could corrupt notes). Instead, you copy
   source material to `data/input/`, agents process it to `data/output/pending/`, the
   QAChecker evaluates that output, and results are sorted into `data/output/ready/`
   (safe to import) or `data/output/flagged/` (needs review). Full pipeline:
   vault → `data/input/` → agent → `data/output/pending/` → QAChecker →
   `data/output/ready/` or `data/output/flagged/`.

3. **QAChecker gates all generated content.** No agent output reaches Roll20 without
   passing validation. The QAChecker is a Claude API call with a validation prompt —
   it reads the output JSON and checks it against a checklist of required fields,
   valid value ranges, and rules consistency. QAChecker runs automatically as the
   final step of every agent's pipeline via `run.py` — you never need to invoke it
   manually. Outputs are sorted into `data/output/ready/` (safe to import) and
   `data/output/flagged/` (needs review).

4. **All Phase 2 scripts are config-driven.** No game data is hardcoded in Roll20 API
   script logic. Conditions, resources, rules lookups, and morale tables all live in
   JSON config files. Adding a new condition or resource means editing a config file —
   zero code changes required.

5. **SessionScribe writes drafts only.** The post-session agent never writes directly
   to the Obsidian vault. It writes a draft to `data/output/session-draft/`. You review
   and approve, then run a commit command to apply the changes. This prevents
   automated mistakes from corrupting session history.

6. **Each phase is mostly independently deployable.** You can run sessions using only
   Phase 1 outputs (manually imported) with zero Phase 2 or 3 tooling. Most Phase 2
   scripts run without Phase 1 being complete — the one exception is `SheetValidator.js`,
   which depends on `SheetPatcher` (Phase 1) having corrected the character sheet first.
   Phase 3 enhances but never blocks.

---

## The Six Subsystems

| # | Subsystem | Phase | Description |
|---|---|---|---|
| 1 | Content Pipeline | 1 | Generate monsters, rooms, handouts from Obsidian vault |
| 2 | Character Sheet Audit & Patch | 1 | Identify and fix gaps between the DCC sheet and homebrew rules |
| 3 | In-Session Tools | 2 | Turn tracker, resources, conditions, morale, rules reference |
| 4 | Rules Automation | 2 | Config-driven enforcement of all homebrew mechanics |
| 5 | MCP Server + Roll20 Access | 3 | Python MCP server with Playwright bridge to Roll20 |
| 6 | Post-Session Feedback Loop | 3 | Chat log → Obsidian updates + next session prep |

---

## Phase 1 — Content Generation

**Stack:** Python 3, Anthropic Python SDK, Claude API
**When:** Before sessions, during prep
**How it delivers value:** Eliminates manual stat block creation and room description
writing. You go from PDF source material to Roll20-ready JSON in minutes instead of
hours.

### Project Structure

```
thracia-agents/
├── PROGRESS.md                    # Running project journal (see Continuity section)
├── DECISIONS.md                   # Architectural decision log with rationale
├── agents/
│   ├── done/                      # Completed, tested agents
│   ├── in-progress/               # Current work
│   │   └── monster_gen.py
│   └── backlog/                   # Not started
├── data/
│   ├── input/                     # Staged copies from Obsidian vault (safe to process)
│   └── output/
│       ├── pending/               # Raw agent output — awaiting QAChecker
│       ├── ready/                 # Passed QA — safe to import to Roll20
│       └── flagged/               # Failed QA — needs human review
├── prompts/
│   └── *.txt                      # Agent instructions as plain text files (edit to tune)
├── .claude/
│   └── commands/                  # Claude Code skill files (loaded via /thracia-* commands)
│       ├── thracia-context.md
│       ├── thracia-rules.md
│       ├── thracia-vault.md
│       └── thracia-roll20.md
└── run.py                         # Entry point — full CLI reference:
                                   #   python run.py monster --level 1
                                   #   python run.py monster --input data/input/gnoll.md
                                   #   python run.py room --input "data/input/1-1 Entry Hall.md"
                                   #   python run.py encounter --level 1
                                   #   python run.py qa --input data/output/pending/
                                   #   python run.py sheet audit
                                   #   python run.py sheet patch
                                   #   python run.py session commit
```

### Agent Roster (Priority Order)

**1. `MonsterGen`**
- Input: Monster stat block from PDF or markdown (`data/input/`)
- Output: Roll20 NPC character sheet JSON written to `data/output/pending/`. Example
  structure matching Roll20's character sheet field names:
  ```json
  {
    "name": "Gnoll Warrior",
    "bar1_value": 12, "bar1_max": 12,   // HP (Roll20 uses bar1 for HP by convention)
    "ac": { "piercing": 14, "slashing": 13, "bludgeoning": 15 },  // armor vectors
    "attacks": [
      { "name": "Spear", "damage": "1d8", "type": "piercing", "reach": true }
    ],
    "morale_dc": 11,
    "faction": "gnoll",
    "special": ["negotiates on morale failure", "enslaves rather than kills"],
    "treasure_type": "B"
  }
  ```
  The exact Roll20 field schema will be documented in `docs/roll20-npc-schema.md`
  during the MonsterGen build sprint, once the target DCC character sheet is inspected.
- Why first: Highest volume of manual work. Thracia has dozens of creature variants.

**2. `QAChecker`**
- Input: Any agent's output JSON
- Output: Pass/fail report with specific failure reasons
- Checks: required fields present, values in valid ranges, referenced rules exist in
  homebrew, no contradictions with your custom armor vector system
- Why second: Must exist before you trust any generated content. Gates everything else.

**3. `SheetAuditor`**
- Input: Roll20 DCC character sheet HTML/JS + your custom rules markdown
- Output: Gap report — fields missing, broken stat relationships, features your
  homebrew adds that the sheet doesn't support
- Key gaps expected: armor vector system (P/S/B AC), fear/madness condition fields,
  ability score loss tracking, Bronze Age weapon properties
- Why third: Must understand the sheet's problems before patching them.

**4. `SheetPatcher`**
- Input: SheetAuditor gap report
- Output: Annotated diff proposals for the sheet HTML/CSS/JS
- Each proposed change includes: what it does, why it's needed, what to test after
  applying
- Applied manually via Roll20's campaign settings > Character Sheet editor
- Why separate from SheetAuditor: The audit is read-only and safe to re-run anytime.
  Patches are code changes that require human review before application.

**5. `RoomGen`**
- Input: Room note from vault (e.g., `1-1- Entry Hall.md`) + relevant custom rules
- Output: DM-facing description (full detail, traps, hazards) + player-facing handout
  text (what they see/smell/hear on entry)
- Why fifth: Depends on having monsters available to reference. Build after
  MonsterGen is stable.

**6. `EncounterGen`**
- Input: Dungeon level notes + monster roster from MonsterGen output
- Output: Wandering monster table with frequency, numbers appearing, morale scores,
  faction alignment
- Faction relationships sourced from `data/input/factions.json` (copy from vault
  before running). Example entries: lizardmen seek allies and won't group with gnolls;
  beastmen check Ring of Agamemnos control status; gnolls prefer enslavement to
  killing and will negotiate.
- Why last: Requires a complete monster roster to draw from.

### The Prompts Folder

Each agent's instructions live in `prompts/agent_name.txt` rather than inside the
Python file. This separation means:
- You can tune agent behavior by editing a text file, no Python knowledge required
- Prompts are version-controlled alongside code
- You can see exactly what instructions the agent is operating under

---

## Phase 2 — In-Session Tools

**Stack:** JavaScript (Roll20 API sandbox)
**When:** During sessions, live at the table
**How it delivers value:** Eliminates the bookkeeping that interrupts play — torch
countdowns, condition stacking, morale rolls, resource tracking.

### Config-Driven Architecture

Every script reads from a companion JSON config file. The script contains logic only
("how to apply a condition"). The config contains data only ("what conditions exist").

Example — adding a new condition requires editing `ConditionTrackerConfig.json` only:

```json
{
  "conditions": {
    "fear": {
      "icon": "overdrive",
      "penalty": "-1d",
      "stacks": true,
      "max_stacks": 5,
      "duration_type": "turns",
      "note": "Cumulative. Each stack adds -1d to all checks."
    },
    "madness_phobia": {
      "icon": "skull",
      "penalty": "-1d",
      "stacks": false,
      "duration_type": "days",
      "note": "Only triggers in presence of phobia source. See Morale rules."
    }
  }
}
```

### Script Roster (Priority Order)

**1. `TurnTracker.js`**
- `!turn` — advances dungeon turn counter, logs elapsed time
- `!light [character] [source]` — starts countdown for torch (60 min) or lantern
  (4 hr); applies 50% extinguish chance on drop (per Combat rules)
- Whispers GM at turn 10 (random encounter check reminder)
- Config controls: turn length in minutes, encounter check interval, light source
  durations and extinguish rules
- Why first: Turn discipline is the mechanical spine of a dungeon crawl.

**2. `ResourceManager.js`**
- Tracks torches, rations, water, arrows, spell components as token bar values
- `!use [resource] [character]` — decrements count, warns on low stock
- `!rest` — triggers ration consumption for all characters, calculates healing per
  your rest rules
- Config controls: resource types, starting quantities, consumption rates, refill
  sources, low-stock warning thresholds
- Why token bars: Visible on the map at a glance, no separate spreadsheet.

**3. `MoraleBot.js`**
- `!morale [creature] [modifier]` — rolls DC 11 Will save with ±4 circumstance mods
- Auto-triggers on first enemy death (configurable per creature type)
- Outputs faction-aware result: gnolls may negotiate, lizardmen may seek alliance,
  beastmen check Ring of Agamemnos control
- Config controls: creature types, base DCs, circumstance modifiers, outcome tables
  per faction
- Why third: Your faction system requires nuanced morale. Generic "roll 2d6" tools
  won't capture gnoll negotiation or lizardman alliance-seeking.

**4. `ConditionTracker.js`**
- `!fear [character]` — stacks fear die penalty (-1d cumulative), whispers current
  total to GM
- `!madness [character] [type]` — records madness type, duration (1d6 days), and
  mechanical effect
- Auto-removes expired conditions each turn
- Config controls: all condition names, icons, penalties, stack rules, durations,
  cure requirements
- Why fourth: Most complex script. Build once simpler tools are stable and you
  understand the Roll20 API patterns.

**5. `RulesRef.js`**
- `!armor [type] [damage-type]` — returns AC for armor vector system (P/S/B)
- `!reach [weapon]` — shows reach rules and opposed AGL/STR check to break reach
- `!crit [weapon]` — shows crit effects (axe +1d, sword expanded range, hammer subdual)
- Config controls: full armor table, weapon properties, all homebrew rule lookups
- Why fifth: Low complexity, build anytime. Pure lookup — no state management.

**6. `SheetValidator.js`**
- Passive — runs on character sheet changes, whispers GM on invalid states
- Examples: AC showing a single value (should have P/S/B variants), ability score
  below minimum, resource count below zero
- Config controls: required fields, valid value ranges, dependency checks
- Why last: Depends on SheetPatcher (Phase 1) having fixed the sheet first.

---

## Phase 3 — MCP Server + Post-Session Loop

**Stack:** Python 3, MCP SDK, Playwright (browser automation)
**When:** Built after Phases 1 and 2 are running
**How it delivers value:** Eliminates copy-paste imports; gives Claude direct Roll20
access; automates post-session bookkeeping.

### Why Playwright for the Roll20 Bridge

Roll20 has no public REST API for external programs. Playwright automates a real
browser — it opens Roll20, navigates to your campaign, and performs actions exactly
as you would. This is the most reliable external access method currently available.

It is intentionally built in Phase 3 because: (a) browser automation is fragile to
UI changes, so you want to build only the specific operations you've proven you need;
(b) Phases 1 and 2 give you that proof before you invest in the bridge.

### MCP Server Tools

```
thracia-mcp-server/
├── server.py                    # MCP server — registers tools, handles requests
├── roll20_client.py             # Playwright bridge — opens Roll20, performs actions
└── tools/
    ├── read_characters.py       # Fetch character sheet data
    ├── pull_character_summary.py # Party state snapshot (HP, ability loss, resources)
    ├── write_character.py       # Push generated sheets to Roll20
    ├── push_xp.py               # Increment XP (1 GP = 1 XP per Bronze Age rules)
    ├── push_ability_loss.py     # Record ability score damage
    ├── push_resource_state.py   # Update post-session resource counts
    ├── bulk_import.py           # Import a folder of Phase 1 JSON outputs at once
    ├── read_journal.py          # Fetch handout/room journal entries
    └── export_session.py        # Pull chat log + character states post-session
```

**`pull_character_summary`** is the highest-priority first tool to build. It is
read-only (low risk as a first Playwright exercise) and enables a session-start ritual:
run it before each session for a one-page party state — who is injured, who is low on
resources, who has active madness conditions. Currently reconstructed manually.

### Post-Session Feedback Loop (SessionScribe)

SessionScribe runs after each session. It reads the Roll20 chat log and your quick
notes, then produces a structured draft of vault updates.

**Input:**
- Roll20 chat log (via `export_session` MCP tool)
- Pre-session character snapshot (via `pull_character_summary`)
- Your quick post-session notes (plain text)

**Output (draft only — never direct to vault):**
```
data/output/session-draft/
├── session-N-summary.md         # Narrative summary for Sessions/ folder
├── character-updates.json       # XP gained, HP lost, ability damage, resources spent
├── room-updates.json            # Rooms visited, looted, traps triggered
├── npc-updates.json             # NPC status changes (dead, charmed, fled)
└── session-N+1-prep.md          # Next session prep draft
```

You review the draft, edit as needed, then run `python run.py session commit` to
apply approved changes to the vault.

**Why draft-only?** SessionScribe interprets natural language (chat logs, shorthand
notes) and will make mistakes early on. The draft-first workflow means errors are
caught before they corrupt session history. As you correct its mistakes and improve
the prompt, the agent becomes more reliable — but the safety gate never goes away.

**Pre/post snapshot diffing:** Because `pull_character_summary` captures party state
before the session, SessionScribe can compare before/after rather than inferring
everything from chat logs. "Davras lost 2 STR" is detected from the diff, not
reconstructed from a description. Much more reliable.

---

## Project Continuity Infrastructure

Built **first**, before any agents or scripts. Without this, weekend-sprint development
becomes a context reconstruction exercise at the start of every session.

### PROGRESS.md

Running project journal. Both human- and agent-readable. Updated at the end of every
work session.

```markdown
# Thracia Agents — Project Journal

## Current Sprint
- Phase: [phase number and name]
- Active task: [what is being built right now]
- Blocked on: [anything blocking progress, or —]
- Next session goal: [specific, achievable target for next weekend]

## Completed
- [YYYY-MM-DD] [what was finished]

## Backlog (ordered by priority)
1. [next thing to build]
2. [thing after that]
...

## Key Decisions Log
- [decision]: [brief rationale]
```

### DECISIONS.md

Permanent log of architectural decisions and their rationale. Referenced when a
decision feels arbitrary — the reason is always recorded here.

### Per-Phase STATUS.md

Each phase folder contains a `STATUS.md` with what's done, in progress, and remaining
within that phase. At a glance, you can see the state of any phase without reading
code.

### Folder Structure as Status Signal

```
agents/
├── done/          # Complete and tested
├── in-progress/   # Currently being built
└── backlog/       # Not started
```

No ambiguity about where any piece of work stands.

### Claude Skill Files

Project-specific skill files stored in `thracia-agents/.claude/commands/`. Claude Code
loads them via the `/` command interface — typing `/thracia-context` at the start of a
session gives Claude immediate project awareness with no reconstruction from scratch.

| Skill file | Invoked as | Contents |
|---|---|---|
| `thracia-context.md` | `/thracia-context` | Current phase, last completed task, active decisions, today's goal |
| `thracia-rules.md` | `/thracia-rules` | Homebrew rules summary — armor vectors, reach, fear, morale, Bronze Age constraints |
| `thracia-vault.md` | `/thracia-vault` | Obsidian vault folder map — where monsters, rooms, sessions, characters live |
| `thracia-roll20.md` | `/thracia-roll20` | Campaign structure, character roster, current Roll20 state |

Skill files are updated as the project evolves. `thracia-context.md` is updated every
session. The others are updated when the underlying content changes.

---

## Implementation Plan Order

The spec for each subsystem will be written and implemented separately, in this order:

1. **Project Continuity Infrastructure** — `PROGRESS.md`, folder structure, first
   skill files. Zero code. Enables everything else.
2. **Phase 1: MonsterGen + QAChecker** — First content generation capability.
3. **Phase 1: SheetAuditor + SheetPatcher** — Fix the character sheet.
4. **Phase 1: RoomGen + EncounterGen** — Complete content pipeline.
5. **Phase 2: TurnTracker + ResourceManager** — Core session tools.
6. **Phase 2: MoraleBot + ConditionTracker** — Faction and psychological mechanics.
7. **Phase 2: RulesRef + SheetValidator** — Reference and validation tools.
8. **Phase 3: MCP Server (read tools first)** — `pull_character_summary` as first tool.
9. **Phase 3: MCP Server (write tools)** — `push_xp`, `push_ability_loss`, bulk import.
10. **Phase 3: SessionScribe** — Post-session feedback loop.

Each item gets its own spec → implementation plan → build cycle before the next begins.

---

## Open Questions / Future Iterations

- Roll20 UI changes may break Playwright automation in Phase 3. Mitigation: build
  only the operations proven necessary in Phases 1–2; add retry logic and failure
  alerts.
- SessionScribe accuracy will improve with prompt tuning over multiple sessions.
  Track correction patterns in a `prompts/sessionscribe-corrections.md` file.
- Character sheet patches (SheetPatcher) may conflict with Roll20 sheet updates if
  the DCC sheet author releases updates. Keep a record of all applied patches.
- The system currently assumes one campaign. Multi-campaign support is out of scope.
