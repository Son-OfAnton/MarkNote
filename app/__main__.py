#!/usr/bin/env python3
"""
MarkNote - A command-line tool for creating, organizing, and managing Markdown-based notes.
"""
import sys
from app.cli.commands import cli

def main():
    """Main entry point for the application"""
    return cli()

if __name__ == "__main__":
    sys.exit(main())