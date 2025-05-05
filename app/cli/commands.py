"""
CLI commands for MarkNote
"""
from datetime import date, datetime
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
from app.utils.template_manager import TemplateManager
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

if __name__ == "__main__":
    cli()
