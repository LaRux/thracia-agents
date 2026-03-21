# run.py
#
# Central CLI entry point for all Thracia agents.
#
# Usage examples:
#   python run.py monster --level 1
#   python run.py monster --input data/input/gnoll.md
#   python run.py room --input "data/input/1-1 Entry Hall.md"
#   python run.py encounter --level 1
#   python run.py qa --input data/output/pending/
#   python run.py sheet audit
#   python run.py sheet patch
#   python run.py session commit
#
# WHY ONE ENTRY POINT FOR EVERYTHING?
# Having a single run.py means you always know how to invoke any agent — just
# 'python run.py <command>'. It also means we can add shared setup (logging,
# API key loading, output directory creation) in one place rather than in every
# individual agent file.

import argparse
import sys


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
        help='Generate Roll20 NPC sheets from source material'
    )
    # mutually_exclusive_group means: provide --level OR --input, not both,
    # not neither. required=True means at least one must be provided.
    monster_group = monster_parser.add_mutually_exclusive_group(required=True)
    monster_group.add_argument(
        '--level', type=int,
        help='Process all missing monsters for a dungeon level (e.g. --level 1)'
    )
    monster_group.add_argument(
        '--input', type=str,
        help='Process a single input file (e.g. --input data/input/gnoll.md)'
    )

    # -------------------------------------------------------------------------
    # room command
    # -------------------------------------------------------------------------
    room_parser = subparsers.add_parser(
        'room',
        help='Generate room descriptions and player handouts'
    )
    room_parser.add_argument(
        '--input', type=str, required=True,
        help='Path to room note markdown file'
    )

    # -------------------------------------------------------------------------
    # encounter command
    # -------------------------------------------------------------------------
    encounter_parser = subparsers.add_parser(
        'encounter',
        help='Generate wandering monster tables for a dungeon level'
    )
    encounter_parser.add_argument(
        '--level', type=int, required=True,
        help='Dungeon level to generate encounter table for'
    )

    # -------------------------------------------------------------------------
    # qa command
    # -------------------------------------------------------------------------
    qa_parser = subparsers.add_parser(
        'qa',
        help='Run QA validation on pending agent output'
    )
    qa_parser.add_argument(
        '--input', type=str, required=True,
        help='Directory of pending output to validate (e.g. data/output/pending/)'
    )

    # -------------------------------------------------------------------------
    # sheet command — has sub-actions: audit and patch
    # -------------------------------------------------------------------------
    sheet_parser = subparsers.add_parser(
        'sheet',
        help='Audit or patch the Roll20 DCC character sheet'
    )
    sheet_subparsers = sheet_parser.add_subparsers(dest='sheet_action')
    sheet_subparsers.required = True
    sheet_subparsers.add_parser('audit', help='Generate gap report between sheet and homebrew rules')
    sheet_subparsers.add_parser('patch', help='Generate annotated patch proposals for the sheet')

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
    """Parse arguments and dispatch to the appropriate agent.

    Right now this prints a placeholder message for every command.
    Each future plan will replace a placeholder with a real agent call.

    WHY A DISPATCH TABLE?
    The handlers dict maps command names to functions. This pattern is cleaner
    than a long if/elif chain and makes it easy to see at a glance what each
    command does. As agents are built, you replace the lambda placeholders with
    real imports: e.g. 'monster': monster_gen.run
    """
    parser = build_parser()
    args = parser.parse_args()

    # Placeholder handlers — replaced one by one as agents are built
    handlers = {
        'monster':   lambda a: print(f"[MonsterGen] Not yet implemented. Args: {vars(a)}"),
        'room':      lambda a: print(f"[RoomGen] Not yet implemented. Args: {vars(a)}"),
        'encounter': lambda a: print(f"[EncounterGen] Not yet implemented. Args: {vars(a)}"),
        'qa':        lambda a: print(f"[QAChecker] Not yet implemented. Args: {vars(a)}"),
        'sheet':     lambda a: print(f"[Sheet:{a.sheet_action}] Not yet implemented. Args: {vars(a)}"),
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
