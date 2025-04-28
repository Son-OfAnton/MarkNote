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

# With full options:
marknote new "My New Note" --template default --tags "work,urgent" --category work --interactive --force --output-dir ~/notes --editor nano

### List Notes
# List all notes
marknote list

# Filter by tag, category and output directory
marknote list --tag work --category work --output-dir ~/notes

### Search Notes
marknote search "meeting" --output-dir ~/notes

### Edit Note(s)
marknote edit "My New Note" --category work --output-dir ~/notes --editor vim

### Show Note
marknote show "My New Note" --category work --output-dir ~/notes

### List Templates
marknote templates

### List Available Editors
marknote editors

### Link Commands
# Add a link (optionally bidirectional)
marknote link add "Source Note" "Target Note" --bidirectional --category sourceCat --target-category targetCat --output-dir ~/notes

# Remove a link
marknote link remove "Source Note" "Target Note" --bidirectional --category sourceCat --target-category targetCat --output-dir ~/notes

# List links from a note (use --backlinks to show incoming links)
marknote link list "Note Title" --category work --output-dir ~/notes --backlinks

# Show orphaned links (links pointing to non-existent notes)
marknote link orphaned --output-dir ~/notes

# Display a note with its links and backlinks
marknote link show "Note Title" --category work --output-dir ~/notes

### Network Commands
# Show network statistics
marknote network stats --output-dir ~/notes --limit 10

# Find standalone notes (with no links)
marknote network standalone --output-dir ~/notes

# Find the shortest path between two notes
marknote network path "Source Note" "Target Note" --category sourceCat --target-category targetCat --output-dir ~/notes --max-depth 5

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

## Project Structure

Below is the project folder structure:
```
MarkNote/
├── app/
│   ├── cli/
│   │   └── commands.py
│   ├── core/
│   │   └── note_manager.py
│   ├── models/
│   │   └── note.py
│   ├── templates/
│   │   ├── default/
│   │   │   └── template.md
│   │   ├── journal/
│   │   │   └── template.md
│   │   └── meeting/
│   │       └── template.md
│   └── utils/
│       ├── editor_handler.py
│       ├── file_handler.py
│       └── template_manager.py
├── tests/
│   ├── cli/
│   ├── core/
│   └── models/
├── .gitignore
├── pyproject.toml
├── README.md
├── requirements.txt
└── setup.py
```
