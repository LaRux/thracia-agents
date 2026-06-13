# tests/test_equipment_gen.py
import json

import pytest

from equipment_gen import (
    load_catalog,
    validate_catalog,
    weapon_attrs,
    armor_vectors,
    armor_vector_string,
    apply_shield,
    build_script,
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


class TestWeaponAttrs:
    def test_melee_weapon_maps_fields(self):
        attrs = weapon_attrs(VALID_CATALOG["weapons"][0])
        assert attrs == {
            "name": "Spear",
            "damage": "1d8",
            "damage_base": "1d8",
            "type": "melee",
        }

    def test_missile_weapon_type_is_missile(self):
        attrs = weapon_attrs(VALID_CATALOG["weapons"][1])
        assert attrs["type"] == "missile"
        assert attrs["damage"] == "1d6"


class TestArmorVectors:
    def test_vectors_returns_psb_order(self):
        armor = VALID_CATALOG["armor"][0]
        # armor_vectors returns (piercing, slashing, bludgeoning)
        assert armor_vectors(armor) == (12, 12, 12)

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
        for cmd in ("equip", "unequip", "armor", "weapon", "crit", "equip-list"):
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

    def test_writes_repeating_weapons(self):
        js = build_script(VALID_CATALOG)
        assert "repeating_weapons_" in js
        assert "generateRowID()" in js


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
