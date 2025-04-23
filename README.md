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

```bash
# Create a new note
marknote new "My New Note"

# List all notes
marknote list

# Search for notes
marknote search "keyword"

# Edit a note
marknote edit "My New Note"

# Display a note with proper formatting
marknote show "My New Note"
```

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