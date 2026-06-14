# agents/in-progress/equipment_gen.py
#
# Stage: Generate a self-contained Roll20 mod (API) script from the curated
# weapon & armor catalog (data/input/equipment.json). The script lets players
# equip homebrew DCC gear onto the selected character with one command:
#   !equip <item>      add a weapon row (damage + type) or set armor-vector AC
#   !unequip <item>    remove the matching weapon row / clear armor vectors
#   !armor [name]      whisper an armor's P/S/B AC and penalties
#   !weapon <name>     whisper a weapon's damage, type, and homebrew property
#   !crit <weapon>     whisper the weapon's crit effect
#   !ac [name]         whisper a character's current P/S/B vectors + speed
#   !equip-list        whisper the catalog index
#   !equip-diag [name] dump a sheet's attributes (by character name, or the
#                      selected token) to find real field names / verify which
#                      fields the API can set
#
# This mirrors encounter_gen.py: read staged data -> validate -> emit a ready
# .js. No Claude call — the catalog is static reference data.
#
# Usage: python run.py equipment --build

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent  # agents/in-progress -> project root
CATALOG_PATH = _ROOT / 'data' / 'input' / 'equipment.json'
READY_DIR = _ROOT / 'data' / 'output' / 'ready'
PENDING_DIR = _ROOT / 'data' / 'output' / 'pending'

DAMAGE_TYPES = {'piercing', 'slashing', 'bludgeoning', 'special'}
RANGES = {'melee', 'missile'}


def load_catalog(path=CATALOG_PATH):
    """Read and parse the equipment catalog JSON."""
    return json.loads(Path(path).read_text(encoding='utf-8'))


def validate_catalog(catalog):
    """Validate the catalog dict. Returns a list of error strings (empty == ok)."""
    errors = []
    weapons = catalog.get('weapons', [])
    armor = catalog.get('armor', [])

    if not isinstance(weapons, list):
        errors.append("'weapons' must be a list")
        weapons = []
    if not isinstance(armor, list):
        errors.append("'armor' must be a list")
        armor = []

    for i, w in enumerate(weapons):
        label = w.get('name', f'#{i}')
        for field in ('name', 'damage', 'damage_type', 'range'):
            if field not in w:
                errors.append(f"weapon {label}: missing '{field}'")
        if w.get('damage_type') not in DAMAGE_TYPES and 'damage_type' in w:
            errors.append(f"weapon {label}: damage_type {w['damage_type']!r} not in {sorted(DAMAGE_TYPES)}")
        if w.get('range') not in RANGES and 'range' in w:
            errors.append(f"weapon {label}: range {w['range']!r} not in {sorted(RANGES)}")

    for i, a in enumerate(armor):
        label = a.get('name', f'#{i}')
        if 'name' not in a:
            errors.append(f"armor {label}: missing 'name'")
        if a.get('is_shield'):
            if not isinstance(a.get('ac_bonus_all'), int):
                errors.append(f"armor {label}: shield must have integer 'ac_bonus_all'")
        else:
            for field in ('base_ac', 'ac_slashing', 'ac_piercing', 'ac_bludgeoning'):
                if not isinstance(a.get(field), int):
                    errors.append(f"armor {label}: '{field}' must be an integer")

    names = [item.get('name', '') for item in weapons + armor]
    seen = set()
    for n in names:
        key = n.strip().lower()
        if key in seen:
            errors.append(f"duplicate item name: {n!r}")
        seen.add(key)

    return errors


# These helpers define the contract the generated JS implements against the
# real DCC sheet (v1.07) field names discovered via !equip-diag:
#   repeating_weapons_<id>_{name,damage_base,two_handed,skill}
#   repeating_armor_<id>_{name,ac_bonus,check_penalty,fumble_die,shield,active}
# The sheet's own sheetworkers then compute armor_class, attack, damage,
# initiative die (d16 when two_handed='yes'), check penalty and fumble die.
# We only add the homebrew P/S/B vectors and speed on top.

def weapon_row(weapon):
    """repeating_weapons field values for an equipped weapon.

    Initiative die: the sheet rolls d16 when two_handed == 'yes'; per house rule
    that also covers size L/XL weapons. Attack bonus / final damage are left to
    the sheet (they depend on STR/AGL/level + skill).
    """
    two_handed = bool(weapon.get('two_handed')) or weapon.get('size') in ('L', 'XL')
    return {
        'name': weapon['name'],
        'damage_base': weapon['damage'],
        'two_handed': 'yes' if two_handed else 'no',
        'skill': 'ranged combat' if weapon['range'] == 'missile' else 'close combat',
    }


def armor_row(armor):
    """repeating_armor field values for an equipped armor or shield.

    ac_bonus is the sheet's armor bonus over the unarmored 10 (so the sheet
    computes armor_class = 10 + agility_modifier + ac_bonus itself).
    """
    is_shield = bool(armor.get('is_shield'))
    ac_bonus = armor['ac_bonus_all'] if is_shield else armor['base_ac'] - 10
    return {
        'name': armor['name'],
        'ac_bonus': ac_bonus,
        'check_penalty': armor.get('check_penalty', 0),
        'fumble_die': armor.get('fumble_die', ''),
        'shield': 'yes' if is_shield else 'no',
        'active': '1',
        'quantity': '1',
    }


def armor_vectors(armor):
    """Return raw (piercing, slashing, bludgeoning) AC for a (non-shield) armor."""
    return (armor['ac_piercing'], armor['ac_slashing'], armor['ac_bludgeoning'])


def capped_vectors(armor, agl_mod):
    """Homebrew (P, S, B) for a body armor given the character's AGL modifier,
    applying the armor's max_agl_mod cap."""
    cap = agl_mod if armor.get('max_agl_mod') is None else min(agl_mod, armor['max_agl_mod'])
    return (armor['ac_piercing'] + cap, armor['ac_slashing'] + cap, armor['ac_bludgeoning'] + cap)


def armor_vector_string(p, s, b):
    """Format the project-standard armor-vector text, e.g. 'AC: P12/S12/B12'."""
    return f"AC: P{p}/S{s}/B{b}"


def apply_shield(vectors, bonus):
    """Add a shield's flat bonus to each of (p, s, b)."""
    p, s, b = vectors
    return (p + bonus, s + bonus, b + bonus)


# --- Roll20 mod script body (logic is written once here in JS) ---------------
# The catalog is injected ahead of this block as `var CATALOG = {...};`.
_SCRIPT_BODY = r"""
// ---------------------------------------------------------------------------
// Thracia Equipment — Roll20 mod (API) script. Auto-generated by equipment_gen.
// Paste into Campaign Settings -> Mod (API) Scripts. Do not edit by hand;
// edit data/input/equipment.json and re-run: python run.py equipment --build
// ---------------------------------------------------------------------------
var ThraciaEquipment = (function () {
    'use strict';

    var VECTOR_RE = /AC:\s*P(-?\d+)\/S(-?\d+)\/B(-?\d+)/i;

    function norm(s) { return String(s || '').trim().toLowerCase(); }

    // Neutralize Roll20 metacharacters so whispered sheet values aren't parsed
    // as rolls/abilities (e.g. "%{Test|crit-action}"), which throws sandbox errors.
    function safe(v) {
        return String(v === undefined || v === null ? '' : v)
            .replace(/[{}\[\]]/g, function (c) { return '&#' + c.charCodeAt(0) + ';'; });
    }

    // generateRowID() is a sheet-worker global, NOT available in the mod (API)
    // sandbox, so define the community-standard implementation here.
    var generateUUID = (function () {
        var a = 0, b = [];
        return function () {
            var c = (new Date()).getTime() + 0, d = c === a;
            a = c;
            var e = new Array(8), f;
            for (f = 7; f >= 0; f--) {
                e[f] = '-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz'.charAt(c % 64);
                c = Math.floor(c / 64);
            }
            c = e.join('');
            if (d) {
                for (f = 11; f >= 0 && b[f] === 63; f--) { b[f] = 0; }
                b[f]++;
            } else {
                for (f = 0; f < 12; f++) { b[f] = Math.floor(64 * Math.random()); }
            }
            for (f = 0; f < 12; f++) {
                c += '-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz'.charAt(b[f]);
            }
            return c;
        };
    })();
    function generateRowID() { return generateUUID().replace(/_/g, 'Z'); }

    function findItem(name) {
        var key = norm(name);
        var all = (CATALOG.weapons || []).concat(CATALOG.armor || []);
        for (var i = 0; i < all.length; i++) {
            if (norm(all[i].name) === key) return all[i];
        }
        return null;
    }

    function isWeapon(item) { return item && item.range !== undefined && item.damage !== undefined; }

    function whisper(to, text) {
        // msg.who comes through as e.g. "Christian L. (GM)"; the " (GM)" suffix
        // breaks /w target lookup, so strip it before whispering.
        to = String(to || 'gm').replace(/\s*\(GM\)$/, '');
        sendChat('Equipment', '/w "' + to + '" ' + text, null, { noarchive: true });
    }

    function charFromMsg(msg) {
        if (!msg.selected || !msg.selected.length) return null;
        var tok = getObj('graphic', msg.selected[0]._id);
        if (!tok) return null;
        var cid = tok.get('represents');
        return cid || null;
    }

    function charByName(name) {
        var key = norm(name);
        var chars = findObjs({ type: 'character' });
        for (var i = 0; i < chars.length; i++) {
            if (norm(chars[i].get('name')) === key) return chars[i].id;
        }
        return null;
    }

    // Resolve a character from an explicit name (if given) or the selected token.
    function resolveChar(msg, name) {
        return name ? charByName(name) : charFromMsg(msg);
    }

    function getAttrObj(cid, name) {
        var objs = findObjs({ type: 'attribute', characterid: cid, name: name });
        return objs.length ? objs[0] : null;
    }

    function setAttr(cid, name, value) {
        var a = getAttrObj(cid, name);
        if (a) { a.set('current', value); return a; }
        return createObj('attribute', { characterid: cid, name: name, current: value });
    }

    function getAttrVal(cid, name, dflt) {
        var a = getAttrObj(cid, name);
        return a ? a.get('current') : dflt;
    }

    function writeVectors(cid, p, s, b) {
        var desc = String(getAttrVal(cid, 'description', '') || '');
        var vec = 'AC: P' + p + '/S' + s + '/B' + b;
        if (VECTOR_RE.test(desc)) {
            desc = desc.replace(VECTOR_RE, vec);
        } else {
            desc = (desc ? desc + ' ' : '') + vec + '.';
        }
        setAttr(cid, 'description', desc);
    }

    function readVectors(cid) {
        var desc = String(getAttrVal(cid, 'description', '') || '');
        var m = VECTOR_RE.exec(desc);
        if (!m) return null;
        return { p: parseInt(m[1], 10), s: parseInt(m[2], 10), b: parseInt(m[3], 10) };
    }

    // --- repeating-section helpers (operate on the sheet's own rows) ---------
    function collectRows(cid, section) {
        var prefix = 'repeating_' + section + '_';
        var rows = {};
        findObjs({ type: 'attribute', characterid: cid }).forEach(function (a) {
            var nm = a.get('name');
            if (nm.indexOf(prefix) !== 0) return;
            var rest = nm.slice(prefix.length);
            var us = rest.indexOf('_');
            if (us < 0) return;
            var rowid = rest.slice(0, us), field = rest.slice(us + 1);
            (rows[rowid] = rows[rowid] || {})[field] = a;
        });
        return rows;
    }

    function rowField(row, field, dflt) {
        return row[field] ? row[field].get('current') : dflt;
    }

    function removeRow(row) { for (var k in row) { row[k].remove(); } }

    function addRow(cid, section, fields) {
        var id = generateRowID();
        for (var k in fields) {
            createObj('attribute', {
                characterid: cid,
                name: 'repeating_' + section + '_' + id + '_' + k,
                current: String(fields[k])
            });
        }
        return id;
    }

    function aglMod(cid) { return parseInt(getAttrVal(cid, 'agility_modifier', 0), 10) || 0; }

    // Capture the unarmored speed once so armor speed penalties never compound.
    function baseSpeed(cid) {
        var b = getAttrVal(cid, 'thr_base_speed', '');
        if (b === '' || b === null || b === undefined) {
            b = parseInt(getAttrVal(cid, 'speed', 30), 10);
            if (isNaN(b) || b <= 0) b = 30;
            setAttr(cid, 'thr_base_speed', b);
        }
        b = parseInt(b, 10);
        return (isNaN(b) || b <= 0) ? 30 : b;
    }

    // The DCC sheet does NOT recompute API-created rows, so we write the final
    // armor_class, homebrew P/S/B vectors and speed directly from the managed
    // armor/shield rows. (Manual armor entries are not tracked here.)
    function recomputeArmor(cid) {
        var rows = collectRows(cid, 'armor');
        var body = null, shieldBonus = 0;
        for (var id in rows) {
            var r = rows[id];
            if (rowField(r, 'managed') !== 'thr') continue;
            if (rowField(r, 'shield') === 'yes') {
                shieldBonus += parseInt(rowField(r, 'ac_bonus', 0), 10) || 0;
            } else {
                body = findItem(rowField(r, 'name', ''));
            }
        }
        var agl = aglMod(cid), p, s, b, single, speed = baseSpeed(cid);
        if (body) {
            var cap = (body.max_agl_mod === null || body.max_agl_mod === undefined)
                ? agl : Math.min(agl, body.max_agl_mod);
            p = body.ac_piercing + cap + shieldBonus;
            s = body.ac_slashing + cap + shieldBonus;
            b = body.ac_bludgeoning + cap + shieldBonus;
            single = body.base_ac + cap + shieldBonus;
            speed = baseSpeed(cid) + (body.speed_penalty || 0);
        } else {
            p = s = b = single = 10 + agl + shieldBonus;
        }
        writeVectors(cid, p, s, b);
        setAttr(cid, 'armor_class', single);
        setAttr(cid, 'speed', speed);
        return { p: p, s: s, b: b, single: single, speed: speed };
    }

    // Set the initiative die directly (d16 if any managed two-handed weapon is
    // equipped, else d20), combined with the agility modifier.
    function recomputeInit(cid) {
        var rows = collectRows(cid, 'weapons'), twoH = false;
        for (var id in rows) {
            var r = rows[id];
            if (rowField(r, 'managed') === 'thr' && rowField(r, 'two_handed') === 'yes') twoH = true;
        }
        var agl = aglMod(cid);
        setAttr(cid, 'initiative', (twoH ? '1d16' : '1d20') + (agl >= 0 ? '+' + agl : agl));
    }

    function equip(msg, name) {
        var item = findItem(name);
        if (!item) { whisper(msg.who, 'No item named "' + safe(name) + '". Try !equip-list.'); return; }
        var cid = charFromMsg(msg);
        if (!cid) { whisper(msg.who, 'Select a token that represents a character first.'); return; }
        var cname = (getObj('character', cid) || { get: function () { return 'character'; } }).get('name');

        if (isWeapon(item)) {
            // Write derived attack bonus + damage directly (the sheet won't compute
            // an API-created row). d16 init when two-handed; house rule adds L/XL.
            var twoH = (item.two_handed || item.size === 'L' || item.size === 'XL') ? 'yes' : 'no';
            var isMissile = item.range === 'missile';
            var skill = isMissile ? 'ranged combat' : 'close combat';
            var atk = parseInt(getAttrVal(cid, isMissile ? 'missile_attack' : 'melee_attack', 0), 10) || 0;
            var dmgBonus = parseInt(getAttrVal(cid, isMissile ? 'missile_damage' : 'melee_damage', 0), 10) || 0;
            var dmgStr = item.damage + (dmgBonus ? (dmgBonus > 0 ? '+' : '') + dmgBonus : '');
            addRow(cid, 'weapons', {
                name: item.name, damage_base: item.damage, damage: dmgStr, attack_bonus: atk,
                two_handed: twoH, skill: skill, managed: 'thr'
            });
            recomputeInit(cid);
            whisper(msg.who, '<b>' + safe(cname) + '</b> equipped <b>' + safe(item.name) + '</b> &mdash; ' +
                'atk ' + (atk >= 0 ? '+' + atk : atk) + ', dmg ' + dmgStr + ', ' + skill +
                (twoH === 'yes' ? ', two-handed (init d16)' : '') +
                '. Crit: ' + safe(item.crit_note || 'standard') + '.');
            return;
        }

        // Armor / shield: write the sheet's native row (it computes armor_class,
        // check penalty, fumble die), then recompute the homebrew vectors + speed.
        var wantShield = !!item.is_shield;
        var rows = collectRows(cid, 'armor');
        for (var id in rows) {       // replace the existing managed row of the same kind
            var r = rows[id];
            if (rowField(r, 'managed') !== 'thr') continue;
            if ((rowField(r, 'shield') === 'yes') === wantShield) removeRow(r);
        }
        addRow(cid, 'armor', {
            name: item.name,
            ac_bonus: wantShield ? (item.ac_bonus_all || 0) : (item.base_ac - 10),
            check_penalty: item.check_penalty || 0,
            fumble_die: item.fumble_die || '',
            shield: wantShield ? 'yes' : 'no',
            active: '1', quantity: '1', managed: 'thr'
        });
        var res = recomputeArmor(cid);
        whisper(msg.who, '<b>' + safe(cname) + '</b> ' + (wantShield ? 'raised' : 'donned') + ' <b>' +
            safe(item.name) + '</b> &mdash; AC ' + res.single + ' (P' + res.p + '/S' + res.s + '/B' + res.b +
            '), speed ' + res.speed + ", check " + (item.check_penalty || 0) +
            ', fumble ' + (item.fumble_die || '-') + '.');
    }

    function unequip(msg, name) {
        var cid = charFromMsg(msg);
        if (!cid) { whisper(msg.who, 'Select a token that represents a character first.'); return; }
        var key = norm(name), removed = 0, armorTouched = false;
        ['weapons', 'armor'].forEach(function (section) {
            var rows = collectRows(cid, section);
            for (var id in rows) {
                var r = rows[id];
                if (rowField(r, 'managed') !== 'thr') continue;
                if (norm(rowField(r, 'name', '')) === key) {
                    removeRow(r); removed++;
                    if (section === 'armor') armorTouched = true;
                }
            }
        });
        if (armorTouched) recomputeArmor(cid);
        recomputeInit(cid);
        whisper(msg.who, removed
            ? 'Unequipped "' + safe(name) + '"' + (armorTouched ? ' (AC recomputed).' : '.')
            : 'No managed item named "' + safe(name) + '" to unequip.');
    }

    function showAC(msg, name) {
        var cid = resolveChar(msg, name);
        if (!cid) { whisper(msg.who, 'Select a token, or run: !ac &lt;character name&gt;'); return; }
        var res = recomputeArmor(cid);
        var cname = (getObj('character', cid) || { get: function () { return 'character'; } }).get('name');
        whisper(msg.who, '<b>' + safe(cname) + '</b> AC: P' + res.p + '/S' + res.s + '/B' + res.b +
            " (speed " + res.speed + "').");
    }

    function lookupArmor(msg, name) {
        if (!name) {
            var list = (CATALOG.armor || []).map(function (a) { return a.name; }).join(', ');
            whisper(msg.who, '<b>Armor:</b> ' + list);
            return;
        }
        var item = findItem(name);
        if (!item || item.is_shield === undefined) {
            whisper(msg.who, 'No armor named "' + name + '".');
            return;
        }
        if (item.is_shield) {
            whisper(msg.who, '<b>' + item.name + '</b>: +' + item.ac_bonus_all + ' AC all vectors, check ' +
                item.check_penalty + ', fumble ' + item.fumble_die + (item.notes ? '. ' + item.notes : ''));
        } else {
            whisper(msg.who, '<b>' + item.name + '</b>: AC P' + item.ac_piercing + '/S' + item.ac_slashing +
                '/B' + item.ac_bludgeoning + ' (base ' + item.base_ac + '), check ' + item.check_penalty +
                ', speed ' + item.speed_penalty + "', fumble " + item.fumble_die);
        }
    }

    function lookupWeapon(msg, name) {
        var item = findItem(name);
        if (!item || !isWeapon(item)) { whisper(msg.who, 'No weapon named "' + name + '".'); return; }
        var extra = item.crit_note ? ' Crit: ' + item.crit_note + '.' : '';
        if (item.notes) extra += ' ' + item.notes + '.';
        whisper(msg.who, '<b>' + item.name + '</b>: ' + item.damage + ' ' + item.damage_type +
            ', ' + item.range + ', size ' + (item.size || '?') + '.' + extra);
    }

    function lookupCrit(msg, name) {
        var item = findItem(name);
        if (!item || !isWeapon(item)) { whisper(msg.who, 'No weapon named "' + name + '".'); return; }
        whisper(msg.who, '<b>' + item.name + '</b> crit: ' + (item.crit_note || 'standard DCC crit') +
            '. (Bronze: 50% sunder on crit fail.)');
    }

    function listAll(msg) {
        var w = (CATALOG.weapons || []).map(function (i) { return i.name; }).join(', ');
        var a = (CATALOG.armor || []).map(function (i) { return i.name; }).join(', ');
        whisper(msg.who, '<b>Weapons:</b> ' + w + '<br><b>Armor:</b> ' + a);
    }

    // Diagnostic: discover this sheet's real attribute names and which fields
    // the API can actually set (vs. fields the sheet recomputes/clobbers).
    //   !equip-diag [name]        dump all attrs to API console + whisper subset
    //   !equip-diag probe [name]  write sentinel values (99 / 1d99) to candidates
    // [name] targets a character by name; omit it to use the selected token.
    function diag(msg, arg) {
        var probe = false;
        var name = String(arg || '').trim();
        var parts = name.split(/\s+/).filter(function (p) { return p.length; });
        if (parts.length && parts[0].toLowerCase() === 'probe') {
            probe = true;
            name = parts.slice(1).join(' ');
        }
        var cid = resolveChar(msg, name);
        if (!cid) {
            whisper(msg.who, name ? ('No character named "' + name + '".')
                : 'Select a token that represents a character, or run: !equip-diag &lt;character name&gt;');
            return;
        }
        var attrs = findObjs({ type: 'attribute', characterid: cid });

        if (probe) {
            var sentinels = {
                armor_class: '99', ac: '99', speed: '99', speed_mod: '99',
                initiative: '1d99', initiative_overwritten: '1d99', initiative_mod: '99'
            };
            var wrote = [];
            for (var k in sentinels) { setAttr(cid, k, sentinels[k]); wrote.push(k); }
            whisper(msg.who, 'Probe wrote sentinels (99 / 1d99) to: ' + wrote.join(', ') +
                '.<br>Open the sheet and note which sentinels actually show &mdash; those fields are ' +
                'API-writable. Reset/re-open the sheet afterward. (Use a disposable test PC.)');
            return;
        }

        var all = attrs.map(function (a) { return a.get('name') + ' = ' + a.get('current'); }).sort();
        log('=== equip-diag: ' + all.length + ' attributes on character ' + cid + ' ===');
        all.forEach(function (line) { log('  ' + line); });
        var rx = /(armor|agility|initiative|speed|fumble|check_penalty|melee_attack|melee_damage|missile_attack|crit_die|crit_table|critical_threat|action_dice|^ac$|^armor_class$)/i;
        var relevant = attrs.filter(function (a) { return rx.test(a.get('name')); })
            .map(function (a) { return a.get('name') + ' = ' + safe(a.get('current')); }).sort();
        whisper(msg.who, '<b>' + all.length + ' attributes</b> dumped to the API console (copy them to me).' +
            '<br><b>Combat-relevant:</b><br>' + (relevant.join('<br>') || '(none matched)'));
    }

    function handle(msg) {
        if (msg.type !== 'api') return;
        var parts = msg.content.replace(/^!/, '').split(/\s+/);
        var cmd = parts.shift().toLowerCase();
        var arg = parts.join(' ').trim();
        switch (cmd) {
            case 'equip': equip(msg, arg); break;
            case 'unequip': unequip(msg, arg); break;
            case 'armor': lookupArmor(msg, arg); break;
            case 'weapon': lookupWeapon(msg, arg); break;
            case 'crit': lookupCrit(msg, arg); break;
            case 'ac': showAC(msg, arg); break;
            case 'equip-list': listAll(msg); break;
            case 'equip-diag': diag(msg, arg); break;
        }
    }

    on('chat:message', handle);
    log('Thracia Equipment ready: ' + (CATALOG.weapons || []).length + ' weapons, ' +
        (CATALOG.armor || []).length + ' armor.');

    return { handle: handle, findItem: findItem };
})();
"""


def build_script(catalog):
    """Render the self-contained Roll20 mod script with the catalog embedded."""
    header = (
        "// Thracia Equipment catalog — auto-generated. Do not edit by hand.\n"
        "// Source: data/input/equipment.json\n\n"
    )
    catalog_js = "var CATALOG = " + json.dumps(catalog, indent=2, ensure_ascii=False) + ";\n"
    return header + catalog_js + _SCRIPT_BODY


# --- Player-facing handout (browsable HTML gear list) -----------------------

def _esc(value):
    """Minimal HTML escape for catalog values."""
    return (
        str(value)
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
    )


def _weapon_special(weapon):
    """Compose the player-facing 'Special' cell for a weapon."""
    bits = []
    if weapon.get('two_handed'):
        bits.append('two-handed')
    if weapon.get('reach'):
        bits.append('reach')
    if weapon.get('finesse'):
        bits.append('finesse (AGL)')
    if weapon.get('thrown'):
        bits.append(f"thrown {weapon['thrown']}")
    if weapon.get('crit_note'):
        bits.append(weapon['crit_note'])
    if weapon.get('notes'):
        bits.append(weapon['notes'])
    return _esc('; '.join(bits))


def build_weapons_table_html(weapons):
    """Render the weapons reference table as HTML."""
    head = (
        "<tr><th>Weapon</th><th>Dmg</th><th>Type</th><th>Size</th>"
        "<th>Range</th><th>Special</th><th>Cost</th></tr>"
    )
    rows = []
    for w in weapons:
        rows.append(
            "<tr>"
            f"<td><strong>{_esc(w['name'])}</strong></td>"
            f"<td>{_esc(w['damage'])}</td>"
            f"<td>{_esc(w['damage_type'])}</td>"
            f"<td>{_esc(w.get('size', '-'))}</td>"
            f"<td>{_esc(w['range'])}</td>"
            f"<td>{_weapon_special(w)}</td>"
            f"<td>{_esc(w.get('cost', '-'))}</td>"
            "</tr>"
        )
    return f"<table border='1' cellpadding='4'><thead>{head}</thead><tbody>{''.join(rows)}</tbody></table>"


def build_armor_table_html(armor):
    """Render the body-armor reference table (non-shield entries) as HTML."""
    head = (
        "<tr><th>Armor</th><th>Base</th><th>P</th><th>S</th><th>B</th>"
        "<th>Max AGL</th><th>Check</th><th>Speed</th><th>Fumble</th><th>Cost</th></tr>"
    )
    rows = []
    for a in armor:
        if a.get('is_shield'):
            continue
        agl = a.get('max_agl_mod')
        agl_str = '-' if agl is None else f"+{agl}"
        speed = a.get('speed_penalty', 0)
        speed_str = '-' if not speed else f"{speed}'"
        rows.append(
            "<tr>"
            f"<td><strong>{_esc(a['name'])}</strong></td>"
            f"<td>{a['base_ac']}</td>"
            f"<td>{a['ac_piercing']}</td>"
            f"<td>{a['ac_slashing']}</td>"
            f"<td>{a['ac_bludgeoning']}</td>"
            f"<td>{_esc(agl_str)}</td>"
            f"<td>{_esc(a.get('check_penalty', 0) or '-')}</td>"
            f"<td>{_esc(speed_str)}</td>"
            f"<td>{_esc(a.get('fumble_die', '-'))}</td>"
            f"<td>{_esc(a.get('cost', '-'))}</td>"
            "</tr>"
        )
    return f"<table border='1' cellpadding='4'><thead>{head}</thead><tbody>{''.join(rows)}</tbody></table>"


def build_shields_table_html(armor):
    """Render the shields reference table (is_shield entries) as HTML."""
    head = (
        "<tr><th>Shield</th><th>AC Bonus</th><th>Check</th>"
        "<th>Fumble</th><th>Cost</th><th>Notes</th></tr>"
    )
    rows = []
    for a in armor:
        if not a.get('is_shield'):
            continue
        rows.append(
            "<tr>"
            f"<td><strong>{_esc(a['name'])}</strong></td>"
            f"<td>+{a['ac_bonus_all']}</td>"
            f"<td>{_esc(a.get('check_penalty', 0) or '-')}</td>"
            f"<td>{_esc(a.get('fumble_die', '-'))}</td>"
            f"<td>{_esc(a.get('cost', '-'))}</td>"
            f"<td>{_esc(a.get('notes', ''))}</td>"
            "</tr>"
        )
    return f"<table border='1' cellpadding='4'><thead>{head}</thead><tbody>{''.join(rows)}</tbody></table>"


def build_handout(catalog):
    """Build a Roll20 handout dict with a browsable, player-facing gear list.

    The same shape room_gen emits, so it flows through QAChecker (`python run.py
    qa`) and any future handout importer.
    """
    weapons = catalog.get('weapons', [])
    armor = catalog.get('armor', [])
    notes = (
        "<h2>Weapons &amp; Armor</h2>"
        "<p>Armor protects differently against each damage type. AC is shown as "
        "<strong>P</strong>iercing / <strong>S</strong>lashing / "
        "<strong>B</strong>ludgeoning &mdash; choose your weapon accordingly.</p>"
        "<h3>Weapons</h3>"
        + build_weapons_table_html(weapons)
        + "<h3>Armor</h3>"
        + build_armor_table_html(armor)
        + "<h3>Shields</h3>"
        + build_shields_table_html(armor)
    )
    gmnotes = (
        "Auto-generated from data/input/equipment.json by equipment_gen. "
        "Edit the catalog and re-run `python run.py equipment --handout` to refresh. "
        "Kept in sync with the !equip mod script."
    )
    return {
        'type': 'handout',
        'name': 'Equipment - Weapons & Armor',
        'notes': notes,
        'gmnotes': gmnotes,
        'folder': 'Reference',
    }


def run_handout():
    """Build the player-facing handout JSON and write it to data/output/pending/."""
    catalog = load_catalog(CATALOG_PATH)
    errors = validate_catalog(catalog)
    if errors:
        raise ValueError(f"[EquipmentGen] Catalog validation errors: {errors}")

    handout = build_handout(catalog)
    Path(PENDING_DIR).mkdir(parents=True, exist_ok=True)
    out_path = Path(PENDING_DIR) / 'equipment_handout.json'
    out_path.write_text(json.dumps(handout, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"EquipmentGen: handout '{handout['name']}' -> {out_path} (run `python run.py qa` to validate)")


def run():
    """Load + validate the catalog, then write equipment.js to data/output/ready/."""
    catalog = load_catalog(CATALOG_PATH)
    errors = validate_catalog(catalog)
    if errors:
        raise ValueError(f"[EquipmentGen] Catalog validation errors: {errors}")

    js = build_script(catalog)
    Path(READY_DIR).mkdir(parents=True, exist_ok=True)
    out_path = Path(READY_DIR) / 'equipment.js'
    out_path.write_text(js, encoding='utf-8')
    n_w = len(catalog.get('weapons', []))
    n_a = len(catalog.get('armor', []))
    print(f"EquipmentGen: {n_w} weapons + {n_a} armor -> {out_path}")
