"""
CLI commands for MarkNote
"""
import os
import sys
from typing import Dict, List, Optional, Tuple
import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text
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
            console.print(f"[bold red]Error:[/bold red] Specified editor '{editor}' not found or not executable")
            available_editors = get_available_editors()
            if available_editors:
                console.print(f"Available editors: {', '.join(available_editors)}")
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
            console.print(f"[bold red]Error:[/bold red] Template '{template}' not found.")
            console.print(f"Available templates: {', '.join(available_templates)}")
            return 1
        
        # Validate output directory
        if output_dir:
            output_dir = os.path.expanduser(output_dir)
            if not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir)
                    console.print(f"Created output directory: [cyan]{output_dir}[/cyan]")
                except (PermissionError, OSError) as e:
                    console.print(f"[bold red]Error:[/bold red] Failed to create output directory: {str(e)}")
                    return 1
            elif not os.access(output_dir, os.W_OK):
                console.print(f"[bold red]Error:[/bold red] No write permission for directory: {output_dir}")
                return 1
        
        additional_metadata = {}
        
        # Interactive mode for additional metadata
        if interactive:
            console.print(Panel(f"[bold]Creating a new note: [cyan]{title}[/cyan][/bold]", 
                               title="MarkNote", subtitle="Interactive Mode"))
            
            # Confirm or update template
            template_options = ", ".join(available_templates)
            console.print(f"Available templates: [cyan]{template_options}[/cyan]")
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
                output_dir_input = Prompt.ask("Save to directory", default=default_dir)
                if output_dir_input and output_dir_input != default_dir:
                    output_dir = output_dir_input
                    
            # Get editor if not provided
            if not editor:
                available_editors = get_available_editors()
                if available_editors:
                    console.print(f"Available editors: [cyan]{', '.join(available_editors)}[/cyan]")
                    editor_input = Prompt.ask("Editor (leave blank for system default)", default="")
                    if editor_input:
                        if is_valid_editor(editor_input):
                            editor = editor_input
                        else:
                            console.print(f"[yellow]Warning: Editor '{editor_input}' not found, using system default.[/yellow]")
            
            # Get additional metadata based on template
            if template == "meeting":
                additional_metadata["meeting_date"] = Prompt.ask("Meeting date", default="")
                additional_metadata["meeting_time"] = Prompt.ask("Meeting time", default="")
                additional_metadata["location"] = Prompt.ask("Location", default="")
                additional_metadata["attendees"] = Prompt.ask("Attendees", default="")
            
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
            console.print(f"[bold green]Note created successfully:[/bold green] {note_path}")
            
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
                existing_note = note_manager.get_note(title, category, output_dir=output_dir)
                if existing_note:
                    # Update the note with new content from the template
                    # This would be a feature to implement later
                    console.print(f"[bold yellow]Note already exists and will be overwritten.[/bold yellow]")
                    # For now, return an error
                    console.print(f"[bold red]Error:[/bold red] Overwriting existing notes is not yet implemented.")
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
            console.print(f"[yellow]No notes found matching query: '{query}'[/yellow]")
            return 0
            
        console.print(f"[bold blue]Found {len(notes)} notes matching '{query}':[/bold blue]")
        
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
            console.print(f"[bold red]Error:[/bold red] Specified editor '{editor}' not found or not executable")
            available_editors = get_available_editors()
            if available_editors:
                console.print(f"Available editors: {', '.join(available_editors)}")
            return 1
        
        note_manager = NoteManager()
        
        for title in titles:
            # Get the note
            note = note_manager.get_note(title, category, output_dir=output_dir)
            
            if not note:
                # Try to find the note without relying on exact category match
                note_path = note_manager.find_note_path(title, category, output_dir)
                if note_path:
                    console.print(f"[yellow]Note found at a different location than specified:[/yellow] {note_path}")
                    
                    # Try to read the note and recreate the Note object
                    try:
                        with open(note_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        metadata, content_without_frontmatter = parse_frontmatter(content)
                        
                        # Extract category from path if possible
                        path_parts = os.path.normpath(note_path).split(os.path.sep)
                        detected_category = None
                        if len(path_parts) >= 2:
                            possible_category = path_parts[-2]
                            base_dir = output_dir if output_dir else note_manager.notes_dir
                            base_name = os.path.basename(os.path.normpath(base_dir))
                            if possible_category != base_name:
                                detected_category = possible_category
                                console.print(f"[yellow]Detected category from path:[/yellow] {detected_category}")
                        
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
                        console.print(f"[bold red]Error reading note:[/bold red] {str(e)}")
                        continue
                else:
                    console.print(f"[bold red]Error:[/bold red] Note '{title}' not found.")
                    if category:
                        console.print(f"Make sure the category '{category}' is correct.")
                    if output_dir:
                        console.print(f"Looking in directory: {output_dir}")
                    continue
                
            # Get the file path
            path = note.metadata.get('path', '')
            if not path or not os.path.exists(path):
                console.print(f"[bold red]Error:[/bold red] Can't find note file at {path}")
                continue
            
            # Display note information before editing
            detected_category = note.category or (category if category else None)
            if detected_category:
                console.print(f"Editing note: [bold cyan]{title}[/bold cyan] in category [bold green]{detected_category}[/bold green]")
            else:
                console.print(f"Editing note: [bold cyan]{title}[/bold cyan]")
            console.print(f"File: [dim]{path}[/dim]")
            
            # Show which editor is being used
            editor_display = editor if editor else "system default"
            console.print(f"Using editor: [bold magenta]{editor_display}[/bold magenta]")
            
            # Open the file in the user's editor
            success, error = edit_file(path, custom_editor=editor)
            
            if not success:
                console.print(f"[bold red]Error editing note:[/bold red] {error}")
                return 1
            
            # Read the updated content
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                console.print(f"[bold red]Error reading updated file:[/bold red] {str(e)}")
                return 1
                
            # Parse frontmatter and content
            metadata, content_without_frontmatter = parse_frontmatter(content)
            
            # Update the note in our system with the new content
            success, updated_note, error = note_manager.edit_note_content(
                title, content_without_frontmatter, category=detected_category, output_dir=output_dir
            )
            
            if success:
                console.print(f"[bold green]Note updated successfully![/bold green]")
            else:
                console.print(f"[bold red]Error updating note:[/bold red] {error}")
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
            note_path = note_manager.find_note_path(title, category, output_dir)
            if note_path:
                console.print(f"[yellow]Note found at:[/yellow] {note_path}")
                
                # Try to read the note content
                with open(note_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                metadata, content_without_frontmatter = parse_frontmatter(content)
                
                # Display the note
                console.print(Panel(
                    f"[bold cyan]{title}[/bold cyan]\n\n{content_without_frontmatter}",
                    title=f"MarkNote - {title}",
                    subtitle="Note found with alternative path lookup"
                ))
                return 0
            else:
                console.print(f"[bold red]Error:[/bold red] Note '{title}' not found.")
                if category:
                    console.print(f"Make sure the category '{category}' is correct.")
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
        console.print(f"[bold red]Error listing templates:[/bold red] {str(e)}")
        return 1

@cli.command()
def editors():
    """List available editors on your system."""
    try:
        available_editors = get_available_editors()
        
        if not available_editors:
            console.print("[yellow]No recognized editors found on your system.[/yellow]")
            console.print("You can still specify a custom editor with the --editor option.")
            return 0
        
        console.print("[bold blue]Available editors on your system:[/bold blue]")
        for editor in available_editors:
            console.print(f"- [cyan]{editor}[/cyan]")
            
        # Show current default editor
        from app.utils.editor_handler import get_editor
        default_editor = get_editor()
        console.print(f"\n[bold green]Default editor:[/bold green] {default_editor}")
        console.print("\n[dim]You can change the default editor by setting the EDITOR or VISUAL environment variable,[/dim]")
        console.print("[dim]or specify a different editor for a single command with --editor (-e) option.[/dim]")
        
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
            console.print(f"[bold green]Successfully linked[/bold green] '{source}' [bold]↔[/bold] '{target}' [dim](bidirectional)[/dim]")
        else:
            console.print(f"[bold green]Successfully linked[/bold green] '{source}' [bold]→[/bold] '{target}'")
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
            console.print(f"[bold green]Successfully removed link[/bold green] between '{source}' and '{target}' [dim](bidirectional)[/dim]")
        else:
            console.print(f"[bold green]Successfully removed link[/bold green] from '{source}' to '{target}'")
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
            console.print(f"No links found from [bold cyan]'{title}'[/bold cyan] to other notes")
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
    console.print("\n[bold yellow]Tip:[/bold yellow] To fix orphaned links, either create the missing notes or remove the links.")
    
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
            linked_table.add_row(linked_note.title, linked_note.category or "None")
        
        console.print(linked_table)
    else:
        console.print("[dim]No linked notes.[/dim]")
    
    # Display backlinks if any
    if backlinks:
        backlinks_table = Table(title="Backlinks (Notes linking to this note)")
        backlinks_table.add_column("Title", style="cyan")
        backlinks_table.add_column("Category", style="green")
        
        for backlink in backlinks:
            backlinks_table.add_row(backlink.title, backlink.category or "None")
        
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
        notes_with_links = sum(1 for stats in link_stats.values() if stats[0] > 0 or stats[1] > 0)
        notes_with_outgoing = sum(1 for stats in link_stats.values() if stats[0] > 0)
        notes_with_incoming = sum(1 for stats in link_stats.values() if stats[1] > 0)
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
        most_linked = note_manager.find_most_linked_notes(output_dir=output_dir, limit=limit)
        
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
        orphaned_links = note_manager.find_orphaned_links(output_dir=output_dir)
        if orphaned_links:
            console.print(f"\n[yellow]Warning:[/yellow] Found {len(orphaned_links)} notes with orphaned links (links to non-existent notes).")
            console.print("Use [bold]marknote link orphaned[/bold] to view details.")
        
        return 0
    
    except Exception as e:
        console.print(f"[bold red]Error analyzing network:[/bold red] {str(e)}")
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
        standalone_notes = note_manager.find_standalone_notes(output_dir=output_dir)
        
        if not standalone_notes:
            console.print("[green]All notes are connected to at least one other note.[/green]")
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
        console.print("\n[blue]Tip:[/blue] Connect these notes to your knowledge network using [bold]marknote link add[/bold]")
        
        return 0
    
    except Exception as e:
        console.print(f"[bold red]Error finding standalone notes:[/bold red] {str(e)}")
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
            console.print(f"[bold red]Error:[/bold red] Source note '{source}' not found.")
            return 1
        
        target_note = note_manager.get_note(target, target_category, output_dir)
        if not target_note:
            console.print(f"[bold red]Error:[/bold red] Target note '{target}' not found.")
            return 1
        
        # Generate the link graph
        outgoing_links, _ = note_manager.generate_link_graph(output_dir=output_dir)
        
        # Find the shortest path using breadth-first search
        paths = find_paths(outgoing_links, source, target, max_depth)
        
        if not paths:
            console.print(f"[yellow]No path found between[/yellow] '{source}' [yellow]and[/yellow] '{target}'.")
            console.print(f"[dim]Try increasing the maximum depth (current: {max_depth}) or add more links.[/dim]")
            return 0
        
        # Sort paths by length (shortest first)
        paths.sort(key=len)
        
        # Display the paths
        console.print(f"[bold green]Found {len(paths)} path(s) between[/bold green] '{source}' [bold green]and[/bold green] '{target}':")
        
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
def list(tag, category, output_dir):
    """List all notes, optionally filtered by tag or category."""
    try:
        note_manager = NoteManager()
        notes = note_manager.list_notes(tag=tag, category=category, output_dir=output_dir)
        
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
                console.print(f"[yellow]No notes found matching {filter_str}.[/yellow]")
            else:
                console.print("[yellow]No notes found.[/yellow]")
            return 0
        
        # Create a table for display
        table = Table(title="Notes")
        table.add_column("Title", style="cyan")
        table.add_column("Tags")
        table.add_column("Updated", style="green")
        table.add_column("Category", style="magenta")
        
        for note in notes:
            tags_display = ", ".join(note.tags) if note.tags else ""
            updated_display = note.updated_at.strftime("%Y-%m-%d %H:%M")
            category_display = note.category if note.category else ""
            
            table.add_row(
                note.title,
                tags_display,
                updated_display,
                category_display
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]Error listing notes:[/bold red] {str(e)}")
        return 1
    
    return 0

# Enhanced list command with more options
@cli.command()
@click.option("--tag", "-t", help="Filter notes by tag.")
@click.option("--category", "-c", help="Filter notes by category.")
@click.option("--output-dir", "-o", help="Custom directory to look for notes.")
@click.option("--sort", "-s", type=click.Choice(['date', 'created', 'title', 'links']), default='date',
              help="Sort notes by date modified (default), creation date, title, or number of links.")
@click.option("--show-links/--hide-links", default=True, help="Show link information in the listing.")
@click.option("--detail", "-d", is_flag=True, help="Show more detailed information including snippets and all links.")
def list_notes(tag: Optional[str], category: Optional[str], output_dir: Optional[str], 
              sort: str, show_links: bool, detail: bool):
    """List notes, optionally filtered by tag or category."""
    note_manager = NoteManager()
    
    try:
        # Determine which sort parameter to use for NoteManager
        sort_by = "updated"  # Default
        if sort == 'created':
            sort_by = "created"
        elif sort == 'title':
            sort_by = "title"
        
        # Get all notes based on filters
        notes = note_manager.list_notes(
            tag=tag, 
            category=category, 
            output_dir=output_dir,
            sort_by=sort_by
        )
        
        if not notes:
            if tag or category:
                filters = []
                if tag:
                    filters.append(f"tag '{tag}'")
                if category:
                    filters.append(f"category '{category}'")
                
                console.print(f"[yellow]No notes found matching {' and '.join(filters)}.[/yellow]")
            else:
                console.print("[yellow]No notes found.[/yellow]")
                
                # If output directory is specified, show that
                if output_dir:
                    console.print(f"Directory: {output_dir}")
            return 0
        
        # If sort is 'links', we need a special sort that can't be done in NoteManager
        if sort == 'links':
            # Sort by total links (outgoing + incoming)
            # We need to find all backlinks first
            notes_by_title = {note.title: note for note in notes}
            backlink_counts: Dict[str, int] = {}
            
            # Count backlinks for each note
            for note in notes:
                for linked_title in note.get_links():
                    if linked_title in backlink_counts:
                        backlink_counts[linked_title] += 1
                    else:
                        backlink_counts[linked_title] = 1
            
            # Sort by total links (outgoing + incoming)
            notes.sort(
                key=lambda x: (len(x.get_links()) + backlink_counts.get(x.title, 0)),
                reverse=True
            )
        
        # If we're showing links, we need to calculate them
        backlink_counts = {}
        linked_to_notes = {}
        note_titles = {note.title for note in notes}
        
        if show_links:
            # Find all links between notes in the list
            for note in notes:
                outgoing_links = note.get_links()
                
                # Record backlinks
                for linked_title in outgoing_links:
                    if linked_title in note_titles:  # Only count links to notes in our list
                        if linked_title in backlink_counts:
                            backlink_counts[linked_title] += 1
                        else:
                            backlink_counts[linked_title] = 1
                            
                        # Record which notes link to which
                        if linked_title not in linked_to_notes:
                            linked_to_notes[linked_title] = set()
                        linked_to_notes[linked_title].add(note.title)
        
        # Create a table for display
        table = Table(title="Notes")
        
        # Basic columns
        table.add_column("Title", style="cyan")
        table.add_column("Tags")
        
        # Show creation date if sorting by it
        if sort == 'created':
            table.add_column("Created", style="green")
        else:
            table.add_column("Updated", style="green")
            
        table.add_column("Category", style="magenta")
        
        # If showing links, add link columns
        if show_links:
            table.add_column("Links", justify="right", style="blue")
            table.add_column("Backlinks", justify="right", style="blue")
        
        # Add rows to the table
        for note in notes:
            row = []
            
            # Title
            row.append(note.title)
            
            # Tags
            tags_display = ", ".join(note.tags) if note.tags else ""
            row.append(tags_display)
            
            # Date
            if sort == 'created':
                date_display = note.created_at.strftime("%Y-%m-%d %H:%M")
            else:
                date_display = note.updated_at.strftime("%Y-%m-%d %H:%M")
            row.append(date_display)
            
            # Category
            category_display = note.category if note.category else ""
            row.append(category_display)
            
            # Links info if enabled
            if show_links:
                outgoing_count = len(note.get_links())
                incoming_count = backlink_counts.get(note.title, 0)
                
                row.append(str(outgoing_count))
                row.append(str(incoming_count))
            
            table.add_row(*row)
            
            # If detail mode is on, show content snippet
            if detail:
                snippet = note.content[:100].replace('\n', ' ') + "..." if len(note.content) > 100 else note.content.replace('\n', ' ')
                detail_table = Table(show_header=False, box=None, padding=(0, 2))
                detail_table.add_row(f"  [dim]{snippet}[/dim]")
                
                # Show explicit links also
                if show_links and note.get_links():
                    link_text = "  [dim]Links to: " + ", ".join(note.get_links()) + "[/dim]"
                    detail_table.add_row(link_text)
                
                # Show backlinks also
                if show_links and note.title in linked_to_notes and linked_to_notes[note.title]:
                    backlink_text = "  [dim]Linked from: " + ", ".join(linked_to_notes[note.title]) + "[/dim]"
                    detail_table.add_row(backlink_text)
                
                table.add_row(detail_table)
        
        console.print(table)
        console.print(f"[dim]Total: {len(notes)} notes[/dim]")
        
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

if __name__ == "__main__":
    cli()