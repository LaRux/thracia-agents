# Thracia Campaign — Obsidian Vault Map

Load this when reading from or writing to the Obsidian vault.
This file means you always know where things live without exploring the vault.

## Vault Location
C:\Users\lheur\Documents\Obsidian Vault\

## Folder Structure
```
Obsidian Vault/
├── Adventures/                  ← source modules (PDFs and markdown)
│   ├── Caverns of Thracia - DCC v2        ← PRIMARY MODULE
│   ├── Grave Robbers of Thracia           ← companion module
│   ├── Lost Lore of Thracia 5e
│   ├── The Alabaster Tower of Thracia
│   └── The Sacrificial Pyre of Thracia    ← volcano stronghold
│
├── Downtime/                    ← downtime activity rules and tables
│   ├── Carousing Tables.md      ← d20 table, 30 outcomes
│   ├── Martial Training.md
│   ├── Magical Research.md      ← corruption table (01-100)
│   └── Skullduggery.md
│
├── Equipment and Services/      ← gear lists, armor vectors, weapon tables
│   └── Equipment, Magic Items, And Treasure.md  ← ARMOR VECTORS HERE
│
├── Lore/                        ← world lore, Theros pantheon
│   └── Gods/                    ← 15 individual god pages with omens tables
│       ← Athreos, Ephara, Erebos, Heliod, Iroas, Karametra, Keranos,
│          Klothys, Kruphix, Mogis, Nylea, Pharika, Phenax, Purphoros, Thassa
│
├── Maps/
│   ├── Region/                  ← overworld: island_of_thracia.png, starry_archipelago.png
│   ├── Level 1/                 ← dungeon level 1
│   │   ├── thracia_1_ss.png     ← level 1 map image
│   │   ├── Thracia Level 1.md   ← interactive Leaflet map
│   │   └── Room Notes/          ← individual room files
│   │       ├── 1-1- Entry Hall.md
│   │       └── 1-20 Ritual Hall of Purification.md
│   └── (Level 2 rooms in session notes)
│
├── NPCs/
│   ├── Basilarius - Mercenary, Merchant, Adventurer.md   ← ALLY
│   └── Sylle Ru Seer.md                                  ← ENEMY
│
├── Player Characters/           ← character sheets by player
│   ├── Christian/               ← Davras (Thief L1), Tycho, Zagrimm
│   ├── Jarrod/                  ← Pelekion, Oryn of Meletis, Damon of Lethaea
│   ├── David P/                 ← Woody, Clovis
│   ├── Rob/                     ← Beoflilu, Frani, Nissos (Wizard L1), Gipeau
│   └── Ryan/                    ← Hoglaf, Cedrigo, Iagupw
│
├── Rulebooks/                   ← custom rules markdown files
│   ├── Combat.md                ← reach, subdual, grappling, charging, torch rules
│   ├── Equipment, Magic Items, And Treasure.md  ← armor vectors, 100+ items
│   ├── The Bronze Age.md        ← setting constraints, XP system, gameplay states
│   ├── Morale, Fear, and Madness.md  ← morale DC, fear stacking, madness types
│   └── Downtime.md              ← activity categories
│
├── Sessions/                    ← session notes
│   ├── Session 3.md             ← completed (cult treasury raid)
│   ├── Session 4.md             ← most recent (Level 2, doppelgangers released)
│   └── Session 5.md             ← prep in progress
│
└── docs/                        ← project documentation (created this session)
    ├── roll20-npc-schema.md     ← EXACT Roll20 field names, existing monster list
    └── superpowers/
        ├── specs/               ← architecture spec
        └── plans/               ← implementation plans and pre-notes
```

## Key Files for Agent Input
When staging files to data/input/, copy from:
- Armor vectors: `Equipment and Services/Equipment, Magic Items, And Treasure.md`
- Combat rules: `Rulebooks/Combat.md`
- Morale/fear: `Rulebooks/Morale, Fear, and Madness.md`
- Bronze Age constraints: `Rulebooks/The Bronze Age.md`
- Monster stats: `Adventures/Caverns of Thracia - DCC v2` (PDF — use PyPDF2 or pdfplumber)
- Existing monster list: `docs/roll20-npc-schema.md`

## Current Campaign State (as of Session 4)
- Party on Level 2, near rooms 2-17a through 2-17h
- Doppelgangers released from room 2-17a (2 loose on Level 2)
- Mummy tomb (2-17a) sealed — not opened
- Crystal chest in 2-17g — not opened
- Ancient writing in 2-17h — not decoded
- Ring of Agamemnos quest active (beastmen control item)
- Sylle Ru (disgraced wizard) is an active threat
- Basilarius (pirate captain, 55-person crew) is an ally on 1/3 cut deal
