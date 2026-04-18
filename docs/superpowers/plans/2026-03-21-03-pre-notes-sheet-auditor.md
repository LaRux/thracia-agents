# Plan 03 Pre-Notes — SheetAuditor + SheetPatcher

**Status:** Pre-notes only — full plan to be written when Plan 02 is complete
**Source:** Live Roll20 campaign export analyzed 2026-03-21

These notes represent the SheetAuditor's findings in advance. When Plan 03 is written,
SheetAuditor should be written to CONFIRM these findings (and catch anything missed),
not discover them from scratch. The known gaps are documented here so Plan 03 starts
with a concrete target list rather than open-ended exploration.

---

## Known Sheet Gaps (Pre-Audited)

The following homebrew features are confirmed absent from the DCC character sheet
as of 2026-03-21. Each gap includes its impact and proposed patch approach.

---

### GAP-01: No Armor Vector System (CRITICAL)

**Current state:** `armor_class` is a single integer (e.g. `14`).
**Needed:** Three separate AC values: `ac_piercing`, `ac_slashing`, `ac_bludgeoning`.
**Impact:** The armor vector system (P/S/B) is your most distinctive homebrew rule.
Without sheet support, GMs must remember three numbers per creature mentally or look
them up in notes.
**Interim workaround (until patch):** Store as text in NPC `description` field —
"AC: P14/S14/B12". `RulesRef.js` will also provide `!armor` lookups.
**Patch approach:** Add three new fields to the sheet HTML, wired to the existing
`armor_class` display with a toggle for NPC vs PC mode.

---

### GAP-02: No Fear/Madness Tracking (HIGH)

**Current state:** No `fear`, `madness_type`, `madness_duration`, or related fields
exist anywhere in the schema across 110 characters.
**Needed:**
- `fear_stacks` (integer 0–5) — cumulative -1d penalty per stack
- `madness_type` (string) — one of: phobia, mania, dementia, paranoia, catatonic,
  twitches, imaginary_illness
- `madness_duration` (integer) — days remaining
- `madness_active` (boolean) — whether madness is currently triggered
**Impact:** Fear and madness are central to your homebrew morale system. ConditionTracker
(Phase 2) needs these fields to work properly.
**Patch approach:** Add a "Conditions" section to the sheet with these fields visible
to both GM and player.

---

### GAP-03: No Ability Score Loss Tracking (HIGH)

**Current state:** Ability scores have `current`/`max` but the `max` is set at
character creation and never updated. There is no separate field tracking permanent
vs. temporary ability loss.
**Needed:**
- `strength_loss`, `agility_loss`, `stamina_loss`, `personality_loss`,
  `intelligence_loss`, `luck_loss` — integer fields tracking points lost
- Displayed as: STR 12 (-2 loss) → effective STR 10
**Impact:** Mummy touch, ability drain, Bronze Age injury consequences all need this.
The `push_ability_loss` MCP tool (Phase 3) targets these fields.
**Patch approach:** Add a "loss" field per stat, subtract from total in displayed
modifier calculation.

---

### GAP-04: No Spellburn Tracking (MEDIUM)

**Current state:** `corruption` field exists but is text-only. No numeric spellburn
tracking.
**Needed:**
- `spellburn_str`, `spellburn_agl`, `spellburn_sta` — temporary burn amounts
- These reduce the relevant stats temporarily (not permanently, unlike ability loss)
**Impact:** Wizards (Nissos etc.) need this for accurate spellcasting.
**Patch approach:** Add spellburn fields adjacent to ability scores, wired to reduce
effective total when set.

---

### GAP-05: No Faction Field (MEDIUM)

**Current state:** No `faction` field on any NPC character.
**Needed:** `faction` string field — "gnoll", "lizardman", "thanatos_cult",
"beastmen", "undead", "neutral", etc.
**Impact:** MoraleBot (Phase 2) needs faction to determine morale outcomes (gnolls
negotiate, lizardmen seek allies). EncounterGen needs it for faction-aware tables.
**Interim workaround:** Faction stored in NPC `description` field as "Faction: gnoll".
MoraleBot config will map creature names to factions until the field is added.
**Patch approach:** Add a `faction` dropdown or text field to the NPC section.

---

### GAP-06: Patron Field Exists But Unused (LOW)

**Current state:** `patrons` field exists but is empty for all characters including
wizard Nissos who has a patron bond.
**Needed:** Patron name, invoke patron check modifier, patron-specific spell list
reference.
**Impact:** Minor — mainly a record-keeping gap. Patron invocation still works
mechanically, just not tracked on sheet.
**Patch approach:** Populate existing `patrons` field; add `patron_invoke_mod` if
needed.

---

## SheetAuditor Test Cases for Plan 03

When SheetAuditor is built, it must detect all 6 gaps above. Use these as acceptance
criteria:

```
PASS: Reports GAP-01 (missing ac_piercing, ac_slashing, ac_bludgeoning)
PASS: Reports GAP-02 (missing fear_stacks, madness_type, madness_duration)
PASS: Reports GAP-03 (missing strength_loss through luck_loss)
PASS: Reports GAP-04 (missing spellburn_str, spellburn_agl, spellburn_sta)
PASS: Reports GAP-05 (missing faction field)
PASS: Reports GAP-06 (patron field populated check)
FAIL condition: SheetAuditor reports zero gaps (means it isn't working)
```

---

## SheetPatcher Priority Order

Based on dependency analysis:

1. **GAP-01 (Armor Vectors)** — unblocks MonsterGen proper AC output and RulesRef
2. **GAP-02 (Fear/Madness)** — unblocks ConditionTracker (Phase 2)
3. **GAP-03 (Ability Loss)** — unblocks push_ability_loss (Phase 3)
4. **GAP-05 (Faction)** — unblocks MoraleBot proper NPC lookup
5. **GAP-04 (Spellburn)** — unblocks wizard accuracy
6. **GAP-06 (Patron)** — nice to have, no blockers
