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
- Encrypt and decrypt notes
- Archive and unarchive notes
- Analyze note networks and connections

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

```bash
# Basic
marknote new "My New Note"

# With full options:
marknote new "My New Note" --template default --tags "work,urgent" --category work --interactive --force --output-dir ~/notes --editor nano
```

### List Notes

```bash
# List all notes
marknote list

# Filter by tag, category, and output directory
marknote list --tag work --category work --output-dir ~/notes
```

### Search Notes

```bash
marknote search "meeting" --output-dir ~/notes
```

### Edit Note(s)

```bash
marknote edit "My New Note" --category work --output-dir ~/notes --editor vim
```

### Show Note

```bash
marknote show "My New Note" --category work --output-dir ~/notes
```

### List Templates

```bash
marknote templates
```

### List Available Editors

```bash
marknote editors
```

### Link Commands

```bash
# Add a link (optionally bidirectional)
marknote link add "Source Note" "Target Note" --bidirectional --category sourceCat --target-category targetCat --output-dir ~/notes

# Remove a link
marknote link remove "Source Note" "Target Note" --bidirectional --category sourceCat --target-category targetCat --output-dir ~/notes

# List links (use --backlinks to show incoming links)
marknote link list "Note Title" --category work --output-dir ~/notes --backlinks

# Show orphaned links (links pointing to non-existent notes)
marknote link orphaned --output-dir ~/notes

# Display a note with its links and backlinks
marknote link show "Note Title" --category work --output-dir ~/notes
```

### Network Commands

```bash
# Show network statistics
marknote network stats --output-dir ~/notes --limit 10

# Find standalone notes (with no links)
marknote network standalone --output-dir ~/notes

# Find the shortest path between two notes
marknote network path "Source Note" "Target Note" --category sourceCat --target-category targetCat --output-dir ~/notes --max-depth 5
```

### Daily Commands

```bash
# Create or open a daily note
marknote daily [options]

# Show today's daily note status (and optionally open it)
marknote today [options]

# Configure daily note settings
marknote config daily [options]
```

### Version Commands

```bash
# List all versions of a note
marknote versions list "Note Title" [options]

# Show a specific version
marknote versions show "Note Title" "version_id" [options]

# Show differences between two versions
marknote versions diff "Note Title" "from_version" "to_version" [options]

# Restore a note to a previous version
marknote versions restore "Note Title" "version_id" [options]

# Purge version history for a note
marknote versions purge "Note Title" [options]

# Show version control status
marknote versions status

# Manually create a new version of a note
marknote versions create "Note Title" [options]

# Edit a specific version
marknote versions edit "Note Title" "version_id" [options]
```

### Encryption Commands

```bash
# Encrypt a note
marknote encrypt note "Note Title" --password "your_password"

# Batch encrypt multiple notes
marknote encrypt batch "Note1" "Note2" --password "your_password"

# Decrypt a note
marknote decrypt note "Note Title" --password "your_password"

# Batch decrypt multiple notes
marknote decrypt batch "Note1" "Note2" --password "your_password"

# Change encryption password for a note
marknote encrypt change-password "Note Title" --current-password "old_password" --new-password "new_password"

# Check encryption status
marknote encrypt status "Note Title"
marknote encrypt status --all
```

### Archive Commands

```bash
# Archive a note
marknote archive note "Note Title" --reason "Outdated"

# Unarchive a note
marknote archive unarchive "Note Title"

# List archived notes
marknote archive list --category work --output json --sort-by title

# Show archive statistics
marknote archive stats --output markdown

# Batch archive multiple notes
marknote archive batch "Note1" "Note2" --reason "Cleanup"

# Auto-archive notes older than a certain number of days
marknote archive auto --days 30 --reason "Old notes" --dry-run

# Check archive status
marknote archive status "Note Title"
```

### Additional Commands

```bash
# Count total notes
marknote count --tag "work" --category "personal"

# Show most frequent tags
marknote tags --top 5 --all

# Show notes per category
marknote categories --sort-by count --reverse

# Display word count for a note
marknote wordcount "My New Note" --category work
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

## Project Structure

```
MarkNote/
├── app/
│   ├── cli/
│   │   └── commands.py
│   ├── config/
│   │   └── config_manager.py
│   ├── core/
│   │   ├── daily_note_service.py
│   │   ├── note_manager.py
│   │   ├── note_manager_archieve_extension.py
│   │   ├── note_manager_extension.py
│   │   └── note_manager_version_control.py
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
│       ├── encryption.py
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
