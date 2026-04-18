# run.py
#
# Central CLI entry point for all Thracia agents.
#
# Usage examples:
#   python run.py monster --parse
#   python run.py monster --gap-analysis
#   python run.py monster --generate --all
#   python run.py monster --generate --name "Stirge"
#   python run.py qa
#
# WHY ONE ENTRY POINT FOR EVERYTHING?
# Having a single run.py means you always know how to invoke any agent — just
# 'python run.py <command>'. It also means we can add shared setup (logging,
# API key loading, output directory creation) in one place rather than in every
# individual agent file.

import argparse
import sys
from pathlib import Path

# Add agents to path so run.py can import them
sys.path.insert(0, str(Path(__file__).parent / 'agents' / 'in-progress'))


def build_parser():
    """Build and return the argument parser.

    Kept as a separate function (rather than inline in main()) so that tests
    can import and call it directly without triggering the actual agent logic.

    WHY SEPARATE FROM main()?
    When pytest imports this file to test argument parsing, we don't want it
    to actually run any agents. Separating build_parser() from main() means
    tests can call build_parser() safely without side effects.
    """

    # The top-level parser — handles 'python run.py <command>'
    parser = argparse.ArgumentParser(
        description="Thracia campaign automation agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  monster    Generate Roll20 NPC sheets from stat block source material
  room       Generate DM descriptions and player handouts for dungeon rooms
  encounter  Generate wandering monster tables for a dungeon level
  qa         Run QA validation on pending agent output
  sheet      Audit or patch the Roll20 DCC character sheet
  session    Commit a reviewed post-session draft to the Obsidian vault
        """
    )

    # Subparsers handle 'python run.py monster', 'python run.py room', etc.
    # dest='command' means the chosen subcommand is stored as args.command
    # so you can later check: if args.command == 'monster': ...
    subparsers = parser.add_subparsers(dest='command')
    subparsers.required = True  # fail with usage message if no command given

    # -------------------------------------------------------------------------
    # monster command
    # -------------------------------------------------------------------------
    monster_parser = subparsers.add_parser(
        'monster',
        help='Parse stat blocks, run gap analysis, or generate Roll20 JSON'
    )
    monster_action_group = monster_parser.add_mutually_exclusive_group(required=True)
    monster_action_group.add_argument(
        '--parse', action='store_true',
        help='Parse dcc_statblocks.txt + lore_5e_sections.txt → master_monsters.csv'
    )
    monster_action_group.add_argument(
        '--gap-analysis', action='store_true', dest='gap_analysis',
        help='Compare master_monsters.csv vs Roll20 export → gap_report.txt'
    )
    monster_action_group.add_argument(
        '--generate', action='store_true',
        help='Generate Roll20 JSON for monsters in gap_report.txt (use --name or --all)'
    )
    monster_parser.add_argument(
        '--name', type=str,
        help='Generate sheet for a single named monster (force-regenerate, bypasses gap report)'
    )
    monster_parser.add_argument(
        '--all', action='store_true',
        help='Generate sheets for all monsters listed in gap_report.txt'
    )

    # -------------------------------------------------------------------------
    # room command
    # -------------------------------------------------------------------------
    room_parser = subparsers.add_parser(
        'room',
        help='Extract rooms from PDF and generate Roll20 handout JSONs'
    )
    room_parser.add_argument(
        '--level', type=int,
        help='Dungeon level to process (e.g. 1 → section level_1 in pdf_sections.json)'
    )
    room_parser.add_argument(
        '--pages', type=str,
        help='Override page range from config (e.g. 120-145)'
    )
    room_parser.add_argument(
        '--all', action='store_true',
        help='Process all sections defined in data/input/pdf_sections.json'
    )
    room_parser.add_argument(
        '--reextract', action='store_true',
        help='Force re-extraction even if staged file exists'
    )

    # -------------------------------------------------------------------------
    # encounter command
    # -------------------------------------------------------------------------
    encounter_parser = subparsers.add_parser(
        'encounter',
        help='Extract wandering tables from PDF and generate Roll20 API scripts'
    )
    encounter_parser.add_argument(
        '--level', type=int,
        help='Dungeon level to process (e.g. 1 → section level_1 in pdf_sections.json)'
    )
    encounter_parser.add_argument(
        '--pages', type=str,
        help='Override page range from config (e.g. 115-120)'
    )
    encounter_parser.add_argument(
        '--all', action='store_true',
        help='Process all sections defined in data/input/pdf_sections.json'
    )
    encounter_parser.add_argument(
        '--reextract', action='store_true',
        help='Force re-extraction even if staged file exists'
    )

    # -------------------------------------------------------------------------
    # qa command
    # -------------------------------------------------------------------------
    qa_parser = subparsers.add_parser(
        'qa',
        help='Run QA validation on all files in data/output/pending/'
    )

    # -------------------------------------------------------------------------
    # sheet command — has flags: --audit and --patch
    # -------------------------------------------------------------------------
    sheet_parser = subparsers.add_parser(
        'sheet',
        help='Audit or patch existing Roll20 NPC sheets'
    )
    sheet_parser.add_argument(
        '--audit', action='store_true',
        help='Audit all NPC sheets in the Roll20 export → audit_report.md + audit_report.json'
    )
    sheet_parser.add_argument(
        '--patch', action='store_true',
        help='Write replacement sheets for patchable NPCs → data/output/pending/ (requires prior --audit)'
    )

    # -------------------------------------------------------------------------
    # session command — has sub-actions: commit
    # -------------------------------------------------------------------------
    session_parser = subparsers.add_parser(
        'session',
        help='Work with post-session draft outputs'
    )
    session_subparsers = session_parser.add_subparsers(dest='session_action')
    session_subparsers.required = True
    session_subparsers.add_parser('commit', help='Apply approved session draft to Obsidian vault')

    return parser


def main():
    """Parse arguments and dispatch to the appropriate agent."""
    import json as _json

    parser = build_parser()
    args = parser.parse_args()

    import parse_statblocks
    import gap_analysis
    import monster_gen
    import qa_checker
    import sheet_auditor
    import sheet_patcher
    import parse_pdf
    import room_gen
    import encounter_gen

    def _resolve_sections(a, pages_key):
        """Return {section_key: (start, end)} from CLI args + pdf_sections.json."""
        config_path = Path('data/input/pdf_sections.json')
        if a.all:
            config = _json.loads(config_path.read_text(encoding='utf-8'))
            return {k: tuple(v[pages_key]) for k, v in config.items()}
        if a.level:
            section_key = f'level_{a.level}'
            if a.pages:
                start, end = map(int, a.pages.split('-'))
                return {section_key: (start, end)}
            config = _json.loads(config_path.read_text(encoding='utf-8'))
            return {section_key: tuple(config[section_key][pages_key])}
        print("Specify --level N or --all. See --help.")
        return {}

    def handle_monster(a):
        if a.parse:
            parse_statblocks.run()
        elif a.gap_analysis:
            gap_analysis.run()
        elif a.generate:
            if a.name:
                monster_gen.run_generate_name(a.name)
            else:
                monster_gen.run_generate_all()

    def handle_room(a):
        sections = _resolve_sections(a, 'room_pages')
        for section_key, pages in sections.items():
            staged = parse_pdf.extract_rooms(section_key, pages, reextract=a.reextract)
            room_gen.run(section_key, str(staged))
        if sections:
            qa_checker.run()

    def handle_encounter(a):
        sections = _resolve_sections(a, 'encounter_pages')
        for section_key, pages in sections.items():
            staged = parse_pdf.extract_wandering(section_key, pages, reextract=a.reextract)
            encounter_gen.run(section_key, str(staged))

    def handle_sheet(a):
        if a.audit:
            sheet_auditor.run()
        if a.patch:
            sheet_patcher.run_patch()
        if not a.audit and not a.patch:
            print("Specify --audit, --patch, or both. See --help.")

    handlers = {
        'monster':   handle_monster,
        'room':      handle_room,
        'encounter': handle_encounter,
        'qa':        lambda a: qa_checker.run(),
        'sheet':     handle_sheet,
        'session':   lambda a: print(f"[Session:{a.session_action}] Not yet implemented. Args: {vars(a)}"),
    }

    handler = handlers.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


# Standard Python idiom: only run main() if this file is executed directly.
# If run.py is imported by tests, main() is NOT called — only build_parser()
# is imported, which is safe.
if __name__ == '__main__':
    main()
