# Thracia Campaign — Roll20 State

Load this when working on Roll20 content generation, Phase 2 scripts, or Phase 3 MCP tools.

## Campaign Details
- Platform: Roll20 (Pro account — Roll20 API available)
- System: DCC (Dungeon Crawl Classics) with homebrew modifications
- Character sheet: Third-party DCC sheet (6 gaps identified — see pre-notes Plan 03)
- Active page: Thracia level 2

## Players and Characters (5 players, 3+ characters each)
| Player | Active Characters | Dead/Retired |
|---|---|---|
| Christian | Davras (Thief L1, STR12/AGL11/STA7/PER10/LUCK16), Tycho, Zagrimm | — |
| Jarrod | Pelekion Stainedfingers, Oryn of Meletis, Damon of Lethaea | — |
| David P | Woody, Clovis | [Dead] Cartman, [Dead] Oren |
| Rob | Beoflilu Pamuta, Frani, Nissos (Wizard L1, spells: choking cloud/feather fall/force manipulation/spider climb), Gipeau Istec | — |
| Ryan | Hoglaf, Cedrigo Cloibo, Iagupw Illebrin | — |

## Existing NPCs in Roll20 (105 total — do NOT regenerate these)
See docs/roll20-npc-schema.md for full list and field schema.
Key groups: Thanatos Cult, Gnolls, Lizardmen, Undead, Creatures, Named NPCs.

## Maps Built in Roll20 (24 pages)
| Map Name | Level/Area | Status |
|---|---|---|
| level 1-1 | Dungeon Level 1 entry | Built |
| 1-9 to 1-14 | Dungeon Level 1 (skeletal area) | Built |
| 1-15:1-26 | Dungeon Level 1 (cult area) | Built |
| 1-27 | Dungeon Level 1 | Built |
| 2-17 | Dungeon Level 2 | Built |
| 2-19, 2-23, 2-31 | Dungeon Level 2 | Built |
| Thracia level 2 | Level 2 overview (ACTIVE) | Built |
| Area C - Tomb | Special area | Built |
| Island of Thracia | Region overworld | Built |
| Starry Archipelago | Region overworld | Built |
| Village of Hirot | Settlement | Built |
| City map | Settlement | Built |
| Landing / Landing page | Port area | Built |
| Surface: Map 1 | Exterior | Built |
| Dynamic Lights & Spells | Effects testing page | Built |
| Wilderness | Overland | Built |
| Hunters Attack | Combat encounter | Built |
| New Page 1/2/3 | In progress | Partial |

## Roll20 API Scripts (Phase 2 — not yet built)
All scripts will go in Campaign Settings → API Scripts.
All scripts are config-driven — data in JSON files, logic in JS.

Priority build order:
1. TurnTracker.js + TurnTrackerConfig.json
2. ResourceManager.js + ResourceManagerConfig.json
3. MoraleBot.js + MoraleBotConfig.json
4. ConditionTracker.js + ConditionTrackerConfig.json
5. RulesRef.js + RulesRefConfig.json
6. SheetValidator.js + SheetValidatorConfig.json (after SheetPatcher)

## Roll20 MCP Server (Phase 3 — not yet built)
Location: thracia-mcp-server/ (separate directory from thracia-agents/)
Access method: Playwright browser automation
First tool to build: pull_character_summary (read-only)

## Known Sheet Gaps (pre-audited from live export)
1. No armor vector AC (P/S/B) — HIGH priority
2. No fear/madness fields — HIGH priority
3. No ability score loss fields — MEDIUM priority
4. No faction field on NPCs — MEDIUM priority
5. No spellburn tracking — MEDIUM priority
6. Patron field empty — LOW priority
Full details: docs/superpowers/plans/2026-03-21-03-pre-notes-sheet-auditor.md
