// =============================================================================
// Thracia Campaign Export Script
// =============================================================================
//
// PURPOSE:
//   Exports all character sheets, map pages, and rollable tables from your
//   Roll20 campaign to handouts in your journal. Run this once to give Claude
//   a full picture of what's already built so we don't duplicate work.
//
// INSTALL:
//   1. Open your Roll20 campaign
//   2. Go to Campaign Settings (gear icon) → API Scripts → New Script
//   3. Paste this entire file into the editor
//   4. Click Save Script
//
// USAGE:
//   Type  !export  in the campaign chat (as GM)
//   Three handouts will appear in your journal:
//     - "Export: Characters"     ← all NPC/character sheets and their fields
//     - "Export: Maps & Tokens"  ← all pages, dimensions, token names
//     - "Export: Tables"         ← all rollable tables
//
// WHY THREE HANDOUTS?
//   Roll20 handout content has size limits. Splitting by category keeps each
//   handout small enough to reliably save, and makes it easier to copy/paste
//   the relevant section.
//
// =============================================================================

// "on ready" fires once when the API sandbox finishes loading.
// We log a message so you can confirm the script loaded (check the API log).
on("ready", function () {
    log("[ThrExport] Loaded. Type !export in chat to run.");
});


// Listen for any chat message that starts with "!export"
on("chat:message", function (msg) {

    // Ignore anything that isn't an API command (lines starting with !)
    if (msg.type !== "api") return;

    // Ignore commands other than !export
    if (msg.content.trim().toLowerCase() !== "!export") return;

    // Safety check: only GMs can export campaign data
    if (!playerIsGM(msg.playerid)) {
        sendChat("Export", "/w " + msg.who + " Only GMs can run !export.");
        return;
    }

    sendChat("Export", "/w gm Running export — three handouts will appear in your journal shortly.");

    // -------------------------------------------------------------------------
    // PART 1: CHARACTERS
    // Exports every character sheet: name, type, and ALL attribute fields.
    // This tells us:
    //   - Which monsters are already built (so we don't re-generate them)
    //   - Exact Roll20 field names used by your DCC character sheet
    //     (critical for filling in roll20-npc-schema.md)
    // -------------------------------------------------------------------------

    var characterExport = [];

    // findObjs returns an array of all Roll20 objects matching the filter.
    // {type: "character"} gets every character sheet in the campaign.
    var characters = findObjs({ type: "character" });

    characters.forEach(function (char) {

        var charRecord = {
            id:       char.id,
            name:     char.get("name"),
            archived: char.get("archived")   // archived = retired/inactive characters
        };

        // Get every attribute (field) on this character sheet.
        // Each attribute has a "name" (the field key) and "current"/"max" values.
        // This is where we discover what fields your DCC sheet actually uses —
        // e.g. whether HP is stored as "hp", "HP", "bar1_value", or something else.
        charRecord.fields = {};
        var attrs = findObjs({ type: "attribute", characterid: char.id });
        attrs.forEach(function (attr) {
            var fieldName = attr.get("name");
            var current   = attr.get("current");
            var max       = attr.get("max");
            // Only include the max if it's set — keeps output cleaner
            charRecord.fields[fieldName] = max ? { current: current, max: max } : current;
        });

        characterExport.push(charRecord);
    });

    // Sort alphabetically by name so the output is easy to scan
    characterExport.sort(function (a, b) {
        return a.name.localeCompare(b.name);
    });

    writeHandout(
        "Export: Characters",
        JSON.stringify(characterExport, null, 2)
    );

    // -------------------------------------------------------------------------
    // PART 2: MAPS & TOKENS
    // Exports every page (map) and the tokens placed on it.
    // This tells us:
    //   - What maps exist and their names/dimensions
    //   - Which tokens are placed (and which characters they represent)
    //   - Token HP bars, status markers, and positions
    // -------------------------------------------------------------------------

    var mapExport = [];

    var pages = findObjs({ type: "page" });

    pages.forEach(function (page) {

        var pageRecord = {
            id:          page.id,
            name:        page.get("name"),
            // Width/height in Roll20 units (each unit = 1 grid square by default)
            width:       page.get("width"),
            height:      page.get("height"),
            // Scale tells us how big one grid unit is in the real world
            scale_num:   page.get("scale_number"),
            scale_units: page.get("scale_units"),
            // Whether the page is currently active (the GM's current map)
            current:     (Campaign().get("playerpageid") === page.id),
            tokens:      []
        };

        // Get all tokens on the "objects" layer (player-visible tokens).
        // "gmlayer" tokens (GM-only) are excluded — add layer: "gmlayer" if you want those.
        var tokens = findObjs({ type: "graphic", pageid: page.id, layer: "objects" });

        tokens.forEach(function (token) {
            pageRecord.tokens.push({
                name:         token.get("name"),
                // "represents" is the character sheet ID this token is linked to.
                // Empty string means the token is not linked to any sheet.
                represents:   token.get("represents"),
                // Bar values: in most Roll20 setups, bar1 = HP, bar2/bar3 vary
                bar1_current: token.get("bar1_value"),
                bar1_max:     token.get("bar1_max"),
                bar2_current: token.get("bar2_value"),
                bar2_max:     token.get("bar2_max"),
                bar3_current: token.get("bar3_value"),
                bar3_max:     token.get("bar3_max"),
                // Status markers: comma-separated list of active status icons
                status:       token.get("statusmarkers"),
                // Position in pixels from top-left of the map
                left:         token.get("left"),
                top:          token.get("top")
            });
        });

        mapExport.push(pageRecord);
    });

    writeHandout(
        "Export: Maps & Tokens",
        JSON.stringify(mapExport, null, 2)
    );

    // -------------------------------------------------------------------------
    // PART 3: ROLLABLE TABLES
    // Exports any rollable tables you've built (encounter tables, loot tables, etc.)
    // This tells us what random tables are already in Roll20 vs. what EncounterGen
    // will need to create.
    // -------------------------------------------------------------------------

    var tableExport = [];

    var tables = findObjs({ type: "rollabletable" });

    tables.forEach(function (table) {

        var tableRecord = {
            id:      table.id,
            name:    table.get("name"),
            // showplayers: whether players can see this table's results
            visible: table.get("showplayers"),
            items:   []
        };

        var items = findObjs({ type: "tableitem", rollabletableid: table.id });
        items.forEach(function (item) {
            tableRecord.items.push({
                name:   item.get("name"),
                // weight = relative probability. Higher weight = more likely to roll.
                weight: item.get("weight")
            });
        });

        // Sort items by weight descending so the most common results appear first
        tableRecord.items.sort(function (a, b) { return b.weight - a.weight; });

        tableExport.push(tableRecord);
    });

    writeHandout(
        "Export: Tables",
        JSON.stringify(tableExport, null, 2)
    );

    sendChat("Export", "/w gm Done! Open 'Export: Characters', 'Export: Maps & Tokens', and 'Export: Tables' in your journal.");
});


// =============================================================================
// HELPER: writeHandout(name, content)
// Creates or updates a handout with the given name.
//
// WHY A HELPER?
//   Roll20 handout "notes" is a special "blob" field that must be written with
//   a callback — you can't set it inline in createObj(). This helper handles
//   that pattern so the main export code stays readable.
// =============================================================================

function writeHandout(name, content) {

    // Wrap content in <pre> tags so Roll20 preserves the JSON formatting
    // (otherwise it collapses whitespace and becomes unreadable)
    var htmlContent = "<pre>" + content + "</pre>";

    // Check if a handout with this name already exists
    var existing = findObjs({ type: "handout", name: name });

    if (existing.length > 0) {
        // Update the existing handout
        existing[0].set("notes", htmlContent, function () {
            log("[ThrExport] Updated handout: " + name);
        });
    } else {
        // Create a new handout, then set its notes via callback
        // (Roll20 requires this two-step approach for blob fields)
        var handout = createObj("handout", {
            name:             name,
            inplayerjournals: "",  // empty = GM-only; "all" = visible to all players
            archived:         false
        });
        handout.set("notes", htmlContent, function () {
            log("[ThrExport] Created handout: " + name);
        });
    }
}
