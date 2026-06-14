# tests/test_equipment_gen.py
import json

import pytest

from equipment_gen import (
    load_catalog,
    validate_catalog,
    weapon_row,
    armor_row,
    armor_vectors,
    capped_vectors,
    armor_vector_string,
    apply_shield,
    build_script,
    build_handout,
)

VALID_CATALOG = {
    "weapons": [
        {"name": "Spear", "damage": "1d8", "damage_type": "piercing", "size": "M",
         "range": "melee", "crit_note": "+1 to crit range"},
        {"name": "Shortbow", "damage": "1d6", "damage_type": "piercing", "size": "M",
         "range": "missile", "two_handed": True},
    ],
    "armor": [
        {"name": "Linothorax", "base_ac": 12, "ac_slashing": 12, "ac_piercing": 12,
         "ac_bludgeoning": 12, "check_penalty": -1, "speed_penalty": 0,
         "fumble_die": "d6", "is_shield": False},
        {"name": "Small shield", "is_shield": True, "ac_bonus_all": 1,
         "check_penalty": -1, "fumble_die": "d8"},
    ],
}


class TestValidateCatalog:
    def test_valid_catalog_passes(self):
        assert validate_catalog(VALID_CATALOG) == []

    def test_missing_damage_type_fails(self):
        cat = {"weapons": [{"name": "Club", "damage": "1d5", "range": "melee"}], "armor": []}
        errors = validate_catalog(cat)
        assert any("damage_type" in e for e in errors)

    def test_bad_damage_type_fails(self):
        cat = {"weapons": [{"name": "X", "damage": "1d4", "damage_type": "fire",
                            "range": "melee"}], "armor": []}
        errors = validate_catalog(cat)
        assert any("damage_type" in e for e in errors)

    def test_bad_range_fails(self):
        cat = {"weapons": [{"name": "X", "damage": "1d4", "damage_type": "piercing",
                            "range": "thrown"}], "armor": []}
        errors = validate_catalog(cat)
        assert any("range" in e for e in errors)

    def test_non_integer_armor_vector_fails(self):
        cat = {"weapons": [], "armor": [
            {"name": "Bad", "base_ac": 12, "ac_slashing": "12", "ac_piercing": 12,
             "ac_bludgeoning": 12, "is_shield": False}]}
        errors = validate_catalog(cat)
        assert any("ac_slashing" in e for e in errors)

    def test_shield_requires_integer_bonus(self):
        cat = {"weapons": [], "armor": [
            {"name": "Wonky shield", "is_shield": True, "ac_bonus_all": "1"}]}
        errors = validate_catalog(cat)
        assert any("ac_bonus_all" in e for e in errors)

    def test_duplicate_name_fails(self):
        cat = {
            "weapons": [{"name": "Spear", "damage": "1d8", "damage_type": "piercing",
                         "range": "melee"}],
            "armor": [{"name": "spear", "is_shield": True, "ac_bonus_all": 1}],
        }
        errors = validate_catalog(cat)
        assert any("duplicate" in e for e in errors)

    def test_real_catalog_is_valid(self):
        """The shipped data/input/equipment.json must validate."""
        assert validate_catalog(load_catalog()) == []


class TestWeaponRow:
    def test_melee_weapon_maps_sheet_fields(self):
        row = weapon_row(VALID_CATALOG["weapons"][0])
        assert row == {
            "name": "Spear",
            "damage_base": "1d8",
            "two_handed": "no",
            "skill": "close combat",
        }

    def test_missile_weapon_uses_ranged_skill(self):
        row = weapon_row(VALID_CATALOG["weapons"][1])
        assert row["skill"] == "ranged combat"
        assert row["damage_base"] == "1d6"

    def test_explicit_two_handed_flag(self):
        row = weapon_row({"name": "Maul", "damage": "1d10", "damage_type": "bludgeoning",
                          "size": "L", "range": "melee", "two_handed": True})
        assert row["two_handed"] == "yes"

    def test_large_size_triggers_two_handed_for_d16(self):
        # Lance is XL but not flagged two_handed; house rule -> d16 init anyway
        row = weapon_row({"name": "Lance", "damage": "1d10", "damage_type": "piercing",
                          "size": "XL", "range": "melee"})
        assert row["two_handed"] == "yes"


class TestArmorRow:
    def test_body_armor_ac_bonus_is_over_ten(self):
        row = armor_row(VALID_CATALOG["armor"][0])  # Linothorax base_ac 12
        assert row["ac_bonus"] == 2
        assert row["shield"] == "no"
        assert row["active"] == "1"
        assert row["fumble_die"] == "d6"

    def test_shield_uses_bonus_all(self):
        row = armor_row(VALID_CATALOG["armor"][1])  # Small shield +1
        assert row["ac_bonus"] == 1
        assert row["shield"] == "yes"


class TestArmorVectors:
    def test_vectors_returns_psb_order(self):
        armor = VALID_CATALOG["armor"][0]
        # armor_vectors returns (piercing, slashing, bludgeoning)
        assert armor_vectors(armor) == (12, 12, 12)

    def test_capped_vectors_adds_agility(self):
        # max_agl_mod absent -> full agility added
        armor = {"ac_piercing": 12, "ac_slashing": 12, "ac_bludgeoning": 12}
        assert capped_vectors(armor, 2) == (14, 14, 14)

    def test_capped_vectors_respects_cap(self):
        # heavy armor caps agility contribution
        armor = {"ac_piercing": 21, "ac_slashing": 22, "ac_bludgeoning": 18, "max_agl_mod": 0}
        assert capped_vectors(armor, 3) == (21, 22, 18)

    def test_vector_string_format(self):
        assert armor_vector_string(14, 13, 12) == "AC: P14/S13/B12"

    def test_shield_adds_to_all_vectors(self):
        assert apply_shield((12, 12, 12), 1) == (13, 13, 13)

    def test_uneven_vectors_preserved(self):
        # e.g. chain mail S17/P15/B13 + shield +2
        assert apply_shield((15, 17, 13), 2) == (17, 19, 15)


class TestBuildScript:
    def test_contains_each_command(self):
        js = build_script(VALID_CATALOG)
        for cmd in ("equip", "unequip", "armor", "weapon", "crit", "ac", "equip-list", "equip-diag"):
            assert "'" + cmd + "'" in js or "case '" + cmd + "'" in js

    def test_embedded_catalog_parses(self):
        js = build_script(VALID_CATALOG)
        start = js.index("var CATALOG = ") + len("var CATALOG = ")
        end = js.index(";\n", start)
        embedded = json.loads(js[start:end])
        assert embedded["weapons"][0]["name"] == "Spear"
        assert len(embedded["armor"]) == 2

    def test_registers_chat_handler(self):
        js = build_script(VALID_CATALOG)
        assert "on('chat:message'" in js

    def test_writes_native_repeating_rows(self):
        js = build_script(VALID_CATALOG)
        # rows are built dynamically: 'repeating_' + section + '_' + id + '_' + field
        assert "'repeating_' + section + '_'" in js
        assert "addRow(cid, 'weapons'" in js
        assert "addRow(cid, 'armor'" in js
        assert "generateRowID()" in js

    def test_recomputes_homebrew_armor_layer(self):
        js = build_script(VALID_CATALOG)
        assert "recomputeArmor" in js
        assert "agility_modifier" in js


class TestBuildHandout:
    def test_handout_shape(self):
        h = build_handout(VALID_CATALOG)
        assert h['type'] == 'handout'
        assert h['name']
        assert h['notes'].strip()
        assert h['gmnotes'].strip()

    def test_notes_contain_item_names_and_tables(self):
        h = build_handout(VALID_CATALOG)
        assert '<table' in h['notes']
        assert 'Spear' in h['notes']
        assert 'Linothorax' in h['notes']
        assert 'Small shield' in h['notes']

    def test_passes_qa_handout_check(self):
        """The generated handout must satisfy the existing QAChecker handout pass."""
        from qa_checker import pass1_handout_check
        assert pass1_handout_check(build_handout(VALID_CATALOG)) == []

    def test_real_catalog_handout_passes_qa(self):
        from qa_checker import pass1_handout_check
        assert pass1_handout_check(build_handout(load_catalog())) == []


class TestRun:
    def test_run_writes_equipment_js(self, tmp_path, monkeypatch):
        import equipment_gen
        catalog_file = tmp_path / "equipment.json"
        catalog_file.write_text(json.dumps(VALID_CATALOG), encoding="utf-8")
        ready_dir = tmp_path / "ready"
        monkeypatch.setattr(equipment_gen, "CATALOG_PATH", catalog_file)
        monkeypatch.setattr(equipment_gen, "READY_DIR", ready_dir)

        equipment_gen.run()

        out = ready_dir / "equipment.js"
        assert out.exists()
        assert "ThraciaEquipment" in out.read_text(encoding="utf-8")

    def test_run_raises_on_invalid_catalog(self, tmp_path, monkeypatch):
        import equipment_gen
        bad = {"weapons": [{"name": "X", "damage": "1d4", "range": "melee"}], "armor": []}
        catalog_file = tmp_path / "equipment.json"
        catalog_file.write_text(json.dumps(bad), encoding="utf-8")
        monkeypatch.setattr(equipment_gen, "CATALOG_PATH", catalog_file)
        monkeypatch.setattr(equipment_gen, "READY_DIR", tmp_path / "ready")

        with pytest.raises(ValueError):
            equipment_gen.run()
