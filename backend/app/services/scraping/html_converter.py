"""
Advanced HTML to text/markdown conversion system with intelligent parsing.

This module provides sophisticated HTML conversion:
- HTML to clean text conversion
- HTML to structured markdown
- Intelligent content extraction
- Link and image handling
- Table structure preservation
"""

import re
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import structlog
from bs4 import BeautifulSoup, Comment

logger = structlog.get_logger(__name__)


@dataclass
class ConversionConfig:
    """Configuration for HTML conversion."""
    body_width: int = 78
    skip_internal_links: bool = False
    inline_links: bool = True
    links_each_paragraph: bool = False
    images_to_alt: bool = True
    images_with_size: bool = False
    ignore_images: bool = False
    ignore_links: bool = False
    ignore_emphasis: bool = False
    ignore_tables: bool = False
    escape_special: bool = True
    mark_code: bool = True
    wrap_links: bool = True
    wrap_list_items: bool = True
    
    # Advanced options
    preserve_whitespace: bool = False
    decode_errors: str = 'ignore'
    baseurl: str = ""
    open_quote: str = '"'
    close_quote: str = '"'
    
    # Element handling
    emphasis_mark: str = "*"
    strong_mark: str = "**"
    list_marker: str = "- "
    code_mark: str = "`"


class HTMLToTextConverter:
    """
    Advanced HTML to text converter with intelligent parsing.
    
    Provides clean text extraction with optional markdown formatting.
    """
    
    def __init__(self, config: ConversionConfig = None):
        """Initialize converter with configuration."""
        self.config = config or ConversionConfig()
        
        # Conversion state
        self.out = []
        self.quiet = 0
        self.p_p = 0  # Number of newlines before current line
        self.outcount = 0
        self.start = True
        self.space = False
        
        # Link handling
        self.a = []
        self.astack = []
        self.acount = 0
        
        # List handling
        self.list = []
        self.blockquote = 0
        self.pre = False
        
        # Table handling
        self.table = False
        self.td_count = 0
        self.tr_count = 0
        
        # Emphasis tracking
        self.emphasis = 0
        self.strong = 0
        self.code = False
        
        # Special characters
        self.abbr_data = {}
        self.abbr_list = {}
        
    def convert(self, html: str, baseurl: str = "") -> str:
        """
        Convert HTML to clean text.
        
        Args:
            html: HTML content to convert
            baseurl: Base URL for resolving relative links
            
        Returns:
            Clean text representation
        """
        self.config.baseurl = baseurl or self.config.baseurl
        
        # Reset state
        self._reset_state()
        
        try:
            # Parse HTML with BeautifulSoup for better handling
            soup = BeautifulSoup(html, 'lxml')
            
            # Remove unwanted elements
            self._remove_unwanted_elements(soup)
            
            # Convert to text
            self._process_element(soup)
            
            # Post-process output
            return self._finalize_output()
            
        except Exception as e:
            logger.error(f"HTML conversion failed: {str(e)}")
            # Fallback to simple text extraction
            return self._simple_text_extraction(html)
    
    def _reset_state(self):
        """Reset conversion state."""
        self.out = []
        self.quiet = 0
        self.p_p = 0
        self.outcount = 0
        self.start = True
        self.space = False
        self.a = []
        self.astack = []
        self.acount = 0
        self.list = []
        self.blockquote = 0
        self.pre = False
        self.table = False
        self.td_count = 0
        self.tr_count = 0
        self.emphasis = 0
        self.strong = 0
        self.code = False
    
    def _remove_unwanted_elements(self, soup: BeautifulSoup):
        """Remove unwanted HTML elements."""
        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        # Remove script and style elements
        for script in soup(["script", "style", "noscript", "meta"]):
            script.decompose()
        
        # Remove hidden elements
        for element in soup.find_all(style=re.compile(r'display:\s*none|visibility:\s*hidden')):
            element.decompose()
    
    def _process_element(self, element):
        """Process HTML element recursively."""
        if hasattr(element, 'name'):
            if element.name:
                self._handle_tag(element, opening=True)
        
        # Process children
        if hasattr(element, 'children'):
            for child in element.children:
                if hasattr(child, 'name'):
                    self._process_element(child)
                else:
                    # Text node
                    self._handle_text(str(child))
        
        if hasattr(element, 'name'):
            if element.name:
                self._handle_tag(element, opening=False)
    
    def _handle_tag(self, element, opening: bool = True):
        """Handle HTML tag opening/closing."""
        tag = element.name.lower()
        
        if opening:
            self._handle_opening_tag(tag, element)
        else:
            self._handle_closing_tag(tag, element)
    
    def _handle_opening_tag(self, tag: str, element):
        """Handle opening HTML tags."""
        if tag in ['p', 'div', 'br']:
            self._handle_paragraph()
        
        elif tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self._handle_heading(tag, element)
        
        elif tag == 'a' and not self.config.ignore_links:
            self._handle_link_open(element)
        
        elif tag == 'img' and not self.config.ignore_images:
            self._handle_image(element)
        
        elif tag in ['strong', 'b'] and not self.config.ignore_emphasis:
            self._handle_strong_open()
        
        elif tag in ['em', 'i'] and not self.config.ignore_emphasis:
            self._handle_emphasis_open()
        
        elif tag == 'code' and self.config.mark_code:
            self._handle_code_open()
        
        elif tag in ['ul', 'ol']:
            self._handle_list_open(tag, element)
        
        elif tag == 'li':
            self._handle_list_item_open()
        
        elif tag == 'blockquote':
            self._handle_blockquote_open()
        
        elif tag == 'table' and not self.config.ignore_tables:
            self._handle_table_open()
        
        elif tag == 'tr' and self.table:
            self._handle_table_row_open()
        
        elif tag in ['td', 'th'] and self.table:
            self._handle_table_cell_open()
        
        elif tag == 'pre':
            self.pre = True
    
    def _handle_closing_tag(self, tag: str, element):
        """Handle closing HTML tags."""
        if tag == 'a' and not self.config.ignore_links:
            self._handle_link_close()
        
        elif tag in ['strong', 'b'] and not self.config.ignore_emphasis:
            self._handle_strong_close()
        
        elif tag in ['em', 'i'] and not self.config.ignore_emphasis:
            self._handle_emphasis_close()
        
        elif tag == 'code' and self.config.mark_code:
            self._handle_code_close()
        
        elif tag in ['ul', 'ol']:
            self._handle_list_close()
        
        elif tag == 'li':
            self._handle_list_item_close()
        
        elif tag == 'blockquote':
            self._handle_blockquote_close()
        
        elif tag == 'table' and not self.config.ignore_tables:
            self._handle_table_close()
        
        elif tag == 'tr' and self.table:
            self._handle_table_row_close()
        
        elif tag in ['td', 'th'] and self.table:
            self._handle_table_cell_close()
        
        elif tag == 'pre':
            self.pre = False
    
    def _handle_text(self, text: str):
        """Handle text content."""
        if self.quiet > 0:
            return
        
        # Preserve whitespace in <pre> tags
        if self.pre:
            self._output(text)
            return
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        if text.strip():
            if self.space:
                text = ' ' + text.lstrip()
            self._output(text)
            self.space = text.endswith(' ')
        else:
            self.space = True
    
    def _handle_paragraph(self):
        """Handle paragraph breaks."""
        self._p()
    
    def _handle_heading(self, tag: str, element):
        """Handle heading elements."""
        level = int(tag[1])  # h1 -> 1, h2 -> 2, etc.
        self._p()
        
        # Add markdown-style heading markers
        if self.config.mark_code:  # Reuse this flag for markdown-style output
            self._output("#" * level + " ")
    
    def _handle_link_open(self, element):
        """Handle opening anchor tag."""
        href = element.get('href', '')
        if href:
            if self.config.baseurl:
                href = urljoin(self.config.baseurl, href)
            
            self.astack.append((href, self.acount))
            self.a.append(href)
            self.acount += 1
            
            if not self.config.inline_links:
                self._output(f"[{self.acount}]")
    
    def _handle_link_close(self):
        """Handle closing anchor tag."""
        if self.astack:
            href, count = self.astack.pop()
            if self.config.inline_links:
                self._output(f" ({href})")
    
    def _handle_image(self, element):
        """Handle image elements."""
        alt = element.get('alt', '')
        src = element.get('src', '')
        
        if self.config.images_to_alt and alt:
            self._output(f"[{alt}]")
        elif src:
            if self.config.baseurl:
                src = urljoin(self.config.baseurl, src)
            self._output(f"[Image: {src}]")
    
    def _handle_strong_open(self):
        """Handle strong/bold opening."""
        if self.config.mark_code:
            self._output(self.config.strong_mark)
        self.strong += 1
    
    def _handle_strong_close(self):
        """Handle strong/bold closing."""
        if self.strong > 0:
            self.strong -= 1
            if self.config.mark_code:
                self._output(self.config.strong_mark)
    
    def _handle_emphasis_open(self):
        """Handle emphasis/italic opening."""
        if self.config.mark_code:
            self._output(self.config.emphasis_mark)
        self.emphasis += 1
    
    def _handle_emphasis_close(self):
        """Handle emphasis/italic closing."""
        if self.emphasis > 0:
            self.emphasis -= 1
            if self.config.mark_code:
                self._output(self.config.emphasis_mark)
    
    def _handle_code_open(self):
        """Handle code opening."""
        self._output(self.config.code_mark)
        self.code = True
    
    def _handle_code_close(self):
        """Handle code closing."""
        if self.code:
            self._output(self.config.code_mark)
            self.code = False
    
    def _handle_list_open(self, tag: str, element):
        """Handle list opening."""
        list_type = 'ordered' if tag == 'ol' else 'unordered'
        start = int(element.get('start', 1)) if tag == 'ol' else 1
        self.list.append((list_type, start, 0))
        self._p()
    
    def _handle_list_close(self):
        """Handle list closing."""
        if self.list:
            self.list.pop()
        self._p()
    
    def _handle_list_item_open(self):
        """Handle list item opening."""
        if self.list:
            list_type, start, current = self.list[-1]
            current += 1
            self.list[-1] = (list_type, start, current)
            
            self._p()
            
            if list_type == 'ordered':
                marker = f"{start + current - 1}. "
            else:
                marker = self.config.list_marker
            
            # Indent nested lists
            indent = "  " * (len(self.list) - 1)
            self._output(indent + marker)
    
    def _handle_list_item_close(self):
        """Handle list item closing."""
        pass  # Handled by paragraph breaks
    
    def _handle_blockquote_open(self):
        """Handle blockquote opening."""
        self.blockquote += 1
        self._p()
    
    def _handle_blockquote_close(self):
        """Handle blockquote closing."""
        if self.blockquote > 0:
            self.blockquote -= 1
        self._p()
    
    def _handle_table_open(self):
        """Handle table opening."""
        self.table = True
        self.td_count = 0
        self.tr_count = 0
        self._p()
    
    def _handle_table_close(self):
        """Handle table closing."""
        self.table = False
        self._p()
    
    def _handle_table_row_open(self):
        """Handle table row opening."""
        if self.tr_count > 0:
            self._p()
        self.tr_count += 1
        self.td_count = 0
    
    def _handle_table_row_close(self):
        """Handle table row closing."""
        pass
    
    def _handle_table_cell_open(self):
        """Handle table cell opening."""
        if self.td_count > 0:
            self._output(" | ")
        self.td_count += 1
    
    def _handle_table_cell_close(self):
        """Handle table cell closing."""
        pass
    
    def _output(self, text: str):
        """Output text with proper formatting."""
        if text:
            self.out.append(text)
            self.outcount += len(text)
            self.start = False
    
    def _p(self):
        """Add paragraph break."""
        if not self.start:
            self.out.append('\n\n')
            self.start = True
            self.space = False
    
    def _finalize_output(self) -> str:
        """Finalize and clean up output."""
        result = ''.join(self.out)
        
        # Clean up excessive whitespace
        result = re.sub(r'\n{3,}', '\n\n', result)  # Max 2 consecutive newlines
        result = re.sub(r'[ \t]+', ' ', result)      # Multiple spaces to single
        result = result.strip()
        
        # Add link references if not inline
        if not self.config.inline_links and self.a:
            result += '\n\n'
            for i, link in enumerate(self.a, 1):
                result += f'[{i}]: {link}\n'
        
        return result
    
    def _simple_text_extraction(self, html: str) -> str:
        """Fallback simple text extraction."""
        try:
            soup = BeautifulSoup(html, 'lxml')
            return soup.get_text(separator=' ', strip=True)
        except Exception:
            # Last resort: remove tags with regex
            text = re.sub(r'<[^>]+>', '', html)
            return ' '.join(text.split())


class HTMLToMarkdownConverter(HTMLToTextConverter):
    """
    HTML to Markdown converter with enhanced formatting.
    
    Extends text converter to produce proper markdown output.
    """
    
    def __init__(self, config: ConversionConfig = None):
        """Initialize markdown converter."""
        super().__init__(config)
        
        # Enable markdown features
        if self.config:
            self.config.mark_code = True
            self.config.inline_links = True
            self.config.emphasis_mark = "*"
            self.config.strong_mark = "**"
            self.config.code_mark = "`"
    
    def _handle_heading(self, tag: str, element):
        """Handle heading with proper markdown formatting."""
        level = int(tag[1])
        self._p()
        self._output("#" * level + " ")
    
    def _handle_link_close(self):
        """Handle link with markdown formatting."""
        if self.astack:
            href, count = self.astack.pop()
            self._output(f"]({href})")
    
    def _handle_link_open(self, element):
        """Handle link opening with markdown formatting."""
        href = element.get('href', '')
        if href:
            if self.config.baseurl:
                href = urljoin(self.config.baseurl, href)
            
            self.astack.append((href, self.acount))
            self.a.append(href)
            self.acount += 1
            self._output("[")
    
    def _handle_image(self, element):
        """Handle image with markdown formatting."""
        alt = element.get('alt', '')
        src = element.get('src', '')
        title = element.get('title', '')
        
        if src:
            if self.config.baseurl:
                src = urljoin(self.config.baseurl, src)
            
            markdown_img = f"![{alt}]({src}"
            if title:
                markdown_img += f' "{title}"'
            markdown_img += ")"
            
            self._output(markdown_img)
    
    def _handle_blockquote_open(self):
        """Handle blockquote with markdown formatting."""
        self.blockquote += 1
        self._p()
        self._output("> ")
    
    def _handle_table_row_close(self):
        """Handle table row with markdown formatting."""
        if self.tr_count == 1:
            # Add separator row after header
            self._p()
            self._output("| " + " | ".join(["---"] * max(1, self.td_count)) + " |")


# Factory functions
def create_html_converter(output_format: str = "text", config: ConversionConfig = None):
    """
    Create HTML converter based on output format.
    
    Args:
        output_format: "text" or "markdown"
        config: Conversion configuration
        
    Returns:
        Appropriate converter instance
    """
    if output_format.lower() == "markdown":
        return HTMLToMarkdownConverter(config)
    else:
        return HTMLToTextConverter(config)


# Convenience functions
def html_to_text(html: str, 
                baseurl: str = "",
                body_width: int = 78,
                **kwargs) -> str:
    """Convert HTML to clean text."""
    config = ConversionConfig(
        body_width=body_width,
        baseurl=baseurl,
        **kwargs
    )
    converter = HTMLToTextConverter(config)
    return converter.convert(html, baseurl)


def html_to_markdown(html: str, 
                    baseurl: str = "",
                    **kwargs) -> str:
    """Convert HTML to markdown."""
    config = ConversionConfig(
        baseurl=baseurl,
        mark_code=True,
        inline_links=True,
        **kwargs
    )
    converter = HTMLToMarkdownConverter(config)
    return converter.convert(html, baseurl)


def extract_clean_text(html: str, **kwargs) -> str:
    """Extract clean text with minimal formatting."""
    config = ConversionConfig(
        ignore_links=True,
        ignore_images=True,
        ignore_emphasis=True,
        mark_code=False,
        **kwargs
    )
    converter = HTMLToTextConverter(config)
    return converter.convert(html)
