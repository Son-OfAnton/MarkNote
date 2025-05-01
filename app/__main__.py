"""
Main CLI entry point with version control and export commands integrated.
"""
#!/usr/bin/env python3

import sys
import click
from rich.console import Console

from app.cli.commands import cli, register_link_commands, register_version_commands, register_export_commands

def main():
    """Main entry point for the application"""
    # Register link commands
    register_link_commands(cli)
    
    # Register version control commands
    register_version_commands(cli)
    
    # Register export commands
    register_export_commands(cli)
    
    # Run the CLI
    return cli()

if __name__ == "__main__":
    sys.exit(main())