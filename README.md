# MarkNote

A command-line tool for creating, organizing, and managing Markdown-based notes.

## Features (Planned)

- Create new notes with customizable templates
- Organize notes with tags and categories
- Search through notes by content, tags, or metadata
- Export notes to different formats
- Preview notes with proper Markdown rendering
- Manage note metadata (frontmatter)
- Track note revisions

## Installation

```bash
# Clone the repository
git clone https://github.com/Son-OfAnton/MarkNote.git

# Navigate to the project directory
cd marknote

# Install the package in development mode
pip install -e ".[dev]"
```

## Usage

### Create a New Note

# Basic

marknote new "My New Note"

# With options: template, tags, category, interactive mode, force, output directory, and editor

marknote new "My New Note" --template default --tags "work,urgent" --category work --interactive --force --output-dir ~/notes --editor nano

### List Notes

# List all notes

marknote list

# Filter by tag, category and specify output directory

marknote list --tag work --category work --output-dir ~/notes

### Search Notes

# Search notes by a query and specify output directory

marknote search "meeting" --output-dir ~/notes

### Edit Note(s)

# Edit a note with options for category, output directory, and custom editor

marknote edit "My New Note" --category work --output-dir ~/notes --editor vim

### Show Note

# Display a note with options for category and output directory

marknote show "My New Note" --category work --output-dir ~/notes

### List Templates

marknote templates

### List Available Editors

marknote editors

## Development

```bash
# Run tests
pytest

# Check code style
black .

# Run linting
flake8 .

# Run type checking
mypy .
```
