# Thracia Campaign — Homebrew Rules Reference

Load this when working on any agent that generates or validates game content.
This file means you never need to ask "what's an armor vector?" or re-read the rules.

## Core System
Dungeon Crawl Classics (DCC) RPG with homebrew modifications for a Bronze Age setting.

## The Bronze Age Setting
- No crossbows, firearms, or widely available steel
- Bronze weapons: 50% sunder chance on critical hits
- Cavalry is rare (small horses, chariots more common)
- Experience: 1 XP per 1 GP of treasure recovered

## Gameplay States
1. **Macro exploration** — hex crawl, overland travel
2. **Micro exploration** — dungeon rounds (10-minute turns)
3. **Combat** — 10-second turns
4. **Downtime** — town activities between sessions

## Armor Vector System (CRITICAL — affects MonsterGen and SheetAuditor)
AC varies by damage type. Every armored creature has THREE AC values:
- **P** = Piercing (spears, arrows, daggers)
- **S** = Slashing (swords, axes)
- **B** = Bludgeoning (hammers, clubs, falling)

Example — Linothorax: P:13 / S:14 / B:12
INTERIM: Until SheetPatcher is complete, store as text in description:
  "AC: P13/S14/B12"

## Weapons (Key Homebrew)
- **Axes:** +1 die size on critical hits
- **Swords:** Expanded critical threat range
- **Hammers:** Versatile, can deal subdual damage without penalty
- **Polearms/Long Spears:** Reach weapons — extend threatened area
- **Two-weapon fighting:** Penalty die based on AGL score

## Combat Rules (Key Homebrew)
- **Reach:** Opposed AGL/STR check to break past a reach weapon
- **Subdual:** Hammers deal subdual without penalty; others at -1d
- **Charging:** +1d attack, -AC penalty until next turn
- **Firing into melee:** Risk of hitting allies (roll to determine target)
- **Grappling:** Opposed STR/AGL checks
- **Torch drop:** 50% extinguish chance (important for TurnTracker)
- **Falling:** 1d6 per 10ft, broken bone consequences on large falls

## Morale, Fear, and Madness (CRITICAL — affects MoraleBot and ConditionTracker)
- **Morale check:** DC 11 Will save, modified ±4 by circumstances
- **Fear:** Failed morale = -1d to all checks (cumulative stacking penalty)
- **Madness:** Natural 1 on morale check triggers madness (d7 roll):
  1. Phobia — -1d when phobia source is present
  2. Mania — -1d when distracted by obsession
  3. Dementia — reduce random attribute by 1d6
  4. Paranoia — -1d to morale and Will saves
  5. Catatonic — -2d to all action die rolls
  6. Twitches/spasms — -1d to action and reflex
  7. Imaginary illness — -1d to -2d depending on severity
- **Duration:** 1d6 days (permanent if roll of 6)
- **Cure:** 4 dice of Lay on Hands or Restore Vitality (DC 34+)
- **Reward:** +1 Luck if madness is enthusiastically roleplayed

## Faction Dynamics (CRITICAL — affects MoraleBot and EncounterGen)
- **Gnolls:** Middle management — prefer enslavement, will NEGOTIATE on morale failure
- **Lizardmen:** Seek allies, not unified with Gnolls — may become party allies
- **Beastmen:** Controlled by Ring of Agamemnos — check control status on morale
- **Thanatos Cult:** Fanatical — morale DC higher, less likely to flee
- **Undead:** Mindless undead have no morale; intelligent undead check normally

## Resource Tracking (CRITICAL — affects TurnTracker and ResourceManager)
- **Torches:** 60-minute burn time, 50% extinguish on drop
- **Lanterns:** 4-hour burn time (oil-dependent)
- **Dungeon turns:** 10 minutes each
- **Random encounter check:** Every 10 turns
- **Rest:** Requires rations; heals per rest rules

## Experience and Advancement
- 1 XP per 1 GP of treasure recovered
- Additional XP for monsters per DCC standard tables
- Carousing: XP gains via d20 carousing table (30 outcomes)
- Magical Research: 1 XP per 100 GP (max 5 XP/session), DC 15 spell check

## Downtime Activities
Full bedrest (2x healing), labor, rumors, mercantile, exploration, research,
crafting, ritual, carousing (d20 table), wilderness actions, dungeon downtime.
