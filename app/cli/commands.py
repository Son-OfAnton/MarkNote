"""
CLI commands for MarkNote
"""
from datetime import date, datetime
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
from app.config.config_manager import get_config_manager, get_daily_note_config
from app.core.daily_note_service import get_daily_note_service
import app.models.note

from app.core.note_manager import NoteManager
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

        success, history, message = note_manager.get_note_version_history(
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

        success, version, message = note_manager.get_note_version(
            title=title,
            version_id=version_id,
            category=category,
            output_dir=output_dir
        )

        if not success or not version:
            console.print(f"[bold red]Error:[/bold red] {message}")
            return 1

        # Show version info
        try:
            dt = datetime.fromisoformat(version.get("timestamp", ""))
            formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            formatted_date = version.get("timestamp", "Unknown")

        console.print(Panel(
            f"[bold]Version ID:[/bold] {version.get('version_id')}\n"
            f"[bold]Date:[/bold] {formatted_date}\n"
            f"[bold]Message:[/bold] {version.get('message', 'No message')}",
            title=f"Version Info for '{title}'",
            border_style="green"
        ))

        # Show the content
        content = version.get("content", "")

        if raw:
            # Show content as syntax-highlighted plain text
            try:
                syntax = Syntax(content, "markdown",
                                theme="monokai", line_numbers=True)
                console.print(syntax)
            except Exception:
                # Fallback if there's an issue with Syntax
                console.print(content)
        else:
            # Render the markdown content
            try:
                md = Markdown(content)
                console.print(Panel(md, title="Content", border_style="blue"))
            except Exception:
                # Fallback if there's an issue with Markdown rendering
                console.print(
                    Panel(content, title="Content", border_style="blue"))

        return 0

    except Exception as e:
        console.print(f"[bold red]Error showing version:[/bold red] {str(e)}")
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

        # Get version details
        history_success, _, versions = note_manager.get_note_version_history(
            title=title,
            category=category,
            output_dir=output_dir
        )

        if history_success and versions:
            # Find the newly created version
            new_version = next(
                (v for v in versions if v["version_id"] == version_id), None)
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


def register_version_commands(cli_group):
    """Register version commands with the main CLI group."""
    cli_group.add_command(versions)


if __name__ == "__main__":
    cli()
