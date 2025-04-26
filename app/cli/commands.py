"""
CLI commands for MarkNote
"""
import os
import sys
from typing import List, Optional, Tuple
import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
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
                console.print("[yellow]No notes found. Create one with 'marknote new'.[/yellow]")
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
            console.print(f"  [dim]Updated:[/dim] {note.updated_at.strftime('%Y-%m-%d %H:%M')}")
            console.print()
            
        return 0
    
    except Exception as e:
        console.print(f"[bold red]Error listing notes:[/bold red] {str(e)}")
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

# Register the link command group with the main CLI
def register_link_commands(cli):
    """
    Register the link command group with the main CLI.
    """
    cli.add_command(link)

if __name__ == "__main__":
    cli()