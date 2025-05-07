"""
CLI commands for MarkNote
"""
import csv
from datetime import date, datetime
from io import StringIO
import json
import os
import sys
from typing import Dict, List, Optional, Tuple
from datetime import date as dt


import click
from markdown import Markdown
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from app.config.config_manager import get_config_manager, get_daily_note_config
from app.core.daily_note_service import get_daily_note_service
from app.core.note_manager_archieve_extension import ArchiveNoteManager
from app.core.note_manager_extension import EncryptionNoteManager
import app.models.note

from app.core.note_manager import NoteManager
from app.utils.encryption import prompt_for_password
from app.utils.template_manager import TemplateManager, get_editor_handlers
from app.utils.editor_handler import edit_file, edit_content, is_valid_editor, get_available_editors
from app.utils.file_handler import parse_frontmatter
from app.models.note import Note

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """MarkNote - A command-line tool for creating, organizing, and managing Markdown-based notes."""
    pass


@cli.command()
@click.argument("title")
@click.option("--template", "-t", default="default", help="Template to use for the new note.")
@click.option("--tags", "-g", help="Tags for the note (comma-separated list).")
@click.option("--category", "-c", help="Category for the new note.")
@click.option("--interactive/--no-interactive", "-i/-n", default=False,
              help="Interactive mode for entering additional metadata.")
@click.option("--force", "-f", is_flag=True, help="Force overwrite if the note already exists.")
@click.option("--output-dir", "-o", help="Custom directory to save the note to. Overrides the default location.")
@click.option("--editor", "-e", help="Specify which editor to use for editing the note (if opening for edit).")
def new(title: str, template: str, tags: Optional[str], category: Optional[str],
        interactive: bool, force: bool, output_dir: Optional[str], editor: Optional[str] = None):
    """Create a new note with the given TITLE."""
    try:
        # Validate the specified editor if provided
        if editor and not is_valid_editor(editor):
            console.print(
                f"[bold red]Error:[/bold red] Specified editor '{editor}' not found or not executable")
            available_editors = get_available_editors()
            if available_editors:
                console.print(
                    f"Available editors: {', '.join(available_editors)}")
            return 1

        # Create note manager
        note_manager = NoteManager()

        # Parse tags from comma-separated string
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',')]

        # Get available templates
        template_manager = TemplateManager()
        available_templates = template_manager.list_templates()

        # Verify template exists
        if template not in available_templates:
            console.print(
                f"[bold red]Error:[/bold red] Template '{template}' not found.")
            console.print(
                f"Available templates: {', '.join(available_templates)}")
            return 1

        # Validate output directory
        if output_dir:
            output_dir = os.path.expanduser(output_dir)
            if not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir)
                    console.print(
                        f"Created output directory: [cyan]{output_dir}[/cyan]")
                except (PermissionError, OSError) as e:
                    console.print(
                        f"[bold red]Error:[/bold red] Failed to create output directory: {str(e)}")
                    return 1
            elif not os.access(output_dir, os.W_OK):
                console.print(
                    f"[bold red]Error:[/bold red] No write permission for directory: {output_dir}")
                return 1

        additional_metadata = {}

        # Interactive mode for additional metadata
        if interactive:
            console.print(Panel(f"[bold]Creating a new note: [cyan]{title}[/cyan][/bold]",
                                title="MarkNote", subtitle="Interactive Mode"))

            # Confirm or update template
            template_options = ", ".join(available_templates)
            console.print(
                f"Available templates: [cyan]{template_options}[/cyan]")
            template = Prompt.ask("Template", default=template)

            # Get tags if not provided
            if not tag_list:
                tags_input = Prompt.ask("Tags (comma-separated)", default="")
                if tags_input:
                    tag_list = [tag.strip() for tag in tags_input.split(",")]

            # Get category if not provided
            if not category:
                category = Prompt.ask("Category", default="")
                if category == "":
                    category = None

            # Get output directory if not provided
            if not output_dir:
                default_dir = note_manager.notes_dir
                output_dir_input = Prompt.ask(
                    "Save to directory", default=default_dir)
                if output_dir_input and output_dir_input != default_dir:
                    output_dir = output_dir_input

            # Get editor if not provided
            if not editor:
                available_editors = get_available_editors()
                if available_editors:
                    console.print(
                        f"Available editors: [cyan]{', '.join(available_editors)}[/cyan]")
                    editor_input = Prompt.ask(
                        "Editor (leave blank for system default)", default="")
                    if editor_input:
                        if is_valid_editor(editor_input):
                            editor = editor_input
                        else:
                            console.print(
                                f"[yellow]Warning: Editor '{editor_input}' not found, using system default.[/yellow]")

            # Get additional metadata based on template
            if template == "meeting":
                additional_metadata["meeting_date"] = Prompt.ask(
                    "Meeting date", default="")
                additional_metadata["meeting_time"] = Prompt.ask(
                    "Meeting time", default="")
                additional_metadata["location"] = Prompt.ask(
                    "Location", default="")
                additional_metadata["attendees"] = Prompt.ask(
                    "Attendees", default="")

            elif template == "journal":
                additional_metadata["mood"] = Prompt.ask("Mood", default="")

        # Console feedback about what we're about to do
        action_desc = f"Creating note '{title}'"
        if output_dir:
            action_desc += f" in directory: {output_dir}"
        if category:
            action_desc += f", category: {category}"
        if tag_list:
            action_desc += f", tags: {', '.join(tag_list)}"
        if editor:
            action_desc += f", editor: {editor}"
        console.print(f"[blue]{action_desc}[/blue]")

        # Create the note
        try:
            note = note_manager.create_note(
                title=title,
                template_name=template,
                tags=tag_list,
                category=category,
                additional_metadata=additional_metadata,
                output_dir=output_dir
            )

            # Success message
            note_path = note.metadata.get('path', '')
            console.print(
                f"[bold green]Note created successfully:[/bold green] {note_path}")

            # Show note information
            console.print(Panel(
                f"[bold]Title:[/bold] {note.title}\n"
                f"[bold]Template:[/bold] {template}\n"
                f"[bold]Tags:[/bold] {', '.join(note.tags) if note.tags else 'None'}\n"
                f"[bold]Category:[/bold] {note.category or 'None'}\n"
                f"[bold]File:[/bold] {os.path.basename(note_path)}\n"
                f"[bold]Path:[/bold] {os.path.dirname(note_path)}"
            ))

            # Ask if user wants to edit the note immediately
            if Confirm.ask("Would you like to edit this note now?", default=False):
                return edit_note([title], category=category, output_dir=output_dir, editor=editor)

            return 0

        except FileExistsError as e:
            if force:
                # If force flag is set, try to get the existing note and update it
                existing_note = note_manager.get_note(
                    title, category, output_dir=output_dir)
                if existing_note:
                    # Update the note with new content from the template
                    # This would be a feature to implement later
                    console.print(
                        f"[bold yellow]Note already exists and will be overwritten.[/bold yellow]")
                    # For now, return an error
                    console.print(
                        f"[bold red]Error:[/bold red] Overwriting existing notes is not yet implemented.")
                    return 1
            else:
                console.print(f"[bold red]Error:[/bold red] {str(e)}")
                console.print("Use --force to overwrite the existing note.")
                return 1
        except (PermissionError, IOError) as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            return 1

    except Exception as e:
        console.print(f"[bold red]Error creating note:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


@cli.command()
@click.argument("query")
@click.option("--output-dir", "-o", help="Custom directory to search in. Overrides the default location.")
def search(query, output_dir):
    """Search for notes containing the given QUERY."""
    try:
        note_manager = NoteManager()
        notes = note_manager.search_notes(query, output_dir=output_dir)

        if not notes:
            console.print(
                f"[yellow]No notes found matching query: '{query}'[/yellow]")
            return 0

        console.print(
            f"[bold blue]Found {len(notes)} notes matching '{query}':[/bold blue]")

        for note in notes:
            path = note.metadata.get('path', '')

            # Format the note information
            console.print(f"[bold cyan]{note.title}[/bold cyan]")
            console.print(f"  [dim]File:[/dim] {path}")
            if note.category:
                console.print(f"  [dim]Category:[/dim] {note.category}")
            if note.tags:
                console.print(f"  [dim]Tags:[/dim] {', '.join(note.tags)}")
            console.print()

        return 0
    except Exception as e:
        console.print(f"[bold red]Error searching notes:[/bold red] {str(e)}")
        return 1


@cli.command()
@click.argument("titles", nargs=-1, required=True)
@click.option("--category", "-c", help="Category of the note.")
@click.option("--output-dir", "-o", help="Custom directory to look in. Overrides the default location.")
@click.option("--editor", "-e", help="Specify which editor to use for editing.")
def edit(titles, category, output_dir, editor):
    """Edit one or more notes with the given TITLES in your preferred editor.

    You can specify a custom editor with the --editor option, otherwise the system default will be used.
    """
    return edit_note(titles, category, output_dir, editor)


def edit_note(titles, category=None, output_dir=None, editor=None):
    """Implementation of the edit functionality to allow reuse."""
    try:
        # Validate the specified editor if provided
        if editor and not is_valid_editor(editor):
            console.print(
                f"[bold red]Error:[/bold red] Specified editor '{editor}' not found or not executable")
            available_editors = get_available_editors()
            if available_editors:
                console.print(
                    f"Available editors: {', '.join(available_editors)}")
            return 1

        note_manager = NoteManager()

        for title in titles:
            # Get the note
            note = note_manager.get_note(
                title, category, output_dir=output_dir)

            if not note:
                # Try to find the note without relying on exact category match
                note_path = note_manager.find_note_path(
                    title, category, output_dir)
                if note_path:
                    console.print(
                        f"[yellow]Note found at a different location than specified:[/yellow] {note_path}")

                    # Try to read the note and recreate the Note object
                    try:
                        with open(note_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        metadata, content_without_frontmatter = parse_frontmatter(
                            content)

                        # Extract category from path if possible
                        path_parts = os.path.normpath(
                            note_path).split(os.path.sep)
                        detected_category = None
                        if len(path_parts) >= 2:
                            possible_category = path_parts[-2]
                            base_dir = output_dir if output_dir else note_manager.notes_dir
                            base_name = os.path.basename(
                                os.path.normpath(base_dir))
                            if possible_category != base_name:
                                detected_category = possible_category
                                console.print(
                                    f"[yellow]Detected category from path:[/yellow] {detected_category}")

                        # Create a temporary note object
                        from datetime import datetime
                        note = Note(
                            title=title,
                            content=content_without_frontmatter,
                            category=detected_category or category,
                            filename=os.path.basename(note_path),
                            metadata={'path': note_path}
                        )
                    except Exception as e:
                        console.print(
                            f"[bold red]Error reading note:[/bold red] {str(e)}")
                        continue
                else:
                    console.print(
                        f"[bold red]Error:[/bold red] Note '{title}' not found.")
                    if category:
                        console.print(
                            f"Make sure the category '{category}' is correct.")
                    if output_dir:
                        console.print(f"Looking in directory: {output_dir}")
                    continue

            # Get the file path
            path = note.metadata.get('path', '')
            if not path or not os.path.exists(path):
                console.print(
                    f"[bold red]Error:[/bold red] Can't find note file at {path}")
                continue

            # Display note information before editing
            detected_category = note.category or (
                category if category else None)
            if detected_category:
                console.print(
                    f"Editing note: [bold cyan]{title}[/bold cyan] in category [bold green]{detected_category}[/bold green]")
            else:
                console.print(f"Editing note: [bold cyan]{title}[/bold cyan]")
            console.print(f"File: [dim]{path}[/dim]")

            # Show which editor is being used
            editor_display = editor if editor else "system default"
            console.print(
                f"Using editor: [bold magenta]{editor_display}[/bold magenta]")

            # Open the file in the user's editor
            success, error = edit_file(path, custom_editor=editor)

            if not success:
                console.print(
                    f"[bold red]Error editing note:[/bold red] {error}")
                return 1

            # Read the updated content
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                console.print(
                    f"[bold red]Error reading updated file:[/bold red] {str(e)}")
                return 1

            # Parse frontmatter and content
            metadata, content_without_frontmatter = parse_frontmatter(content)

            # Update the note in our system with the new content
            success, updated_note, error = note_manager.edit_note_content(
                title, content_without_frontmatter, category=detected_category, output_dir=output_dir
            )

            if success:
                console.print(
                    f"[bold green]Note updated successfully![/bold green]")
            else:
                console.print(
                    f"[bold red]Error updating note:[/bold red] {error}")
                return 1

        return 0

    except Exception as e:
        console.print(f"[bold red]Error editing note:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


@cli.command()
@click.argument("title")
@click.option("--category", "-c", help="Category of the note.")
@click.option("--output-dir", "-o", help="Custom directory to look in. Overrides the default location.")
def show(title, category, output_dir):
    """Display the note with the given TITLE with proper formatting."""
    try:
        note_manager = NoteManager()
        note = note_manager.get_note(title, category, output_dir=output_dir)

        if note:
            # Display the note
            console.print(Panel(
                f"[bold cyan]{note.title}[/bold cyan]\n\n{note.content}",
                title=f"MarkNote - {note.title}",
                subtitle=f"Category: {note.category or 'None'} | Tags: {', '.join(note.tags) if note.tags else 'None'}"
            ))
            return 0
        else:
            # Try to find the note without relying on exact category match
            note_path = note_manager.find_note_path(
                title, category, output_dir)
            if note_path:
                console.print(f"[yellow]Note found at:[/yellow] {note_path}")

                # Try to read the note content
                with open(note_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                metadata, content_without_frontmatter = parse_frontmatter(
                    content)

                # Display the note
                console.print(Panel(
                    f"[bold cyan]{title}[/bold cyan]\n\n{content_without_frontmatter}",
                    title=f"MarkNote - {title}",
                    subtitle="Note found with alternative path lookup"
                ))
                return 0
            else:
                console.print(
                    f"[bold red]Error:[/bold red] Note '{title}' not found.")
                if category:
                    console.print(
                        f"Make sure the category '{category}' is correct.")
                if output_dir:
                    console.print(f"Looking in directory: {output_dir}")
                return 1

    except Exception as e:
        console.print(f"[bold red]Error displaying note:[/bold red] {str(e)}")
        return 1


@cli.command()
def templates():
    """List available note templates."""
    try:
        template_manager = TemplateManager()
        templates = template_manager.list_templates()

        if not templates:
            console.print("[yellow]No templates found.[/yellow]")
            return 0

        console.print("[bold blue]Available templates:[/bold blue]")
        for template in templates:
            console.print(f"- [cyan]{template}[/cyan]")

        return 0

    except Exception as e:
        console.print(
            f"[bold red]Error listing templates:[/bold red] {str(e)}")
        return 1


@cli.command()
def editors():
    """List available editors on your system."""
    try:
        available_editors = get_available_editors()

        if not available_editors:
            console.print(
                "[yellow]No recognized editors found on your system.[/yellow]")
            console.print(
                "You can still specify a custom editor with the --editor option.")
            return 0

        console.print(
            "[bold blue]Available editors on your system:[/bold blue]")
        for editor in available_editors:
            console.print(f"- [cyan]{editor}[/cyan]")

        # Show current default editor
        from app.utils.editor_handler import get_editor
        default_editor = get_editor()
        console.print(
            f"\n[bold green]Default editor:[/bold green] {default_editor}")
        console.print(
            "\n[dim]You can change the default editor by setting the EDITOR or VISUAL environment variable,[/dim]")
        console.print(
            "[dim]or specify a different editor for a single command with --editor (-e) option.[/dim]")

        return 0

    except Exception as e:
        console.print(f"[bold red]Error listing editors:[/bold red] {str(e)}")
        return 1


@click.group()
def link():
    """Commands for managing links between notes."""
    pass


@link.command(name="add")
@click.argument("source")
@click.argument("target")
@click.option("--bidirectional", "-b", is_flag=True, help="Create a two-way link between notes.")
@click.option("--category", "-c", help="Category of the source note.")
@click.option("--target-category", "-tc", help="Category of the target note.")
@click.option("--output-dir", "-o", help="Custom directory to look for notes.")
def add_link(source, target, bidirectional, category, target_category, output_dir):
    """
    Add a link from SOURCE note to TARGET note.

    If --bidirectional is specified, a link will also be created from TARGET to SOURCE.
    """
    note_manager = NoteManager()

    # Add link between notes
    success, error = note_manager.add_link_between_notes(
        source_title=source,
        target_title=target,
        bidirectional=bidirectional,
        category=category,
        target_category=target_category,
        output_dir=output_dir
    )

    if success:
        if bidirectional:
            console.print(
                f"[bold green]Successfully linked[/bold green] '{source}' [bold]↔[/bold] '{target}' [dim](bidirectional)[/dim]")
        else:
            console.print(
                f"[bold green]Successfully linked[/bold green] '{source}' [bold]→[/bold] '{target}'")
    else:
        console.print(f"[bold red]Error:[/bold red] {error}")
        return 1

    return 0


@link.command(name="remove")
@click.argument("source")
@click.argument("target")
@click.option("--bidirectional", "-b", is_flag=True, help="Remove links in both directions.")
@click.option("--category", "-c", help="Category of the source note.")
@click.option("--target-category", "-tc", help="Category of the target note.")
@click.option("--output-dir", "-o", help="Custom directory to look for notes.")
def remove_link(source, target, bidirectional, category, target_category, output_dir):
    """
    Remove a link from SOURCE note to TARGET note.

    If --bidirectional is specified, links in both directions will be removed.
    """
    note_manager = NoteManager()

    # Remove link between notes
    success, error = note_manager.remove_link_between_notes(
        source_title=source,
        target_title=target,
        bidirectional=bidirectional,
        category=category,
        target_category=target_category,
        output_dir=output_dir
    )

    if success:
        if bidirectional:
            console.print(
                f"[bold green]Successfully removed link[/bold green] between '{source}' and '{target}' [dim](bidirectional)[/dim]")
        else:
            console.print(
                f"[bold green]Successfully removed link[/bold green] from '{source}' to '{target}'")
    else:
        console.print(f"[bold red]Error:[/bold red] {error}")
        return 1

    return 0


@link.command(name="list")
@click.argument("title")
@click.option("--category", "-c", help="Category of the note.")
@click.option("--output-dir", "-o", help="Custom directory to look for notes.")
@click.option("--backlinks", "-b", is_flag=True, help="Show notes that link to this note instead.")
def list_links(title, category, output_dir, backlinks):
    """
    List all links from the specified note.

    If --backlinks is specified, show notes that link to this note instead.
    """
    note_manager = NoteManager()

    if backlinks:
        # Get backlinks (notes that link to this note)
        success, linked_notes, error = note_manager.get_backlinks(
            title=title,
            category=category,
            output_dir=output_dir
        )
        link_type = "backlinks"
    else:
        # Get outgoing links from this note
        success, linked_notes, error = note_manager.get_linked_notes(
            title=title,
            category=category,
            output_dir=output_dir
        )
        link_type = "linked notes"

    if not success:
        console.print(f"[bold red]Error:[/bold red] {error}")
        return 1

    # Check if there are any linked notes
    if not linked_notes:
        if backlinks:
            console.print(f"No notes link to [bold cyan]'{title}'[/bold cyan]")
        else:
            console.print(
                f"No links found from [bold cyan]'{title}'[/bold cyan] to other notes")
        return 0

    # Create a table to display linked notes
    table = Table(title=f"{link_type.capitalize()} for '{title}'")
    table.add_column("Title", style="cyan")
    table.add_column("Category", style="green")
    table.add_column("Tags", style="yellow")
    table.add_column("Last Modified", style="dim")

    # Add each linked note to the table
    for note in linked_notes:
        table.add_row(
            note.title,
            note.category or "None",
            ", ".join(note.tags) if note.tags else "None",
            note.updated_at.strftime("%Y-%m-%d %H:%M")
        )

    # Display the table
    console.print(table)

    # If there was a warning about missing notes, display it
    if error:
        console.print(f"[yellow]Warning:[/yellow] {error}")

    return 0


@link.command(name="orphaned")
@click.option("--output-dir", "-o", help="Custom directory to look for notes.")
def find_orphaned_links(output_dir):
    """
    Find all links that point to non-existent notes.
    """
    note_manager = NoteManager()

    # Find orphaned links
    orphaned_links = note_manager.find_orphaned_links(output_dir=output_dir)

    if not orphaned_links:
        console.print("[bold green]No orphaned links found.[/bold green]")
        return 0

    # Create a table to display orphaned links
    table = Table(title="Orphaned Links")
    table.add_column("Note", style="cyan")
    table.add_column("Category", style="green")
    table.add_column("Missing Links", style="yellow")

    # Add each note with orphaned links to the table
    for note, missing_links in orphaned_links:
        table.add_row(
            note.title,
            note.category or "None",
            ", ".join(missing_links)
        )

    # Display the table
    console.print(table)
    console.print(
        "\n[bold yellow]Tip:[/bold yellow] To fix orphaned links, either create the missing notes or remove the links.")

    return 0


@link.command(name="show")
@click.argument("title")
@click.option("--category", "-c", help="Category of the note.")
@click.option("--output-dir", "-o", help="Custom directory to look for notes.")
def show_note_with_links(title, category, output_dir):
    """
    Display a note with its linked notes and backlinks.
    """
    note_manager = NoteManager()

    # Get the note and its links
    note, linked_notes, backlinks = note_manager.get_note_with_links(
        title=title,
        category=category,
        output_dir=output_dir
    )

    if not note:
        console.print(f"[bold red]Error:[/bold red] Note '{title}' not found.")
        return 1

    # Display the note content
    console.print(Panel(
        f"[bold cyan]{note.title}[/bold cyan]\n\n{note.content}",
        title=f"MarkNote - {note.title}",
        subtitle=f"Category: {note.category or 'None'} | Tags: {', '.join(note.tags) if note.tags else 'None'}"
    ))

    # Display linked notes if any
    if linked_notes:
        linked_table = Table(title="Linked Notes")
        linked_table.add_column("Title", style="cyan")
        linked_table.add_column("Category", style="green")

        for linked_note in linked_notes:
            linked_table.add_row(
                linked_note.title, linked_note.category or "None")

        console.print(linked_table)
    else:
        console.print("[dim]No linked notes.[/dim]")

    # Display backlinks if any
    if backlinks:
        backlinks_table = Table(title="Backlinks (Notes linking to this note)")
        backlinks_table.add_column("Title", style="cyan")
        backlinks_table.add_column("Category", style="green")

        for backlink in backlinks:
            backlinks_table.add_row(
                backlink.title, backlink.category or "None")

        console.print(backlinks_table)
    else:
        console.print("[dim]No backlinks.[/dim]")

    return 0


@click.group()
def network():
    """Commands for analyzing note networks and connections."""
    pass


@network.command(name="stats")
@click.option("--output-dir", "-o", help="Custom directory to look for notes.")
@click.option("--limit", "-l", default=10, help="Maximum number of notes to show.")
def network_stats(output_dir, limit):
    """
    Show statistics about the note network.
    """
    note_manager = NoteManager()

    try:
        # Get all notes
        all_notes = note_manager.list_notes(output_dir=output_dir)

        if not all_notes:
            console.print("[yellow]No notes found.[/yellow]")
            return 0

        # Get link statistics
        link_stats = note_manager.get_linked_notes_stats(output_dir=output_dir)

        # Calculate network stats
        total_notes = len(all_notes)
        notes_with_links = sum(
            1 for stats in link_stats.values() if stats[0] > 0 or stats[1] > 0)
        notes_with_outgoing = sum(
            1 for stats in link_stats.values() if stats[0] > 0)
        notes_with_incoming = sum(
            1 for stats in link_stats.values() if stats[1] > 0)
        standalone_notes = total_notes - notes_with_links

        total_links = sum(stats[0] for stats in link_stats.values())
        avg_links_per_note = total_links / total_notes if total_notes > 0 else 0

        # Display overall stats
        stats_panel = Panel(
            f"Total Notes: [bold]{total_notes}[/bold]\n"
            f"Notes with Links: [bold]{notes_with_links}[/bold] ({notes_with_links/total_notes*100:.1f}%)\n"
            f"Notes with Outgoing Links: [bold]{notes_with_outgoing}[/bold]\n"
            f"Notes with Incoming Links: [bold]{notes_with_incoming}[/bold]\n"
            f"Standalone Notes: [bold]{standalone_notes}[/bold]\n"
            f"Total Links: [bold]{total_links}[/bold]\n"
            f"Average Links per Note: [bold]{avg_links_per_note:.2f}[/bold]",
            title="Network Statistics"
        )
        console.print(stats_panel)

        # Show the most connected notes
        most_linked = note_manager.find_most_linked_notes(
            output_dir=output_dir, limit=limit)

        if most_linked:
            table = Table(title=f"Most Connected Notes (Top {limit})")
            table.add_column("Title", style="cyan")
            table.add_column("Outgoing Links", justify="right", style="green")
            table.add_column("Incoming Links", justify="right", style="blue")
            table.add_column("Total Links", justify="right", style="yellow")

            for title, outgoing, incoming in most_linked:
                table.add_row(
                    title,
                    str(outgoing),
                    str(incoming),
                    str(outgoing + incoming)
                )

            console.print(table)

        # Show orphaned links if any exist
        orphaned_links = note_manager.find_orphaned_links(
            output_dir=output_dir)
        if orphaned_links:
            console.print(
                f"\n[yellow]Warning:[/yellow] Found {len(orphaned_links)} notes with orphaned links (links to non-existent notes).")
            console.print(
                "Use [bold]marknote link orphaned[/bold] to view details.")

        return 0

    except Exception as e:
        console.print(
            f"[bold red]Error analyzing network:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


@network.command(name="standalone")
@click.option("--output-dir", "-o", help="Custom directory to look for notes.")
def find_standalone_notes(output_dir):
    """
    Find notes that are not connected to any other notes.
    """
    note_manager = NoteManager()

    try:
        # Find standalone notes
        standalone_notes = note_manager.find_standalone_notes(
            output_dir=output_dir)

        if not standalone_notes:
            console.print(
                "[green]All notes are connected to at least one other note.[/green]")
            return 0

        # Display the standalone notes
        table = Table(title=f"Standalone Notes ({len(standalone_notes)})")
        table.add_column("Title", style="cyan")
        table.add_column("Category", style="yellow")
        table.add_column("Updated", style="green")
        table.add_column("Tags", style="magenta")

        for note in standalone_notes:
            table.add_row(
                note.title,
                note.category or "None",
                note.updated_at.strftime("%Y-%m-%d"),
                ", ".join(note.tags) if note.tags else "None"
            )

        console.print(table)
        console.print(
            "\n[blue]Tip:[/blue] Connect these notes to your knowledge network using [bold]marknote link add[/bold]")

        return 0

    except Exception as e:
        console.print(
            f"[bold red]Error finding standalone notes:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


@network.command(name="path")
@click.argument("source")
@click.argument("target")
@click.option("--category", "-c", help="Category of the source note.")
@click.option("--target-category", "-tc", help="Category of the target note.")
@click.option("--output-dir", "-o", help="Custom directory to look for notes.")
@click.option("--max-depth", "-d", default=5, help="Maximum path length to search.")
def find_path_between_notes(source, target, category, target_category, output_dir, max_depth):
    """
    Find the shortest path between SOURCE and TARGET notes.

    This command attempts to find a connection between two notes by following links.
    """
    note_manager = NoteManager()

    try:
        # Verify that source and target notes exist
        source_note = note_manager.get_note(source, category, output_dir)
        if not source_note:
            console.print(
                f"[bold red]Error:[/bold red] Source note '{source}' not found.")
            return 1

        target_note = note_manager.get_note(
            target, target_category, output_dir)
        if not target_note:
            console.print(
                f"[bold red]Error:[/bold red] Target note '{target}' not found.")
            return 1

        # Generate the link graph
        outgoing_links, _ = note_manager.generate_link_graph(
            output_dir=output_dir)

        # Find the shortest path using breadth-first search
        paths = find_paths(outgoing_links, source, target, max_depth)

        if not paths:
            console.print(
                f"[yellow]No path found between[/yellow] '{source}' [yellow]and[/yellow] '{target}'.")
            console.print(
                f"[dim]Try increasing the maximum depth (current: {max_depth}) or add more links.[/dim]")
            return 0

        # Sort paths by length (shortest first)
        paths.sort(key=len)

        # Display the paths
        console.print(
            f"[bold green]Found {len(paths)} path(s) between[/bold green] '{source}' [bold green]and[/bold green] '{target}':")

        for i, path in enumerate(paths, 1):
            path_str = " → ".join([f"[cyan]{note}[/cyan]" for note in path])
            console.print(f"{i}. {path_str} [dim]({len(path)-1} steps)[/dim]")

        return 0

    except Exception as e:
        console.print(f"[bold red]Error finding path:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


def find_paths(link_graph, source, target, max_depth):
    """
    Find all paths from source to target using breadth-first search.

    Args:
        link_graph: Dictionary mapping note titles to sets of linked note titles.
        source: Title of the source note.
        target: Title of the target note.
        max_depth: Maximum path length to consider.

    Returns:
        A list of paths, where each path is a list of note titles.
    """
    if source == target:
        return [[source]]

    # Queue of (current_node, path_so_far)
    queue = [(source, [source])]
    paths = []

    # Keep track of visited nodes to avoid cycles
    visited = set()

    while queue:
        current, path = queue.pop(0)

        # Skip if we've visited this node already
        if current in visited:
            continue

        # Skip if path is too long
        if len(path) > max_depth:
            continue

        # Mark as visited
        visited.add(current)

        # Get linked notes
        linked_notes = link_graph.get(current, set())

        for linked in linked_notes:
            # Create new path with this node
            new_path = path + [linked]

            # If we found the target, add to results
            if linked == target:
                paths.append(new_path)
            # Otherwise add to queue for further exploration
            elif linked not in path:  # Avoid cycles
                queue.append((linked, new_path))

    return paths


def register_network_commands(cli):
    """
    Register the network command group with the main CLI.
    """
    cli.add_command(network)


@cli.command()
@click.option("--tag", help="Filter notes by tag.")
@click.option("--category", "-c", help="Filter notes by category.")
@click.option("--output-dir", "-o", help="Custom directory to look for notes. Overrides the default location.")
@click.option("--sort", "-s", type=click.Choice(['date', 'created', 'title']), default='date',
              help="Sort notes by date modified (default), creation date, or title.")
def list(tag, category, output_dir, sort):
    """List all notes, optionally filtered by tag or category."""
    try:
        note_manager = NoteManager()

        # Convert CLI sort parameter to NoteManager sort_by parameter
        sort_by = "updated"  # Default for 'date'
        if sort == 'created':
            sort_by = "created"
        elif sort == 'title':
            sort_by = "title"

        # Get notes with sorting parameter
        notes = note_manager.list_notes(
            tag=tag,
            category=category,
            output_dir=output_dir,
            sort_by=sort_by
        )

        # Determine base directory for relative path display
        base_dir = output_dir if output_dir else note_manager.notes_dir

        if not notes:
            if tag or category or output_dir:
                filters = []
                if tag:
                    filters.append(f"tag '{tag}'")
                if category:
                    filters.append(f"category '{category}'")
                if output_dir:
                    filters.append(f"directory '{output_dir}'")
                filter_str = " and ".join(filters)
                console.print(
                    f"[yellow]No notes found matching {filter_str}.[/yellow]")
            else:
                console.print(
                    "[yellow]No notes found. Create one with 'marknote new'.[/yellow]")
            return 0

        console.print(f"[bold blue]Found {len(notes)} notes:[/bold blue]")

        for note in notes:
            path = note.metadata.get('path', '')
            relative_path = os.path.relpath(path, base_dir) if path else ''

            # Format the note information
            console.print(f"[bold cyan]{note.title}[/bold cyan]")
            console.print(f"  [dim]File:[/dim] {relative_path}")
            if note.category:
                console.print(f"  [dim]Category:[/dim] {note.category}")
            if note.tags:
                console.print(f"  [dim]Tags:[/dim] {', '.join(note.tags)}")

            # Show appropriate date based on sort parameter
            if sort == 'created':
                date_str = note.created_at.strftime("%Y-%m-%d %H:%M")
                console.print(f"  [dim]Created:[/dim] {date_str}")
            else:
                date_str = note.updated_at.strftime("%Y-%m-%d %H:%M")
                console.print(f"  [dim]Updated:[/dim] {date_str}")

            # Show a separator line between notes
            console.print()

    except Exception as e:
        console.print(f"[bold red]Error listing notes:[/bold red] {str(e)}")
        return 1

    return 0

# Register the link command group with the main CLI


def register_link_commands(cli):
    """
    Register the link command group with the main CLI.
    """
    cli.add_command(link)


@cli.command()
@click.option("--date", "-d", help="Specific date for the daily note (YYYY-MM-DD). Defaults to today.")
@click.option("--force", "-f", is_flag=True, help="Force creation even if a daily note already exists.")
@click.option("--category", "-c", help="Category for the daily note. Defaults to config setting.")
@click.option("--tags", "-t", help="Additional tags for the note (comma-separated).")
@click.option("--output-dir", "-o", help="Custom directory to save the note to. Overrides the default location.")
@click.option("--editor", "-e", help="Specify which editor to use for editing the note (if opening for edit).")
@click.option("--edit/--no-edit", help="Open the daily note for editing after creation.")
@click.option("--template", help="Template to use for the daily note. Defaults to config setting.")
def daily(date, force, category, tags, output_dir, editor, edit, template):
    """
    Create or open a daily note.

    If no date is provided, today's date is used. If a daily note for the specified date already
    exists, it will be opened for editing unless --force is used to create a new one.
    """
    try:
        # Get configuration
        config = get_daily_note_config()

        # Validate the specified editor if provided
        if editor and not is_valid_editor(editor):
            console.print(
                f"[bold red]Error:[/bold red] Specified editor '{editor}' not found or not executable")
            return 1

        # Parse tags from comma-separated string
        tag_list = None
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',')]
            # Ensure "daily" is always included
            if "daily" not in tag_list:
                tag_list.append("daily")

        # Get the daily note service
        service = get_daily_note_service()

        if date:
            # Create a note for the specific date
            success, message, note = service.create_note_for_date(
                date_str=date,
                tags=tag_list,
                category=category,
                template_name=template,
                output_dir=output_dir,
                force=force,
                editor=editor,
                auto_open=edit
            )
        else:
            # Today's date - Use dt.today() instead of date.today() to avoid name collision
            today_str = dt.today().strftime("%Y-%m-%d")

            if force:
                # Force create a new note for today
                success, message, note = service.create_note_for_date(
                    date_str=today_str,
                    tags=tag_list,
                    category=category,
                    template_name=template,
                    output_dir=output_dir,
                    force=True,
                    editor=editor,
                    auto_open=edit
                )
            else:
                # Get or create today's note
                exists, message, note = service.get_or_create_todays_note(
                    category=category,
                    output_dir=output_dir,
                    editor=editor,
                    auto_open=edit
                )
                success = True

        if success:
            console.print(f"[bold green]Success:[/bold green] {message}")
            if note:
                note_path = note.metadata.get('path', '')
                if note_path:
                    console.print(f"Note path: [cyan]{note_path}[/cyan]")
        else:
            console.print(f"[bold red]Error:[/bold red] {message}")
            return 1

        return 0

    except Exception as e:
        console.print(
            f"[bold red]Error creating daily note:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


@cli.command()
@click.option("--category", "-c", help="Category to look in. Defaults to config setting.")
@click.option("--output-dir", "-o", help="Custom directory to look for notes.")
def today(category, output_dir):
    """
    Show today's daily note status and open it if it exists.

    If today's daily note doesn't exist, it will show a message and offer to create one.
    """
    try:
        # Get configuration
        config = get_daily_note_config()

        # Get the daily note service
        service = get_daily_note_service()

        # Get or create today's note without auto-opening it
        exists, message, note = service.get_or_create_todays_note(
            category=category,
            output_dir=output_dir,
            auto_open=False
        )

        if exists:
            note_path = note.metadata.get('path', '')
            date_str = note.metadata.get(
                'date', dt.today().strftime("%Y-%m-%d"))
            day_str = note.metadata.get(
                'day_of_week', dt.today().strftime("%A"))

            console.print(Panel(
                f"[bold]Today's Daily Note[/bold]\n\n"
                f"[cyan]{note.title}[/cyan]\n"
                f"Date: {date_str} ({day_str})\n"
                f"Path: {note_path}\n",
                title="Status", border_style="green"
            ))

            # Ask if user wants to open the note
            if click.confirm("Would you like to open today's note?", default=True):
                # Pick a default editor
                editor = None
                success, error = edit_file(note_path, custom_editor=editor)
                if not success:
                    console.print(
                        f"[bold red]Error opening editor:[/bold red] {error}")
                    return 1
        else:
            # Note doesn't exist yet
            today_date = dt.today()
            formatted_date = today_date.strftime("%Y-%m-%d")
            day_name = today_date.strftime("%A")

            console.print(Panel(
                f"No daily note exists for today ({formatted_date}, {day_name}).\n"
                f"Use the [bold]daily[/bold] command to create one.",
                title="Status", border_style="yellow"
            ))

            # Ask if user wants to create one now
            if click.confirm("Would you like to create today's note now?", default=True):
                success, message, note = service.create_note_for_date(
                    date_str=None,  # Today by default
                    category=category,
                    output_dir=output_dir,
                    auto_open=True  # Automatically open the note
                )

                if not success:
                    console.print(f"[bold red]Error:[/bold red] {message}")
                    return 1

                console.print(f"[bold green]Success:[/bold green] {message}")

        return 0

    except Exception as e:
        console.print(
            f"[bold red]Error checking daily note:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


@cli.group(name="config")
def config_group():
    """Commands for managing MarkNote configuration."""
    pass


@config_group.command(name="daily")
@click.option("--template", help="Set the default template for daily notes.")
@click.option("--category", help="Set the default category for daily notes.")
@click.option("--auto-open/--no-auto-open", help="Whether to automatically open daily notes after creation.")
def config_daily(template, category, auto_open):
    """
    Configure daily note settings.
    """
    try:
        config_manager = get_config_manager()
        daily_config = config_manager.get_daily_note_config()

        # Show current config if no options provided
        if not any([template, category, auto_open is not None]):
            console.print(Panel(
                f"[bold]Current Daily Note Configuration:[/bold]\n\n"
                f"Template: {daily_config.get('template', 'daily')}\n"
                f"Category: {daily_config.get('category', 'daily')}\n"
                f"Auto-open: {daily_config.get('auto_open', True)}\n"
                f"Default Tags: {', '.join(daily_config.get('default_tags', ['daily']))}\n"
                f"Title Format: {daily_config.get('title_format', 'Daily Note: {date} ({day})')}\n",
                title="Daily Note Configuration", border_style="blue"
            ))
            return 0

        # Update configuration based on provided options
        if template:
            config_manager.set_config("daily_notes", "template", template)
            console.print(
                f"[green]Default daily note template set to:[/green] {template}")

        if category:
            config_manager.set_config("daily_notes", "category", category)
            console.print(
                f"[green]Default daily note category set to:[/green] {category}")

        if auto_open is not None:
            config_manager.set_config("daily_notes", "auto_open", auto_open)
            status = "enabled" if auto_open else "disabled"
            console.print(f"[green]Auto-open for daily notes {status}[/green]")

        # Save the configuration
        if config_manager.save_config():
            console.print(
                "[bold green]Configuration saved successfully![/bold green]")
        else:
            console.print("[bold red]Error saving configuration![/bold red]")
            return 1

        return 0

    except Exception as e:
        console.print(
            f"[bold red]Error configuring daily notes:[/bold red] {str(e)}")
        return 1


try:
    from app.core.note_manager import NoteManager
    note_manager_available = True
except ImportError:
    note_manager_available = False


@click.group(name="versions")
def versions():
    """Commands for managing note versions."""
    pass


def create_note_manager():
    """
    Create a NoteManager instance with proper error handling.

    Returns:
        A NoteManager instance or None if not available.
    """
    if not note_manager_available:
        console.print(
            "[bold red]Error:[/bold red] The NoteManager module is not available.")
        return None

    try:
        note_manager = NoteManager()
        # Check if version control is enabled
        if hasattr(note_manager, 'version_control_enabled'):
            if not note_manager.version_control_enabled:
                console.print(
                    "[bold yellow]Warning:[/bold yellow] Version control is not enabled in this installation.")
            return note_manager
        else:
            # Add the attribute if missing
            note_manager.version_control_enabled = True
            note_manager.version_store = getattr(
                note_manager, 'version_store', None)
            if note_manager.version_store is None:
                console.print(
                    "[bold red]Error:[/bold red] Version store is not available.")
                return None
            return note_manager
    except Exception as e:
        console.print(
            f"[bold red]Error:[/bold red] Failed to initialize NoteManager: {str(e)}")
        return None


@versions.command(name="list")
@click.argument("title")
@click.option("--category", "-c", help="Category of the note.")
@click.option("--output-dir", "-o", help="Custom directory to look for notes.")
def list_versions(title: str, category: Optional[str], output_dir: Optional[str]):
    """
    List all versions of a note.

    TITLE is the title of the note to show versions for.
    """
    try:
        # Create NoteManager with error handling
        note_manager = create_note_manager()
        if not note_manager:
            return 1

        # Check if needed method exists
        if not hasattr(note_manager, 'get_note_version_history'):
            console.print(
                "[bold red]Error:[/bold red] Version control functionality is not available.")
            return 1

        success, message, history = note_manager.get_note_version_history(
            title=title,
            category=category,
            output_dir=output_dir
        )

        if not success:
            console.print(f"[bold red]Error:[/bold red] {message}")
            return 1

        if not history:
            console.print(
                f"[yellow]No version history found for note '{title}'.[/yellow]")
            return 0

        # Create a table to display the version history
        table = Table(title=f"Version History for '{title}'")
        table.add_column("Version ID", style="cyan")
        table.add_column("Date", style="green")
        table.add_column("Message")

        # Add rows to the table
        for version in history:
            version_id = version.get("version_id", "")
            timestamp = version.get("timestamp", "")
            message = version.get("message", "")

            # Format the timestamp
            try:
                dt = datetime.fromisoformat(timestamp)
                formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                formatted_date = timestamp

            table.add_row(version_id, formatted_date, message)

        console.print(table)
        return 0

    except Exception as e:
        console.print(f"[bold red]Error listing versions:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


@versions.command(name="show")
@click.argument("title")
@click.argument("version_id")
@click.option("--category", "-c", help="Category of the note.")
@click.option("--output-dir", "-o", help="Custom directory to look for notes.")
@click.option("--raw", is_flag=True, help="Show raw content without rendering.")
def show_version(title: str, version_id: str, category: Optional[str], output_dir: Optional[str], raw: bool):
    """
    Show a specific version of a note.

    TITLE is the title of the note.
    VERSION_ID is the ID of the version to show.
    """
    try:
        # Create NoteManager with error handling
        note_manager = create_note_manager()
        if not note_manager:
            return 1

        # Check if needed method exists
        if not hasattr(note_manager, 'get_note_version'):
            console.print(
                "[bold red]Error:[/bold red] Version control functionality is not available.")
            return 1

        success, message, content, version_info = note_manager.get_note_version(
            title=title,
            version_id=version_id,
            category=category,
            output_dir=output_dir
        )

        if not success:
            console.print(
                f"[bold red]Error showing version:[/bold red] {message}")
            return 1

        # Show version info if available
        if version_info:
            try:
                dt = datetime.fromisoformat(version_info.get("timestamp", ""))
                formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                formatted_date = version_info.get("timestamp", "Unknown")

            console.print(Panel(
                f"[bold]Version ID:[/bold] {version_info.get('version_id')}\n"
                f"[bold]Date:[/bold] {formatted_date}\n"
                f"[bold]Message:[/bold] {version_info.get('message', 'No message')}",
                title=f"Version of '{title}'",
                border_style="cyan"
            ))

        # Show the content
        if raw:
            console.print(content)
        else:
            # Render markdown
            try:
                md = Markdown()
                html = md.convert(content)

                # Parse YAML frontmatter if present
                metadata = {}
                try:
                    metadata, _ = parse_frontmatter(content)
                except Exception:
                    pass

                # Display metadata separately
                if metadata:
                    metadata_panel = Panel(
                        "\n".join(f"[bold]{k}:[/bold] {v}" for k,
                                  v in metadata.items()),
                        title="Metadata",
                        border_style="green"
                    )
                    console.print(metadata_panel)

                # Display the content with syntax highlighting
                console.print(
                    Syntax(content, "markdown", theme="monokai", line_numbers=True, word_wrap=True))

            except Exception as e:
                console.print(
                    f"[yellow]Error rendering markdown, showing raw content: {str(e)}[/yellow]")
                console.print(content)

        return 0

    except Exception as e:
        console.print(f"[bold red]Error showing version:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


@versions.command(name="diff")
@click.argument("title")
@click.argument("from_version")
@click.argument("to_version")
@click.option("--category", "-c", help="Category of the note.")
@click.option("--output-dir", "-o", help="Custom directory to look for notes.")
def diff_versions(title: str, from_version: str, to_version: str, category: Optional[str], output_dir: Optional[str]):
    """
    Show the differences between two versions of a note.

    TITLE is the title of the note.
    FROM_VERSION is the ID of the base version.
    TO_VERSION is the ID of the target version to compare against.
    """
    try:
        # Create NoteManager with error handling
        note_manager = create_note_manager()
        if not note_manager:
            return 1

        # Check if needed method exists
        if not hasattr(note_manager, 'diff_note_versions'):
            console.print(
                "[bold red]Error:[/bold red] Version control functionality is not available.")
            return 1

        success, diff, message = note_manager.diff_note_versions(
            title=title,
            from_version_id=from_version,
            to_version_id=to_version,
            category=category,
            output_dir=output_dir
        )

        if not success:
            console.print(f"[bold red]Error:[/bold red] {message}")
            return 1

        if not diff:
            console.print(
                "[yellow]No differences found between versions.[/yellow]")
            return 0

        # Join the diff lines and print
        diff_text = "".join(diff)

        # Create a more visual diff display
        console.print(Panel(
            f"[bold]Comparing versions:[/bold]\n"
            f"[bold]From:[/bold] {from_version}\n"
            f"[bold]To:[/bold] {to_version}",
            title=f"Diff for '{title}'",
            border_style="yellow"
        ))

        # Display the diff with syntax highlighting
        try:
            syntax = Syntax(diff_text, "diff", theme="monokai", word_wrap=True)
            console.print(syntax)
        except Exception:
            # Fallback to plain text if there's an issue with Syntax
            console.print(diff_text)

        return 0

    except Exception as e:
        console.print(f"[bold red]Error showing diff:[/bold red] {str(e)}")
        return 1


@versions.command(name="restore")
@click.argument("title")
@click.argument("version_id")
@click.option("--category", "-c", help="Category of the note.")
@click.option("--output-dir", "-o", help="Custom directory to look for notes.")
@click.option("--message", "-m", help="Commit message for the restore operation.")
@click.option("--force", "-f", is_flag=True, help="Force restore without confirmation.")
def restore_version(title: str, version_id: str, category: Optional[str], output_dir: Optional[str],
                    message: Optional[str], force: bool):
    """
    Restore a note to a previous version.

    TITLE is the title of the note.
    VERSION_ID is the ID of the version to restore.
    """
    try:
        # Create NoteManager with error handling
        note_manager = create_note_manager()
        if not note_manager:
            return 1

        # Check if needed method exists
        if not hasattr(note_manager, 'restore_note_version'):
            console.print(
                "[bold red]Error:[/bold red] Version control functionality is not available.")
            return 1

        # Confirm the restore operation if not forced
        if not force:
            if not click.confirm(f"Are you sure you want to restore note '{title}' to version {version_id}?"):
                console.print("[yellow]Restore operation cancelled.[/yellow]")
                return 0

        # Provide a default message if not specified
        if not message:
            message = f"Restored to version {version_id}"

        success, restore_message, note = note_manager.restore_note_version(
            title=title,
            version_id=version_id,
            category=category,
            output_dir=output_dir,
            commit_message=message
        )

        if not success:
            console.print(f"[bold red]Error:[/bold red] {restore_message}")
            return 1

        console.print(f"[bold green]Success:[/bold green] {restore_message}")
        console.print(
            f"Note '{title}' has been restored to version {version_id}.")

        # Show the path of the restored note
        if note and hasattr(note, 'metadata'):
            note_path = note.metadata.get('path', '')
            if note_path:
                console.print(f"Note path: [cyan]{note_path}[/cyan]")

        return 0

    except Exception as e:
        console.print(
            f"[bold red]Error restoring version:[/bold red] {str(e)}")
        return 1


@versions.command(name="purge")
@click.argument("title")
@click.option("--category", "-c", help="Category of the note.")
@click.option("--output-dir", "-o", help="Custom directory to look for notes.")
@click.option("--force", "-f", is_flag=True, help="Force purge without confirmation.")
def purge_history(title: str, category: Optional[str], output_dir: Optional[str], force: bool):
    """
    Delete all version history for a note.

    TITLE is the title of the note.
    """
    try:
        # Create NoteManager with error handling
        note_manager = create_note_manager()
        if not note_manager:
            return 1

        # Check if needed method exists
        if not hasattr(note_manager, 'purge_note_history'):
            console.print(
                "[bold red]Error:[/bold red] Version control functionality is not available.")
            return 1

        # Confirm the purge operation if not forced
        if not force:
            if not click.confirm(f"Are you sure you want to delete ALL version history for note '{title}'?"):
                console.print("[yellow]Purge operation cancelled.[/yellow]")
                return 0

        success, message = note_manager.purge_note_history(
            title=title,
            category=category,
            output_dir=output_dir
        )

        if not success:
            console.print(f"[bold red]Error:[/bold red] {message}")
            return 1

        console.print(f"[bold green]Success:[/bold green] {message}")
        return 0

    except Exception as e:
        console.print(f"[bold red]Error purging history:[/bold red] {str(e)}")
        return 1


@versions.command(name="status")
def version_status():
    """
    Show version control system status.
    """
    try:
        # Check if NoteManager is available
        if not note_manager_available:
            console.print(
                "[bold red]Status:[/bold red] NoteManager is not available.")
            return 1

        try:
            note_manager = NoteManager()

            # Check version control attributes
            vc_enabled = getattr(
                note_manager, 'version_control_enabled', False)
            vs_available = getattr(
                note_manager, 'version_store', None) is not None

            status_table = Table(title="Version Control Status")
            status_table.add_column("Component", style="cyan")
            status_table.add_column("Status", style="green")

            status_table.add_row(
                "NoteManager",
                "[green]Available[/green]"
            )

            status_table.add_row(
                "Version Control",
                f"[{'green' if vc_enabled else 'red'}]{'Enabled' if vc_enabled else 'Disabled'}[/{'green' if vc_enabled else 'red'}]"
            )

            status_table.add_row(
                "Version Store",
                f"[{'green' if vs_available else 'red'}]{'Available' if vs_available else 'Not Available'}[/{'green' if vs_available else 'red'}]"
            )

            # Check if all needed methods exist
            methods = [
                'get_note_version_history',
                'get_note_version',
                'diff_note_versions',
                'restore_note_version',
                'purge_note_history'
            ]

            for method in methods:
                method_available = hasattr(note_manager, method) and callable(
                    getattr(note_manager, method))
                status_table.add_row(
                    f"Method: {method}",
                    f"[{'green' if method_available else 'red'}]{'Available' if method_available else 'Missing'}[/{'green' if method_available else 'red'}]"
                )

            console.print(status_table)

            # Check version store directory
            if vs_available and hasattr(note_manager.version_store, 'base_dir'):
                vs_dir = note_manager.version_store.base_dir
                vs_dir_exists = os.path.exists(vs_dir)

                console.print(Panel(
                    f"Version Store Directory: {vs_dir}\n"
                    f"Directory exists: [{'green' if vs_dir_exists else 'red'}]{vs_dir_exists}[/{'green' if vs_dir_exists else 'red'}]",
                    title="Storage Information",
                    border_style="blue"
                ))

            return 0 if vc_enabled and vs_available else 1

        except Exception as e:
            console.print(
                f"[bold red]Error checking version control status:[/bold red] {str(e)}")
            return 1

    except Exception as e:
        console.print(f"[bold red]Error getting status:[/bold red] {str(e)}")
        return 1


@versions.command(name="create")
@click.argument("title")
@click.option("--category", "-c", help="Category of the note.")
@click.option("--output-dir", "-o", help="Custom directory to look for notes.")
@click.option("--message", "-m", help="Message describing this version.")
@click.option("--author", "-a", help="Author of this version.")
def create_version(title: str, category: Optional[str], output_dir: Optional[str],
                   message: Optional[str], author: Optional[str]):
    """
    Manually create a new version of an existing note.

    TITLE is the title of the note.
    """
    try:
        # Create note manager
        note_manager = create_note_manager()
        if not note_manager:
            return 1

        # Check if needed method exists
        if not hasattr(note_manager, 'create_version'):
            console.print(
                "[bold red]Error:[/bold red] Version creation functionality is not available.")
            console.print(
                "Make sure you have the latest version of MarkNote with version control support.")
            return 1

        # Use version_control_enabled check from note_manager if available
        if hasattr(note_manager, 'version_control_enabled') and not note_manager.version_control_enabled:
            console.print(
                "[bold red]Error:[/bold red] Version control is not enabled.")
            return 1

        console.print(f"Creating version for note: [cyan]{title}[/cyan]")

        # Create the version
        success, msg, version_id = note_manager.create_version(
            title=title,
            category=category,
            output_dir=output_dir,
            message=message,
            author=author
        )

        if not success:
            console.print(f"[bold red]Error:[/bold red] {msg}")
            return 1

        console.print(f"[bold green]Success:[/bold green] {msg}")

        # Get version details with variable name changed from "versions" to "history"
        history_success, _, history = note_manager.get_note_version_history(
            title=title,
            category=category,
            output_dir=output_dir
        )
        if history_success and history:
            # Find the newly created version, filtering on "history" now
            new_version = next(
                (v for v in history if v["version_id"] == version_id), None)
            if new_version:
                # Show version details in a panel
                panel = Panel(
                    f"[bold]Version ID:[/bold] {new_version['version_id']}\n"
                    f"[bold]Created:[/bold] {new_version['timestamp']}\n"
                    f"[bold]Author:[/bold] {new_version['author']}\n"
                    f"[bold]Message:[/bold] {new_version['message']}",
                    title="Version Details",
                    border_style="green"
                )
                console.print(panel)

        return 0

    except Exception as e:
        console.print(f"[bold red]Error creating version:[/bold red] {str(e)}")
        return 1


@versions.command(name="edit")
@click.argument("title")
@click.argument("version_id")
@click.option("--category", "-c", help="Category of the note.")
@click.option("--output-dir", "-o", help="Custom directory to look for notes.")
@click.option("--editor", "-e", help="Editor to use for editing.")
@click.option("--message", "-m", help="Commit message for the new version.")
@click.option("--author", "-a", help="Author of the edit.")
def edit_version(title: str, version_id: str, category: Optional[str], output_dir: Optional[str],
                 editor: Optional[str], message: Optional[str], author: Optional[str]):
    """
    Edit a specific version of a note.

    TITLE is the title of the note.
    VERSION_ID is the ID of the version to edit.

    This will create a new version based on the edits.
    """
    try:
        # Create NoteManager with error handling
        note_manager = create_note_manager()
        if not note_manager:
            return 1

        # Check if needed method exists
        if not hasattr(note_manager, 'edit_version'):
            console.print(
                "[bold red]Error:[/bold red] Version editing functionality is not available.")
            console.print(
                "Make sure you have the latest version of MarkNote with version editing support.")
            return 1

        # Use version_control_enabled check from note_manager if available
        if hasattr(note_manager, 'version_control_enabled') and not note_manager.version_control_enabled:
            console.print(
                "[bold red]Error:[/bold red] Version control is not enabled.")
            return 1

        console.print(
            f"Editing version [cyan]{version_id}[/cyan] of note: [cyan]{title}[/cyan]")

        # Edit the version
        success, msg, new_version_id = note_manager.edit_version(
            title=title,
            version_id=version_id,
            category=category,
            output_dir=output_dir,
            editor=editor,
            commit_message=message,
            author=author
        )

        if not success:
            console.print(f"[bold red]Error:[/bold red] {msg}")
            return 1

        if not new_version_id:
            console.print(f"[yellow]{msg}[/yellow]")
            return 0

        console.print(f"[bold green]Success:[/bold green] {msg}")

        # Get version details
        history_success, _, history = note_manager.get_note_version_history(
            title=title,
            category=category,
            output_dir=output_dir
        )

        if history_success and history:
            # Find the newly created version
            new_version = next(
                (v for v in history if v["version_id"] == new_version_id), None)
            if new_version:
                # Show version details in a panel
                panel = Panel(
                    f"[bold]Version ID:[/bold] {new_version['version_id']}\n"
                    f"[bold]Created:[/bold] {new_version['timestamp']}\n"
                    f"[bold]Author:[/bold] {new_version['author']}\n"
                    f"[bold]Message:[/bold] {new_version['message']}",
                    title="New Version Details",
                    border_style="green"
                )
                console.print(panel)

        return 0

    except Exception as e:
        console.print(f"[bold red]Error editing version:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


@click.group(name="encrypt")
def encrypt_commands():
    """Encrypt and manage encrypted notes."""
    pass


@encrypt_commands.command(name="note")
@click.argument("title")
@click.option("--category", "-c", help="Category of the note.")
@click.option("--output-dir", "-o", help="Custom directory to look for notes.")
@click.option("--password", "-p", help="Password for encryption (will prompt if not provided).")
@click.option("--force", "-f", is_flag=True, help="Force encryption even if already encrypted.")
def encrypt_note(title: str, category: Optional[str], output_dir: Optional[str],
                 password: Optional[str], force: bool):
    """
    Encrypt a note with a password.

    TITLE is the title of the note to encrypt.
    """
    try:
        # Create encryption-enabled note manager
        note_manager = EncryptionNoteManager()

        # Check if the note is already encrypted
        if not force and note_manager.is_note_encrypted(title, category, output_dir):
            if not Confirm.ask(f"Note '{title}' is already encrypted. Re-encrypt?"):
                console.print("[yellow]Operation cancelled.[/yellow]")
                return 0

        # If password not provided, prompt for it
        if not password:
            try:
                password = prompt_for_password(
                    "Enter encryption password: ", confirm=True)
            except ValueError as e:
                console.print(f"[bold red]Error:[/bold red] {str(e)}")
                return 1

        # Encrypt the note
        success, message = note_manager.encrypt_note(
            title, password, category, output_dir)

        if success:
            console.print(f"[bold green]Success:[/bold green] {message}")
            console.print(
                "[bold yellow]Important:[/bold yellow] Keep your password safe! There is NO WAY to recover the note if you forget it.")
            return 0
        else:
            console.print(f"[bold red]Error:[/bold red] {message}")
            return 1

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return 1


@encrypt_commands.command(name="batch")
@click.argument("titles", nargs=-1, required=True)
@click.option("--category", "-c", help="Category of the notes.")
@click.option("--output-dir", "-o", help="Custom directory to look for notes.")
@click.option("--password", "-p", help="Password for encryption (will prompt if not provided).")
@click.option("--force", "-f", is_flag=True, help="Force encryption even if already encrypted.")
def batch_encrypt(titles: List[str], category: Optional[str], output_dir: Optional[str],
                  password: Optional[str], force: bool):
    """
    Encrypt multiple notes with the same password.

    TITLES is a space-separated list of note titles to encrypt.
    """
    try:
        if not titles:
            console.print("[bold yellow]No titles provided.[/bold yellow]")
            return 0

        # Create encryption-enabled note manager
        note_manager = EncryptionNoteManager()

        # If password not provided, prompt for it
        if not password:
            try:
                password = prompt_for_password(
                    "Enter encryption password: ", confirm=True)
            except ValueError as e:
                console.print(f"[bold red]Error:[/bold red] {str(e)}")
                return 1

        # Show progress spinner
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            task = progress.add_task("Encrypting notes...", total=len(titles))

            # Process each note
            results = {}
            for title in titles:
                progress.update(
                    task, description=f"Encrypting [cyan]{title}[/cyan]...")

                # Skip already encrypted notes unless force is specified
                if not force and note_manager.is_note_encrypted(title, category, output_dir):
                    results[title] = "Already encrypted (skipped)"
                    progress.advance(task)
                    continue

                # Encrypt the note
                success, message = note_manager.encrypt_note(
                    title, password, category, output_dir)
                results[title] = message if success else f"Failed: {message}"
                progress.advance(task)

        # Display results
        table = Table(title=f"Encryption Results ({len(titles)} notes)")
        table.add_column("Note", style="cyan")
        table.add_column("Status", style="bold")

        success_count = 0
        for title, result in results.items():
            status_style = "green" if "success" in result.lower(
            ) else "red" if "failed" in result.lower() else "yellow"
            table.add_row(title, f"[{status_style}]{result}[/{status_style}]")
            if "success" in result.lower():
                success_count += 1

        console.print(table)

        # Summary message
        console.print(Panel(
            f"Successfully encrypted {success_count} of {len(titles)} notes.",
            title="Encryption Summary",
            border_style="green" if success_count == len(titles) else "yellow"
        ))

        if success_count > 0:
            console.print(
                "[bold yellow]Important:[/bold yellow] Keep your password safe! There is NO WAY to recover the notes if you forget it.")

        return 0 if success_count == len(titles) else 1

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return 1


@click.group(name="decrypt")
def decrypt_commands():
    """Decrypt encrypted notes."""
    pass


@decrypt_commands.command(name="note")
@click.argument("title")
@click.option("--category", "-c", help="Category of the note.")
@click.option("--output-dir", "-o", help="Custom directory to look for notes.")
@click.option("--password", "-p", help="Password for decryption (will prompt if not provided).")
def decrypt_note(title: str, category: Optional[str], output_dir: Optional[str], password: Optional[str]):
    """
    Decrypt an encrypted note.

    TITLE is the title of the note to decrypt.
    """
    try:
        # Create encryption-enabled note manager
        note_manager = EncryptionNoteManager()

        # Check if the note is actually encrypted
        if not note_manager.is_note_encrypted(title, category, output_dir):
            console.print(
                f"[bold yellow]Note '{title}' is not encrypted.[/bold yellow]")
            return 0

        # If password not provided, prompt for it
        if not password:
            password = prompt_for_password("Enter decryption password: ")

        # Decrypt the note
        success, message = note_manager.decrypt_note(
            title, password, category, output_dir)

        if success:
            console.print(f"[bold green]Success:[/bold green] {message}")
            return 0
        else:
            console.print(f"[bold red]Error:[/bold red] {message}")
            return 1

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return 1


@decrypt_commands.command(name="batch")
@click.argument("titles", nargs=-1, required=True)
@click.option("--category", "-c", help="Category of the notes.")
@click.option("--output-dir", "-o", help="Custom directory to look for notes.")
@click.option("--password", "-p", help="Password for decryption (will prompt if not provided).")
def batch_decrypt(titles: List[str], category: Optional[str], output_dir: Optional[str], password: Optional[str]):
    """
    Decrypt multiple encrypted notes with the same password.

    TITLES is a space-separated list of note titles to decrypt.
    """
    try:
        if not titles:
            console.print("[bold yellow]No titles provided.[/bold yellow]")
            return 0

        # Create encryption-enabled note manager
        note_manager = EncryptionNoteManager()

        # If password not provided, prompt for it
        if not password:
            password = prompt_for_password("Enter decryption password: ")

        # Show progress spinner
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            task = progress.add_task("Decrypting notes...", total=len(titles))

            # Process each note
            results = {}
            for title in titles:
                progress.update(
                    task, description=f"Decrypting [cyan]{title}[/cyan]...")

                # Skip notes that aren't encrypted
                if not note_manager.is_note_encrypted(title, category, output_dir):
                    results[title] = "Not encrypted (skipped)"
                    progress.advance(task)
                    continue

                # Decrypt the note
                success, message = note_manager.decrypt_note(
                    title, password, category, output_dir)
                results[title] = message if success else f"Failed: {message}"
                progress.advance(task)

        # Display results
        table = Table(title=f"Decryption Results ({len(titles)} notes)")
        table.add_column("Note", style="cyan")
        table.add_column("Status", style="bold")

        success_count = 0
        for title, result in results.items():
            status_style = "green" if "success" in result.lower(
            ) else "red" if "failed" in result.lower() else "yellow"
            table.add_row(title, f"[{status_style}]{result}[/{status_style}]")
            if "success" in result.lower():
                success_count += 1

        console.print(table)

        # Summary message
        console.print(Panel(
            f"Successfully decrypted {success_count} of {len(titles)} notes.",
            title="Decryption Summary",
            border_style="green" if success_count == len(titles) else "yellow"
        ))

        return 0 if success_count == len(titles) else 1

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return 1


@encrypt_commands.command(name="change-password")
@click.argument("title")
@click.option("--category", "-c", help="Category of the note.")
@click.option("--output-dir", "-o", help="Custom directory to look for notes.")
@click.option("--current-password", help="Current password (will prompt if not provided).")
@click.option("--new-password", help="New password (will prompt if not provided).")
def change_password(title: str, category: Optional[str], output_dir: Optional[str],
                    current_password: Optional[str], new_password: Optional[str]):
    """
    Change the encryption password for a note.

    TITLE is the title of the encrypted note.
    """
    try:
        # Create encryption-enabled note manager
        note_manager = EncryptionNoteManager()

        # Check if the note is actually encrypted
        if not note_manager.is_note_encrypted(title, category, output_dir):
            console.print(
                f"[bold red]Error:[/bold red] Note '{title}' is not encrypted.")
            return 1

        # If current password not provided, prompt for it
        if not current_password:
            current_password = prompt_for_password("Enter current password: ")

        # If new password not provided, prompt for it
        if not new_password:
            try:
                new_password = prompt_for_password(
                    "Enter new password: ", confirm=True)
            except ValueError as e:
                console.print(f"[bold red]Error:[/bold red] {str(e)}")
                return 1

        # Change the password
        success, message = note_manager.change_encryption_password(
            title, current_password, new_password, category, output_dir
        )

        if success:
            console.print(f"[bold green]Success:[/bold green] {message}")
            console.print(
                "[bold yellow]Important:[/bold yellow] Keep your new password safe! There is NO WAY to recover the note if you forget it.")
            return 0
        else:
            console.print(f"[bold red]Error:[/bold red] {message}")
            return 1

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return 1


@encrypt_commands.command(name="status")
@click.argument("title", required=False)
@click.option("--category", "-c", help="Category of the note.")
@click.option("--output-dir", "-o", help="Custom directory to look for notes.")
@click.option("--all", "-a", is_flag=True, help="Check encryption status of all notes.")
def encryption_status(title: Optional[str], category: Optional[str], output_dir: Optional[str], all: bool):
    """
    Check the encryption status of notes.

    If TITLE is provided, checks that specific note.
    If --all is specified, checks all notes.
    """
    try:
        # Create encryption-enabled note manager
        note_manager = EncryptionNoteManager()

        if title and not all:
            # Check a single note
            is_encrypted = note_manager.is_note_encrypted(
                title, category, output_dir)
            note_path = note_manager.find_note_path(
                title, category, output_dir)

            if not note_path:
                console.print(
                    f"[bold red]Error:[/bold red] Note '{title}' not found.")
                return 1

            status_text = "[green]Encrypted[/green]" if is_encrypted else "[yellow]Not Encrypted[/yellow]"

            panel = Panel(
                f"Status: {status_text}\nPath: {note_path}",
                title=f"Encryption Status: {title}",
                border_style="cyan"
            )
            console.print(panel)
            return 0

        elif all:
            # Check all notes
            from app.utils.file_handler import list_note_files

            # Get all notes
            source_dir = output_dir or note_manager.notes_dir
            note_files = list_note_files(source_dir, category)

            if not note_files:
                console.print("[yellow]No notes found.[/yellow]")
                return 0

            # Create a table for results
            table = Table(title=f"Encryption Status ({len(note_files)} notes)")
            table.add_column("Note", style="cyan")
            table.add_column("Status", style="bold")
            table.add_column("Path", style="dim")

            encrypted_count = 0
            for note_file in note_files:
                # Extract note title from filename or metadata
                try:
                    metadata, _ = note_manager.encryption_manager.read_note_file(
                        note_file)
                    title = metadata.get('title', os.path.splitext(
                        os.path.basename(note_file))[0])
                except Exception:
                    title = os.path.splitext(os.path.basename(note_file))[0]

                # Check encryption status
                is_encrypted = note_manager.encryption_manager.is_note_encrypted(
                    note_file)
                if is_encrypted:
                    encrypted_count += 1

                status_text = "[green]Encrypted[/green]" if is_encrypted else "[yellow]Not Encrypted[/yellow]"

                table.add_row(title, status_text, note_file)

            console.print(table)

            # Summary
            console.print(f"Total notes: {len(note_files)}")
            console.print(
                f"Encrypted: {encrypted_count} ({encrypted_count / len(note_files) * 100:.1f}%)")
            console.print(
                f"Unencrypted: {len(note_files) - encrypted_count} ({(len(note_files) - encrypted_count) / len(note_files) * 100:.1f}%)")

            return 0
        else:
            # No title or --all specified
            console.print(
                "[yellow]Please provide a note title or use the --all option.[/yellow]")
            return 1

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return 1


@click.group(name="archive")
def archive_commands():
    """Archive and manage archived notes."""
    pass


@archive_commands.command(name="note")
@click.argument("title")
@click.option("--reason", "-r", help="Reason for archiving the note.")
@click.option("--category", "-c", help="Category of the note.")
@click.option("--output-dir", "-o", help="Custom directory to look for notes.")
@click.option("--move", "-m", is_flag=True, help="Move the note to a dedicated archive directory.")
def archive_note(title: str, reason: Optional[str], category: Optional[str],
                 output_dir: Optional[str], move: bool):
    """
    Archive a note.

    TITLE is the title of the note to archive.
    """
    try:
        # Create archive-enabled note manager
        note_manager = ArchiveNoteManager()

        # Check if the note is already archived
        if note_manager.is_note_archived(title, category, output_dir):
            console.print(
                f"[yellow]Note '{title}' is already archived.[/yellow]")
            return 0

        # Archive the note
        success, message = note_manager.archive_note(
            title=title,
            reason=reason,
            category=category,
            output_dir=output_dir,
            move_to_archive_dir=move
        )

        if success:
            console.print(f"[bold green]Success:[/bold green] {message}")
            console.print(
                "[blue]Note has been marked as 'Archived' and tagged with 'Archived'.[/blue]")
            return 0
        else:
            console.print(f"[bold red]Error:[/bold red] {message}")
            return 1

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return 1


@archive_commands.command(name="unarchive")
@click.argument("title")
@click.option("--category", "-c", help="Category of the note.")
@click.option("--output-dir", "-o", help="Custom directory to look for notes.")
@click.option("--move", "-m", is_flag=True, help="Move the note from the archive directory.")
@click.option("--destination", "-d", help="Destination directory for the unarchived note.")
def unarchive_note(title: str, category: Optional[str], output_dir: Optional[str],
                   move: bool, destination: Optional[str]):
    """
    Unarchive an archived note.

    TITLE is the title of the note to unarchive.
    """
    try:
        # Create archive-enabled note manager
        note_manager = ArchiveNoteManager()

        # Check if the note exists and is archived
        if not note_manager.is_note_archived(title, category, output_dir):
            # Try archive directory if specified in options
            if output_dir:
                console.print(
                    f"[bold red]Error:[/bold red] Note '{title}' is not archived.")
                return 1

            # Try to find in archive directory
            archive_dir = os.path.join(note_manager.notes_dir, "archive")
            if not note_manager.is_note_archived(title, category, archive_dir):
                console.print(
                    f"[bold red]Error:[/bold red] Note '{title}' is not found or not archived.")
                return 1

        # Unarchive the note
        success, message = note_manager.unarchive_note(
            title=title,
            category=category,
            output_dir=output_dir,
            move_from_archive_dir=move,
            destination_dir=destination
        )

        if success:
            console.print(f"[bold green]Success:[/bold green] {message}")
            console.print(
                "[blue]Note has been unmarked as 'Archived' and the 'Archived' tag has been removed.[/blue]")
            return 0
        else:
            console.print(f"[bold red]Error:[/bold red] {message}")
            return 1

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return 1


@archive_commands.command(name="list")
@click.option("--category", "-c", help="Filter notes by category.")
@click.option("--output", "-o", help="Output format: table (default), json, or markdown.")
@click.option("--sort-by", type=click.Choice(['title', 'date', 'category', 'size']), default='date',
              help="Sort archived notes by: title, date, category, or size.")
@click.option("--reverse", "-r", is_flag=True, help="Reverse the sorting order.")
def list_archived_notes(category: Optional[str], output: Optional[str],
                        sort_by: str, reverse: bool):
    """
    List all archived notes.
    """
    try:
        # Create archive-enabled note manager
        note_manager = ArchiveNoteManager()

        # Get all archived notes
        archived_notes = note_manager.list_archived_notes(
            include_content=False, category=category)

        if not archived_notes:
            console.print("[yellow]No archived notes found.[/yellow]")
            return 0

        # Sort the notes
        if sort_by == 'title':
            archived_notes.sort(key=lambda x: x.get(
                'title', ''), reverse=reverse)
        elif sort_by == 'date':
            archived_notes.sort(key=lambda x: x.get(
                'archived_at', ''), reverse=not reverse)  # Reverse logic for dates
        elif sort_by == 'category':
            archived_notes.sort(key=lambda x: x.get(
                'category', ''), reverse=reverse)
        elif sort_by == 'size':
            archived_notes.sort(key=lambda x: x.get(
                'size_bytes', 0), reverse=not reverse)  # Larger size first

        # Output format
        output_format = output.lower() if output else 'table'

        if output_format == 'json':
            # JSON output
            console.print(json.dumps(archived_notes, indent=2))

        elif output_format == 'markdown':
            # Markdown output
            md = "# Archived Notes\n\n"
            md += f"*{len(archived_notes)} archived notes found*\n\n"

            md += "| Title | Category | Archived Date | Reason |\n"
            md += "|-------|----------|--------------|--------|\n"

            for note in archived_notes:
                title = note.get('title', 'Untitled')
                category = note.get('category', 'Uncategorized')
                archived_date = note.get('archived_at', 'Unknown')
                if archived_date:
                    try:
                        date = datetime.fromisoformat(archived_date)
                        archived_date = date.strftime('%Y-%m-%d')
                    except (ValueError, TypeError):
                        pass

                reason = note.get('archive_reason', 'No reason specified')

                md += f"| {title} | {category} | {archived_date} | {reason} |\n"

            console.print(Markdown(md))

        else:
            # Table output (default)
            table = Table(title=f"Archived Notes ({len(archived_notes)})")
            table.add_column("Title", style="cyan")
            table.add_column("Category", style="blue")
            table.add_column("Archived Date", style="yellow")
            table.add_column("Size", style="green")
            table.add_column("Reason", style="dim")

            for note in archived_notes:
                title = note.get('title', 'Untitled')
                category = note.get('category', 'Uncategorized')

                # Format date
                archived_date = note.get('archived_at', 'Unknown')
                if archived_date:
                    try:
                        date = datetime.fromisoformat(archived_date)
                        archived_date = date.strftime('%Y-%m-%d')
                    except (ValueError, TypeError):
                        pass

                # Format size
                size_bytes = note.get('size_bytes', 0)
                if size_bytes < 1024:
                    size_str = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size_str = f"{size_bytes / 1024:.1f} KB"
                else:
                    size_str = f"{size_bytes / (1024 * 1024):.1f} MB"

                reason = note.get('archive_reason', 'No reason specified')

                table.add_row(title, category, archived_date, size_str, reason)

            console.print(table)

        return 0

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return 1


@archive_commands.command(name="stats")
@click.option("--output", "-o", help="Output format: panel (default), json, or markdown.")
def archive_stats(output: Optional[str]):
    """
    Display statistics about archived notes.
    """
    try:
        # Create archive-enabled note manager
        note_manager = ArchiveNoteManager()

        # Get archive stats
        stats = note_manager.get_archive_stats()

        if stats['total_archived'] == 0:
            console.print("[yellow]No archived notes found.[/yellow]")
            return 0

        # Output format
        output_format = output.lower() if output else 'panel'

        if output_format == 'json':
            # JSON output
            console.print(json.dumps(stats, indent=2))

        elif output_format == 'markdown':
            # Markdown output
            md = "# Archive Statistics\n\n"
            md += f"**Total archived notes:** {stats['total_archived']}\n"

            # Format storage size
            storage_bytes = stats.get('storage_bytes', 0)
            if storage_bytes < 1024:
                storage_str = f"{storage_bytes} B"
            elif storage_bytes < 1024 * 1024:
                storage_str = f"{storage_bytes / 1024:.1f} KB"
            else:
                storage_str = f"{storage_bytes / (1024 * 1024):.1f} MB"

            md += f"**Total storage used:** {storage_str}\n"

            # Date information
            if stats['oldest_archive']:
                try:
                    oldest = datetime.fromisoformat(stats['oldest_archive'])
                    md += f"**Oldest archive:** {oldest.strftime('%Y-%m-%d')}\n"
                except (ValueError, TypeError):
                    md += f"**Oldest archive:** {stats['oldest_archive']}\n"

            if stats['newest_archive']:
                try:
                    newest = datetime.fromisoformat(stats['newest_archive'])
                    md += f"**Newest archive:** {newest.strftime('%Y-%m-%d')}\n"
                except (ValueError, TypeError):
                    md += f"**Newest archive:** {stats['newest_archive']}\n"

            # Categories
            if stats['categories']:
                md += "\n## Categories\n\n"
                for category, count in sorted(stats['categories'].items(), key=lambda x: x[1], reverse=True):
                    md += f"- **{category}:** {count}\n"

            # Tags
            if stats['tags']:
                md += "\n## Tags\n\n"
                for tag, count in sorted(stats['tags'].items(), key=lambda x: x[1], reverse=True):
                    md += f"- **{tag}:** {count}\n"

            # Reasons
            if stats['archive_reasons']:
                md += "\n## Archive Reasons\n\n"
                for reason, count in sorted(stats['archive_reasons'].items(), key=lambda x: x[1], reverse=True):
                    if reason is None:
                        reason = "No reason specified"
                    md += f"- **{reason}:** {count}\n"

            console.print(Markdown(md))

        else:
            # Panel output (default)
            # Format storage size
            storage_bytes = stats.get('storage_bytes', 0)
            if storage_bytes < 1024:
                storage_str = f"{storage_bytes} B"
            elif storage_bytes < 1024 * 1024:
                storage_str = f"{storage_bytes / 1024:.1f} KB"
            else:
                storage_str = f"{storage_bytes / (1024 * 1024):.1f} MB"

            # Create summary panel
            summary = f"Total archived notes: {stats['total_archived']}\n"
            summary += f"Total storage used: {storage_str}\n"

            if stats['oldest_archive']:
                try:
                    oldest = datetime.fromisoformat(stats['oldest_archive'])
                    summary += f"Oldest archive: {oldest.strftime('%Y-%m-%d')}\n"
                except (ValueError, TypeError):
                    summary += f"Oldest archive: {stats['oldest_archive']}\n"

            if stats['newest_archive']:
                try:
                    newest = datetime.fromisoformat(stats['newest_archive'])
                    summary += f"Newest archive: {newest.strftime('%Y-%m-%d')}\n"
                except (ValueError, TypeError):
                    summary += f"Newest archive: {stats['newest_archive']}\n"

            console.print(
                Panel(summary, title="Archive Summary", border_style="blue"))

            # Categories table
            if stats['categories']:
                categories_table = Table(title="Categories")
                categories_table.add_column("Category", style="cyan")
                categories_table.add_column(
                    "Count", style="green", justify="right")

                for category, count in sorted(stats['categories'].items(), key=lambda x: x[1], reverse=True):
                    categories_table.add_row(category, str(count))

                console.print(categories_table)

            # Tags table
            if stats['tags']:
                tags_table = Table(title="Tags")
                tags_table.add_column("Tag", style="cyan")
                tags_table.add_column("Count", style="green", justify="right")

                for tag, count in sorted(stats['tags'].items(), key=lambda x: x[1], reverse=True):
                    tags_table.add_row(tag, str(count))

                console.print(tags_table)

            # Reasons table
            if stats['archive_reasons']:
                reasons_table = Table(title="Archive Reasons")
                reasons_table.add_column("Reason", style="cyan")
                reasons_table.add_column(
                    "Count", style="green", justify="right")

                for reason, count in sorted(stats['archive_reasons'].items(), key=lambda x: x[1], reverse=True):
                    if reason is None:
                        reason = "No reason specified"
                    reasons_table.add_row(reason, str(count))

                console.print(reasons_table)

        return 0

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return 1


@archive_commands.command(name="batch")
@click.argument("titles", nargs=-1, required=True)
@click.option("--reason", "-r", help="Reason for archiving the notes.")
@click.option("--category", "-c", help="Category of the notes.")
@click.option("--output-dir", "-o", help="Custom directory to look for notes.")
@click.option("--move", "-m", is_flag=True, help="Move notes to a dedicated archive directory.")
def batch_archive(titles: List[str], reason: Optional[str], category: Optional[str],
                  output_dir: Optional[str], move: bool):
    """
    Archive multiple notes.

    TITLES is a space-separated list of note titles to archive.
    """
    try:
        if not titles:
            console.print("[bold yellow]No titles provided.[/bold yellow]")
            return 0

        # Create archive-enabled note manager
        note_manager = ArchiveNoteManager()

        # Show progress spinner for each note
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            task = progress.add_task("Archiving notes...", total=len(titles))

            # Process each note
            results = {}
            for title in titles:
                progress.update(
                    task, description=f"Archiving [cyan]{title}[/cyan]...")

                # Skip notes that are already archived
                if note_manager.is_note_archived(title, category, output_dir):
                    results[title] = "Already archived (skipped)"
                    progress.advance(task)
                    continue

                # Archive the note
                success, message = note_manager.archive_note(
                    title=title,
                    reason=reason,
                    category=category,
                    output_dir=output_dir,
                    move_to_archive_dir=move
                )

                results[title] = message if success else f"Failed: {message}"
                progress.advance(task)

            # If no titles were processed, exit
            if not results:
                console.print("[yellow]No notes found to archive.[/yellow]")
                return 0

        # Display results
        table = Table(title=f"Archiving Results ({len(titles)} notes)")
        table.add_column("Note", style="cyan")
        table.add_column("Status", style="bold")

        success_count = 0
        for title, result in results.items():
            status_style = "green" if "success" in result.lower(
            ) else "red" if "failed" in result.lower() else "yellow"
            table.add_row(title, f"[{status_style}]{result}[/{status_style}]")
            if "success" in result.lower():
                success_count += 1

        console.print(table)

        # Summary message
        console.print(Panel(
            f"Successfully archived {success_count} of {len(titles)} notes.",
            title="Archiving Summary",
            border_style="green" if success_count == len(titles) else "yellow"
        ))

        return 0 if success_count == len(titles) else 1

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return 1


@archive_commands.command(name="auto")
@click.option("--days", "-d", type=int, required=True, help="Archive notes older than this many days.")
@click.option("--reason", "-r", default="Auto-archived due to age",
              help="Reason for archiving the notes.")
@click.option("--move", "-m", is_flag=True, default=True,
              help="Move notes to a dedicated archive directory.")
@click.option("--dry-run", is_flag=True, help="Show what would be archived without archiving.")
def auto_archive(days: int, reason: str, move: bool, dry_run: bool):
    """
    Auto-archive notes that haven't been updated in the specified number of days.
    """
    try:
        if days < 1:
            console.print(
                "[bold red]Error:[/bold red] Days must be a positive number.")
            return 1

        console.print(f"Finding notes older than [cyan]{days}[/cyan] days...")

        # Create archive-enabled note manager
        note_manager = ArchiveNoteManager()

        if dry_run:
            # Find notes that would be archived without actually archiving
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=days)

            console.print(
                f"Cutoff date: [yellow]{cutoff_date.strftime('%Y-%m-%d')}[/yellow]")
            console.print("Scanning notes...")

            # Get all note files
            from app.utils.file_handler import list_note_files
            all_notes = list_note_files(note_manager.notes_dir)

            to_archive = []

            for note_path in all_notes:
                try:
                    # Skip notes that are already in the archive directory
                    if "archive" in note_path:
                        continue

                    # Read the note
                    from app.utils.file_handler import read_note_file
                    metadata, _ = read_note_file(note_path)

                    # Skip notes that are already archived
                    if metadata.get('is_archived', False):
                        continue

                    # Check the last update date
                    updated_at = None
                    if 'updated_at' in metadata:
                        try:
                            updated_at = datetime.fromisoformat(
                                metadata['updated_at'])
                        except (ValueError, TypeError):
                            # If parsing fails, use file modification time
                            updated_at = datetime.fromtimestamp(
                                os.path.getmtime(note_path))
                    else:
                        # Use file modification time if metadata doesn't include update time
                        updated_at = datetime.fromtimestamp(
                            os.path.getmtime(note_path))

                    # Archive if older than cutoff date
                    if updated_at < cutoff_date:
                        title = metadata.get('title', os.path.splitext(
                            os.path.basename(note_path))[0])
                        category = metadata.get('category', None) or os.path.basename(
                            os.path.dirname(note_path))
                        to_archive.append({
                            'title': title,
                            'path': note_path,
                            'updated_at': updated_at,
                            'category': category,
                            'days_old': (datetime.now() - updated_at).days
                        })
                except Exception:
                    # Skip files that can't be read
                    pass

            if not to_archive:
                console.print(
                    "[green]No notes found that would be auto-archived.[/green]")
                return 0

            # Display notes that would be archived
            table = Table(
                title=f"Notes That Would Be Archived ({len(to_archive)})")
            table.add_column("Title", style="cyan")
            table.add_column("Category", style="blue")
            table.add_column("Last Updated", style="yellow")
            table.add_column("Days Old", style="red")

            for note in sorted(to_archive, key=lambda x: x['days_old'], reverse=True):
                table.add_row(
                    note['title'],
                    note['category'],
                    note['updated_at'].strftime('%Y-%m-%d'),
                    str(note['days_old'])
                )

            console.print(table)
            console.print(
                f"[bold yellow]Dry run - no changes made.[/bold yellow]")

            # Ask if user wants to proceed with archiving
            if Confirm.ask("Do you want to archive these notes now?"):
                console.print(
                    "[bold blue]Proceeding with archiving...[/bold blue]")
            else:
                console.print(
                    "[bold blue]Exiting without archiving.[/bold blue]")
                return 0

        # Show progress spinner
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Auto-archiving notes...", total=None)

            # Auto-archive notes
            results = note_manager.auto_archive_by_age(
                days=days,
                reason=reason,
                move_to_archive_dir=move
            )

            # Complete the progress
            progress.update(task, completed=True, total=1)

        # Check results
        if not results:
            console.print("[green]No notes were auto-archived.[/green]")
            return 0

        # Count successes and failures
        success_count = list(results.values()).count(
            "Successfully archived and moved to archive directory")
        success_count += list(results.values()).count("Successfully archived")

        # Display results
        table = Table(title=f"Auto-Archive Results ({len(results)} notes)")
        table.add_column("Note", style="cyan")
        table.add_column("Status", style="bold")

        # Sort by path - group by directory
        for path, result in sorted(results.items()):
            note_name = os.path.splitext(os.path.basename(path))[0]
            status_style = "green" if "success" in result.lower(
            ) else "red" if "failed" in result.lower() else "yellow"
            table.add_row(
                note_name, f"[{status_style}]{result}[/{status_style}]")

        console.print(table)

        # Summary message
        console.print(Panel(
            f"Auto-archived {success_count} notes that were older than {days} days.",
            title="Auto-Archive Summary",
            border_style="green" if success_count > 0 else "yellow"
        ))

        return 0

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return 1


@archive_commands.command(name="status")
@click.argument("title", required=False)
@click.option("--category", "-c", help="Category of the note.")
@click.option("--output-dir", "-o", help="Custom directory to look for notes.")
def archive_status(title: Optional[str], category: Optional[str], output_dir: Optional[str]):
    """
    Check the archive status of a note or get general archive stats.

    If TITLE is provided, checks that specific note.
    If not, provides general archive statistics.
    """
    try:
        # Create archive-enabled note manager
        note_manager = ArchiveNoteManager()

        if title:
            # Check a single note
            is_archived = note_manager.is_note_archived(
                title, category, output_dir)

            if not is_archived:
                # Try archive directory
                archive_dir = os.path.join(note_manager.notes_dir, "archive")
                if category:
                    archive_cat_dir = os.path.join(archive_dir, category)
                    is_archived = note_manager.is_note_archived(
                        title, None, archive_cat_dir)

                if not is_archived:
                    is_archived = note_manager.is_note_archived(
                        title, None, archive_dir)

            # Get note path
            note_path = note_manager.find_note_path(
                title, category, output_dir)

            if not note_path:
                # Try archive directory
                archive_dir = os.path.join(note_manager.notes_dir, "archive")
                if category:
                    archive_cat_dir = os.path.join(archive_dir, category)
                    note_path = note_manager.find_note_path(
                        title, None, archive_cat_dir)

                if not note_path:
                    note_path = note_manager.find_note_path(
                        title, None, archive_dir)

            if not note_path:
                console.print(
                    f"[bold red]Error:[/bold red] Note '{title}' not found.")
                return 1

            status_text = "[green]Archived[/green]" if is_archived else "[yellow]Not Archived[/yellow]"

            # If archived, get additional details
            additional_info = ""
            if is_archived:
                metadata, _ = note_manager.archive_manager.read_note_file(
                    note_path)
                archived_at = metadata.get('archived_at')
                if archived_at:
                    try:
                        date = datetime.fromisoformat(archived_at)
                        additional_info += f"Archived on: {date.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    except (ValueError, TypeError):
                        additional_info += f"Archived on: {archived_at}\n"

                reason = metadata.get('archive_reason')
                if reason:
                    additional_info += f"Reason: {reason}\n"

            panel = Panel(
                f"Status: {status_text}\n"
                f"Path: {note_path}\n"
                f"{additional_info}",
                title=f"Archive Status: {title}",
                border_style="cyan"
            )
            console.print(panel)

        else:
            # No title provided, show archive stats
            stats = note_manager.get_archive_stats()

            # Format storage size
            storage_bytes = stats.get('storage_bytes', 0)
            if storage_bytes < 1024:
                storage_str = f"{storage_bytes} B"
            elif storage_bytes < 1024 * 1024:
                storage_str = f"{storage_bytes / 1024:.1f} KB"
            else:
                storage_str = f"{storage_bytes / (1024 * 1024):.1f} MB"

            # Create summary panel
            summary = f"Total archived notes: {stats['total_archived']}\n"
            summary += f"Total storage used: {storage_str}\n"

            if stats['oldest_archive']:
                try:
                    oldest = datetime.fromisoformat(stats['oldest_archive'])
                    summary += f"Oldest archive: {oldest.strftime('%Y-%m-%d')}\n"
                except (ValueError, TypeError):
                    summary += f"Oldest archive: {stats['oldest_archive']}\n"

            if stats['newest_archive']:
                try:
                    newest = datetime.fromisoformat(stats['newest_archive'])
                    summary += f"Newest archive: {newest.strftime('%Y-%m-%d')}\n"
                except (ValueError, TypeError):
                    summary += f"Newest archive: {stats['newest_archive']}\n"

            console.print(
                Panel(summary, title="Archive Statistics", border_style="blue"))

        return 0

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return 1


@cli.command()
@click.option("--tag", "-t", help="Filter notes by tag.")
@click.option("--category", "-c", help="Filter notes by category.")
@click.option("--output-dir", "-o", help="Custom output directory for notes.")
@click.option("--detail/--no-detail", "-d/-n", default=False,
              help="Show detailed breakdown by category and tags.")
def count(tag: Optional[str] = None,
          category: Optional[str] = None,
          output_dir: Optional[str] = None,
          detail: bool = False):
    """
    Count the total number of notes in the system.
    """
    note_manager = NoteManager(output_dir)

    # Get total count
    total_count = note_manager.get_notes_count(
        tag=tag,
        category=category,
        output_dir=output_dir
    )

    # Create a panel with the count information
    if not detail:
        # Simple count display
        count_text = f"Total notes: {total_count}"
        if tag:
            count_text += f" (filtered by tag: {tag})"
        if category:
            count_text += f" (filtered by category: {category})"

        panel = Panel(
            count_text,
            title="Note Count",
            border_style="blue"
        )
        console.print(panel)
    else:
        # Detailed breakdown
        table = Table(title="Note Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green")

        # Add total count row
        table.add_row("Total Notes", str(total_count))

        # Get counts by category if no category filter is applied
        if not category:
            # Get all categories
            categories = []
            base_dir = output_dir if output_dir else note_manager.notes_dir
            base_dir = os.path.expanduser(base_dir)

            if os.path.exists(base_dir):
                for item in os.listdir(base_dir):
                    item_path = os.path.join(base_dir, item)
                    if os.path.isdir(item_path) and not item.startswith('.'):
                        categories.append(item)

            # Add empty / uncategorized category
            categories.append("(uncategorized)")

            # Add a section header for categories
            table.add_row("", "")
            table.add_row("By Category", "")

            # Count notes in each category
            for cat in categories:
                filter_category = None if cat == "(uncategorized)" else cat
                count = note_manager.get_notes_count(
                    tag=tag, category=filter_category, output_dir=output_dir)
                if count > 0:  # Only show categories with notes
                    table.add_row(cat, str(count))

        # Get counts by tags if tag filter is not applied
        if not tag:
            # Get all notes to extract tags
            notes = note_manager.list_notes(
                category=category, output_dir=output_dir)

            # Count notes by tag
            tag_counts = {}
            for note in notes:
                for note_tag in note.tags:
                    tag_counts[note_tag] = tag_counts.get(note_tag, 0) + 1

            if tag_counts:
                # Add a section header for tags
                table.add_row("", "")
                table.add_row("By Tag", "")

                # Sort tags by count (descending)
                sorted_tags = sorted(tag_counts.items(),
                                     key=lambda x: x[1], reverse=True)

                # Show top 10 tags
                for tag_name, tag_count in sorted_tags[:10]:
                    table.add_row(tag_name, str(tag_count))

                # Indicate if there are more tags
                if len(sorted_tags) > 10:
                    table.add_row(
                        "...", f"(and {len(sorted_tags) - 10} more tags)")
            else:
                table.add_row("No tags found", "")

        # Display the table
        console.print(table)


@cli.command()
@click.option("--category", "-c", help="Filter notes by category.")
@click.option("--output-dir", "-o", help="Custom output directory for notes.")
@click.option("--top", "-t", type=int, default=1,
              help="Show top N most frequent tags (default: 1).")
@click.option("--all/--no-all", "-a/-n", default=False,
              help="Show all tags sorted by frequency.")
def tags(category: Optional[str] = None,
         output_dir: Optional[str] = None,
         top: int = 1,
         all: bool = False):
    """
    Show the most frequently used tags in your notes.
    """
    note_manager = NoteManager(output_dir)

    # Get most frequent tag and all tag counts
    most_frequent, count, tag_counts = note_manager.get_most_frequent_tag(
        category=category,
        output_dir=output_dir
    )

    # Create a table for the tags
    table = Table(title="Tag Statistics")
    table.add_column("Rank", style="cyan", justify="right")
    table.add_column("Tag", style="green")
    table.add_column("Count", style="blue", justify="right")
    table.add_column("Percentage", style="yellow", justify="right")

    # If no tags found
    if not most_frequent:
        if category:
            message = f"No tags found in category '{category}'."
        else:
            message = "No tags found in any notes."

        console.print(
            Panel(message, title="Tag Statistics", border_style="red"))
        return

    # Get total number of tags
    total_tags = sum(tag_counts.values())

    if all:
        # Show all tags sorted by frequency
        sorted_tags = sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))
        for rank, (tag, tag_count) in enumerate(sorted_tags, 1):
            percentage = (tag_count / total_tags) * 100
            table.add_row(
                f"{rank}",
                tag,
                f"{tag_count}",
                f"{percentage:.1f}%"
            )
    else:
        # Show only top N tags
        sorted_tags = sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))
        for rank, (tag, tag_count) in enumerate(sorted_tags[:top], 1):
            percentage = (tag_count / total_tags) * 100
            table.add_row(
                f"{rank}",
                tag,
                f"{tag_count}",
                f"{percentage:.1f}%"
            )

        # If there are more tags, show a summary row
        remaining_tags = len(tag_counts) - top
        if remaining_tags > 0:
            remaining_count = sum(count for _, count in sorted_tags[top:])
            remaining_percentage = (remaining_count / total_tags) * 100
            table.add_row(
                "...",
                f"({remaining_tags} more tags)",
                f"{remaining_count}",
                f"{remaining_percentage:.1f}%"
            )

    # Add a summary footer
    table.add_row("", "", "", "")
    table.add_row(
        "Total", f"{len(tag_counts)} unique tags", f"{total_tags}", "100.0%")

    # Display the results
    console.print(table)

    # Also display some insights
    if most_frequent and not all and top == 1:
        most_frequent_percentage = (count / total_tags) * 100
        insights = [
            f"Most frequent tag: '[bold green]{most_frequent}[/bold green]' (used in {count} notes)",
            f"This tag represents [bold yellow]{most_frequent_percentage:.1f}%[/bold yellow] of all tag usage."
        ]
        console.print(Panel("\n".join(insights),
                      title="Tag Insights", border_style="blue"))


@cli.command()
@click.option("--tag", "-t", help="Filter notes by tag.")
@click.option("--output-dir", "-o", help="Custom output directory for notes.")
@click.option("--sort-by", "-s", type=click.Choice(['name', 'count']), default='count',
              help="Sort categories by name or count.")
@click.option("--reverse/--no-reverse", "-r/-n", default=False,
              help="Reverse the sort order.")
@click.option("--output", type=click.Choice(['text', 'table', 'json', 'markdown']), default='table',
              help="Output format.")
def categories(tag: Optional[str] = None,
               output_dir: Optional[str] = None,
               sort_by: str = 'count',
               reverse: bool = False,
               output: str = 'table'):
    """
    Show the number of notes per category.
    """
    note_manager = NoteManager(output_dir)

    # Get category counts
    category_counts = note_manager.get_notes_per_category(
        tag=tag,
        output_dir=output_dir
    )

    # If no categories found
    if not category_counts:
        console.print("No categories found.", style="yellow")
        return

    # Get total notes count for reference
    total_notes = sum(category_counts.values())

    # Sort the categories
    if sort_by == 'name':
        # Sort alphabetically by category name
        sorted_categories = sorted(
            category_counts.items(),
            reverse=reverse
        )
    else:
        # Sort by note count (default)
        sorted_categories = sorted(
            category_counts.items(),
            key=lambda x: x[1],  # Sort by count
            reverse=not reverse  # Default to highest count first
        )

    # Format the output based on selected format
    if output == 'json':
        # JSON output
        json_data = {
            "total_notes": total_notes,
            "categories": dict(sorted_categories)
        }
        console.print(json.dumps(json_data, indent=2))

    elif output == 'markdown':
        # Markdown table output
        console.print("# Note Categories\n")
        console.print(f"Total notes: {total_notes}\n")
        console.print("| Category | Count | Percentage |")
        console.print("|----------|-------|------------|")

        for category, count in sorted_categories:
            percentage = (count / total_notes) * 100 if total_notes > 0 else 0
            console.print(f"| {category} | {count} | {percentage:.1f}% |")

    elif output == 'text':
        # Simple text output
        console.print(f"Total notes: {total_notes}\n")
        for category, count in sorted_categories:
            percentage = (count / total_notes) * 100 if total_notes > 0 else 0
            console.print(f"{category}: {count} ({percentage:.1f}%)")

    else:
        # Rich table output (default)
        table = Table(title="Notes per Category")
        table.add_column("Category", style="cyan")
        table.add_column("Count", style="green", justify="right")
        table.add_column("Percentage", justify="right")

        for category, count in sorted_categories:
            percentage = (count / total_notes) * 100 if total_notes > 0 else 0
            table.add_row(
                category,
                str(count),
                f"{percentage:.1f}%"
            )

        # Add total row
        table.add_row("Total", str(total_notes), "100.0%", style="bold")

        # Print additional info
        if tag:
            console.print(f"[italic]Notes filtered by tag: {tag}[/italic]\n")

        console.print(table)


@cli.command()
@click.argument("title")
@click.option("--category", "-c", help="Category of the note.")
@click.option("--output-dir", "-o", help="Custom directory to look in. Overrides the default location.")
def wordcount(title: str, category: Optional[str] = None, output_dir: Optional[str] = None):
    """
    Display word count and other statistics for the note with the given TITLE.
    """
    note_manager = NoteManager(output_dir)
    success, message, stats = note_manager.get_note_word_count(
        title=title,
        category=category,
        output_dir=output_dir
    )

    if not success:
        console.print(f"[bold red]Error:[/bold red] {message}")
        return 1

    # Create a table to display statistics
    table = Table(
        title=f"Statistics for '{title}'", show_header=True, header_style="bold cyan")
    table.add_column("Metric")
    table.add_column("Count", justify="right")

    # Add rows for each statistic
    table.add_row("Word count", str(stats["word_count"]))
    table.add_row("Character count", str(stats["character_count"]))
    table.add_row("Character count (no spaces)", str(
        stats["character_count_no_spaces"]))
    table.add_row("Line count", str(stats["line_count"]))
    table.add_row("Paragraph count", str(stats["paragraph_count"]))
    table.add_row("Avg words per paragraph",
                  f"{stats['avg_words_per_paragraph']:.1f}")

    # Display the table
    console.print(table)

    return 0


@cli.command()
@click.argument("title")
@click.option("--category", "-c", help="Category of the note.")
@click.option("--output-dir", "-o", help="Directory where the note is located.")
@click.option("--force", "-f", is_flag=True, help="Delete without confirmation.")
def delete(title: str, category: Optional[str], output_dir: Optional[str], force: bool):
    """Delete a note."""
    try:
        note_manager = NoteManager()

        if not force:
            if not click.confirm(f"Are you sure you want to delete note '{title}'?"):
                console.print("[yellow]Deletion cancelled.[/yellow]")
                return 0

        success, message = note_manager.delete_note(
            title,
            category=category,
            output_dir=output_dir,
            force=force
        )

        if success:
            console.print(f"[green]{message}[/green]")
        else:
            console.print(f"[bold red]Error:[/bold red] {message}")
            return 1

    except Exception as e:
        console.print(f"[bold red]Error deleting note:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


@click.group(name="bulk-delete")
def delete_commands():
    """Commands for bulk deleting notes."""
    pass


@delete_commands.command(name="titles")
@click.argument("titles", nargs=-1, required=True)
@click.option("--category", "-c", help="Category of the notes.")
@click.option("--output-dir", "-o", help="Directory where the notes are located.")
@click.option("--force", "-f", is_flag=True, help="Delete without confirmation for each note.")
def bulk_delete_by_titles(titles: List[str], category: Optional[str],
                          output_dir: Optional[str], force: bool):
    """Delete multiple notes by their titles."""
    try:
        note_manager = NoteManager()

        # Convert tuple to list
        titles_list = list(titles)

        if not force:
            console.print(f"You are about to delete {len(titles_list)} notes:")
            for title in titles_list:
                console.print(f"  - {title}")
            if not click.confirm("Are you sure you want to proceed?"):
                console.print("[yellow]Bulk deletion cancelled.[/yellow]")
                return 0

        results = note_manager.bulk_delete_notes(
            titles_list,
            category=category,
            output_dir=output_dir,
            force=force
        )

        console.print("[bold]Bulk delete results:[/bold]")
        for title, result in results.items():
            if result.startswith("✓"):
                console.print(f"[green]{result}[/green]")
            else:
                console.print(f"[red]{result}[/red]")

    except Exception as e:
        console.print(f"[bold red]Error in bulk delete:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


@delete_commands.command(name="tags")
@click.argument("tags", nargs=-1, required=True)
@click.option("--category", "-c", help="Category of the notes.")
@click.option("--output-dir", "-o", help="Directory where the notes are located.")
@click.option("--force", "-f", is_flag=True, help="Delete without confirmation.")
@click.option("--all-tags", "-a", is_flag=True, help="Notes must have all tags (AND logic) instead of any tag (OR logic).")
def bulk_delete_by_tags(tags: List[str], category: Optional[str],
                        output_dir: Optional[str], force: bool, all_tags: bool):
    """Delete multiple notes by their tags."""
    try:
        note_manager = NoteManager()

        # First, find all notes with the specified tags
        matched_notes = []
        all_notes = note_manager.list_notes(
            category=category, output_dir=output_dir)

        for note in all_notes:
            note_tags = note.get_tags()
            if all_tags:
                # AND logic - note must have all specified tags
                if all(tag in note_tags for tag in tags):
                    matched_notes.append(note.title)
            else:
                # OR logic - note must have any of the specified tags
                if any(tag in note_tags for tag in tags):
                    matched_notes.append(note.title)

        if not matched_notes:
            console.print(
                f"[yellow]No notes found with the specified tags: {', '.join(tags)}[/yellow]")
            return 0

        if not force:
            console.print(
                f"You are about to delete {len(matched_notes)} notes with tag(s): {', '.join(tags)}")
            for title in matched_notes:
                console.print(f"  - {title}")
            if not click.confirm("Are you sure you want to proceed?"):
                console.print("[yellow]Bulk deletion cancelled.[/yellow]")
                return 0

        results = note_manager.bulk_delete_notes(
            matched_notes,
            category=category,
            output_dir=output_dir,
            force=force
        )

        console.print("[bold]Bulk delete results:[/bold]")
        for title, result in results.items():
            if result.startswith("✓"):
                console.print(f"[green]{result}[/green]")
            else:
                console.print(f"[red]{result}[/red]")

    except Exception as e:
        console.print(
            f"[bold red]Error in bulk delete by tags:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


@cli.group(name="tags")
def tag_commands():
    """Commands for managing note tags."""
    pass

@tag_commands.command(name="rename")
@click.argument("old_tag", required=True)
@click.argument("new_tag", required=True)
@click.option("--filter-tags", "-f", multiple=True, help="Only rename tags in notes that have these tags.")
@click.option("--all-filter-tags/--any-filter-tags", "-a/-n", default=False, 
                help="Require notes to have all filter tags (AND logic) instead of any (OR logic).")
@click.option("--category", "-c", help="Only rename tags in notes from this category.")
@click.option("--output-dir", "-o", help="Directory where the notes are located.")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
def bulk_rename_tag(old_tag: str, new_tag: str, filter_tags: List[str], all_filter_tags: bool, 
                    category: Optional[str], output_dir: Optional[str], yes: bool):
    """
    Rename a tag across multiple notes.
    
    Examples:
        rename "todo" "to-do"          # Rename all "todo" tags to "to-do"
        rename "priority" "urgent" -f "project" -f "deadline"  # Only in notes with "project" OR "deadline" tags
        rename "tech" "technology" -f "blog" -a -f "draft"     # Only in notes with "blog" AND "draft" tags
    """
    try:
        note_manager = NoteManager()
        
        # Show what will be done and confirm
        message = f"Renaming tag '{old_tag}' to '{new_tag}'"
        if filter_tags:
            logic_type = "ALL" if all_filter_tags else "ANY"
            message += f" in notes with {logic_type} of these tags: {', '.join(filter_tags)}"
        if category:
            message += f" in category '{category}'"
            
        console.print(f"[bold]{message}[/bold]")
        
        if not yes:
            if not click.confirm("Do you want to continue?"):
                console.print("[yellow]Operation cancelled.[/yellow]")
                return 0
        
        results = note_manager.bulk_rename_tag(
            old_tag, 
            new_tag,
            filter_tags=list(filter_tags) if filter_tags else None,
            all_filter_tags=all_filter_tags,
            category=category,
            output_dir=output_dir
        )
        
        # Display results
        success_count = sum(1 for msg in results.values() if msg.startswith("✓"))
        console.print(f"\n[bold]Results: {success_count}/{len(results)} notes updated[/bold]")
        
        for note_title, result in results.items():
            if result.startswith("✓"):
                console.print(f"[green]{note_title}: {result}[/green]")
            else:
                console.print(f"[red]{note_title}: {result}[/red]")
                
    except Exception as e:
        console.print(f"[bold red]Error renaming tags:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0

@tag_commands.command(name="list")
@click.option("--count", "-c", is_flag=True, help="Show tag count.")
@click.option("--sort", "-s", type=click.Choice(["name", "count"]), default="name", 
                help="Sort by name or count.")
@click.option("--limit", "-l", type=int, help="Limit number of tags shown.")
@click.option("--output-dir", "-o", help="Directory where to look for notes.")
def list_tags(count: bool, sort: str, limit: Optional[int], output_dir: Optional[str]):
    """
    List all tags used across notes.
    """
    try:
        note_manager = NoteManager()
        tag_counts = {}
        
        # Get all notes
        notes = note_manager.list_notes(output_dir=output_dir)
        
        # Count tags
        for note in notes:
            for tag in note.get_tags():
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
                
        if not tag_counts:
            console.print("[yellow]No tags found.[/yellow]")
            return 0
            
        # Sort tags
        if sort == "name":
            sorted_tags = sorted(tag_counts.items())
        else:  # sort == "count"
            sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
            
        # Limit number of tags if requested
        if limit and limit > 0:
            sorted_tags = sorted_tags[:limit]
            
        # Display tags
        table = Table(title="Tags")
        table.add_column("Tag", style="green")
        if count:
            table.add_column("Count", style="cyan", justify="right")
            
        for tag, count_value in sorted_tags:
            if count:
                table.add_row(tag, str(count_value))
            else:
                table.add_row(tag)
                
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]Error listing tags:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0



@cli.group(name="templates-manage")
def template_commands():
    """Commands for managing note templates."""
    pass

@template_commands.command(name="create")
@click.argument("name")
@click.option("--from", "-f", "base_template", help="Base template to use.")
@click.option("--editor", "-e", help="Open in editor after creation. Optionally specify editor name.")
@click.option("--open-editor", is_flag=True, help="Open in default editor after creation.")
@click.option("--empty", is_flag=True, help="Create an empty template (ignores --from).")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompts.")
def create_template(name: str, base_template: Optional[str] = None, editor: Optional[str] = None, open_editor: bool = False, empty: bool = False, yes: bool = False):
    """
    Create a new template with the given NAME.
    
    Examples:
        templates-manage create project
        templates-manage create research --from meeting
    """
    try:
        template_manager = TemplateManager()
        
        # Check if the name is valid
        if not name or not name.isalnum() and not name.replace('_', '').isalnum():
            console.print("[bold red]Error:[/bold red] Template name must be alphanumeric (underscores allowed)")
            return 1
            
        if not yes:
            if empty:
                confirm_message = f"Create a new empty template '{name}'?"
            elif base_template:
                confirm_message = f"Create a new template '{name}' based on '{base_template}'?"
            else:
                confirm_message = f"Create a new template '{name}' with default content?"
                
            if not click.confirm(confirm_message):
                console.print("[yellow]Template creation cancelled.[/yellow]")
                return 0
        
        # Create the template
        content = "" if empty else None
        template_path = template_manager.create_template(name, content, base_template)
        
        console.print(f"[green]Template '{name}' created successfully.[/green]")
        
        # Open in editor if requested
        if editor or open_editor:
            editor_handlers = get_editor_handlers()
            if editor_handlers:
                try:
                    editor_handlers.edit_file(template_path, editor)
                    console.print("[green]Template opened in editor.[/green]")
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not open template in editor: {str(e)}[/yellow]")
        return 0
        
    except FileExistsError:
        console.print(f"[bold red]Error:[/bold red] Template '{name}' already exists")
        return 1
    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return 1
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return 1
    except Exception as e:
        console.print(f"[bold red]Error creating template:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

@template_commands.command(name="edit")
@click.argument("name")
@click.option("--output", "-o", help="Save to a file instead of opening in editor.")
@click.option("--editor", "-e", help="Specify which editor to use for editing the template.")
def edit_template(name: str, output: Optional[str], editor: Optional[str] = None):
    """
    Edit an existing template with NAME.
    """
    try:
        template_manager = TemplateManager()
        
        # Check if template exists
        template_path = os.path.join(template_manager.templates_dir, name, "template.md")
        if not os.path.exists(template_path):
            console.print(f"[bold red]Error:[/bold red] Template '{name}' not found")
            return 1
            
        # Read template content
        with open(template_path, 'r') as f:
            template_content = f.read()
            
        # Either save to file or open in editor
        if output:
            with open(output, 'w') as f:
                f.write(template_content)
            console.print(f"[green]Template '{name}' saved to {output}.[/green]")
        else:
            editor_handlers = get_editor_handlers()
            if editor_handlers:
                try:
                    editor_handlers.edit_file(template_path)
                    console.print(f"[green]Template '{name}' edited successfully.[/green]")
                except Exception as e:
                    console.print(f"[bold red]Error:[/bold red] Could not open template in editor: {str(e)}")
                    return 1
            else:
                console.print("[bold red]Error:[/bold red] No editor available")
                return 1
                
        return 0
        
    except Exception as e:
        console.print(f"[bold red]Error editing template:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

@template_commands.command(name="show")
@click.argument("name")
@click.option("--raw/--formatted", default=False, help="Show raw template or with formatting.")
def show_template(name: str, raw: bool):
    """
    Show the content of a template with NAME.
    """
    try:
        template_manager = TemplateManager()
        
        # Check if template exists
        template_path = os.path.join(template_manager.templates_dir, name, "template.md")
        if not os.path.exists(template_path):
            console.print(f"[bold red]Error:[/bold red] Template '{name}' not found")
            return 1
            
        # Read template content
        with open(template_path, 'r') as f:
            template_content = f.read()
            
        # Display template content
        if raw:
            console.print(template_content)
        else:
            console.print(Panel(Markdown(template_content), 
                            title=f"Template: {name}",
                            border_style="cyan"))
            
        return 0
        
    except Exception as e:
        console.print(f"[bold red]Error showing template:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

@template_commands.command(name="delete")
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
def delete_template(name: str, yes: bool):
    """
    Delete a template with NAME.
    
    Built-in templates cannot be deleted.
    """
    try:
        template_manager = TemplateManager()
        
        if not yes:
            if not click.confirm(f"Are you sure you want to delete template '{name}'?"):
                console.print("[yellow]Template deletion cancelled.[/yellow]")
                return 0
            
        try:
            template_manager.delete_template(name)
            console.print(f"[green]Template '{name}' deleted successfully.[/green]")
        except ValueError as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            return 1
        except FileNotFoundError:
            console.print(f"[bold red]Error:[/bold red] Template '{name}' not found")
            return 1
            
        return 0
        
    except Exception as e:
        console.print(f"[bold red]Error deleting template:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

@template_commands.command(name="copy")
@click.argument("source")
@click.argument("destination")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
def copy_template(source: str, destination: str, yes: bool):
    """
    Copy a template from SOURCE to DESTINATION.
    """
    try:
        template_manager = TemplateManager()
        
        # Check if source template exists
        source_path = os.path.join(template_manager.templates_dir, source, "template.md")
        if not os.path.exists(source_path):
            console.print(f"[bold red]Error:[/bold red] Source template '{source}' not found")
            return 1
            
        # Read source template
        with open(source_path, 'r') as f:
            content = f.read()
            
        # Confirm copy
        if not yes:
            if not click.confirm(f"Copy template '{source}' to '{destination}'?"):
                console.print("[yellow]Template copy cancelled.[/yellow]")
                return 0
        
        try:
            # Create destination template with source content
            template_path = template_manager.create_template(destination, content)
            
            # Update the type field in the new template
            with open(template_path, 'r') as f:
                updated_content = f.read()
                
            updated_content = updated_content.replace(f"type: {source}", f"type: {destination}")
            
            with open(template_path, 'w') as f:
                f.write(updated_content)
                
            console.print(f"[green]Template copied from '{source}' to '{destination}'.[/green]")
            
        except FileExistsError:
            console.print(f"[bold red]Error:[/bold red] Destination template '{destination}' already exists")
            return 1
        except ValueError as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            return 1
            
        return 0
        
    except Exception as e:
        console.print(f"[bold red]Error copying template:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

@template_commands.command(name="list")
@click.option("--details", "-d", is_flag=True, help="Show more details about templates.")
def list_templates(details: bool):
    """
    List all available templates.
    """
    try:
        template_manager = TemplateManager()
        templates = template_manager.list_templates()
        
        if not templates:
            console.print("[yellow]No templates found.[/yellow]")
            return 0
            
        # Sort templates: built-in first, then alphabetically
        builtin_templates = ["default", "daily", "meeting", "journal"]
        builtin = [t for t in templates if t in builtin_templates]
        custom = [t for t in templates if t not in builtin_templates]
        
        sorted_builtin = sorted(builtin, key=lambda x: builtin_templates.index(x))
        sorted_custom = sorted(custom)
        
        sorted_templates = sorted_builtin + sorted_custom
        
        # Display templates
        if details:
            table = Table(title="Available Note Templates")
            table.add_column("Name", style="cyan")
            table.add_column("Type", style="magenta")
            table.add_column("Size", style="blue")
            
            for template in sorted_templates:
                template_path = os.path.join(template_manager.templates_dir, template, "template.md")
                template_type = "Built-in" if template in builtin_templates else "Custom"
                template_size = os.path.getsize(template_path) if os.path.exists(template_path) else 0
                
                table.add_row(
                    template,
                    template_type,
                    f"{template_size} bytes"
                )
                
            console.print(table)
        else:
            console.print("[bold blue]Available templates:[/bold blue]")
            for template in sorted_builtin:
                console.print(f"- [cyan]{template}[/cyan] [dim](built-in)[/dim]")
                
            if sorted_custom:
                console.print("\n[bold blue]Custom templates:[/bold blue]")
                for template in sorted_custom:
                    console.print(f"- [green]{template}[/green]")
            
        return 0
        
    except Exception as e:
        console.print(f"[bold red]Error listing templates:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


@archive_commands.command(name="auto-date")
@click.argument("date")
@click.option("--field", "-f", default="created_at",
              help="The date field to compare ('created_at', 'updated_at', or a custom field).")
@click.option("--before/--after", default=True,
              help="Archive notes created before the date (--before) or after the date (--after).")
@click.option("--reason", "-r", default="Auto-archived by date",
              help="Reason for archiving the notes.")
@click.option("--move/--no-move", "-m/-n", default=True,
              help="Move notes to a dedicated archive directory.")
@click.option("--dry-run", is_flag=True, help="Show what would be archived without archiving.")
def auto_archive_by_date(date: str, field: str, before: bool, reason: str, move: bool, dry_run: bool):
    """
    Auto-archive notes based on a specific date.
    
    DATE should be in ISO format (YYYY-MM-DD).
    
    Examples:
      archive auto-date 2023-01-01            # Archive notes created before Jan 1, 2023
      archive auto-date 2023-06-15 --after    # Archive notes created after June 15, 2023
      archive auto-date 2023-03-01 --field updated_at  # Archive notes updated before Mar 1, 2023
    """
    try:
        # Validate the date format
        try:
            if "T" in date:
                # Handle full ISO format with time
                archive_date = datetime.fromisoformat(date)
            else:
                # Handle date-only format
                archive_date = datetime.fromisoformat(f"{date}T00:00:00")
        except ValueError:
            console.print(f"[bold red]Error:[/bold red] Invalid date format. Use YYYY-MM-DD or ISO format.")
            return 1
            
        # Show what we're going to do
        date_comparison = "before" if before else "after"
        console.print(f"Finding notes with {field} {date_comparison} [cyan]{date}[/cyan]...")
        
        # Create archive-enabled note manager
        note_manager = ArchiveNoteManager()
        
        if dry_run:
            # Find notes that would be archived without actually archiving
            console.print(f"[yellow]DRY RUN[/yellow]: Notes will not actually be archived.")
            
            # Get all notes that match the criteria
            all_notes = note_manager.list_notes()
            to_archive = []
            
            for note in all_notes:
                # Skip already archived notes
                if hasattr(note, 'is_archived') and note.is_archived:
                    continue
                    
                # Get the date field value
                date_value = None
                if field in note.metadata:
                    try:
                        # Try to parse the date from metadata
                        if isinstance(note.metadata[field], str):
                            date_value = datetime.fromisoformat(note.metadata[field])
                        elif isinstance(note.metadata[field], datetime):
                            date_value = note.metadata[field]
                        else:
                            date_value = datetime.fromisoformat(str(note.metadata[field]))
                    except (ValueError, TypeError):
                        console.print(f"[yellow]Warning:[/yellow] Could not parse date field '{field}' for note '{note.title}'")
                        continue
                elif hasattr(note, field):
                    # If it's a direct attribute of the note
                    date_value = getattr(note, field)
                    
                if date_value is None:
                    continue
                    
                # Check if we should archive based on the date comparison
                should_archive = False
                if before and date_value < archive_date:
                    should_archive = True
                elif not before and date_value > archive_date:
                    should_archive = True
                    
                if should_archive:
                    to_archive.append(note)
                    
            # Display the notes that would be archived
            if to_archive:
                console.print(f"\nWould archive [cyan]{len(to_archive)}[/cyan] notes:")
                for note in to_archive:
                    date_value = None
                    if field in note.metadata:
                        date_value = note.metadata[field]
                    elif hasattr(note, field):
                        date_value = getattr(note, field)
                        if isinstance(date_value, datetime):
                            date_value = date_value.isoformat()
                    
                    console.print(f"  - [yellow]{note.title}[/yellow] ({field}: {date_value})")
            else:
                console.print("\n[green]No notes found that would be archived.[/green]")
        else:
            # Actually archive the notes
            console.print("Archiving notes...")
            
            results = note_manager.auto_archive_by_date(
                date,
                field=field,
                before_date=before,
                reason=reason,
                move_to_archive_dir=move
            )
            
            # Display results
            archived_count = sum(1 for msg in results.values() if "archived successfully" in msg)
            
            if archived_count > 0:
                console.print(f"\n[green]Successfully archived {archived_count} notes.[/green]")
                
                # Show details
                table = Table(show_header=True, header_style="bold cyan")
                table.add_column("Note Path")
                table.add_column("Status")
                
                for path, message in results.items():
                    status_color = "green" if "archived successfully" in message else "red" 
                    table.add_row(path, f"[{status_color}]{message}[/{status_color}]")
                
                console.print(table)
            else:
                console.print("\n[yellow]No notes were archived.[/yellow]")
                
                if results:
                    console.print("\nDetails:")
                    for path, message in results.items():
                        console.print(f"  - {path}: {message}")
        
        return 0
            
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
def register_merge_commands(cli_group):
    """Register note merge commands to the CLI group."""
    
    @cli_group.command(name="merge")
    @click.argument("source_note_title", type=str)
    @click.argument("target_note_title", type=str)
    @click.option("--new-title", "-n", type=str, required=False, help="Title for the merged note. Default is target note title.")
    @click.option("--source-category", "-sc", type=str, required=False, help="Category of the source note.")
    @click.option("--target-category", "-tc", type=str, required=False, help="Category of the target note.")
    @click.option("--output-dir", "-o", type=str, required=False, help="Directory to look for the notes.")
    @click.option("--no-merge-metadata", is_flag=True, help="Do not merge metadata (tags, links, etc.).")
    @click.option("--separator", "-s", type=str, default="\n\n---\n\n", help="Content separator between the merged notes.")
    @click.option("--keep-originals", "-k", is_flag=True, help="Keep original notes after merging.")
    @click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt.")
    @click.option("--show", is_flag=True, help="Show the merged note after creation.")
    def merge_notes(source_note_title, target_note_title, new_title, source_category, target_category,
                   output_dir, no_merge_metadata, separator, keep_originals, force, show):
        """
        Merge two notes into one.
        
        This command combines the content and optionally the metadata of two notes.
        By default, the merged note will have the title of the target note unless 
        a new title is specified. The original notes are deleted by default unless 
        the --keep-originals flag is used.
        
        Example usage:
        
        \b
        # Basic merge
        marknote merge "Note1" "Note2"
        
        \b
        # Merge with a new title
        marknote merge "Note1" "Note2" --new-title "Combined Note"
        
        \b
        # Keep the original notes
        marknote merge "Note1" "Note2" --keep-originals
        
        \b
        # Don't merge metadata (tags, links, etc.)
        marknote merge "Note1" "Note2" --no-merge-metadata
        """
        console = Console()
        from app.core.note_manager import NoteManager
        
        # Initialize the NoteManager
        note_manager = NoteManager(output_dir)
        
        # Check if both notes exist
        source_note = note_manager.get_note(source_note_title, source_category, output_dir)
        target_note = note_manager.get_note(target_note_title, target_category, output_dir)
        
        if not source_note:
            console.print(f"[bold red]Error:[/] Source note '{source_note_title}' not found.")
            return 1
        
        if not target_note:
            console.print(f"[bold red]Error:[/] Target note '{target_note_title}' not found.")
            return 1
            
        # Display information about what will happen
        final_title = new_title if new_title else target_note_title
        console.print(f"[bold]Merge Operation:[/]")
        console.print(f"  Source Note: [cyan]{source_note_title}[/]")
        console.print(f"  Target Note: [cyan]{target_note_title}[/]")
        console.print(f"  Merged Title: [green]{final_title}[/]")
        console.print(f"  Keep Originals: [{'green' if keep_originals else 'red'}]{keep_originals}[/]")
        console.print(f"  Merge Metadata: [{'green' if not no_merge_metadata else 'red'}]{not no_merge_metadata}[/]")
        
        # Confirmation prompt
        if not force:
            if final_title != target_note_title and final_title != source_note_title and not keep_originals:
                console.print("\n[yellow]Warning:[/] Both original notes will be deleted after merging.")
                
            proceed = click.confirm("Do you want to continue with the merge?", default=True)
            if not proceed:
                console.print("Merge operation cancelled.")
                return 0
        
        # Perform the merge
        success, message, merged_note = note_manager.merge_notes(
            source_note_title=source_note_title,
            target_note_title=target_note_title,
            new_title=new_title,
            source_category=source_category,
            target_category=target_category,
            output_dir=output_dir,
            merge_metadata=not no_merge_metadata,
            content_separator=separator,
            keep_original_notes=keep_originals
        )
        
        if success:
            console.print(f"[bold green]Success:[/] {message}")
            
            # Show the merged note if requested
            if show and merged_note:
                console.print("\n[bold]Merged Note Content:[/]")
                console.print(Panel(
                    Markdown(merged_note.content),
                    title=merged_note.title,
                    expand=False
                ))
                
                if not no_merge_metadata:
                    console.print("\n[bold]Merged Metadata:[/]")
                    console.print(f"  Tags: {', '.join(merged_note.tags) if merged_note.tags else 'None'}")
                    console.print(f"  Links: {', '.join(merged_note.get_links()) if merged_note.get_links() else 'None'}")
            
            return 0
        else:
            console.print(f"[bold red]Error:[/] {message}")
            return 1


def register_backup_commands(cli_group):
    """
    Register backup and restore commands to the CLI.
    """
    # Create backup command group
    @cli_group.group(name="backup")
    def backup_group():
        """
        Backup and restore your notes.
        """
        pass
    
    @backup_group.command(name="create")
    @click.option("--name", "-n", help="Optional name for the backup file (will be suffixed with .zip if needed).")
    @click.option("--category", "-c", help="Only backup notes in this category.")
    @click.option("--tags", "-t", multiple=True, help="Only backup notes with these tags (can be used multiple times).")
    @click.option("--no-versions", is_flag=True, help="Don't include version history in the backup.")
    @click.option("--include-archived", is_flag=True, help="Include archived notes in the backup.")
    @click.option("--backup-dir", "-d", help="Custom directory to store the backup file.")
    @click.option("--output-format", "-f", type=click.Choice(["text", "json"]), default="text", help="Output format.")
    def create_backup(name, category, tags, no_versions, include_archived, backup_dir, output_format):
        """
        Create a backup of your notes.
        
        This command creates a zip archive containing your notes, optionally
        filtered by category or tags. By default, version history is included
        but archived notes are not.
        
        Examples:
        
        \b
        # Create a backup of all notes
        marknote backup create
        
        \b
        # Create a backup with a custom name
        marknote backup create --name my_project_backup
        
        \b
        # Backup only notes with specific tags
        marknote backup create --tags work --tags important
        
        \b
        # Backup only notes in a specific category without version history
        marknote backup create --category projects --no-versions
        """
        from app.core.backup_manager import BackupManager
        from app.core.note_manager import NoteManager
        
        console = Console()
        
        # Initialize managers
        note_manager = NoteManager()
        backup_manager = BackupManager(notes_dir=note_manager.notes_dir, backup_dir=backup_dir)
        
        # Create user metadata
        metadata = {
            "created_by_command": "marknote backup create",
            "command_options": {
                "name": name,
                "category": category,
                "tags": list(tags) if tags else None,
                "no_versions": no_versions,
                "include_archived": include_archived,
                "backup_dir": backup_dir
            }
        }
        
        # Show what we're going to do
        if output_format == "text":
            console.print("[bold]Creating backup with the following settings:[/]")
            console.print(f"  Notes Directory: [cyan]{note_manager.notes_dir}[/]")
            console.print(f"  Backup Directory: [cyan]{backup_manager.backup_dir}[/]")
            if name:
                console.print(f"  Backup Name: [cyan]{name}[/]")
            if category:
                console.print(f"  Filtering by Category: [cyan]{category}[/]")
            if tags:
                console.print(f"  Filtering by Tags: [cyan]{', '.join(tags)}[/]")
            console.print(f"  Including Version History: [cyan]{'No' if no_versions else 'Yes'}[/]")
            console.print(f"  Including Archived Notes: [cyan]{'Yes' if include_archived else 'No'}[/]")
            
            console.print("\nCreating backup...", style="bold")
        
        # Create the backup with progress display
        with Progress(transient=True) as progress:
            if output_format == "text":
                task = progress.add_task("Creating backup...", total=None)
            
            # Perform backup operation
            success, message, backup_path = backup_manager.create_backup(
                backup_name=name,
                category=category,
                tags=list(tags) if tags else None,
                include_versions=not no_versions,
                include_archived=include_archived,
                metadata=metadata
            )
            
            if output_format == "text":
                progress.update(task, completed=True)
        
        # Display results
        if output_format == "text":
            if success:
                console.print(f"[bold green]Success:[/] {message}")
                if backup_path:
                    size_mb = os.path.getsize(backup_path) / (1024 * 1024)
                    console.print(f"Backup size: [cyan]{size_mb:.2f} MB[/]")
            else:
                console.print(f"[bold red]Error:[/] {message}")
        elif output_format == "json":
            result = {
                "success": success,
                "message": message,
                "backup_path": backup_path
            }
            if backup_path and os.path.exists(backup_path):
                result["backup_size"] = os.path.getsize(backup_path)
            
            click.echo(json.dumps(result, indent=2))
        
        return 0 if success else 1
    
    @backup_group.command(name="list")
    @click.option("--limit", "-l", type=int, default=None, help="Limit the number of backups to show.")
    @click.option("--backup-dir", "-d", help="Custom directory to look for backups.")
    @click.option("--output-format", "-f", type=click.Choice(["text", "json"]), default="text", help="Output format.")
    def list_backups(limit, backup_dir, output_format):
        """
        List available backups.
        
        Displays a list of all available backups with details such as creation date,
        size, and included note count.
        
        Examples:
        
        \b
        # List all backups
        marknote backup list
        
        \b
        # List only the 5 most recent backups
        marknote backup list --limit 5
        
        \b
        # List backups from a specific directory in JSON format
        marknote backup list --backup-dir /path/to/backups --output-format json
        """
        from app.core.backup_manager import BackupManager
        from app.core.note_manager import NoteManager
        
        console = Console()
        
        # Initialize managers
        note_manager = NoteManager()
        backup_manager = BackupManager(notes_dir=note_manager.notes_dir, backup_dir=backup_dir)
        
        # Get list of backups
        backups = backup_manager.list_backups()
        
        # Apply limit if specified
        if limit is not None and limit > 0:
            backups = backups[:limit]
            
        # Display results
        if output_format == "text":
            if not backups:
                console.print("[italic]No backups found.[/]")
                return 0
                
            table = Table(title="Available Backups")
            table.add_column("Filename", style="cyan")
            table.add_column("Created", style="green")
            table.add_column("Size", style="magenta", justify="right")
            table.add_column("Notes", justify="right")
            
            for backup in backups:
                filename = backup["filename"]
                
                # Format created date
                created_date = datetime.fromtimestamp(backup["created_at"]).strftime("%Y-%m-%d %H:%M:%S")
                
                # Format size
                size_mb = backup["size"] / (1024 * 1024)
                size_str = f"{size_mb:.2f} MB"
                
                # Get note count from metadata if available
                note_count = "N/A"
                if "metadata" in backup and isinstance(backup["metadata"], dict):
                    if "included_notes" in backup["metadata"]:
                        note_count = str(backup["metadata"]["included_notes"])
                
                table.add_row(filename, created_date, size_str, note_count)
            
            console.print(table)
        elif output_format == "json":
            click.echo(json.dumps(backups, indent=2, default=str))
        
        return 0
    
    @backup_group.command(name="info")
    @click.argument("backup_name", type=str)
    @click.option("--backup-dir", "-d", help="Custom directory to look for backups.")
    @click.option("--output-format", "-f", type=click.Choice(["text", "json"]), default="text", help="Output format.")
    def backup_info(backup_name, backup_dir, output_format):
        """
        Show detailed information about a backup.
        
        Displays complete information about a specific backup, including
        its metadata, note count, and filtering criteria used during creation.
        
        Examples:
        
        \b
        # Show information about a specific backup
        marknote backup info marknote_backup_20230501_123045.zip
        
        \b
        # Show information in JSON format
        marknote backup info my_backup.zip --output-format json
        """
        from app.core.backup_manager import BackupManager
        from app.core.note_manager import NoteManager
        
        console = Console()
        
        # Initialize managers
        note_manager = NoteManager()
        backup_manager = BackupManager(notes_dir=note_manager.notes_dir, backup_dir=backup_dir)
        
        # Get backup info
        backup_info = backup_manager.get_backup_info(backup_name)
        
        if not backup_info:
            if output_format == "text":
                console.print(f"[bold red]Error:[/] Backup '{backup_name}' not found.")
            else:
                click.echo(json.dumps({"success": False, "error": f"Backup '{backup_name}' not found."}))
            return 1
            
        # Display results
        if output_format == "text":
            console.print(f"[bold]Backup Information: [cyan]{backup_info['filename']}[/][/]")
            
            # Create a panel for basic info
            basic_info = [
                f"Created: {datetime.fromtimestamp(backup_info['created_at']).strftime('%Y-%m-%d %H:%M:%S')}",
                f"Size: {backup_info['size'] / (1024 * 1024):.2f} MB",
                f"Notes: {backup_info.get('note_count', 'N/A')}",
                f"Version files: {backup_info.get('version_count', 'N/A')}",
                f"Archived notes: {backup_info.get('archive_count', 'N/A')}",
                f"Total files: {backup_info.get('all_files_count', 'N/A')}"
            ]
            
            console.print(Panel("\n".join(basic_info), title="Basic Information", expand=False))
            
            # Display metadata if available
            if "metadata" in backup_info and backup_info["metadata"]:
                metadata_table = Table(title="Backup Metadata")
                metadata_table.add_column("Property", style="cyan")
                metadata_table.add_column("Value")
                
                metadata = backup_info["metadata"]
                
                # Add key metadata fields
                for key, value in metadata.items():
                    if key != "included_note_files" and key != "user_metadata":  # Skip file list and user metadata for now
                        metadata_table.add_row(key, str(value))
                
                console.print(metadata_table)
                
                # Display user metadata in a separate panel if available
                if "user_metadata" in metadata:
                    user_metadata = metadata["user_metadata"]
                    console.print(Panel(str(json.dumps(user_metadata, indent=2)), 
                                      title="User Metadata", expand=False))
                
                # Show included note files if available
                if "included_note_files" in metadata and metadata["included_note_files"]:
                    file_count = len(metadata["included_note_files"])
                    if file_count <= 10:  # Only show all files if there are 10 or fewer
                        files_panel = Panel("\n".join(metadata["included_note_files"]),
                                         title=f"Included Notes ({file_count})", expand=False)
                    else:
                        # Show first 5 and indicate there are more
                        files_list = metadata["included_note_files"][:5]
                        files_list.append(f"... and {file_count - 5} more files")
                        files_panel = Panel("\n".join(files_list),
                                         title=f"Included Notes ({file_count})", expand=False)
                    
                    console.print(files_panel)
                    
            # Show any errors
            if "error" in backup_info:
                console.print(f"[bold red]Error:[/] {backup_info['error']}")
                
        elif output_format == "json":
            click.echo(json.dumps(backup_info, indent=2, default=str))
            
        return 0
    
    @backup_group.command(name="restore")
    @click.argument("backup_name", type=str)
    @click.option("--restore-dir", "-d", help="Directory to restore to. If not provided, restores to the default notes directory.")
    @click.option("--overwrite", "-o", is_flag=True, help="Overwrite existing files during restore.")
    @click.option("--no-versions", is_flag=True, help="Don't restore version history.")
    @click.option("--no-archives", is_flag=True, help="Don't restore archived notes.")
    @click.option("--backup-dir", help="Custom directory to look for backups.")
    @click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
    @click.option("--output-format", "-f", type=click.Choice(["text", "json"]), default="text", help="Output format.")
    def restore_backup(backup_name, restore_dir, overwrite, no_versions, no_archives, backup_dir, yes, output_format):
        """
        Restore notes from a backup.
        
        Extracts notes and optionally version history and archived notes from a backup file.
        By default, existing files are not overwritten, but this behavior can be changed
        with the --overwrite flag.
        
        Examples:
        
        \b
        # Restore from a backup (will prompt for confirmation)
        marknote backup restore marknote_backup_20230501_123045.zip
        
        \b
        # Restore to a specific directory, overwriting existing files
        marknote backup restore my_backup.zip --restore-dir ~/new_notes --overwrite
        
        \b
        # Restore only the notes, without version history or archives
        marknote backup restore my_backup.zip --no-versions --no-archives
        
        \b
        # Skip confirmation prompt
        marknote backup restore my_backup.zip --yes
        """
        from app.core.backup_manager import BackupManager
        from app.core.note_manager import NoteManager
        
        console = Console()
        
        # Initialize managers
        note_manager = NoteManager()
        backup_manager = BackupManager(notes_dir=note_manager.notes_dir, backup_dir=backup_dir)
        
        # Verify backup exists
        backup_info = backup_manager.get_backup_info(backup_name)
        if not backup_info:
            if output_format == "text":
                console.print(f"[bold red]Error:[/] Backup '{backup_name}' not found.")
            else:
                click.echo(json.dumps({"success": False, "error": f"Backup '{backup_name}' not found."}))
            return 1
            
        # Determine target directory
        target_dir = restore_dir if restore_dir else note_manager.notes_dir
        
        # Show what we're going to do
        if output_format == "text":
            console.print("[bold]Restore Operation:[/]")
            console.print(f"  Backup: [cyan]{backup_info['filename']}[/]")
            console.print(f"  Target Directory: [cyan]{target_dir}[/]")
            console.print(f"  Overwrite Existing Files: [cyan]{'Yes' if overwrite else 'No'}[/]")
            console.print(f"  Restore Version History: [cyan]{'No' if no_versions else 'Yes'}[/]")
            console.print(f"  Restore Archived Notes: [cyan]{'No' if no_archives else 'Yes'}[/]")
            
            # Show warning if target directory exists and is not empty
            if os.path.exists(target_dir) and os.listdir(target_dir):
                console.print("\n[bold yellow]Warning:[/] Target directory exists and is not empty.")
                if not overwrite:
                    console.print("         Existing files will be kept (use --overwrite to replace them).")
                else:
                    console.print("[bold red]         Existing files will be overwritten![/]")
            
            # Confirm restoration
            if not yes:
                proceed = click.confirm("\nDo you want to proceed with the restore?", default=False)
                if not proceed:
                    console.print("Restore operation cancelled.")
                    return 0
            
            console.print("\nRestoring from backup...", style="bold")
        
        # Perform restore with progress display
        with Progress(transient=True) as progress:
            if output_format == "text":
                task = progress.add_task("Restoring from backup...", total=None)
            
            # Execute restore
            success, message, stats = backup_manager.restore_backup(
                backup_name=backup_name,
                restore_dir=target_dir,
                overwrite=overwrite,
                restore_versions=not no_versions,
                restore_archives=not no_archives
            )
            
            if output_format == "text":
                progress.update(task, completed=True)
        
        # Display results
        if output_format == "text":
            if success:
                console.print(f"[bold green]Success:[/] {message}")
                
                # Display stats in a table
                if stats:
                    table = Table(title="Restoration Statistics")
                    table.add_column("Item", style="cyan")
                    table.add_column("Count", justify="right")
                    
                    table.add_row("Notes Restored", str(stats.get("notes_restored", 0)))
                    table.add_row("Notes Skipped", str(stats.get("notes_skipped", 0)))
                    
                    if not no_versions:
                        table.add_row("Versions Restored", str(stats.get("versions_restored", 0)))
                        table.add_row("Versions Skipped", str(stats.get("versions_skipped", 0)))
                        
                    if not no_archives:
                        table.add_row("Archives Restored", str(stats.get("archives_restored", 0)))
                        table.add_row("Archives Skipped", str(stats.get("archives_skipped", 0)))
                    
                    console.print(table)
                    
                    # Show errors if any
                    if "errors" in stats and stats["errors"]:
                        console.print("[bold red]Errors during restore:[/]")
                        for error in stats["errors"][:10]:  # Limit to first 10 errors
                            console.print(f"  - {error}")
                        
                        if len(stats["errors"]) > 10:
                            console.print(f"  ... and {len(stats['errors']) - 10} more errors.")
            else:
                console.print(f"[bold red]Error:[/] {message}")
                
                # Show errors if available
                if stats and "errors" in stats and stats["errors"]:
                    console.print("[bold red]Details:[/]")
                    for error in stats["errors"][:5]:  # Limit to first 5 errors
                        console.print(f"  - {error}")
                        
                    if len(stats["errors"]) > 5:
                        console.print(f"  ... and {len(stats['errors']) - 5} more errors.")
        elif output_format == "json":
            result = {
                "success": success,
                "message": message,
                "stats": stats
            }
            click.echo(json.dumps(result, indent=2, default=str))
        
        return 0 if success else 1
    
    @backup_group.command(name="delete")
    @click.argument("backup_name", type=str)
    @click.option("--backup-dir", help="Custom directory to look for backups.")
    @click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
    @click.option("--output-format", "-f", type=click.Choice(["text", "json"]), default="text", help="Output format.")
    def delete_backup(backup_name, backup_dir, yes, output_format):
        """
        Delete a backup file.
        
        Permanently removes a backup file from the backups directory.
        
        Examples:
        
        \b
        # Delete a backup (will prompt for confirmation)
        marknote backup delete marknote_backup_20230501_123045.zip
        
        \b
        # Delete without confirmation
        marknote backup delete old_backup.zip --yes
        """
        from app.core.backup_manager import BackupManager
        from app.core.note_manager import NoteManager
        
        console = Console()
        
        # Initialize managers
        note_manager = NoteManager()
        backup_manager = BackupManager(notes_dir=note_manager.notes_dir, backup_dir=backup_dir)
        
        # Verify backup exists
        backup_info = backup_manager.get_backup_info(backup_name)
        if not backup_info:
            if output_format == "text":
                console.print(f"[bold red]Error:[/] Backup '{backup_name}' not found.")
            else:
                click.echo(json.dumps({"success": False, "error": f"Backup '{backup_name}' not found."}))
            return 1
            
        # Confirm deletion
        if not yes and output_format == "text":
            console.print(f"[bold]You are about to delete the backup:[/] [cyan]{backup_name}[/]")
            console.print("[bold red]This action cannot be undone![/]")
            
            proceed = click.confirm("Are you sure you want to proceed?", default=False)
            if not proceed:
                console.print("Delete operation cancelled.")
                return 0
        
        # Delete the backup
        success, message = backup_manager.delete_backup(backup_name)
        
        # Display results
        if output_format == "text":
            if success:
                console.print(f"[bold green]Success:[/] {message}")
            else:
                console.print(f"[bold red]Error:[/] {message}")
        elif output_format == "json":
            result = {
                "success": success,
                "message": message
            }
            click.echo(json.dumps(result, indent=2))
        
        return 0 if success else 1
    
def register_cleanup_commands(cli_group):
    """
    Register cleanup commands to the CLI.
    """
    # Create cleanup command group
    @cli_group.group(name="cleanup")
    def cleanup_group():
        """
        Clean up empty and duplicate notes.
        """
        pass
    
    @cleanup_group.command(name="empty")
    @click.option("--min-length", "-m", type=int, default=10, 
                 help="Minimum content length (in characters) to consider non-empty.")
    @click.option("--include-whitespace", "-w", is_flag=True, 
                 help="Count whitespace-only notes as empty.")
    @click.option("--delete", "-d", is_flag=True, 
                 help="Delete the empty notes (otherwise just lists them).")
    @click.option("--force", "-f", is_flag=True, 
                 help="Skip confirmation prompt when deleting.")
    @click.option("--output-dir", "-o", help="Directory to look for notes.")
    @click.option("--output-format", type=click.Choice(["text", "json"]), default="text",
                 help="Output format.")
    def find_empty_notes(min_length, include_whitespace, delete, force, output_dir, output_format):
        """
        Find and optionally delete empty or near-empty notes.
        
        This command identifies notes with no content or very little content and 
        provides options to delete them. By default, it only lists the empty notes
        without deleting them.
        
        Examples:
        
        \b
        # Find empty notes (just lists them)
        marknote cleanup empty
        
        \b
        # Find notes with less than 50 characters of content
        marknote cleanup empty --min-length 50
        
        \b
        # Delete empty notes (will prompt for confirmation)
        marknote cleanup empty --delete
        
        \b
        # Delete empty notes without confirmation
        marknote cleanup empty --delete --force
        """
        from app.core.cleanup_manager import CleanupManager
        from app.core.note_manager import NoteManager
        
        console = Console()
        
        # Initialize managers
        note_manager = NoteManager(output_dir)
        cleanup_manager = CleanupManager(note_manager)
        
        # Find empty notes
        if output_format == "text":
            with Progress(transient=True) as progress:
                task = progress.add_task("Finding empty notes...", total=None)
                empty_notes = cleanup_manager.find_empty_notes(
                    min_content_length=min_length,
                    include_whitespace_only=include_whitespace
                )
                progress.update(task, completed=True)
        else:
            empty_notes = cleanup_manager.find_empty_notes(
                min_content_length=min_length,
                include_whitespace_only=include_whitespace
            )
        
        # Display results
        if output_format == "text":
            if not empty_notes:
                console.print("[green]No empty notes found.[/]")
                return 0
                
            # Display empty notes
            console.print(f"[bold]Found {len(empty_notes)} empty notes (less than {min_length} characters):[/]")
            
            # Create a table
            table = Table()
            table.add_column("Title", style="cyan")
            table.add_column("Category", style="green")
            table.add_column("Size", style="magenta", justify="right")
            table.add_column("Has Metadata", justify="center")
            table.add_column("Has Tags", justify="center")
            table.add_column("Links", justify="right")
            
            for note in empty_notes:
                # Format size
                size_kb = note.size_bytes / 1024
                size_str = f"{size_kb:.1f} KB"
                
                table.add_row(
                    note.title,
                    note.category or "N/A",
                    size_str,
                    "✓" if note.has_metadata else "✗",
                    "✓" if note.has_tags else "✗",
                    str(note.link_count)
                )
            
            console.print(table)
            
            # Handle deletion if requested
            if delete:
                if not force:
                    proceed = click.confirm(f"Delete {len(empty_notes)} empty notes?", default=False)
                    if not proceed:
                        console.print("Deletion cancelled.")
                        return 0
                
                # Perform deletion
                console.print("\nDeleting empty notes...", style="bold")
                
                with Progress(transient=True) as progress:
                    task = progress.add_task("Deleting...", total=None)
                    count, deleted, errors = cleanup_manager.delete_empty_notes(
                        empty_notes=empty_notes,
                        dry_run=False
                    )
                    progress.update(task, completed=True)
                
                console.print(f"[bold green]Success:[/] Deleted {count} empty notes.")
                
                # Display errors if any
                if errors:
                    console.print("\n[bold red]Errors during deletion:[/]")
                    for error in errors:
                        console.print(f"  - {error}")
        
        elif output_format == "json":
            result = {
                "empty_notes_count": len(empty_notes),
                "min_length": min_length,
                "include_whitespace": include_whitespace,
                "empty_notes": [
                    {
                        "title": note.title,
                        "category": note.category,
                        "path": note.path,
                        "size_bytes": note.size_bytes,
                        "has_metadata": note.has_metadata,
                        "has_tags": note.has_tags,
                        "link_count": note.link_count
                    }
                    for note in empty_notes
                ]
            }
            
            # Add deletion results if applicable
            if delete:
                count, deleted, errors = cleanup_manager.delete_empty_notes(
                    empty_notes=empty_notes,
                    dry_run=False
                )
                
                result["deleted"] = {
                    "count": count,
                    "deleted_titles": deleted,
                    "errors": errors
                }
            
            click.echo(json.dumps(result, indent=2))
        
        return 0
    
    @cleanup_group.command(name="duplicates")
    @click.option("--similarity", "-s", type=float, default=0.9, 
                 help="Similarity threshold (0.0-1.0) for considering notes as duplicates.")
    @click.option("--content-only", "-c", is_flag=True, 
                 help="Compare only note content, not metadata.")
    @click.option("--case-sensitive", is_flag=True, 
                 help="Make comparison case-sensitive.")
    @click.option("--delete", "-d", is_flag=True, 
                 help="Delete duplicate notes (otherwise just lists them).")
    @click.option("--keep", "-k", type=click.Choice(["newest", "oldest", "longest", "shortest"]), 
                 default="newest", help="Which note to keep when deleting duplicates.")
    @click.option("--show-content", is_flag=True, 
                 help="Show note content in the results.")
    @click.option("--force", "-f", is_flag=True, 
                 help="Skip confirmation prompt when deleting.")
    @click.option("--output-dir", "-o", help="Directory to look for notes.")
    @click.option("--output-format", type=click.Choice(["text", "json"]), default="text",
                 help="Output format.")
    def find_duplicate_notes(similarity, content_only, case_sensitive, delete, keep, 
                            show_content, force, output_dir, output_format):
        """
        Find and optionally delete duplicate notes.
        
        This command identifies notes with identical or similar content and
        provides options to delete duplicates, keeping one note from each group.
        By default, it only lists the duplicates without deleting them.
        
        Examples:
        
        \b
        # Find duplicate notes (just lists them)
        marknote cleanup duplicates
        
        \b
        # Find notes with at least 80% similar content
        marknote cleanup duplicates --similarity 0.8
        
        \b
        # Delete duplicates, keeping the oldest version of each note
        marknote cleanup duplicates --delete --keep oldest
        
        \b
        # Compare only note content, ignoring metadata
        marknote cleanup duplicates --content-only
        
        \b
        # Show the content of found duplicates
        marknote cleanup duplicates --show-content
        """
        from app.core.cleanup_manager import CleanupManager
        from app.core.note_manager import NoteManager
        
        console = Console()
        
        # Initialize managers
        note_manager = NoteManager(output_dir)
        cleanup_manager = CleanupManager(note_manager)
        
        # Find duplicate notes
        if output_format == "text":
            console.print(f"Finding duplicate notes (similarity threshold: {similarity:.0%})...")
            
            with Progress(transient=True) as progress:
                task = progress.add_task("Searching...", total=None)
                duplicate_groups = cleanup_manager.find_duplicate_notes(
                    similarity_threshold=similarity,
                    compare_content_only=content_only,
                    ignore_case=not case_sensitive
                )
                progress.update(task, completed=True)
        else:
            duplicate_groups = cleanup_manager.find_duplicate_notes(
                similarity_threshold=similarity,
                compare_content_only=content_only,
                ignore_case=not case_sensitive
            )
        
        # Display results
        if output_format == "text":
            if not duplicate_groups:
                console.print("[green]No duplicate notes found.[/]")
                return 0
                
            # Count total duplicates
            total_notes = sum(len(group.notes) for group in duplicate_groups)
            unique_groups = len(duplicate_groups)
            duplicate_count = total_notes - unique_groups  # one note per group is not a duplicate
            
            console.print(f"[bold]Found {duplicate_count} duplicate notes in {unique_groups} groups:[/]")
            
            # Display each group
            for i, group in enumerate(duplicate_groups, 1):
                # Sort notes by title for consistent display
                notes = sorted(group.notes, key=lambda n: n.title)
                
                console.print(f"\n[bold cyan]Group {i}[/] ([bold]{len(notes)}[/] notes, "
                            f"[bold]{group.similarity:.0%}[/] similarity)")
                
                # Create a table for this group
                table = Table()
                table.add_column("Title", style="cyan")
                table.add_column("Category", style="green")
                table.add_column("Last Updated", style="yellow")
                table.add_column("Created", style="blue")
                table.add_column("Size", style="magenta", justify="right")
                
                # Add a note about which would be kept
                if keep == "newest":
                    keep_note = max(notes, key=lambda n: n.updated_at)
                    keep_message = "newest update date"
                elif keep == "oldest":
                    keep_note = min(notes, key=lambda n: n.created_at)
                    keep_message = "oldest creation date"
                elif keep == "longest":
                    keep_note = max(notes, key=lambda n: len(n.content))
                    keep_message = "longest content"
                elif keep == "shortest":
                    keep_note = min(notes, key=lambda n: len(n.content))
                    keep_message = "shortest content"
                else:
                    keep_note = notes[0]  # Fallback
                    keep_message = "default strategy"
                
                for note in notes:
                    # Format dates
                    updated = note.updated_at.strftime("%Y-%m-%d %H:%M")
                    created = note.created_at.strftime("%Y-%m-%d %H:%M")
                    
                    # Format content size
                    size_kb = len(note.content) / 1024
                    size_str = f"{size_kb:.1f} KB"
                    
                    # Mark the note that would be kept
                    title = note.title
                    if note.title == keep_note.title and note.category == keep_note.category:
                        title = f"{title} [green](would keep)[/]"
                    
                    table.add_row(
                        title,
                        note.category or "N/A",
                        updated,
                        created,
                        size_str
                    )
                
                console.print(table)
                console.print(f"[italic]Note: Using '{keep}' strategy ({keep_message}), "
                            f"the note '{keep_note.title}' would be kept.[/]")
                
                # Show content if requested
                if show_content and notes:
                    # Just show the content of the first note in the group
                    sample_note = notes[0]
                    preview_content = sample_note.content[:500] + "..." if len(sample_note.content) > 500 else sample_note.content
                    
                    console.print(Panel(
                        Markdown(preview_content),
                        title=f"Content Sample ({sample_note.title})",
                        expand=False
                    ))
            
            # Handle deletion if requested
            if delete:
                if not force:
                    proceed = click.confirm(
                        f"Delete {duplicate_count} duplicate notes, keeping one note from each group using '{keep}' strategy?", 
                        default=False
                    )
                    if not proceed:
                        console.print("Deletion cancelled.")
                        return 0
                
                # Perform deletion
                console.print("\nDeleting duplicate notes...", style="bold")
                
                with Progress(transient=True) as progress:
                    task = progress.add_task("Deleting...", total=None)
                    count, deleted, errors = cleanup_manager.delete_duplicate_notes(
                        duplicate_groups=duplicate_groups,
                        keep_strategy=keep,
                        dry_run=False
                    )
                    progress.update(task, completed=True)
                
                console.print(f"[bold green]Success:[/] Deleted {count} duplicate notes, kept {unique_groups} unique notes.")
                
                # Display errors if any
                if errors:
                    console.print("\n[bold red]Errors during deletion:[/]")
                    for error in errors:
                        console.print(f"  - {error}")
        
        elif output_format == "json":
            # Extract information about duplicate groups
            groups_data = []
            for i, group in enumerate(duplicate_groups, 1):
                group_data = {
                    "group_id": i,
                    "note_count": len(group.notes),
                    "similarity": group.similarity,
                    "notes": [
                        {
                            "title": note.title,
                            "category": note.category,
                            "updated_at": note.updated_at.isoformat(),
                            "created_at": note.created_at.isoformat(),
                            "content_length": len(note.content),
                            "tags": note.tags
                        }
                        for note in group.notes
                    ]
                }
                
                # Determine which note would be kept
                notes = group.notes
                if keep == "newest":
                    keep_note = max(notes, key=lambda n: n.updated_at)
                elif keep == "oldest":
                    keep_note = min(notes, key=lambda n: n.created_at)
                elif keep == "longest":
                    keep_note = max(notes, key=lambda n: len(n.content))
                elif keep == "shortest":
                    keep_note = min(notes, key=lambda n: len(n.content))
                else:
                    keep_note = notes[0]  # Fallback
                
                group_data["keep_strategy"] = keep
                group_data["keep_note"] = {
                    "title": keep_note.title,
                    "category": keep_note.category
                }
                
                groups_data.append(group_data)
            
            # Build result object
            result = {
                "total_groups": len(duplicate_groups),
                "total_notes": sum(len(group.notes) for group in duplicate_groups),
                "duplicate_notes": sum(len(group.notes) for group in duplicate_groups) - len(duplicate_groups),
                "similarity_threshold": similarity,
                "compare_content_only": content_only,
                "case_sensitive": case_sensitive,
                "groups": groups_data
            }
            
            # Add deletion results if applicable
            if delete:
                count, deleted, errors = cleanup_manager.delete_duplicate_notes(
                    duplicate_groups=duplicate_groups,
                    keep_strategy=keep,
                    dry_run=False
                )
                
                result["deleted"] = {
                    "count": count,
                    "deleted_titles": deleted,
                    "errors": errors
                }
            
            click.echo(json.dumps(result, indent=2, default=str))
        
        return 0
    
    @cleanup_group.command(name="scan")
    @click.option("--output-dir", "-o", help="Directory to look for notes.")
    @click.option("--min-length", "-m", type=int, default=10, 
                 help="Minimum content length for empty note detection.")
    @click.option("--similarity", "-s", type=float, default=0.9, 
                 help="Similarity threshold for duplicate detection.")
    @click.option("--dry-run", "-n", is_flag=True, 
                 help="Only simulate cleaning, don't actually delete notes.")
    @click.option("--force", "-f", is_flag=True, 
                 help="Skip confirmation prompt.")
    def scan_and_clean(output_dir, min_length, similarity, dry_run, force):
        """
        Scan for and clean both empty and duplicate notes.
        
        This is a convenience command that runs both empty and duplicate
        detection and provides a summary report. By default, it only
        reports issues without making changes.
        
        Examples:
        
        \b
        # Scan for issues without cleaning
        marknote cleanup scan
        
        \b
        # Scan and clean with lower thresholds
        marknote cleanup scan --min-length 5 --similarity 0.8
        
        \b
        # Clean without confirmation (actually deletes notes)
        marknote cleanup scan --dry-run --force
        """
        from app.core.cleanup_manager import CleanupManager
        from app.core.note_manager import NoteManager
        
        console = Console()
        
        # Initialize managers
        note_manager = NoteManager(output_dir)
        cleanup_manager = CleanupManager(note_manager)
        
        console.print("[bold]Scanning notes for issues...[/]")
        
        # Find empty notes
        with Progress(transient=True) as progress:
            task = progress.add_task("Finding empty notes...", total=None)
            empty_notes = cleanup_manager.find_empty_notes(
                min_content_length=min_length,
                include_whitespace_only=True
            )
            progress.update(task, completed=True)
        
        # Find duplicate notes
        with Progress(transient=True) as progress:
            task = progress.add_task("Finding duplicate notes...", total=None)
            duplicate_groups = cleanup_manager.find_duplicate_notes(
                similarity_threshold=similarity
            )
            progress.update(task, completed=True)
        
        # Count duplicate notes
        duplicate_count = sum(len(group.notes) - 1 for group in duplicate_groups)
        
        # Display summary
        console.print("\n[bold]Scan Results:[/]")
        console.print(f"  Empty notes: [cyan]{len(empty_notes)}[/]")
        console.print(f"  Duplicate notes: [cyan]{duplicate_count}[/] (in {len(duplicate_groups)} groups)")
        console.print(f"  Total issues: [bold red]{len(empty_notes) + duplicate_count}[/]")
        
        # Detail sections
        if empty_notes:
            console.print("\n[bold]Empty Notes:[/]")
            for i, note in enumerate(empty_notes[:5], 1):  # Show only first 5
                console.print(f"  {i}. [cyan]{note.title}[/] ({note.size_bytes} bytes)")
            
            if len(empty_notes) > 5:
                console.print(f"  ... and {len(empty_notes) - 5} more")
        
        if duplicate_groups:
            console.print("\n[bold]Duplicate Groups:[/]")
            for i, group in enumerate(duplicate_groups[:3], 1):  # Show only first 3 groups
                note_titles = [note.title for note in group.notes]
                console.print(f"  {i}. [cyan]{len(note_titles)}[/] notes with [green]{group.similarity:.0%}[/] similarity")
                for j, title in enumerate(note_titles[:3], 1):
                    console.print(f"     {j}. {title}")
                if len(note_titles) > 3:
                    console.print(f"     ... and {len(note_titles) - 3} more notes")
            
            if len(duplicate_groups) > 3:
                console.print(f"  ... and {len(duplicate_groups) - 3} more groups")
        
        # Offer to clean up
        if (empty_notes or duplicate_groups) and not dry_run:
            if not force:
                cleanup = click.confirm("\nDo you want to clean up these issues?", default=False)
                if not cleanup:
                    console.print("Cleanup cancelled.")
                    return 0
            
            console.print("\n[bold]Cleaning up issues...[/]")
            
            # Delete empty notes
            if empty_notes:
                with Progress(transient=True) as progress:
                    task = progress.add_task("Deleting empty notes...", total=None)
                    empty_count, empty_deleted, empty_errors = cleanup_manager.delete_empty_notes(
                        empty_notes=empty_notes,
                        dry_run=False
                    )
                    progress.update(task, completed=True)
                
                console.print(f"[green]Deleted {empty_count} empty notes.[/]")
            
            # Delete duplicate notes
            if duplicate_groups:
                with Progress(transient=True) as progress:
                    task = progress.add_task("Deleting duplicate notes...", total=None)
                    dup_count, dup_deleted, dup_errors = cleanup_manager.delete_duplicate_notes(
                        duplicate_groups=duplicate_groups,
                        keep_strategy="newest",
                        dry_run=False
                    )
                    progress.update(task, completed=True)
                
                console.print(f"[green]Deleted {dup_count} duplicate notes.[/]")
            
            # Show any errors
            all_errors = (empty_errors if empty_notes else []) + (dup_errors if duplicate_groups else [])
            if all_errors:
                console.print("\n[bold red]Errors during cleanup:[/]")
                for error in all_errors[:10]:  # Show max 10 errors
                    console.print(f"  - {error}")
                
                if len(all_errors) > 10:
                    console.print(f"  ... and {len(all_errors) - 10} more errors")
        
        elif dry_run and (empty_notes or duplicate_groups):
            console.print("\n[yellow]Note:[/] This was a dry run. No notes were actually deleted.")
            console.print("To perform the actual cleanup, run the command without --dry-run option.")
        
        return 0
    
def register_wordfreq_commands(cli_group):
    """
    Register word frequency commands to the CLI.
    """
    @cli_group.command(name="wordfreq")
    @click.argument("title", type=str)
    @click.option("--category", "-c", help="Category of the note.")
    @click.option("--output-dir", "-o", help="Directory to look for the note.")
    @click.option("--min-length", "-m", type=int, default=3, help="Minimum word length to include.")
    @click.option("--max-words", "-n", type=int, default=50, help="Maximum number of words to display.")
    @click.option("--include-stopwords", is_flag=True, help="Include common stopwords in the analysis.")
    @click.option("--case-sensitive", is_flag=True, help="Make word matching case-sensitive.")
    @click.option("--visualization", "-v", is_flag=True, help="Show simple ASCII visualization of frequencies.")
    @click.option("--export", "-e", type=click.Choice(['json', 'csv']), help="Export results to JSON or CSV.")
    @click.option("--export-path", "-p", help="Path to export results to. If not provided, prints to stdout.")
    @click.option("--output-format", type=click.Choice(["text", "json"]), default="text", help="Output format.")
    def wordfreq(
        title, category, output_dir, min_length, max_words, include_stopwords, 
        case_sensitive, visualization, export, export_path, output_format
    ):
        """
        Analyze word frequency in a note.
        
        This command displays the most frequently used words in a note, 
        with options to filter by word length, exclude common words, 
        and export the results in various formats.
        
        Examples:
        
        \b
        # Basic analysis
        marknote wordfreq "My Note Title"
        
        \b
        # More detailed analysis with visualization
        marknote wordfreq "My Note Title" --min-length 4 --max-words 40 --visualization
        
        \b
        # Include common stopwords in the analysis
        marknote wordfreq "My Note Title" --include-stopwords
        
        \b
        # Export results to JSON
        marknote wordfreq "My Note Title" --export json --export-path ./word_frequencies.json
        """
        from app.core.note_manager import NoteManager
        from app.core.word_frequency_analyzer import WordFrequencyAnalyzer
        
        console = Console()
        
        # Initialize note manager
        note_manager = NoteManager(output_dir)
        
        # Get the note
        note = note_manager.get_note(title, category, output_dir)
        
        if not note:
            if output_format == "text":
                console.print(f"[bold red]Error:[/] Note '{title}' not found.")
            else:
                click.echo(json.dumps({
                    "success": False,
                    "error": f"Note '{title}' not found."
                }))
            return 1
        
        # Create analyzer
        stopwords = None if include_stopwords else None  # Use default stopwords unless explicitly including them
        analyzer = WordFrequencyAnalyzer(
            stopwords=stopwords,
            min_word_length=min_length,
            max_words=max_words,
            case_sensitive=case_sensitive
        )
        
        # Analyze word frequency
        if output_format == "text":
            with Progress(transient=True) as progress:
                task = progress.add_task("Analyzing word frequency...", total=None)
                word_frequencies = analyzer.analyze(note.content)
                report = analyzer.generate_report(note.content, include_stats=True)
                progress.update(task, completed=True)
        else:
            word_frequencies = analyzer.analyze(note.content)
            report = analyzer.generate_report(note.content, include_stats=True)
        
        # Handle different output formats
        if export:
            # Export to JSON
            if export == 'json':
                export_data = report
                export_str = json.dumps(export_data, indent=2)
                
            # Export to CSV
            elif export == 'csv':
                csv_buffer = StringIO()
                writer = csv.writer(csv_buffer)
                writer.writerow(['Word', 'Frequency'])
                for item in report['word_frequencies']:
                    writer.writerow([item['word'], item['count']])
                export_str = csv_buffer.getvalue()
                
            # Write to file or stdout
            if export_path:
                with open(export_path, 'w') as f:
                    f.write(export_str)
                if output_format == "text":
                    console.print(f"[bold green]Success:[/] Results exported to '{export_path}'")
            else:
                if output_format == "text":
                    console.print(export_str)
                else:
                    click.echo(export_str)
        
        # Display results in terminal
        elif output_format == "text":
            stats = report['statistics']
            
            # Print header
            console.print(f"[bold]Word Frequency Analysis for:[/] [cyan]{note.title}[/]")
            
            # Print statistics
            console.print(f"\n[bold]Statistics:[/]")
            console.print(f"  Total words: [cyan]{stats['total_words']}[/]")
            console.print(f"  Total unique words: [cyan]{stats['total_unique_words_all']}[/]")
            console.print(f"  Most frequent word: [cyan]{stats['most_frequent_word']}[/] "
                          f"([cyan]{stats['most_frequent_count']}[/] occurrences)")
            
            # Print frequency table
            console.print(f"\n[bold]Top {len(word_frequencies)} Words:[/]")
            
            # Create table
            table = Table()
            table.add_column("Rank", style="dim")
            table.add_column("Word", style="cyan")
            table.add_column("Count", justify="right")
            table.add_column("Percentage", justify="right")
            
            if visualization:
                table.add_column("Chart", justify="left")
            
            # Calculate percentages
            total_analyzed = sum(count for _, count in word_frequencies)
            
            # Add rows
            for i, (word, count) in enumerate(word_frequencies, 1):
                percentage = (count / total_analyzed) * 100
                
                row = [
                    str(i),
                    word,
                    str(count),
                    f"{percentage:.1f}%"
                ]
                
                # Add visualization
                if visualization:
                    # Scale the visualization to a max of 30 characters
                    max_bars = 30
                    max_count = word_frequencies[0][1] if word_frequencies else 1
                    bars = int((count / max_count) * max_bars)
                    bar_chart = "█" * bars
                    row.append(bar_chart)
                
                table.add_row(*row)
            
            console.print(table)
            
            # Analysis parameters
            console.print(f"\n[bold]Analysis Parameters:[/]")
            console.print(f"  Minimum word length: [cyan]{min_length}[/]")
            console.print(f"  Maximum words shown: [cyan]{max_words}[/]")
            console.print(f"  Case sensitive: [cyan]{case_sensitive}[/]")
            console.print(f"  Include stopwords: [cyan]{include_stopwords}[/]")
            
        # JSON output
        else:
            result = {
                "success": True,
                "title": note.title,
                "category": note.category,
                "word_frequency": report
            }
            click.echo(json.dumps(result, indent=2))
        
        return 0
    
    @cli_group.command(name="cloudwords")
    @click.argument("title", type=str)
    @click.option("--category", "-c", help="Category of the note.")
    @click.option("--output-dir", "-o", help="Directory to look for the note.")
    @click.option("--min-length", "-m", type=int, default=4, help="Minimum word length to include.")
    @click.option("--max-words", "-n", type=int, default=100, help="Maximum number of words to display.")
    @click.option("--include-stopwords", is_flag=True, help="Include common stopwords in the analysis.")
    @click.option("--export-path", "-p", help="Path to export word cloud to. Required.")
    @click.option("--width", type=int, default=800, help="Width of the word cloud image.")
    @click.option("--height", type=int, default=400, help="Height of the word cloud image.")
    @click.option("--background", help="Background color of the word cloud (e.g. 'white', '#000000').")
    @click.option("--output-format", type=click.Choice(["text", "json"]), default="text", help="Output format.")
    def wordcloud(
        title, category, output_dir, min_length, max_words, include_stopwords, 
        export_path, width, height, background, output_format
    ):
        """
        Generate a word cloud image from a note.
        
        This command creates a visual word cloud image where words are sized
        according to their frequency in the note. This requires the wordcloud
        Python package to be installed.
        
        Examples:
        
        \b
        # Basic word cloud generation
        marknote cloudwords "My Note Title" --export-path ./wordcloud.png
        
        \b
        # Customized word cloud 
        marknote cloudwords "Research Notes" --min-length 5 --max-words 150 --background "black" --width 1000 --height 600 --export-path ./research_cloud.png
        """
        from app.core.note_manager import NoteManager
        from app.core.word_frequency_analyzer import WordFrequencyAnalyzer
        
        console = Console()
        
        # Check if export path is provided
        if not export_path:
            if output_format == "text":
                console.print("[bold red]Error:[/] --export-path is required to save the word cloud image.")
            else:
                click.echo(json.dumps({
                    "success": False,
                    "error": "--export-path is required to save the word cloud image."
                }))
            return 1
            
        # Check if wordcloud package is available
        try:
            import wordcloud
            from wordcloud import WordCloud
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            if output_format == "text":
                console.print("[bold red]Error:[/] This command requires the wordcloud, matplotlib and numpy packages.")
                console.print("Please install them with: [cyan]pip install wordcloud matplotlib numpy[/]")
            else:
                click.echo(json.dumps({
                    "success": False,
                    "error": "This command requires the wordcloud, matplotlib and numpy packages."
                }))
            return 1
        
        # Initialize note manager
        note_manager = NoteManager(output_dir)
        
        # Get the note
        note = note_manager.get_note(title, category, output_dir)
        
        if not note:
            if output_format == "text":
                console.print(f"[bold red]Error:[/] Note '{title}' not found.")
            else:
                click.echo(json.dumps({
                    "success": False,
                    "error": f"Note '{title}' not found."
                }))
            return 1
        
        # Create analyzer
        stopwords = None if include_stopwords else None  # Use default stopwords unless explicitly including them
        analyzer = WordFrequencyAnalyzer(
            stopwords=stopwords,
            min_word_length=min_length,
            max_words=max_words,
            case_sensitive=False  # Word clouds typically ignore case
        )
        
        # Analyze and get word frequencies
        if output_format == "text":
            console.print("[bold]Generating word cloud...[/]")
            with Progress(transient=True) as progress:
                task = progress.add_task("Analyzing word frequency...", total=None)
                word_frequencies = analyzer.analyze(note.content)
                progress.update(task, completed=True)
        else:
            word_frequencies = analyzer.analyze(note.content)
        
        # Create word frequency dictionary
        word_freq_dict = dict(word_frequencies)
        
        # Generate word cloud
        wc_params = {
            "width": width,
            "height": height,
            "max_words": max_words,
            "background_color": background or "white",
            "colormap": "viridis",  # Nice blue-yellow-green colormap
            "prefer_horizontal": 0.9,  # Slightly prefer horizontal text
            "relative_scaling": 0.5,  # Relative scaling between frequencies
        }
        
        # Create and save word cloud
        try:
            wc = WordCloud(**wc_params)
            wc.generate_from_frequencies(word_freq_dict)
            
            # Save the image
            wc.to_file(export_path)
            
            if output_format == "text":
                console.print(f"[bold green]Success:[/] Word cloud saved to '{export_path}'")
                console.print(f"\n[bold]Word Cloud Details:[/]")
                console.print(f"  Words included: [cyan]{len(word_frequencies)}[/]")
                console.print(f"  Top words: [cyan]{', '.join([w for w, _ in word_frequencies[:5]])}[/]")
                console.print(f"  Image size: [cyan]{width}x{height}[/]")
            else:
                click.echo(json.dumps({
                    "success": True,
                    "export_path": export_path,
                    "width": width,
                    "height": height,
                    "word_count": len(word_frequencies),
                    "top_words": [w for w, _ in word_frequencies[:10]]
                }))
                
        except Exception as e:
            if output_format == "text":
                console.print(f"[bold red]Error:[/] Failed to generate word cloud: {str(e)}")
            else:
                click.echo(json.dumps({
                    "success": False,
                    "error": f"Failed to generate word cloud: {str(e)}"
                }))
            return 1
        
        return 0
    
    
    @cli_group.command(name="comparewords")
    @click.argument("title1", type=str)
    @click.argument("title2", type=str)
    @click.option("--category1", help="Category of the first note.")
    @click.option("--category2", help="Category of the second note.")
    @click.option("--output-dir", "-o", help="Directory to look for the notes.")
    @click.option("--min-length", "-m", type=int, default=3, help="Minimum word length to include.")
    @click.option("--max-words", "-n", type=int, default=30, help="Maximum number of words to display.")
    @click.option("--include-stopwords", is_flag=True, help="Include common stopwords in the analysis.")
    @click.option("--unique-only", is_flag=True, help="Show only words unique to each note.")
    @click.option("--export", "-e", type=click.Choice(['json', 'csv']), help="Export results to JSON or CSV.")
    @click.option("--export-path", "-p", help="Path to export results to. If not provided, prints to stdout.")
    @click.option("--output-format", type=click.Choice(["text", "json"]), default="text", help="Output format.")
    def compare_word_frequencies(
        title1, title2, category1, category2, output_dir, min_length, max_words, 
        include_stopwords, unique_only, export, export_path, output_format
    ):
        """
        Compare word frequencies between two notes.
        
        This command analyses and compares the word frequencies in two notes,
        highlighting common and unique vocabulary.
        
        Examples:
        
        \b
        # Basic comparison
        marknote comparewords "Note 1" "Note 2"
        
        \b
        # Show only words unique to each note
        marknote comparewords "Note 1" "Note 2" --unique-only
        
        \b
        # Compare with more words and export to JSON
        marknote comparewords "Note 1" "Note 2" --max-words 50 --export json --export-path ./comparison.json
        """
        from app.core.note_manager import NoteManager
        from app.core.word_frequency_analyzer import WordFrequencyAnalyzer
        
        console = Console()
        
        # Initialize note manager
        note_manager = NoteManager(output_dir)
        
        # Get the notes
        note1 = note_manager.get_note(title1, category1, output_dir)
        note2 = note_manager.get_note(title2, category2, output_dir)
        
        if not note1:
            if output_format == "text":
                console.print(f"[bold red]Error:[/] Note '{title1}' not found.")
            else:
                click.echo(json.dumps({
                    "success": False,
                    "error": f"Note '{title1}' not found."
                }))
            return 1
            
        if not note2:
            if output_format == "text":
                console.print(f"[bold red]Error:[/] Note '{title2}' not found.")
            else:
                click.echo(json.dumps({
                    "success": False,
                    "error": f"Note '{title2}' not found."
                }))
            return 1
        
        # Create analyzer
        stopwords = None if include_stopwords else None  # Use default stopwords unless explicitly including them
        analyzer = WordFrequencyAnalyzer(
            stopwords=stopwords,
            min_word_length=min_length,
            max_words=1000,  # Use a high value to get more data for comparison
            case_sensitive=False
        )
        
        # Analyze word frequencies for both notes
        if output_format == "text":
            with Progress(transient=True) as progress:
                task = progress.add_task("Analyzing notes...", total=None)
                
                # Analyze both notes
                word_freqs1 = dict(analyzer.analyze(note1.content))
                word_freqs2 = dict(analyzer.analyze(note2.content))
                
                # Get general stats
                report1 = analyzer.generate_report(note1.content)
                report2 = analyzer.generate_report(note2.content)
                
                progress.update(task, completed=True)
        else:
            word_freqs1 = dict(analyzer.analyze(note1.content))
            word_freqs2 = dict(analyzer.analyze(note2.content))
            report1 = analyzer.generate_report(note1.content)
            report2 = analyzer.generate_report(note2.content)
        
        # Get all words
        all_words = set(word_freqs1.keys()) | set(word_freqs2.keys())
        
        # Calculate common and unique words
        common_words = set(word_freqs1.keys()) & set(word_freqs2.keys())
        unique_to_note1 = set(word_freqs1.keys()) - set(word_freqs2.keys())
        unique_to_note2 = set(word_freqs2.keys()) - set(word_freqs1.keys())
        
        # Prepare comparison data
        comparison_data = {
            "notes": {
                "note1": {
                    "title": note1.title,
                    "category": note1.category,
                    "total_words": report1['statistics']['total_words'],
                    "unique_words": report1['statistics']['total_unique_words_all']
                },
                "note2": {
                    "title": note2.title,
                    "category": note2.category,
                    "total_words": report2['statistics']['total_words'],
                    "unique_words": report2['statistics']['total_unique_words_all']
                }
            },
            "comparison": {
                "total_unique_words_across_both": len(all_words),
                "common_words_count": len(common_words),
                "unique_to_note1_count": len(unique_to_note1),
                "unique_to_note2_count": len(unique_to_note2),
                "similarity_percentage": round((len(common_words) / len(all_words) if all_words else 0) * 100, 2)
            },
            "common_words": [
                {
                    "word": word,
                    "count_note1": word_freqs1.get(word, 0),
                    "count_note2": word_freqs2.get(word, 0),
                    "difference": abs(word_freqs1.get(word, 0) - word_freqs2.get(word, 0))
                }
                for word in sorted(common_words, key=lambda w: abs(word_freqs1.get(w, 0) - word_freqs2.get(w, 0)), reverse=True)
            ][:max_words],
            "unique_words": {
                "note1": [{"word": word, "count": word_freqs1.get(word, 0)} 
                          for word in sorted(unique_to_note1, key=lambda w: word_freqs1.get(w, 0), reverse=True)][:max_words],
                "note2": [{"word": word, "count": word_freqs2.get(word, 0)}
                          for word in sorted(unique_to_note2, key=lambda w: word_freqs2.get(w, 0), reverse=True)][:max_words]
            }
        }
        
        # Handle different output formats
        if export:
            # Export to JSON
            if export == 'json':
                export_data = comparison_data
                export_str = json.dumps(export_data, indent=2)
                
            # Export to CSV
            elif export == 'csv':
                csv_buffer = StringIO()
                writer = csv.writer(csv_buffer)
                
                # Write headers
                writer.writerow(['Word', f'Count in {note1.title}', f'Count in {note2.title}', 'Difference', 'Status'])
                
                # Write common words
                for item in comparison_data['common_words']:
                    word = item['word']
                    count1 = item['count_note1']
                    count2 = item['count_note2']
                    diff = item['difference']
                    writer.writerow([word, count1, count2, diff, 'Common'])
                
                # Write unique words for note 1
                for item in comparison_data['unique_words']['note1'][:max_words//2]:
                    writer.writerow([item['word'], item['count'], 0, item['count'], f'Unique to {note1.title}'])
                    
                # Write unique words for note 2
                for item in comparison_data['unique_words']['note2'][:max_words//2]:
                    writer.writerow([item['word'], 0, item['count'], item['count'], f'Unique to {note2.title}'])
                
                export_str = csv_buffer.getvalue()
                
            # Write to file or stdout
            if export_path:
                with open(export_path, 'w') as f:
                    f.write(export_str)
                if output_format == "text":
                    console.print(f"[bold green]Success:[/] Comparison exported to '{export_path}'")
            else:
                if output_format == "text":
                    console.print(export_str)
                else:
                    click.echo(export_str)
        
        # Display results in terminal
        elif output_format == "text":
            # Print header
            console.print(f"[bold]Word Frequency Comparison:[/]")
            console.print(f"  [cyan]{note1.title}[/] vs [cyan]{note2.title}[/]")
            
            # Print statistics
            stats = comparison_data['comparison']
            note1_stats = comparison_data['notes']['note1']
            note2_stats = comparison_data['notes']['note2']
            
            console.print(f"\n[bold]Comparison Statistics:[/]")
            console.print(f"  Total words in note 1: [cyan]{note1_stats['total_words']}[/]")
            console.print(f"  Total words in note 2: [cyan]{note2_stats['total_words']}[/]")
            console.print(f"  Unique words in note 1: [cyan]{note1_stats['unique_words']}[/]")
            console.print(f"  Unique words in note 2: [cyan]{note2_stats['unique_words']}[/]")
            console.print(f"  Unique words across both notes: [cyan]{stats['total_unique_words_across_both']}[/]")
            console.print(f"  Common words count: [cyan]{stats['common_words_count']}[/]")
            console.print(f"  Unique to note 1: [cyan]{stats['unique_to_note1_count']}[/]")
            console.print(f"  Unique to note 2: [cyan]{stats['unique_to_note2_count']}[/]")
            console.print(f"  Vocabulary similarity: [cyan]{stats['similarity_percentage']}%[/]")
            
            # If unique Only flag is set, only show unique words
            if unique_only:
                # Unique to Note 1
                console.print(f"\n[bold]Words Unique to '{note1.title}':[/]")
                unique1_table = Table()
                unique1_table.add_column("Word", style="cyan")
                unique1_table.add_column("Count", justify="right")
                
                for item in comparison_data['unique_words']['note1']:
                    unique1_table.add_row(item['word'], str(item['count']))
                    
                console.print(unique1_table)
                
                # Unique to Note 2
                console.print(f"\n[bold]Words Unique to '{note2.title}':[/]")
                unique2_table = Table()
                unique2_table.add_column("Word", style="cyan")
                unique2_table.add_column("Count", justify="right")
                
                for item in comparison_data['unique_words']['note2']:
                    unique2_table.add_row(item['word'], str(item['count']))
                    
                console.print(unique2_table)
                
            else:
                # Common words with biggest frequency difference
                console.print(f"\n[bold]Common Words (with biggest frequency difference):[/]")
                common_table = Table()
                common_table.add_column("Word", style="cyan")
                common_table.add_column(f"Count in {note1.title}")
                common_table.add_column(f"Count in {note2.title}")
                common_table.add_column("Difference")
                
                for item in comparison_data['common_words'][:max_words]:
                    common_table.add_row(
                        item['word'], 
                        str(item['count_note1']),
                        str(item['count_note2']),
                        str(item['difference'])
                    )
                    
                console.print(common_table)
                
                # Unique to Note 1 (abbreviated)
                console.print(f"\n[bold]Words Unique to '{note1.title}':[/]")
                unique1_table = Table()
                unique1_table.add_column("Word", style="cyan")
                unique1_table.add_column("Count", justify="right")
                
                for item in comparison_data['unique_words']['note1'][:max_words//2]:
                    unique1_table.add_row(item['word'], str(item['count']))
                    
                console.print(unique1_table)
                if len(comparison_data['unique_words']['note1']) > max_words//2:
                    console.print(f"  ... and {len(comparison_data['unique_words']['note1']) - max_words//2} more")
                
                # Unique to Note 2 (abbreviated)
                console.print(f"\n[bold]Words Unique to '{note2.title}':[/]")
                unique2_table = Table()
                unique2_table.add_column("Word", style="cyan")
                unique2_table.add_column("Count", justify="right")
                
                for item in comparison_data['unique_words']['note2'][:max_words//2]:
                    unique2_table.add_row(item['word'], str(item['count']))
                    
                console.print(unique2_table)
                if len(comparison_data['unique_words']['note2']) > max_words//2:
                    console.print(f"  ... and {len(comparison_data['unique_words']['note2']) - max_words//2} more")
            
            # Analysis parameters
            console.print(f"\n[bold]Analysis Parameters:[/]")
            console.print(f"  Minimum word length: [cyan]{min_length}[/]")
            console.print(f"  Maximum words shown: [cyan]{max_words}[/]")
            console.print(f"  Include stopwords: [cyan]{include_stopwords}[/]")
            console.print(f"  Show unique words only: [cyan]{unique_only}[/]")
            
        # JSON output
        else:
            click.echo(json.dumps(comparison_data, indent=2))
        
        return 0

def register_archive_commands(cli_group):
    """Register archive commands with the main CLI group."""
    cli_group.add_command(archive_commands)


def register_encryption_commands(cli_group):
    """Register encryption commands with the main CLI group."""
    cli_group.add_command(encrypt_commands)
    cli_group.add_command(decrypt_commands)


def register_version_commands(cli_group):
    """Register version commands with the main CLI group."""
    cli_group.add_command(versions)

def register_delete_commands(cli_group):
    cli_group.add_command(delete_commands)


def register_tag_commands(cli_group):
    """Register tag commands with the main CLI group."""
    cli_group.add_command(tag_commands)

def register_template_commands(cli_group):
    """Register template commands with the main CLI group."""
    cli_group.add_command(template_commands)


if __name__ == "__main__":
    cli()
