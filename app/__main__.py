"""
Main CLI entry point with link commands integrated.
"""
#!/usr/bin/env python3

import sys
import click
from rich.console import Console

from app.cli.commands import cli, link, register_link_commands

def main():
    """Main entry point for the application"""
    # Register link commands
    register_link_commands(cli)
    
    # Run the CLI
    return cli()

if __name__ == "__main__":
    sys.exit(main())