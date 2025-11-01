"""
Advanced markdown generation with citations and link analysis inspired by crawl4ai.

This module implements sophisticated markdown generation capabilities:
- Enhanced HTML to markdown conversion
- Citation management and link analysis
- Multiple output formats (raw, fit, with references)
- Link prioritization and scoring
"""

import re
import html
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any, Set
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag, NavigableString
import structlog

from app.utils.text_processing import sanitize_text
from app.services.content_filters import RelevantContentFilter

logger = structlog.get_logger(__name__)

# Pre-compile regex patterns for performance
LINK_PATTERN = re.compile(r'!?\[([^\]]+)\]\(([^)]+?)(?:\s+"([^"]*)")?\)')
CITATION_PATTERN = re.compile(r'\[(\d+)\]')
WHITESPACE_PATTERN = re.compile(r'\s+')
EMPTY_LINE_PATTERN = re.compile(r'\n\s*\n')


@dataclass
class MarkdownGenerationResult:
    """Result of markdown generation process."""
    raw_markdown: str
    fit_markdown: Optional[str] = None
    fit_html: Optional[str] = None  
    references_markdown: Optional[str] = None
    citation_map: Dict[str, int] = None
    link_analysis: Dict[str, Any] = None
    generation_metadata: Dict[str, Any] = None


@dataclass
class LinkInfo:
    """Information about a link found during processing."""
    url: str
    title: str
    text: str
    domain: str
    is_external: bool
    relevance_score: float = 0.0
    frequency: int = 1


def fast_urljoin(base: str, url: str) -> str:
    """Fast URL joining for common cases."""
    if not url:
        return base
    if url.startswith(("http://", "https://", "mailto:", "//")):
        return url
    if url.startswith("/"):
        # Handle absolute paths
        parsed_base = urlparse(base)
        return f"{parsed_base.scheme}://{parsed_base.netloc}{url}"
    return urljoin(base, url)


class MarkdownGenerationStrategy(ABC):
    """Abstract base class for markdown generation strategies."""

    def __init__(
        self,
        content_filter: Optional[RelevantContentFilter] = None,
        options: Optional[Dict[str, Any]] = None,
        verbose: bool = False,
        content_source: str = "cleaned_html",
    ):
        """
        Initialize markdown generation strategy.
        
        Args:
            content_filter: Optional content filter for generating fit markdown
            options: Additional options for markdown generation
            verbose: Enable verbose logging
            content_source: Source content type ("cleaned_html", "raw_html", "fit_html")
        """
        self.content_filter = content_filter
        self.options = options or {}
        self.verbose = verbose
        self.content_source = content_source

    @abstractmethod
    async def generate_markdown(
        self,
        input_html: str,
        base_url: str = "",
        citations: bool = True,
        **kwargs,
    ) -> MarkdownGenerationResult:
        """Generate markdown from the selected input HTML."""
        pass


class DefaultMarkdownGenerator(MarkdownGenerationStrategy):
    """
    Default implementation of markdown generation strategy.

    This generator:
    1. Generates raw markdown from cleaned HTML
    2. Converts links to citations with reference management
    3. Generates fit markdown if content filter is provided
    4. Performs link analysis and scoring
    5. Returns comprehensive MarkdownGenerationResult
    """

    def __init__(
        self,
        content_filter: Optional[RelevantContentFilter] = None,
        options: Optional[Dict[str, Any]] = None,
        content_source: str = "cleaned_html",
        **kwargs
    ):
        """Initialize default markdown generator."""
        super().__init__(
            content_filter=content_filter,
            options=options,
            verbose=kwargs.get("verbose", False),
            content_source=content_source
        )
        
        # Configuration options
        self.include_images = self.options.get("include_images", True)
        self.include_links = self.options.get("include_links", True)
        self.include_tables = self.options.get("include_tables", True)
        self.include_code = self.options.get("include_code", True)
        self.max_image_width = self.options.get("max_image_width", 800)
        self.link_preview = self.options.get("link_preview", False)

    async def generate_markdown(
        self,
        input_html: str,
        base_url: str = "",
        citations: bool = True,
        **kwargs,
    ) -> MarkdownGenerationResult:
        """Generate comprehensive markdown with citations and analysis."""
        try:
            # Parse HTML
            soup = BeautifulSoup(input_html, 'lxml')
            
            # Clean and prepare HTML
            cleaned_soup = self._clean_html(soup)
            
            # Generate raw markdown
            raw_markdown = self._html_to_markdown(cleaned_soup, base_url)
            
            # Handle citations and link analysis
            citation_map = {}
            references_markdown = ""
            link_analysis = {}
            
            if citations and self.include_links:
                raw_markdown, references_markdown, citation_map, link_analysis = await self._process_citations_and_links(
                    raw_markdown, base_url
                )
            
            # Generate fit markdown if content filter is provided
            fit_markdown = None
            fit_html = None
            
            if self.content_filter:
                filter_result = await self.content_filter.filter(input_html)
                if filter_result.filtered_content != input_html:
                    fit_soup = BeautifulSoup(filter_result.filtered_content, 'lxml')
                    fit_html = str(fit_soup)
                    fit_markdown = self._html_to_markdown(fit_soup, base_url)
                    
                    if citations and self.include_links:
                        fit_markdown, _, _, _ = await self._process_citations_and_links(
                            fit_markdown, base_url
                        )
            
            # Prepare generation metadata
            generation_metadata = {
                "generator": self.__class__.__name__,
                "content_source": self.content_source,
                "citations_enabled": citations,
                "links_processed": len(citation_map),
                "base_url": base_url,
                "options": self.options,
                "filter_applied": self.content_filter is not None,
                "raw_length": len(raw_markdown),
                "fit_length": len(fit_markdown) if fit_markdown else 0
            }
            
            return MarkdownGenerationResult(
                raw_markdown=raw_markdown,
                fit_markdown=fit_markdown,
                fit_html=fit_html,
                references_markdown=references_markdown,
                citation_map=citation_map,
                link_analysis=link_analysis,
                generation_metadata=generation_metadata
            )
            
        except Exception as e:
            logger.error("markdown_generation_failed", error=str(e), base_url=base_url)
            
            # Return basic markdown on error
            return MarkdownGenerationResult(
                raw_markdown=self._fallback_markdown(input_html),
                generation_metadata={"error": str(e)}
            )

    def _clean_html(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Clean and prepare HTML for markdown conversion."""
        # Remove unwanted elements
        unwanted_tags = ['script', 'style', 'noscript', 'iframe', 'embed', 'object']
        for tag in unwanted_tags:
            for element in soup.find_all(tag):
                element.decompose()

        # Remove comments
        from bs4 import Comment
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Clean empty elements
        for element in soup.find_all():
            if not element.get_text(strip=True) and not element.find('img'):
                element.decompose()

        # Normalize whitespace in text nodes
        for text_node in soup.find_all(string=True):
            if text_node.parent.name not in ['pre', 'code']:
                cleaned_text = WHITESPACE_PATTERN.sub(' ', text_node.strip())
                text_node.replace_with(cleaned_text)

        return soup

    def _html_to_markdown(self, soup: BeautifulSoup, base_url: str) -> str:
        """Convert HTML to markdown with proper formatting."""
        markdown_parts = []
        
        # Process top-level elements
        for element in soup.body.children if soup.body else soup.children:
            if isinstance(element, Tag):
                md_content = self._process_element(element, base_url)
                if md_content:
                    markdown_parts.append(md_content)
            elif isinstance(element, NavigableString):
                text = str(element).strip()
                if text:
                    markdown_parts.append(text)

        # Join and clean up markdown
        markdown = '\n\n'.join(markdown_parts)
        markdown = EMPTY_LINE_PATTERN.sub('\n\n', markdown)
        
        return markdown.strip()

    def _process_element(self, element: Tag, base_url: str) -> str:
        """Process individual HTML elements to markdown."""
        tag_name = element.name.lower()
        
        # Headers
        if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = int(tag_name[1])
            text = self._get_text_content(element)
            return f"{'#' * level} {text}"
        
        # Paragraphs
        elif tag_name == 'p':
            return self._process_paragraph(element, base_url)
        
        # Lists
        elif tag_name in ['ul', 'ol']:
            return self._process_list(element, base_url, ordered=(tag_name == 'ol'))
        
        # Tables
        elif tag_name == 'table' and self.include_tables:
            return self._process_table(element, base_url)
        
        # Code blocks
        elif tag_name in ['pre', 'code'] and self.include_code:
            return self._process_code(element)
        
        # Blockquotes
        elif tag_name == 'blockquote':
            return self._process_blockquote(element, base_url)
        
        # Images
        elif tag_name == 'img' and self.include_images:
            return self._process_image(element, base_url)
        
        # Links
        elif tag_name == 'a' and self.include_links:
            return self._process_link(element, base_url)
        
        # Div and section elements - process children
        elif tag_name in ['div', 'section', 'article', 'main']:
            return self._process_container(element, base_url)
        
        # Inline formatting
        elif tag_name in ['strong', 'b']:
            text = self._get_text_content(element)
            return f"**{text}**"
        
        elif tag_name in ['em', 'i']:
            text = self._get_text_content(element)
            return f"*{text}*"
        
        elif tag_name == 'mark':
            text = self._get_text_content(element)
            return f"=={text}=="
        
        # Line breaks
        elif tag_name == 'br':
            return '\n'
        
        # Horizontal rules
        elif tag_name == 'hr':
            return '---'
        
        # Default - get text content
        else:
            return self._get_text_content(element)

    def _process_paragraph(self, element: Tag, base_url: str) -> str:
        """Process paragraph elements with inline formatting."""
        parts = []
        
        for child in element.children:
            if isinstance(child, NavigableString):
                text = str(child).strip()
                if text:
                    parts.append(text)
            elif isinstance(child, Tag):
                child_md = self._process_element(child, base_url)
                if child_md:
                    parts.append(child_md)
        
        return ' '.join(parts)

    def _process_list(self, element: Tag, base_url: str, ordered: bool = False) -> str:
        """Process ordered and unordered lists."""
        items = []
        
        for i, li in enumerate(element.find_all('li', recursive=False)):
            prefix = f"{i+1}. " if ordered else "- "
            item_content = self._process_container(li, base_url)
            
            # Handle nested lists
            if item_content:
                # Indent nested content
                lines = item_content.split('\n')
                indented_lines = [lines[0]] + ['  ' + line for line in lines[1:]]
                items.append(prefix + '\n'.join(indented_lines))
        
        return '\n'.join(items)

    def _process_table(self, element: Tag, base_url: str) -> str:
        """Process HTML tables to markdown format."""
        rows = []
        
        # Process header row
        thead = element.find('thead')
        if thead:
            header_row = thead.find('tr')
            if header_row:
                headers = []
                for th in header_row.find_all(['th', 'td']):
                    headers.append(self._get_text_content(th))
                
                if headers:
                    rows.append('| ' + ' | '.join(headers) + ' |')
                    rows.append('| ' + ' | '.join(['---'] * len(headers)) + ' |')
        
        # Process body rows
        tbody = element.find('tbody') or element
        for tr in tbody.find_all('tr'):
            cells = []
            for td in tr.find_all(['td', 'th']):
                cell_content = self._get_text_content(td)
                # Escape pipe characters in cell content
                cell_content = cell_content.replace('|', '\\|')
                cells.append(cell_content)
            
            if cells:
                rows.append('| ' + ' | '.join(cells) + ' |')
        
        return '\n'.join(rows)

    def _process_code(self, element: Tag) -> str:
        """Process code elements."""
        content = element.get_text()
        
        # Detect language from class attribute
        language = ''
        if element.get('class'):
            for cls in element.get('class'):
                if cls.startswith('language-'):
                    language = cls[9:]
                    break
                elif cls.startswith('lang-'):
                    language = cls[5:]
                    break

        if element.name == 'pre':
            # Code block
            return f"```{language}\n{content}\n```"
        else:
            # Inline code
            return f"`{content}`"

    def _process_blockquote(self, element: Tag, base_url: str) -> str:
        """Process blockquote elements."""
        content = self._process_container(element, base_url)
        lines = content.split('\n')
        quoted_lines = ['> ' + line for line in lines]
        return '\n'.join(quoted_lines)

    def _process_image(self, element: Tag, base_url: str) -> str:
        """Process image elements."""
        src = element.get('src', '')
        alt = element.get('alt', '')
        title = element.get('title', '')
        
        if src:
            # Make URL absolute
            abs_src = fast_urljoin(base_url, src)
            
            # Format markdown image
            if title:
                return f'![{alt}]({abs_src} "{title}")'
            else:
                return f'![{alt}]({abs_src})'
        
        return f'![{alt}]' if alt else ''

    def _process_link(self, element: Tag, base_url: str) -> str:
        """Process link elements."""
        href = element.get('href', '')
        text = self._get_text_content(element)
        title = element.get('title', '')
        
        if href:
            # Make URL absolute
            abs_href = fast_urljoin(base_url, href)
            
            # Format markdown link
            if title:
                return f'[{text}]({abs_href} "{title}")'
            else:
                return f'[{text}]({abs_href})'
        
        return text

    def _process_container(self, element: Tag, base_url: str) -> str:
        """Process container elements by processing their children."""
        parts = []
        
        for child in element.children:
            if isinstance(child, NavigableString):
                text = str(child).strip()
                if text:
                    parts.append(text)
            elif isinstance(child, Tag):
                child_md = self._process_element(child, base_url)
                if child_md:
                    parts.append(child_md)
        
        return '\n'.join(parts)

    def _get_text_content(self, element: Tag) -> str:
        """Get clean text content from element."""
        text = element.get_text()
        return sanitize_text(text)

    async def _process_citations_and_links(
        self, 
        markdown: str, 
        base_url: str
    ) -> Tuple[str, str, Dict[str, int], Dict[str, Any]]:
        """Process citations and perform link analysis."""
        citation_map = {}
        link_info = {}
        citation_counter = 1
        
        def replace_link(match):
            nonlocal citation_counter
            
            text = match.group(1)
            url = match.group(2)
            title = match.group(3) or ''
            
            # Make URL absolute
            abs_url = fast_urljoin(base_url, url)
            
            # Skip if already processed
            if abs_url in citation_map:
                return f"{text}[{citation_map[abs_url]}]"
            
            # Add to citation map
            citation_map[abs_url] = citation_counter
            
            # Store link information
            link_info[abs_url] = LinkInfo(
                url=abs_url,
                title=title,
                text=text,
                domain=urlparse(abs_url).netloc,
                is_external=urlparse(abs_url).netloc != urlparse(base_url).netloc
            )
            
            result = f"{text}[{citation_counter}]"
            citation_counter += 1
            return result
        
        # Replace links with citations
        markdown_with_citations = LINK_PATTERN.sub(replace_link, markdown)
        
        # Generate references markdown
        references_lines = ["## References"]
        for url, citation_num in sorted(citation_map.items(), key=lambda x: x[1]):
            link_data = link_info[url]
            title = link_data.title or link_data.text or "Link"
            references_lines.append(f"{citation_num}. [{title}]({url})")
        
        references_markdown = '\n'.join(references_lines) if len(references_lines) > 1 else ""
        
        # Perform link analysis
        link_analysis = await self._analyze_links(link_info, base_url)
        
        return markdown_with_citations, references_markdown, citation_map, link_analysis

    async def _analyze_links(
        self, 
        link_info: Dict[str, LinkInfo], 
        base_url: str
    ) -> Dict[str, Any]:
        """Analyze links for quality and relevance scoring."""
        if not link_info:
            return {}
        
        # Count domains
        domain_counts = {}
        external_links = 0
        internal_links = 0
        
        for link_data in link_info.values():
            domain = link_data.domain
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
            
            if link_data.is_external:
                external_links += 1
            else:
                internal_links += 1
        
        # Calculate link quality scores (simplified)
        base_domain = urlparse(base_url).netloc
        
        for url, link_data in link_info.items():
            score = 0.5  # Base score
            
            # Authority domains get higher scores
            authority_domains = [
                'wikipedia.org', 'github.com', 'stackoverflow.com',
                'mozilla.org', 'w3.org', 'ietf.org'
            ]
            
            if any(domain in link_data.domain for domain in authority_domains):
                score += 0.3
            
            # Internal links get slight boost for context
            if not link_data.is_external:
                score += 0.1
            
            # Links with descriptive text get higher scores
            if len(link_data.text) > 10 and not link_data.text.startswith('http'):
                score += 0.2
            
            link_data.relevance_score = min(1.0, score)
        
        return {
            "total_links": len(link_info),
            "external_links": external_links,
            "internal_links": internal_links,
            "unique_domains": len(domain_counts),
            "top_domains": sorted(
                domain_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5],
            "avg_relevance_score": sum(
                link.relevance_score for link in link_info.values()
            ) / len(link_info),
            "base_domain": urlparse(base_url).netloc
        }

    def _fallback_markdown(self, html_content: str) -> str:
        """Generate basic markdown as fallback when main conversion fails."""
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'noscript']):
                element.decompose()
            
            # Get plain text
            text = soup.get_text()
            return sanitize_text(text)
            
        except Exception:
            return "Error: Could not convert HTML to markdown"


# Convenience functions
async def generate_markdown(
    html_content: str,
    base_url: str = "",
    content_filter: Optional[RelevantContentFilter] = None,
    options: Optional[Dict[str, Any]] = None,
    citations: bool = True
) -> MarkdownGenerationResult:
    """
    Generate markdown using the default generator.
    
    Args:
        html_content: HTML content to convert
        base_url: Base URL for link resolution
        content_filter: Optional content filter for fit markdown
        options: Additional generation options
        citations: Whether to generate citations
        
    Returns:
        MarkdownGenerationResult with all generated content
    """
    generator = DefaultMarkdownGenerator(
        content_filter=content_filter,
        options=options or {}
    )
    
    return await generator.generate_markdown(
        html_content,
        base_url=base_url,
        citations=citations
    )


async def generate_simple_markdown(html_content: str, base_url: str = "") -> str:
    """Generate simple markdown without advanced features."""
    generator = DefaultMarkdownGenerator(
        options={"include_links": False, "include_images": False}
    )
    
    result = await generator.generate_markdown(
        html_content,
        base_url=base_url,
        citations=False
    )
    
    return result.raw_markdown
