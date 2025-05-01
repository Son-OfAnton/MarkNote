"""
Tests for the PDF export utility functionality.
"""
import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock

from app.utils.pdf_exporter import export_note_to_pdf, convert_markdown_to_pdf

# Sample Markdown content for tests
SAMPLE_MARKDOWN = """
# Test Note

This is a test note with *italic* and **bold** text.

## Section 1

- List item 1
- List item 2

## Section 2

1. Numbered item 1
2. Numbered item 2

```python
def hello_world():
    print("Hello, World!")
```

> This is a blockquote.
"""

# Sample metadata for tests
SAMPLE_METADATA = {
    "title": "Test Note",
    "created_at": "2024-06-26T10:00:00",
    "updated_at": "2024-06-26T11:00:00",
    "tags": ["test", "example", "pdf"],
    "category": "Tests"
}


class TestPdfExporter:
    """Tests for the PDF export utility functions."""

    def test_export_note_to_pdf_success(self, monkeypatch):
        """Test successful export of note content to PDF."""
        # Mock WeasyPrint's HTML class
        mock_html = MagicMock()
        monkeypatch.setattr("app.utils.pdf_exporter.HTML", mock_html)

        with tempfile.NamedTemporaryFile(suffix='.pdf') as temp_file:
            result = export_note_to_pdf(
                note_content=SAMPLE_MARKDOWN,
                title="Test Note",
                output_path=temp_file.name,
                metadata=SAMPLE_METADATA
            )
            
            # Check the result is True for success
            assert result is True
            # Verify HTML was called and write_pdf was called
            mock_html.assert_called_once()
            mock_html.return_value.write_pdf.assert_called_once_with(temp_file.name)

    def test_export_note_to_pdf_failure(self, monkeypatch):
        """Test handling of failure during PDF export."""
        # Mock WeasyPrint's HTML class to raise an exception
        mock_html = MagicMock()
        mock_html.side_effect = Exception("Mock PDF generation error")
        monkeypatch.setattr("app.utils.pdf_exporter.HTML", mock_html)

        with tempfile.NamedTemporaryFile(suffix='.pdf') as temp_file:
            result = export_note_to_pdf(
                note_content=SAMPLE_MARKDOWN,
                title="Test Note",
                output_path=temp_file.name,
                metadata=SAMPLE_METADATA
            )
            
            # Check the result is False for failure
            assert result is False

    def test_export_with_custom_css(self, monkeypatch):
        """Test PDF export with custom CSS."""
        # Mock WeasyPrint's HTML class
        mock_html = MagicMock()
        monkeypatch.setattr("app.utils.pdf_exporter.HTML", mock_html)
        
        # Custom CSS
        custom_css = "body { font-family: Arial; color: #333; }"

        with tempfile.NamedTemporaryFile(suffix='.pdf') as temp_file:
            result = export_note_to_pdf(
                note_content=SAMPLE_MARKDOWN,
                title="Test Note",
                output_path=temp_file.name,
                metadata=SAMPLE_METADATA,
                custom_css=custom_css
            )
            
            # Check the result is True for success
            assert result is True
            
            # Verify HTML was called
            mock_html.assert_called_once()
            
            # Extract the HTML string passed to the constructor
            html_string = mock_html.call_args[1]['filename']
            
            # Read the content of the temp HTML file
            with open(html_string, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Check if the custom CSS is in the content
            assert custom_css in html_content
            
            # Verify the PDF was written
            mock_html.return_value.write_pdf.assert_called_once_with(temp_file.name)

    def test_export_without_metadata(self, monkeypatch):
        """Test PDF export with metadata display disabled."""
        # Mock WeasyPrint's HTML class
        mock_html = MagicMock()
        monkeypatch.setattr("app.utils.pdf_exporter.HTML", mock_html)

        with tempfile.NamedTemporaryFile(suffix='.pdf') as temp_file:
            result = export_note_to_pdf(
                note_content=SAMPLE_MARKDOWN,
                title="Test Note",
                output_path=temp_file.name,
                metadata=SAMPLE_METADATA,
                include_metadata=False
            )
            
            # Check the result is True for success
            assert result is True
            
            # Verify HTML was called
            mock_html.assert_called_once()
            
            # Extract the HTML string passed to the constructor
            html_string = mock_html.call_args[1]['filename']
            
            # Read the content of the temp HTML file
            with open(html_string, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Check if the metadata section is not included
            assert 'class="metadata"' not in html_content

    def test_convert_markdown_to_pdf(self, monkeypatch):
        """Test conversion of a Markdown file to PDF."""
        # Mock file_handler.parse_frontmatter function
        mock_parse_frontmatter = MagicMock(
            return_value=(SAMPLE_METADATA, SAMPLE_MARKDOWN)
        )
        monkeypatch.setattr(
            "app.utils.file_handler.parse_frontmatter", 
            mock_parse_frontmatter
        )
        
        # Mock open to return our sample markdown
        mock_open = MagicMock()
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = SAMPLE_MARKDOWN
        mock_open.return_value = mock_file
        monkeypatch.setattr("builtins.open", mock_open)
        
        # Mock export_note_to_pdf to return True
        mock_export = MagicMock(return_value=True)
        monkeypatch.setattr(
            "app.utils.pdf_exporter.export_note_to_pdf", 
            mock_export
        )
        
        # Test conversion
        result = convert_markdown_to_pdf(
            markdown_path="test.md",
            output_path="test.pdf"
        )
        
        # Check the result is True for success
        assert result is True
        
        # Verify parse_frontmatter was called
        mock_parse_frontmatter.assert_called_once_with(SAMPLE_MARKDOWN)
        
        # Verify export_note_to_pdf was called with correct parameters
        mock_export.assert_called_once()
        args, kwargs = mock_export.call_args
        assert kwargs["note_content"] == SAMPLE_MARKDOWN
        assert kwargs["title"] == SAMPLE_METADATA["title"]
        assert kwargs["output_path"] == "test.pdf"
        assert kwargs["metadata"] == SAMPLE_METADATA

    def test_convert_markdown_to_pdf_without_frontmatter(self, monkeypatch):
        """Test conversion of a Markdown file without frontmatter."""
        # Mock file_handler.parse_frontmatter to return empty metadata
        mock_parse_frontmatter = MagicMock(
            return_value=({}, SAMPLE_MARKDOWN)
        )
        monkeypatch.setattr(
            "app.utils.file_handler.parse_frontmatter", 
            mock_parse_frontmatter
        )
        
        # Mock open to return our sample markdown
        mock_open = MagicMock()
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = SAMPLE_MARKDOWN
        mock_open.return_value = mock_file
        monkeypatch.setattr("builtins.open", mock_open)
        
        # Mock export_note_to_pdf to return True
        mock_export = MagicMock(return_value=True)
        monkeypatch.setattr(
            "app.utils.pdf_exporter.export_note_to_pdf", 
            mock_export
        )
        
        # Test conversion
        result = convert_markdown_to_pdf(
            markdown_path="test.md",
            output_path="test.pdf"
        )
        
        # Check the result is True for success
        assert result is True
        
        # Verify export_note_to_pdf was called with the filename as title
        mock_export.assert_called_once()
        args, kwargs = mock_export.call_args
        assert kwargs["title"] == "test"  # Extracted from filename

    def test_convert_markdown_to_pdf_with_custom_title(self, monkeypatch):
        """Test conversion of a Markdown file with a custom title."""
        # Mock file_handler.parse_frontmatter to return empty metadata
        mock_parse_frontmatter = MagicMock(
            return_value=({}, SAMPLE_MARKDOWN)
        )
        monkeypatch.setattr(
            "app.utils.file_handler.parse_frontmatter", 
            mock_parse_frontmatter
        )
        
        # Mock open to return our sample markdown
        mock_open = MagicMock()
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = SAMPLE_MARKDOWN
        mock_open.return_value = mock_file
        monkeypatch.setattr("builtins.open", mock_open)
        
        # Mock export_note_to_pdf to return True
        mock_export = MagicMock(return_value=True)
        monkeypatch.setattr(
            "app.utils.pdf_exporter.export_note_to_pdf", 
            mock_export
        )
        
        # Test conversion with custom title
        custom_title = "Custom Title"
        result = convert_markdown_to_pdf(
            markdown_path="test.md",
            output_path="test.pdf",
            title=custom_title
        )
        
        # Check the result is True for success
        assert result is True
        
        # Verify export_note_to_pdf was called with the custom title
        mock_export.assert_called_once()
        args, kwargs = mock_export.call_args
        assert kwargs["title"] == custom_title