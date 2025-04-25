"""
Unit tests for the 'search' command functionality in the CLI.

These tests focus on the functionality of the search command,
including searching notes by content, title, and tags.
"""
import os
import shutil
import tempfile
import pytest
from click.testing import CliRunner
from app.cli.commands import new, cli


class TestSearchCommandFunctionality:
    """Test case for the 'search' command functionality."""

    @pytest.fixture
    def runner(self):
        """Provide a Click CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_notes_dir(self):
        """Create a temporary directory for test notes."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup after test
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_notes_with_content(self, runner, temp_notes_dir):
        """Create sample notes with specific content for search testing."""
        notes = [
            {
                "title": "Project Planning",
                "tags": "work,planning,project",
                "category": "work",
                "content": """
                # Project Planning
                
                This note contains information about planning our new software project.
                
                ## Key Points
                
                - Timeline: 3 months
                - Resources needed: 5 developers, 1 designer
                - Budget: $50,000
                
                ## Technologies
                
                We'll be using Python with Flask for the backend and React for the frontend.
                
                ## Action Items
                
                - Set up GitHub repository
                - Create initial project structure
                - Establish CI/CD pipeline
                """
            },
            {
                "title": "Meeting Notes - Client Introduction",
                "tags": "client,meeting,important",
                "category": "meetings",
                "content": """
                # Meeting Notes - Client Introduction
                
                Initial meeting with the new client to discuss requirements.
                
                ## Attendees
                
                - John Smith (Client)
                - Jane Doe (Project Manager)
                - Mark Johnson (Developer)
                
                ## Discussion Points
                
                The client needs a web application for tracking inventory.
                Budget is approximately $40,000.
                Timeline is flexible but preferably within 4 months.
                
                ## Technologies Discussed
                
                We recommended using Python for the backend.
                """
            },
            {
                "title": "Personal Goals",
                "tags": "personal,goals,private",
                "category": "personal",
                "content": """
                # Personal Goals
                
                My personal goals for the next 6 months.
                
                ## Career
                
                - Learn React and improve JavaScript skills
                - Contribute to at least 2 open-source projects
                - Write 5 technical blog posts
                
                ## Health
                
                - Exercise 3 times per week
                - Reduce coffee consumption
                - Get at least 7 hours of sleep each night
                
                ## Hobbies
                
                - Read 10 books
                - Improve photography skills
                """
            },
            {
                "title": "Shopping List",
                "tags": "personal,shopping",
                "category": "personal",
                "content": """
                # Shopping List
                
                Items to purchase on the next shopping trip.
                
                ## Groceries
                
                - Milk
                - Eggs
                - Bread
                - Apples
                - Coffee
                
                ## Household
                
                - Paper towels
                - Laundry detergent
                
                ## Electronics
                
                - USB cable
                - Laptop stand
                """
            }
        ]
        
        created_notes = []
        for note in notes:
            # Create the category directory if needed
            category_dir = os.path.join(temp_notes_dir, note["category"])
            os.makedirs(category_dir, exist_ok=True)
            
            # Determine filename
            filename = note["title"].lower().replace(" ", "-") + ".md"
            file_path = os.path.join(category_dir, filename)
            
            # Create frontmatter
            frontmatter = f"""---
title: {note["title"]}
created_at: 2024-04-23T10:00:00
updated_at: 2024-04-23T10:00:00
tags:
{chr(10).join([f'  - {tag}' for tag in note["tags"].split(',')])}
category: {note["category"]}
---

{note["content"]}
"""
            # Write the file directly
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(frontmatter)
                
            # Add the note to the created list
            created_notes.append({**note, "path": file_path})
            
        return created_notes

    def test_search_basic_functionality(self, runner, temp_notes_dir, sample_notes_with_content):
        """Test basic functionality of the 'search' command."""
        # Act - search for a term that should be in one note
        result = runner.invoke(cli, 
            ["search", "inventory", "--output-dir", temp_notes_dir],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 0
        
        # Should find the client meeting notes (contains "inventory")
        assert "Meeting Notes - Client Introduction" in result.output
        
        # Should not find other notes
        assert "Project Planning" not in result.output
        assert "Personal Goals" not in result.output
        assert "Shopping List" not in result.output

    def test_search_multiple_matches(self, runner, temp_notes_dir, sample_notes_with_content):
        """Test search with a term that appears in multiple notes."""
        # Act - search for 'Python' which should be in two notes
        result = runner.invoke(cli, 
            ["search", "Python", "--output-dir", temp_notes_dir],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 0
        
        # Should find both project planning and client meeting notes
        assert "Project Planning" in result.output
        assert "Meeting Notes - Client Introduction" in result.output
        
        # Should not find the other notes
        assert "Personal Goals" not in result.output
        assert "Shopping List" not in result.output

    def test_search_case_insensitive(self, runner, temp_notes_dir, sample_notes_with_content):
        """Test that search is case-insensitive."""
        # Act - search for 'python' (lowercase) which should match 'Python' (uppercase) in notes
        result = runner.invoke(cli, 
            ["search", "python", "--output-dir", temp_notes_dir],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 0
        
        # Should find both notes with 'Python' in them, despite different case
        assert "Project Planning" in result.output
        assert "Meeting Notes - Client Introduction" in result.output

    def test_search_in_tags(self, runner, temp_notes_dir, sample_notes_with_content):
        """Test searching in note tags."""
        # Act - search for 'important' which is a tag on the client meeting
        result = runner.invoke(cli, 
            ["search", "important", "--output-dir", temp_notes_dir],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 0
        
        # Should find only the client meeting notes
        assert "Meeting Notes - Client Introduction" in result.output
        
        # Should not find the other notes
        assert "Project Planning" not in result.output
        assert "Personal Goals" not in result.output
        assert "Shopping List" not in result.output

    def test_search_in_title(self, runner, temp_notes_dir, sample_notes_with_content):
        """Test searching in note titles."""
        # Act - search for 'Shopping' which is in a title
        result = runner.invoke(cli, 
            ["search", "Shopping", "--output-dir", temp_notes_dir],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 0
        
        # Should find only the shopping list note
        assert "Shopping List" in result.output
        
        # Should not find the other notes
        assert "Project Planning" not in result.output
        assert "Meeting Notes - Client Introduction" not in result.output
        assert "Personal Goals" not in result.output

    def test_search_partial_word_matching(self, runner, temp_notes_dir, sample_notes_with_content):
        """Test searching with partial word matching."""
        # Act - search for 'plan' which should match 'planning', 'plane', etc.
        result = runner.invoke(cli, 
            ["search", "plan", "--output-dir", temp_notes_dir],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 0
        
        # Should find 'Project Planning' (title and content has 'planning')
        assert "Project Planning" in result.output

    def test_search_with_no_results(self, runner, temp_notes_dir, sample_notes_with_content):
        """Test search with a term that doesn't match any notes."""
        # Act - search for a term that shouldn't be in any notes
        result = runner.invoke(cli, 
            ["search", "xylophone", "--output-dir", temp_notes_dir],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 0
        assert "No notes found matching" in result.output

    def test_search_displays_relevant_context(self, runner, temp_notes_dir, sample_notes_with_content):
        """Test that search results include some context from the matching content."""
        # Act - search for a specific term
        result = runner.invoke(cli, 
            ["search", "Budget", "--output-dir", temp_notes_dir],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 0
        
        # Should find both notes with budget information
        assert "Project Planning" in result.output
        assert "Meeting Notes - Client Introduction" in result.output
        
        # Should show context around the matches
        assert "$50,000" in result.output or "50,000" in result.output
        assert "$40,000" in result.output or "40,000" in result.output

    def test_search_with_special_characters(self, runner, temp_notes_dir, sample_notes_with_content):
        """Test search with special characters and symbols."""
        # Act - search for a term with special characters
        result = runner.invoke(cli, 
            ["search", "$40,000", "--output-dir", temp_notes_dir],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 0
        
        # Should find the client meeting notes
        assert "Meeting Notes - Client Introduction" in result.output
        
        # Should not find the other notes
        assert "Project Planning" not in result.output
        assert "Personal Goals" not in result.output
        assert "Shopping List" not in result.output

    def test_search_multiple_words(self, runner, temp_notes_dir, sample_notes_with_content):
        """Test searching for multiple words together."""
        # Act - search for multiple words
        result = runner.invoke(cli, 
            ["search", "open-source projects", "--output-dir", temp_notes_dir],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 0
        
        # Should find the personal goals note
        assert "Personal Goals" in result.output
        
        # Should not find the other notes
        assert "Project Planning" not in result.output
        assert "Meeting Notes - Client Introduction" not in result.output
        assert "Shopping List" not in result.output

    def test_search_custom_output_dir(self, runner):
        """Test 'search' command with a custom output directory."""
        with tempfile.TemporaryDirectory() as main_dir:
            # Create a custom output directory
            custom_dir = os.path.join(main_dir, "custom-notes")
            os.makedirs(custom_dir)
            
            # Create a note in the custom directory with specific content
            title = "Test Note in Custom Dir"
            result = runner.invoke(new, 
                [title, "--output-dir", custom_dir],
                catch_exceptions=False
            )
            assert result.exit_code == 0
            
            # Modify the note to include searchable content
            note_path = os.path.join(custom_dir, "test-note-in-custom-dir.md")
            with open(note_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Add unique searchable text
            modified_content = content.replace(
                "Add more detailed information here...",
                "This is a unique search phrase for testing."
            )
            
            with open(note_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
                
            # Act - search in the custom directory
            search_result = runner.invoke(cli, 
                ["search", "unique search phrase", "--output-dir", custom_dir],
                catch_exceptions=False
            )
            
            # Assert
            assert search_result.exit_code == 0
            assert title in search_result.output
            
            # Also verify searching in a different directory doesn't find it
            different_dir = os.path.join(main_dir, "different-dir")
            os.makedirs(different_dir)
            
            different_result = runner.invoke(cli, 
                ["search", "unique search phrase", "--output-dir", different_dir],
                catch_exceptions=False
            )
            
            assert different_result.exit_code == 0
            assert "No notes found" in different_result.output
            assert title not in different_result.output

    def test_search_with_nonexistent_directory(self, runner):
        """Test search with a directory that doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_dir = os.path.join(temp_dir, "does_not_exist")
            
            # Act
            result = runner.invoke(cli, 
                ["search", "anything", "--output-dir", nonexistent_dir],
                catch_exceptions=False
            )
            
            # Assert
            assert result.exit_code == 0
            assert "No notes found" in result.output