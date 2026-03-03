import argparse

from cli.commands.analyze import analyze_command
from cli.commands.export import export_command
from app.api.routes.upload import upload_command
from app.api.routes.health import health_command
from app.utils import print_banner

def main():
    print_banner()

    parser = argparse.ArgumentParser(
        prog="codeatlas",
        description="CodeAtlas – AI Code Intelligence Platform"
    )

    parser.add_argument("command", help="Command to execute")
    parser.add_argument("--path", help="Path to source code")
    parser.add_argument("--file", help="ZIP file path")
    parser.add_argument("--format", default="json", help="Export format")

    args = parser.parse_args()

    match args.command:
        case "analyze":
            analyze_command(args.path)

        case "upload":
            upload_command(args.file)

        case "export":
            export_command(args.format)

        case "health":
            health_command()

        

if __name__ == "__main__":
    main()
