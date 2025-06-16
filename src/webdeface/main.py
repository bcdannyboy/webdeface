"""Main entry points for WebDeface Monitor applications."""

import sys


def main_cli() -> None:
    """Entry point for the CLI application."""
    try:
        from .cli.main import cli

        cli()
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)


def main_api() -> None:
    """Entry point for the API application."""
    try:
        from .api.app import main

        main()
    except KeyboardInterrupt:
        print("\n❌ API server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error starting API server: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    # Default to CLI if run directly
    main_cli()
