"""
CodeAtlas CLI entry point.
"""
import argparse
import sys

from cli.commands.analyze import analyze_command
from cli.commands.export import export_command


def print_banner() -> None:
    banner = r"""
   ______          __      ___  __          __
  / ____/___  ____/ /__   /   |/_/___ ______/ /____
 / /   / __ \/ __  / _ \ / /| | / __ `/ ___/ __/ ___/
/ /___/ /_/ / /_/ /  __// ___ |/ /_/ / /  (__  )__)
\____/\____/\__,_/\___//_/  |_|\__,_/_/  /____/____/
    """
    print(banner)
    print("  CodeAtlas – AI Code Intelligence Platform\n")


def main() -> int:
    print_banner()

    parser = argparse.ArgumentParser(
        prog="codeatlas",
        description="CodeAtlas – AI Code Intelligence Platform",
    )
    parser.add_argument("command", help="Command: analyze | export")
    parser.add_argument("--path", help="Path to source code (for analyze)")
    parser.add_argument("--format", default="json", help="Export format (json|html|markdown)")
    parser.add_argument("report_id", nargs="?", help="Report ID (for export)")

    args = parser.parse_args()

    if args.command == "analyze":
        analyze_command(args.path)
    elif args.command == "export":
        export_command(args.format, args.report_id)
    else:
        print(f"❌ Unknown command: {args.command}")
        parser.print_help()
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())