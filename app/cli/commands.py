"""
CLI commands for MarkNote
"""
import click
from rich.console import Console

console = Console()

@click.group()
@click.version_option(version="0.1.0")
def cli():
    """MarkNote - A command-line tool for creating, organizing, and managing Markdown-based notes."""
    pass

@cli.command()
@click.argument("title")
@click.option("--template", "-t", default="default", help="Template to use for the new note.")
@click.option("--tags", multiple=True, help="Tags for the new note.")
@click.option("--category", "-c", help="Category for the new note.")
def new(title, template, tags, category):
    """Create a new note with the given TITLE."""
    console.print(f"Creating a new note: [bold]{title}[/bold]", style="green")
    console.print(f"Template: [italic]{template}[/italic]")
    if tags:
        console.print(f"Tags: [italic]{', '.join(tags)}[/italic]")
    if category:
        console.print(f"Category: [italic]{category}[/italic]")
    console.print("\n[yellow]Note: This is just a placeholder for now.[/yellow]")

@cli.command()
@click.option("--tag", help="Filter notes by tag.")
@click.option("--category", "-c", help="Filter notes by category.")
def list(tag, category):
    """List all notes, optionally filtered by tag or category."""
    console.print("[bold]Notes:[/bold]", style="blue")
    console.print("\n[yellow]Note: This is just a placeholder for now.[/yellow]")

@cli.command()
@click.argument("query")
def search(query):
    """Search for notes containing the given QUERY."""
    console.print(f"Searching for notes containing: [bold]{query}[/bold]", style="blue")
    console.print("\n[yellow]Note: This is just a placeholder for now.[/yellow]")

@cli.command()
@click.argument("title")
def edit(title):
    """Edit the note with the given TITLE."""
    console.print(f"Editing note: [bold]{title}[/bold]", style="green")
    console.print("\n[yellow]Note: This is just a placeholder for now.[/yellow]")

@cli.command()
@click.argument("title")
def show(title):
    """Display the note with the given TITLE with proper formatting."""
    console.print(f"Displaying note: [bold]{title}[/bold]", style="blue")
    console.print("\n[yellow]Note: This is just a placeholder for now.[/yellow]")

if __name__ == "__main__":
    cli()