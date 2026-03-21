# Roll20 NPC Character Sheet Schema

**Status:** Complete — populated from live campaign export (2026-03-21)
**Source:** thracia-characters.json export, 110 characters analyzed

---

## NPC vs PC Mode

Characters are switched to NPC mode by setting:
```json
"is_npc": 1
```
When `is_npc = 1`, the sheet renders a simplified NPC stat block instead of the full
PC sheet. All MonsterGen output must include this field.

---

## Core NPC Fields

| Field | Type | Required | Example | Notes |
|---|---|---|---|---|
| `is_npc` | number | YES | `1` | Always 1 for monsters/NPCs |
| `name` | string | YES | `"Gnoll Alpha"` | Displayed name |
| `hd` | string | YES | `"3d8"` | Hit dice notation |
| `hit_points` | object | YES | `{"current": 14, "max": 14}` | Use average of HD |
| `ac` | number | YES | `14` | Single value until SheetPatcher adds P/S/B |
| `fort` | number | YES | `2` | Fortitude save bonus |
| `ref` | number | YES | `1` | Reflex save bonus |
| `will` | number | YES | `0` | Will save bonus |
| `init` | number | YES | `1` | Initiative modifier |
| `act` | string | YES | `"1d20"` | Action die |
| `speed` | string | YES | `"30"` | Movement speed in feet |
| `sp` | string | YES | `""` | Special powers (plain text) |
| `description` | string | YES | `""` | Full abilities + armor vectors as text |
| `alignment` | string | YES | `"neutral"` | "lawful", "neutral", or "chaotic" |

---

## Attack Fields (Repeating Section)

```json
"repeating_attacks_-npc_attack_1_name":   "Spear",
"repeating_attacks_-npc_attack_1_attack": "+3",
"repeating_attacks_-npc_attack_1_damage": "1d8+1",
"repeating_attacks_-npc_attack_1_type":   "piercing"
```

Use `-npc_attack_1`, `-npc_attack_2` etc. as keys for multiple attacks.

---

## Known Schema Gaps (targets for SheetPatcher — Plan 03)

| Missing Field | Needed For | Priority |
|---|---|---|
| `ac_piercing`, `ac_slashing`, `ac_bludgeoning` | Armor vector system | HIGH |
| `fear_stacks` | Fear condition tracking | HIGH |
| `madness_type`, `madness_duration` | Madness tracking | HIGH |
| `strength_loss` through `luck_loss` | Ability drain tracking | MEDIUM |
| `faction` | MoraleBot faction-aware outcomes | MEDIUM |
| `spellburn_str/agl/sta` | Wizard spellburn | MEDIUM |

**Interim workaround:** Store armor vectors and faction in `description` field as text.
Example: "AC: P14/S14/B12. Faction: gnoll."

---

## Example: Complete MonsterGen Output

```json
{
  "is_npc": 1,
  "name": "Gnoll Warrior",
  "hd": "2d8",
  "hit_points": { "current": 9, "max": 9 },
  "ac": 14,
  "fort": 2,
  "ref": 1,
  "will": 0,
  "init": 1,
  "act": "1d20",
  "speed": "30",
  "alignment": "chaotic",
  "sp": "Negotiate on morale failure (DC11 Will). Enslave rather than kill.",
  "description": "AC: P14/S14/B13. Faction: gnoll. Morale DC: 11.",
  "repeating_attacks_-npc_attack_1_name": "Spear",
  "repeating_attacks_-npc_attack_1_attack": "+2",
  "repeating_attacks_-npc_attack_1_damage": "1d8",
  "repeating_attacks_-npc_attack_1_type": "piercing"
}
```

---

## Existing Monsters Already in Roll20 (as of 2026-03-21)

105 NPCs already built — MonsterGen should skip these unless updating a variant.

**Thanatos Cult:** Acolyte, Friar, Cleric, Macreus, Ceremonial Guard, Bier Guard, Pall-bearer
**Gnolls:** Gnoll, Gnoll Alpha, Gnoll Beta, Grotch (leader)
**Lizardmen:** G'ruk (shaman), Lizardman Fanatic, Lizardman Mercenary, Skeleton Lizardman Warrior
**Undead:** Barrow Wight, Elder Skeleton, Skeleton, Tomb Ghoul, The Dead King, Immortal King
**Creatures:** Carrion Crawler, Giant Bat, Giant Rat, Giant Wolverine, Black Bear, War Bear,
Stirge, Spider (black widow + hatchling swarm), Ghoul Serpents, Piercer (medium + small),
Minotaur Lizard, Red-headed Centipede Swarm, Swarm of Rats, Swarm of Bats, Primeval Slime
**Named NPCs:** Anteus, Aristippus, G'ruk, Grotch, Iraco, Ontussa (gynosphinx),
Guardian of Singular Combat, Sylle Ru, The Stone King, The Hound of Hirot, Vredd,
Nothan the Younger, Diogenes
