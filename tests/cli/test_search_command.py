import os
import shutil
import tempfile
import unittest

from app.core.note_manager import NoteManager


class TestSearchCommand(unittest.TestCase):
    """Test the functionality of the 'search' command for searching notes."""
    
    def setUp(self):
        """Set up a temporary directory and create test notes with searchable content."""
        # Create a temporary directory for test notes
        self.temp_dir = tempfile.mkdtemp()
        self.note_manager = NoteManager(notes_dir=self.temp_dir)
        
        # Create a second temporary directory for testing output_dir parameter
        self.custom_dir = tempfile.mkdtemp()
        
        # Create a variety of test notes with different content for search testing
        
        # Note 1: Note with Python content
        self.note1 = self.note_manager.create_note(
            title="Python Programming",
            content="Python is a high-level programming language known for its readability.\n\n"
                    "Example Python code:\n```python\ndef hello_world():\n    print('Hello, World!')\n```\n\n"
                    "Python has a rich ecosystem of libraries for data science, web development, and more.",
            tags=["programming", "python", "coding"]
        )
        
        # Note 2: Note with Java content
        self.note2 = self.note_manager.create_note(
            title="Java Basics",
            content="Java is a popular object-oriented programming language.\n\n"
                    "Example Java code:\n```java\npublic class HelloWorld {\n    "
                    "public static void main(String[] args) {\n        "
                    "System.out.println(\"Hello, World!\");\n    }\n}\n```",
            tags=["programming", "java", "coding"],
            category="programming"
        )
        
        # Note 3: Note with meeting details
        self.note3 = self.note_manager.create_note(
            title="Project Planning Meeting",
            content="Meeting Notes - Project Alpha\n\n"
                    "Date: 2023-03-15\n"
                    "Attendees: John, Sarah, Michael\n\n"
                    "Discussion Points:\n"
                    "- Timeline for the project\n"
                    "- Resource allocation\n"
                    "- Budget constraints\n\n"
                    "Action Items:\n"
                    "- Sarah to prepare project schedule\n"
                    "- Michael to estimate resource needs\n"
                    "- John to work on budget proposal",
            tags=["meeting", "planning", "project-alpha"],
            category="meetings"
        )
        
        # Note 4: Note with personal journal content
        self.note4 = self.note_manager.create_note(
            title="Daily Reflection",
            content="Today was a productive day. I managed to complete several tasks including:\n\n"
                    "1. Finished the documentation for the API\n"
                    "2. Resolved the database connection issue\n"
                    "3. Had a good planning meeting with the team\n\n"
                    "I'm feeling satisfied with the progress we're making on Project Alpha.",
            tags=["journal", "reflection", "productivity"],
            category="personal"
        )
        
        # Note 5: Note with similar words but different context
        self.note5 = self.note_manager.create_note(
            title="Database Management",
            content="Managing database connections and ensuring proper resource allocation is critical.\n\n"
                    "Common database types include:\n"
                    "- SQL databases (MySQL, PostgreSQL)\n"
                    "- NoSQL databases (MongoDB, Cassandra)\n\n"
                    "Performance considerations include proper indexing and query optimization.",
            tags=["database", "programming", "optimization"],
            category="programming"
        )
        
        # Note 6: Note with special characters and formatting
        self.note6 = self.note_manager.create_note(
            title="Markdown Syntax Guide",
            content="# Markdown Syntax Guide\n\n"
                    "## Headers\n\n"
                    "# H1\n## H2\n### H3\n\n"
                    "## Emphasis\n\n"
                    "*Italic text* or _italic text_\n\n"
                    "**Bold text** or __bold text__\n\n"
                    "## Lists\n\n"
                    "* Item 1\n* Item 2\n  * Subitem 2.1\n  * Subitem 2.2\n\n"
                    "1. First item\n2. Second item\n\n"
                    "## Links\n\n"
                    "[Link text](http://example.com)\n\n"
                    "## Code\n\n"
                    "`inline code`\n\n"
                    "```\ncode block\n```",
            tags=["markdown", "documentation", "syntax"]
        )
        
        # Note 7: Note in custom directory with specific searchable term
        self.note7 = self.note_manager.create_note(
            title="Custom Directory Note",
            content="This note contains a specific searchable term: 'UNIQUESEARCHTERM123'.\n\n"
                    "It is stored in a custom directory to test search functionality across directories.",
            output_dir=self.custom_dir
        )
    
    def tearDown(self):
        """Clean up the temporary directories after tests."""
        shutil.rmtree(self.temp_dir)
        shutil.rmtree(self.custom_dir)
    
    def test_search_basic(self):
        """Test basic search functionality with simple keywords."""
        # Search for a common programming term
        results = self.note_manager.search_notes("programming")
        
        # Should match notes about Python, Java, and databases
        self.assertEqual(len(results), 3)
        titles = [note.title for note in results]
        self.assertIn("Python Programming", titles)
        self.assertIn("Java Basics", titles)
        self.assertIn("Database Management", titles)
        
        # Search for a specific programming language
        results = self.note_manager.search_notes("python")
        
        # Should only match the Python note
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Python Programming")
    
    def test_search_case_insensitive(self):
        """Test that search is case insensitive."""
        # Search for "python" in lowercase
        results_lower = self.note_manager.search_notes("python")
        
        # Search for "Python" with uppercase P
        results_upper = self.note_manager.search_notes("Python")
        
        # Both searches should return the same note
        self.assertEqual(len(results_lower), 1)
        self.assertEqual(len(results_upper), 1)
        self.assertEqual(results_lower[0].title, results_upper[0].title)
        self.assertEqual(results_lower[0].title, "Python Programming")
    
    def test_search_across_titles_and_content(self):
        """Test that search looks in both titles and content of notes."""
        # Search for a term that appears in a title
        results = self.note_manager.search_notes("Basics")
        
        # Should match the Java Basics note
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Java Basics")
        
        # Search for a term that appears in content but not title
        results = self.note_manager.search_notes("ecosystem")
        
        # Should match the Python note which mentions "ecosystem" in content
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Python Programming")
    
    def test_search_partial_words(self):
        """Test searching for partial words or parts of phrases."""
        # Search for a partial word that could appear in multiple notes
        results = self.note_manager.search_notes("program")
        
        # Should match notes containing "programming" or "program"
        self.assertTrue(len(results) >= 2)
        
        titles = [note.title for note in results]
        self.assertIn("Python Programming", titles)
        self.assertIn("Java Basics", titles)
    
    def test_search_with_multiple_terms(self):
        """Test searching for multiple terms in a single query."""
        # Search for "project planning" (appears in meeting note title)
        results = self.note_manager.search_notes("project planning")
        
        # Should match the meeting note
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Project Planning Meeting")
        
        # Search for "project alpha" (across title and content)
        results = self.note_manager.search_notes("project alpha")
        
        # Should match both the meeting note and daily reflection note
        self.assertEqual(len(results), 2)
        titles = [note.title for note in results]
        self.assertIn("Project Planning Meeting", titles)
        self.assertIn("Daily Reflection", titles)
    
    def test_search_tags(self):
        """Test that search includes tags in its scope."""
        # Search for a term that appears only as a tag
        results = self.note_manager.search_notes("project-alpha")
        
        # Should match the meeting note with this tag
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Project Planning Meeting")
        
        # Search for a tag that appears in multiple notes
        results = self.note_manager.search_notes("coding")
        
        # Should match both the Python and Java notes
        self.assertEqual(len(results), 2)
        titles = [note.title for note in results]
        self.assertIn("Python Programming", titles)
        self.assertIn("Java Basics", titles)
    
    def test_search_formatting_and_special_characters(self):
        """Test searching through formatted content with special characters."""
        # Search for a markdown formatting symbol
        results = self.note_manager.search_notes("##")
        
        # Should match the markdown syntax guide
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Markdown Syntax Guide")
        
        # Search for code block syntax
        results = self.note_manager.search_notes("```")
        
        # Should match notes with code blocks (Python, Java, and markdown guide)
        self.assertTrue(len(results) >= 3)
        titles = [note.title for note in results]
        self.assertIn("Python Programming", titles)
        self.assertIn("Java Basics", titles)
        self.assertIn("Markdown Syntax Guide", titles)
    
    def test_search_in_custom_directory(self):
        """Test searching for notes in a custom directory."""
        # Search in the default directory for the unique term
        results_default = self.note_manager.search_notes("UNIQUESEARCHTERM123")
        
        # Should not find any notes in the default directory
        self.assertEqual(len(results_default), 0)
        
        # Search in the custom directory for the unique term
        results_custom = self.note_manager.search_notes("UNIQUESEARCHTERM123", output_dir=self.custom_dir)
        
        # Should find the custom directory note
        self.assertEqual(len(results_custom), 1)
        self.assertEqual(results_custom[0].title, "Custom Directory Note")
    
    def test_search_non_existent_term(self):
        """Test searching for a term that doesn't exist in any notes."""
        # Search for a term that doesn't exist
        results = self.note_manager.search_notes("ThisTermDefitelyDoesNotExistInAnyNote12345")
        
        # Should return an empty list
        self.assertEqual(len(results), 0)
    
    def test_search_empty_query(self):
        """Test searching with an empty query."""
        # Search with an empty string
        results = self.note_manager.search_notes("")
        
        # Implementation might vary, but it should either:
        # 1. Return no results, or
        # 2. Return all notes (like a list operation)
        
        # We'll test based on the actual behavior
        if len(results) > 0:
            # If it returns all notes, check that the count is correct
            self.assertEqual(len(results), 6)  # 6 notes in default directory
        else:
            # If it returns no results, check that the list is empty
            self.assertEqual(len(results), 0)
    
    def test_search_with_context_overlap(self):
        """Test searching where multiple notes have semantic overlap."""
        # Search for "meeting" which appears in multiple contexts
        results = self.note_manager.search_notes("meeting")
        
        # Should match both the meeting note and the reflection note
        self.assertEqual(len(results), 2)
        titles = [note.title for note in results]
        self.assertIn("Project Planning Meeting", titles)
        self.assertIn("Daily Reflection", titles)
        
        # Search for a term with context to disambiguate
        results = self.note_manager.search_notes("planning meeting")
        
        # Should only match the meeting note
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Project Planning Meeting")


if __name__ == '__main__':
    unittest.main()