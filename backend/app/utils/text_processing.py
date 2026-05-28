"""
Text processing utilities for content extraction and sanitization.
"""
import re
import html
from typing import Dict, List, Optional
import unicodedata
from langdetect import detect, LangDetectException
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)


def sanitize_text(text: str) -> str:
    """
    Sanitize text by removing HTML entities, extra whitespace, and control characters.
    
    Args:
        text: Raw text to sanitize
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
        
    # Decode HTML entities
    text = html.unescape(text)
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove control characters except newlines and tabs
    text = ''.join(char for char in text if char == '\n' or char == '\t' or not unicodedata.category(char).startswith('C'))
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    return text


def clean_text(text: str, lowercase: bool = False, remove_punctuation: bool = False) -> str:
    """
    Clean text by normalizing whitespace and optionally lowercasing/removing punctuation.
    
    Args:
        text: Text to clean
        lowercase: Whether to convert to lowercase
        remove_punctuation: Whether to remove punctuation
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # First sanitize
    text = sanitize_text(text)
    
    # Optionally lowercase
    if lowercase:
        text = text.lower()
    
    # Optionally remove punctuation
    if remove_punctuation:
        text = re.sub(r'[^\w\s]', '', text)
    
    # Normalize multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def clean_tokens(tokens: List[str], language: str = 'english') -> List[str]:
    """
    Clean a list of tokens by removing stopwords and non-alphabetic tokens.
    
    Args:
        tokens: List of tokens to clean
        language: Language for stopword removal
        
    Returns:
        Cleaned list of tokens
    """
    try:
        stop_words = set(stopwords.words(language))
    except Exception:
        stop_words = set()
    
    cleaned = []
    for token in tokens:
        token = token.lower().strip()
        if token and token.isalpha() and token not in stop_words and len(token) > 1:
            cleaned.append(token)
    
    return cleaned


def extract_entities(text: str, entity_types: Optional[List[str]] = None) -> Dict[str, List[str]]:
    """
    Extract named entities from text using simple pattern matching.
    
    Args:
        text: Text to extract entities from
        entity_types: Optional list of entity types to extract
        
    Returns:
        Dictionary mapping entity types to lists of found entities
    """
    import re
    
    entities = {
        'emails': [],
        'urls': [],
        'phone_numbers': [],
        'dates': [],
        'currencies': []
    }
    
    # Extract emails
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    entities['emails'] = re.findall(email_pattern, text)
    
    # Extract URLs
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    entities['urls'] = re.findall(url_pattern, text)
    
    # Extract phone numbers (basic pattern)
    phone_pattern = r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\./0-9]{7,}'
    entities['phone_numbers'] = re.findall(phone_pattern, text)
    
    # Extract dates (basic patterns)
    date_patterns = [
        r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
        r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}'
    ]
    for pattern in date_patterns:
        entities['dates'].extend(re.findall(pattern, text, re.IGNORECASE))
    
    # Extract currencies
    currency_pattern = r'[\$\€\£\¥]\s*\d+(?:,\d{3})*(?:\.\d{2})?'
    entities['currencies'] = re.findall(currency_pattern, text)
    
    # Filter by requested entity types
    if entity_types:
        entities = {k: v for k, v in entities.items() if k in entity_types}
    
    return entities


def extract_snippet(text: str, query: str, max_length: int = 200, context_words: int = 10) -> str:
    """
    Extract a relevant snippet from text based on query terms.
    
    Args:
        text: Full text to extract from
        query: Search query
        max_length: Maximum snippet length
        context_words: Number of words to include before/after match
        
    Returns:
        Extracted snippet with ellipsis if truncated
    """
    if not text:
        return ""
        
    # Clean text
    text = sanitize_text(text)
    
    if len(text) <= max_length:
        return text
        
    # Extract query terms
    query_terms = [term.lower() for term in query.split() if len(term) > 2]
    
    if not query_terms:
        # If no valid query terms, return beginning of text
        return text[:max_length] + "..." if len(text) > max_length else text
        
    # Find best matching sentence
    sentences = sent_tokenize(text)
    best_sentence = None
    best_score = 0
    
    for sentence in sentences:
        sentence_lower = sentence.lower()
        score = sum(1 for term in query_terms if term in sentence_lower)
        
        if score > best_score:
            best_score = score
            best_sentence = sentence
            
    if best_sentence and len(best_sentence) <= max_length:
        return best_sentence
        
    # Find first occurrence of any query term
    text_lower = text.lower()
    first_match_pos = len(text)
    
    for term in query_terms:
        pos = text_lower.find(term)
        if pos != -1 and pos < first_match_pos:
            first_match_pos = pos
            
    if first_match_pos == len(text):
        # No match found, return beginning
        return text[:max_length] + "..."
        
    # Extract context around match
    words = text.split()
    word_positions = []
    current_pos = 0
    
    for word in words:
        word_positions.append((current_pos, current_pos + len(word)))
        current_pos += len(word) + 1  # +1 for space
        
    # Find word containing match
    match_word_idx = 0
    for idx, (start, end) in enumerate(word_positions):
        if start <= first_match_pos <= end:
            match_word_idx = idx
            break
            
    # Extract snippet with context
    start_idx = max(0, match_word_idx - context_words)
    end_idx = min(len(words), match_word_idx + context_words + 1)
    
    snippet_words = words[start_idx:end_idx]
    snippet = ' '.join(snippet_words)
    
    # Add ellipsis
    if start_idx > 0:
        snippet = "..." + snippet
    if end_idx < len(words):
        snippet = snippet + "..."
        
    # Ensure snippet isn't too long
    if len(snippet) > max_length:
        snippet = snippet[:max_length-3] + "..."
        
    return snippet


def detect_language(text: str) -> Optional[str]:
    """
    Detect the language of text.
    
    Args:
        text: Text to analyze
        
    Returns:
        ISO 639-1 language code or None if detection fails
    """
    if not text or len(text) < 20:
        return None
        
    try:
        return detect(text)
    except LangDetectException:
        return None


def calculate_text_quality(text: str, min_words: int = 50) -> float:
    """
    Calculate quality score for extracted text.
    
    Args:
        text: Text to analyze
        min_words: Minimum words for good quality
        
    Returns:
        Quality score between 0.0 and 1.0
    """
    if not text:
        return 0.0
        
    # Clean text
    text = sanitize_text(text)
    
    # Basic metrics
    words = text.split()
    word_count = len(words)
    
    if word_count < min_words:
        return word_count / min_words * 0.5
        
    # Calculate various quality indicators
    scores = []
    
    # Word count score
    word_score = min(1.0, word_count / 500)  # Normalize to 500 words
    scores.append(word_score)
    
    # Sentence structure score
    sentences = sent_tokenize(text)
    if sentences:
        avg_sentence_length = word_count / len(sentences)
        # Optimal sentence length is 15-20 words
        if 15 <= avg_sentence_length <= 20:
            sentence_score = 1.0
        elif 10 <= avg_sentence_length <= 30:
            sentence_score = 0.8
        else:
            sentence_score = 0.5
        scores.append(sentence_score)
    
    # Vocabulary diversity score
    unique_words = set(word.lower() for word in words if len(word) > 3)
    diversity_score = min(1.0, len(unique_words) / (word_count * 0.5))
    scores.append(diversity_score)
    
    # Alphanumeric ratio (detect gibberish)
    alphanumeric_chars = sum(1 for char in text if char.isalnum() or char.isspace())
    total_chars = len(text)
    if total_chars > 0:
        alphanumeric_ratio = alphanumeric_chars / total_chars
        scores.append(alphanumeric_ratio)
    
    # Calculate final score
    return sum(scores) / len(scores)


def extract_keywords(text: str, language: str = 'english', max_keywords: int = 10) -> List[str]:
    """
    Extract keywords from text using TF-IDF approach.
    
    Args:
        text: Text to analyze
        language: Language for stopwords
        max_keywords: Maximum number of keywords to return
        
    Returns:
        List of keywords
    """
    if not text:
        return []
        
    # Tokenize and clean
    words = word_tokenize(text.lower())
    
    # Remove stopwords and short words
    try:
        stop_words = set(stopwords.words(language))
    except:
        stop_words = set()
        
    keywords = [
        word for word in words 
        if word.isalnum() and len(word) > 3 and word not in stop_words
    ]
    
    # Count frequencies
    word_freq = {}
    for word in keywords:
        word_freq[word] = word_freq.get(word, 0) + 1
        
    # Sort by frequency and return top keywords
    sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    
    return [word for word, _ in sorted_keywords[:max_keywords]]


def truncate_text(text: str, max_length: int, ellipsis: str = "...") -> str:
    """
    Truncate text to maximum length, breaking at word boundaries.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        ellipsis: String to append if truncated
        
    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text
        
    # Find last space before max_length
    truncate_at = text.rfind(' ', 0, max_length - len(ellipsis))
    
    if truncate_at == -1:
        # No space found, hard truncate
        return text[:max_length - len(ellipsis)] + ellipsis
        
    return text[:truncate_at] + ellipsis


def normalize_url(url: str) -> str:
    """
    Normalize URL for comparison and deduplication.
    
    Args:
        url: URL to normalize
        
    Returns:
        Normalized URL
    """
    if not url:
        return ""
        
    # Remove trailing slashes
    url = url.rstrip('/')
    
    # Remove common tracking parameters
    tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'fbclid', 'gclid']
    
    for param in tracking_params:
        url = re.sub(rf'[?&]{param}=[^&]*', '', url)
        
    # Clean up multiple ? or &
    url = re.sub(r'\?&', '?', url)
    url = re.sub(r'&&+', '&', url)
    url = url.rstrip('?&')
    
    return url
