from typing import List
import re

def clean_text(text: str) -> str:
    """Clean the input text by removing unwanted characters and extra spaces."""
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with a single space
    return text.strip()

def tokenize(text: str) -> List[str]:
    """Tokenize the input text into words."""
    return text.split()

def normalize_text(text: str) -> str:
    """Normalize the input text to lowercase."""
    return text.lower()

def extract_keywords(text: str, num_keywords: int = 5) -> List[str]:
    """Extract keywords from the input text."""
    words = tokenize(text)
    word_freq = {}
    for word in words:
        word_freq[word] = word_freq.get(word, 0) + 1
    sorted_keywords = sorted(word_freq, key=word_freq.get, reverse=True)
    return sorted_keywords[:num_keywords]