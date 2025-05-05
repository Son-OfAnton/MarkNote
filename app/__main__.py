"""
Main CLI entry point with version control and export commands integrated.
"""
#!/usr/bin/env python3

import sys
import click
from rich.console import Console

from app.cli.commands import cli, register_archive_commands, register_delete_commands, register_encryption_commands, register_link_commands, register_tag_commands, register_version_commands


def main():
    """Main entry point for the application"""
    # Register link commands
    register_link_commands(cli)

    # Register version control commands
    register_version_commands(cli)

    register_encryption_commands(cli)

    # Register archive commands
    register_archive_commands(cli)

    register_delete_commands(cli)

    register_tag_commands(cli)

    # Run the CLI
    return cli()


if __name__ == "__main__":
    sys.exit(main())
