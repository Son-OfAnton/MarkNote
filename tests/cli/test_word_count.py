"""
Tests for the word count functionality in both Note model and NoteManager.
"""
import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Optional

from app.core.note_manager import NoteManager
from app.models.note import Note

class TestNoteWordCount:
    """
    Tests for the word count methods in the Note class.
    """
    
    def test_get_word_count_empty_content(self):
        """Test word count for empty content."""
        note = Note(title="Test Note", content="")
        assert note.get_word_count() == 0, "Empty content should have 0 words"
        
    def test_get_word_count_single_word(self):
        """Test word count for single word content."""
        note = Note(title="Test Note", content="Hello")
        assert note.get_word_count() == 1, "Single word content should have 1 word"
        
    def test_get_word_count_multiple_words(self):
        """Test word count for content with multiple words."""
        note = Note(title="Test Note", content="This is a test note with multiple words")
        assert note.get_word_count() == 8, "Should count 8 words"
        
    def test_get_word_count_with_newlines(self):
        """Test word count for content with newlines."""
        note = Note(title="Test Note", content="Line one\nLine two\nLine three")
        assert note.get_word_count() == 6, "Should count 6 words across multiple lines"
        
    def test_get_word_count_with_extra_whitespace(self):
        """Test that extra whitespace doesn't affect word count."""
        note = Note(title="Test Note", content="  Extra  spaces    between    words  ")
        assert note.get_word_count() == 4, "Should count 4 words regardless of extra spaces"
        
    def test_get_statistics_empty_content(self):
        """Test statistics for empty content."""
        note = Note(title="Test Note", content="")
        stats = note.get_statistics()
        
        assert stats["word_count"] == 0, "Empty content should have 0 words"
        assert stats["character_count"] == 0, "Empty content should have 0 characters"
        assert stats["character_count_no_spaces"] == 0, "Empty content should have 0 non-space characters"
        assert stats["line_count"] == 1, "Empty content should have 1 line"
        assert stats["paragraph_count"] == 0, "Empty content should have 0 paragraphs"
        assert stats["avg_words_per_paragraph"] == 0, "Empty content should have 0 avg words per paragraph"
        
    def test_get_statistics_simple_content(self):
        """Test statistics for simple content."""
        note = Note(title="Test Note", content="This is a simple note.")
        stats = note.get_statistics()
        
        assert stats["word_count"] == 5, "Should have 5 words"
        assert stats["character_count"] == 22, "Should have 22 characters including spaces"
        assert stats["character_count_no_spaces"] == 18, "Should have 18 non-space characters"
        assert stats["line_count"] == 1, "Should have 1 line"
        assert stats["paragraph_count"] == 1, "Should have 1 paragraph"
        assert stats["avg_words_per_paragraph"] == 5, "Should have 5 words per paragraph"
        
    def test_get_statistics_complex_content(self):
        """Test statistics for more complex content with paragraphs."""
        content = "This is paragraph one.\n\nThis is the second paragraph with more words in it.\n\nAnd finally a third short paragraph."
        note = Note(title="Test Note", content=content)
        stats = note.get_statistics()
        
        assert stats["word_count"] == 19, "Should have 19 words total"
        assert stats["paragraph_count"] == 3, "Should have 3 paragraphs"
        assert abs(stats["avg_words_per_paragraph"] - (19/3)) < 0.01, "Should have correct average"
        
    def test_get_statistics_with_code_blocks(self):
        """Test statistics for content with code blocks."""
        content = """Here is some text.

```python
def hello():
    print("Hello, World!")
```

And some more text."""
        note = Note(title="Test Note", content=content)
        stats = note.get_statistics()
        
        assert stats["word_count"] == 14, "Should count code as words"
        assert stats["paragraph_count"] == 3, "Should identify 3 paragraphs"
        assert stats["line_count"] == 7, "Should count 7 lines"

class TestNoteManagerWordCount:
    """
    Tests for the word count methods in the NoteManager class.
    """
    
    def test_get_note_word_count_note_not_found(self, note_manager, temp_dir):
        """Test handling of non-existent notes."""
        success, message, stats = note_manager.get_note_word_count(
            title="NonExistentNote", 
            output_dir=temp_dir
        )
        
        assert not success, "Should return False for non-existent note"
        assert "not found" in message, "Error message should indicate note was not found"
        assert stats is None, "Statistics should be None for non-existent note"
        
    def test_get_note_word_count_simple_note(self, note_manager, temp_dir):
        """Test word count for a simple note."""
        # Create a test note
        note_manager.create_note(
            title="Test Note",
            content="This is a simple test note with ten words in it.",
            output_dir=temp_dir
        )
        
        success, message, stats = note_manager.get_note_word_count(
            title="Test Note", 
            output_dir=temp_dir
        )
        
        assert success, "Should return True for existing note"
        assert "Test Note" in message, "Message should contain note title"
        assert stats is not None, "Statistics should not be None"
        assert stats["word_count"] == 10, "Should count 10 words"
        assert stats["character_count"] == 46, "Should count 46 characters"
        
    def test_get_note_word_count_with_category(self, note_manager, temp_dir):
        """Test word count for a note in a specific category."""
        # Create test notes in different categories
        note_manager.create_note(
            title="Work Note",
            content="This is a work note with specific content.",
            category="work",
            output_dir=temp_dir
        )
        
        note_manager.create_note(
            title="Personal Note",
            content="A personal note has different text.",
            category="personal",
            output_dir=temp_dir
        )
        
        # Get word count for work note
        success, message, stats = note_manager.get_note_word_count(
            title="Work Note",
            category="work", 
            output_dir=temp_dir
        )
        
        assert success, "Should find note in work category"
        assert stats["word_count"] == 8, "Work note should have 8 words"
        
        # Get word count for personal note
        success, message, stats = note_manager.get_note_word_count(
            title="Personal Note",
            category="personal", 
            output_dir=temp_dir
        )
        
        assert success, "Should find note in personal category"
        assert stats["word_count"] == 6, "Personal note should have 6 words"
        
    def test_get_note_word_count_complex_content(self, note_manager, temp_dir):
        """Test word count for a note with complex content."""
        content = """# Heading

Paragraph one has some words.

Paragraph two has more text and more complex structure.

## Subheading

- Bullet point one
- Bullet point two

```
Code block with some text
that spans multiple lines
```

Final paragraph with conclusion."""
        
        note_manager.create_note(
            title="Complex Note",
            content=content,
            output_dir=temp_dir
        )
        
        success, message, stats = note_manager.get_note_word_count(
            title="Complex Note", 
            output_dir=temp_dir
        )
        
        assert success, "Should return True for existing note"
        assert stats is not None, "Statistics should not be None"
        assert stats["word_count"] > 30, "Should count all words including headings, bullets, and code"
        assert stats["paragraph_count"] >= 5, "Should identify multiple paragraphs"
        
    @patch('app.core.note_manager.NoteManager.get_note')
    def test_get_note_word_count_calls_get_note(self, mock_get_note, note_manager):
        """Test that get_note_word_count calls get_note with correct parameters."""
        # Create a mock note with stats
        mock_note = MagicMock()
        mock_note.get_statistics.return_value = {"word_count": 42}
        mock_get_note.return_value = mock_note
        
        # Call the method with specific parameters
        success, message, stats = note_manager.get_note_word_count(
            title="Test Note",
            category="test-category",
            output_dir="/test/dir"
        )
        
        # Verify get_note was called with the right parameters
        mock_get_note.assert_called_once_with(
            "Test Note",
            "test-category",
            "/test/dir"
        )
        
        # Verify result
        assert success, "Should return True for mocked note"
        assert stats["word_count"] == 42, "Should return mocked statistics"
