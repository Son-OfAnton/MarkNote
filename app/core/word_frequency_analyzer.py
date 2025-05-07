import re
import string
from collections import Counter
from typing import List, Dict, Tuple, Optional, Set, Any, Union

class WordFrequencyAnalyzer:
    """
    Analyzes word frequency in note content.
    """
    
    def __init__(self, 
                 stopwords: Optional[Set[str]] = None,
                 min_word_length: int = 3,
                 max_words: int = 100,
                 case_sensitive: bool = False):
        """
        Initialize the word frequency analyzer.
        
        Args:
            stopwords: Optional set of words to exclude from analysis (common words like "the", "and", etc.)
            min_word_length: Minimum length of words to include in analysis
            max_words: Maximum number of words to return in results
            case_sensitive: Whether to treat different cases as different words
        """
        self.stopwords = stopwords or self._get_default_stopwords()
        self.min_word_length = min_word_length
        self.max_words = max_words
        self.case_sensitive = case_sensitive
    
    def _get_default_stopwords(self) -> Set[str]:
        """
        Get a default set of English stopwords.
        
        Returns:
            A set of common English words to exclude from analysis.
        """
        return {
            "the", "and", "a", "an", "in", "on", "at", "to", "for", "of", "with", "by",
            "is", "was", "are", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "done",
            "i", "you", "he", "she", "it", "we", "they",
            "me", "him", "her", "us", "them",
            "my", "your", "his", "its", "our", "their",
            "this", "that", "these", "those",
            "am", "is", "are", "was", "were", "be", "been",
            "can", "could", "will", "would", "shall", "should",
            "may", "might", "must", "ought",
            "not", "no", "none", "nothing",
            "from", "about", "but", "than", "as", "if", "when", "than", "because", "while", "where", "how",
            "all", "any", "both", "each", "few", "many", "more", "most", "other", "some", "such",
            "just", "very", "so", "too", "then", "there", "here"
        }
    
    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text by removing Markdown formatting, code blocks, etc.
        
        Args:
            text: The text to preprocess
            
        Returns:
            Preprocessed text
        """
        # Remove code blocks (both ```code``` and inline `code`)
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'`.*?`', '', text)
        
        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)
        
        # Remove Markdown links [text](url)
        text = re.sub(r'\[.*?\]\(.*?\)', '', text)
        
        # Remove Markdown formatting symbols (#, *, _, etc.)
        text = re.sub(r'[#*_~]', ' ', text)
        
        # Remove HTML tags if present
        text = re.sub(r'<.*?>', '', text)
        
        return text
    
    def analyze(self, text: str) -> List[Tuple[str, int]]:
        """
        Analyze word frequency in text.
        
        Args:
            text: The text to analyze
            
        Returns:
            List of (word, count) tuples sorted by frequency (highest first)
        """
        # Preprocess text
        processed_text = self._preprocess_text(text)
        
        # Convert case if not case-sensitive
        if not self.case_sensitive:
            processed_text = processed_text.lower()
        
        # Tokenize text (split into words)
        # This regex splits on any non-alphanumeric character
        words = re.findall(r'\b[a-zA-Z0-9]+\b', processed_text)
        
        # Filter words by length and exclude stopwords
        filtered_words = [
            word for word in words 
            if len(word) >= self.min_word_length and 
            (word.lower() not in self.stopwords if not self.case_sensitive else word not in self.stopwords)
        ]
        
        # Count word frequencies
        word_counts = Counter(filtered_words)
        
        # Sort by frequency (highest first) and limit to max_words
        most_common = word_counts.most_common(self.max_words)
        
        return most_common
    
    def generate_report(self, 
                       text: str, 
                       include_stats: bool = True,
                       include_raw: bool = False) -> Dict[str, Any]:
        """
        Generate a comprehensive word frequency report.
        
        Args:
            text: The text to analyze
            include_stats: Whether to include general statistics
            include_raw: Whether to include the original and processed text
            
        Returns:
            Dictionary with analysis results
        """
        # Get word frequency
        word_frequencies = self.analyze(text)
        
        # Prepare report
        report = {
            "word_frequencies": [{"word": word, "count": count} for word, count in word_frequencies],
            "total_unique_words": len(word_frequencies)
        }
        
        # Add statistics if requested
        if include_stats:
            # Preprocess text for statistics
            processed_text = self._preprocess_text(text)
            
            # Calculate statistics
            total_chars = len(text)
            total_processed_chars = len(processed_text)
            total_words = len(re.findall(r'\b\w+\b', processed_text))
            
            # All words, including those below min_length and stopwords
            all_words = re.findall(r'\b[a-zA-Z0-9]+\b', processed_text.lower())
            total_unique_all = len(set(all_words))
            
            report["statistics"] = {
                "total_characters": total_chars,
                "total_words": total_words,
                "total_unique_words_all": total_unique_all,
                "total_analyzed_words": sum(count for _, count in word_frequencies),
                "character_to_word_ratio": round(total_chars / total_words if total_words > 0 else 0, 2),
                "most_frequent_word": word_frequencies[0][0] if word_frequencies else None,
                "most_frequent_count": word_frequencies[0][1] if word_frequencies else 0,
                "analysis_settings": {
                    "min_word_length": self.min_word_length,
                    "max_words": self.max_words,
                    "case_sensitive": self.case_sensitive,
                    "stopwords_count": len(self.stopwords),
                }
            }
        
        # Add raw text if requested
        if include_raw:
            report["raw"] = {
                "original_text": text,
                "processed_text": self._preprocess_text(text)
            }
            
        return report

def analyze_note_word_frequency(
    note_content: str,
    stopwords: Optional[Set[str]] = None,
    min_word_length: int = 3,
    max_words: int = 100,
    case_sensitive: bool = False,
    include_stats: bool = True,
    include_raw: bool = False
) -> Dict[str, Any]:
    """
    Analyze word frequency in a note.
    
    Args:
        note_content: The content of the note
        stopwords: Optional set of words to exclude from analysis
        min_word_length: Minimum length of words to include in analysis
        max_words: Maximum number of words to return in results
        case_sensitive: Whether to treat different cases as different words
        include_stats: Whether to include general statistics
        include_raw: Whether to include the original and processed text
        
    Returns:
        Dictionary with analysis results
    """
    analyzer = WordFrequencyAnalyzer(
        stopwords=stopwords,
        min_word_length=min_word_length,
        max_words=max_words,
        case_sensitive=case_sensitive
    )
    
    return analyzer.generate_report(
        text=note_content,
        include_stats=include_stats,
        include_raw=include_raw
    )