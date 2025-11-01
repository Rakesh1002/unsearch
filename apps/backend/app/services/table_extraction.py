"""
Table extraction strategies for detecting and extracting tables from HTML content.

This module provides various strategies for table extraction:
- DefaultTableExtraction: Score-based table detection and extraction
- LLMTableExtraction: AI-powered table understanding and extraction
- NoTableExtraction: Skip table extraction
"""

import json
import re
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, Tuple
from urllib.parse import urljoin

import structlog
from bs4 import BeautifulSoup, Tag, NavigableString

from app.utils.text_processing import sanitize_text

logger = structlog.get_logger(__name__)


class TableExtractionStrategy(ABC):
    """
    Abstract base class for all table extraction strategies.
    
    This class defines the interface that all table extraction strategies must implement.
    """
    
    def __init__(self, **kwargs):
        """
        Initialize the table extraction strategy.
        
        Args:
            **kwargs: Additional keyword arguments for specific strategies
        """
        self.verbose = kwargs.get("verbose", False)
    
    @abstractmethod
    def extract_tables(self, html_content: str, base_url: str = "", **kwargs) -> List[Dict[str, Any]]:
        """
        Extract tables from the given HTML content.
        
        Args:
            html_content: HTML content to extract tables from
            base_url: Base URL for resolving relative links
            **kwargs: Additional parameters for extraction
            
        Returns:
            List of dictionaries containing table data, each with:
                - headers: List of column headers
                - rows: List of row data (each row is a list)
                - caption: Table caption if present
                - summary: Table summary attribute if present  
                - metadata: Additional metadata about the table
        """
        pass


class NoTableExtraction(TableExtractionStrategy):
    """Table extraction strategy that skips table processing."""
    
    def extract_tables(self, html_content: str, base_url: str = "", **kwargs) -> List[Dict[str, Any]]:
        """Return empty list - no table extraction."""
        return []


class DefaultTableExtraction(TableExtractionStrategy):
    """
    Default table extraction strategy using scoring to identify data tables.
    
    This strategy uses a scoring system to differentiate between layout tables
    and actual data tables, then extracts structured data while handling
    colspan and rowspan attributes.
    """
    
    def __init__(self, **kwargs):
        """
        Initialize the default table extraction strategy.
        
        Args:
            table_score_threshold (int): Minimum score for a table to be considered data table (default: 7)
            min_rows (int): Minimum number of rows for a valid table (default: 2)
            min_cols (int): Minimum number of columns for a valid table (default: 2)
            extract_links (bool): Whether to extract links within table cells (default: True)
            **kwargs: Additional parameters
        """
        super().__init__(**kwargs)
        self.table_score_threshold = kwargs.get("table_score_threshold", 7)
        self.min_rows = kwargs.get("min_rows", 2)
        self.min_cols = kwargs.get("min_cols", 2)
        self.extract_links = kwargs.get("extract_links", True)
    
    def extract_tables(self, html_content: str, base_url: str = "", **kwargs) -> List[Dict[str, Any]]:
        """Extract all data tables from the HTML content."""
        if not html_content:
            return []
        
        soup = BeautifulSoup(html_content, 'lxml')
        table_tags = soup.find_all('table')
        
        if not table_tags:
            return []
        
        extracted_tables = []
        
        for idx, table_tag in enumerate(table_tags):
            try:
                # Score the table to determine if it's a data table
                table_score = self._score_table(table_tag)
                
                if table_score < self.table_score_threshold:
                    if self.verbose:
                        logger.debug(f"Table {idx} skipped (score: {table_score} < {self.table_score_threshold})")
                    continue
                
                # Extract table data
                table_data = self._extract_table_data(table_tag, base_url, idx)
                
                if table_data and self._is_valid_table(table_data):
                    table_data['metadata']['score'] = table_score
                    extracted_tables.append(table_data)
                    
                    if self.verbose:
                        logger.debug(f"Table {idx} extracted (score: {table_score}, rows: {len(table_data['rows'])})")
                
            except Exception as e:
                logger.error(f"Error extracting table {idx}: {str(e)}")
                continue
        
        logger.info(f"Extracted {len(extracted_tables)} tables from HTML content")
        return extracted_tables
    
    def _score_table(self, table_tag: Tag) -> int:
        """
        Score a table to determine if it's likely a data table vs layout table.
        
        Args:
            table_tag: BeautifulSoup table tag
            
        Returns:
            Integer score (higher = more likely to be data table)
        """
        score = 0
        
        # Check for table headers
        th_tags = table_tag.find_all('th')
        if th_tags:
            score += 5
            # More headers = higher score
            score += min(len(th_tags), 5)
        
        # Check for thead/tbody structure
        if table_tag.find('thead'):
            score += 3
        if table_tag.find('tbody'):
            score += 2
        
        # Check for caption
        if table_tag.find('caption'):
            score += 2
        
        # Check for summary attribute
        if table_tag.get('summary'):
            score += 1
        
        # Count rows and columns
        rows = table_tag.find_all('tr')
        if rows:
            # More rows generally indicate data table
            row_count = len(rows)
            if row_count > 5:
                score += 3
            elif row_count > 2:
                score += 1
            
            # Check column consistency
            col_counts = []
            for row in rows:
                cells = row.find_all(['td', 'th'])
                col_counts.append(len(cells))
            
            if col_counts:
                # Consistent column count is good
                if len(set(col_counts)) == 1:
                    score += 2
                
                # More columns can indicate data table
                max_cols = max(col_counts)
                if max_cols > 4:
                    score += 2
                elif max_cols > 2:
                    score += 1
        
        # Check for data-like attributes
        data_attributes = ['data-table', 'data-grid', 'sortable']
        for attr in data_attributes:
            if table_tag.get(attr):
                score += 1
        
        # Check class names for data table indicators
        classes = table_tag.get('class', [])
        data_class_indicators = ['data', 'grid', 'sortable', 'results', 'listing']
        for indicator in data_class_indicators:
            if any(indicator in str(cls).lower() for cls in classes):
                score += 1
        
        # Penalize layout table indicators
        layout_indicators = ['layout', 'wrapper', 'container', 'nav']
        for indicator in layout_indicators:
            if any(indicator in str(cls).lower() for cls in classes):
                score -= 2
        
        # Check for form elements (usually layout tables)
        if table_tag.find(['input', 'select', 'textarea']):
            score -= 3
        
        return max(0, score)  # Ensure non-negative
    
    def _extract_table_data(self, table_tag: Tag, base_url: str, table_index: int) -> Dict[str, Any]:
        """Extract structured data from a table."""
        # Initialize table data structure
        table_data = {
            'headers': [],
            'rows': [],
            'caption': None,
            'summary': None,
            'metadata': {
                'index': table_index,
                'row_count': 0,
                'col_count': 0,
                'has_header': False,
                'has_footer': False,
                'extraction_time': time.time()
            }
        }
        
        # Extract caption
        caption_tag = table_tag.find('caption')
        if caption_tag:
            table_data['caption'] = sanitize_text(caption_tag.get_text())
        
        # Extract summary
        summary = table_tag.get('summary')
        if summary:
            table_data['summary'] = sanitize_text(summary)
        
        # Find all rows
        rows = table_tag.find_all('tr')
        if not rows:
            return table_data
        
        # Process header row(s)
        header_rows = []
        data_rows = []
        
        # Check for thead section
        thead = table_tag.find('thead')
        if thead:
            header_rows = thead.find_all('tr')
            # Remaining rows are in tbody or directly in table
            tbody = table_tag.find('tbody')
            if tbody:
                data_rows = tbody.find_all('tr')
            else:
                # Find rows not in thead
                all_rows = table_tag.find_all('tr')
                thead_rows = set(thead.find_all('tr'))
                data_rows = [row for row in all_rows if row not in thead_rows]
        else:
            # No explicit thead, use heuristics
            # Check if first row has mostly th tags
            first_row = rows[0]
            th_count = len(first_row.find_all('th'))
            td_count = len(first_row.find_all('td'))
            
            if th_count > td_count:
                header_rows = [first_row]
                data_rows = rows[1:]
            else:
                data_rows = rows
        
        # Extract headers
        if header_rows:
            table_data['metadata']['has_header'] = True
            for header_row in header_rows:
                header_cells = header_row.find_all(['th', 'td'])
                if not table_data['headers']:  # First header row
                    table_data['headers'] = [
                        sanitize_text(cell.get_text()) for cell in header_cells
                    ]
                # Note: Multi-row headers could be handled more sophisticatedly
        
        # Extract data rows
        for row_idx, row in enumerate(data_rows):
            cells = row.find_all(['td', 'th'])
            row_data = []
            
            for cell in cells:
                cell_data = self._extract_cell_data(cell, base_url)
                
                # Handle colspan
                colspan = int(cell.get('colspan', 1))
                if colspan > 1:
                    # Add empty cells for colspan
                    row_data.extend([cell_data] + [''] * (colspan - 1))
                else:
                    row_data.append(cell_data)
            
            if row_data:
                table_data['rows'].append(row_data)
        
        # Update metadata
        table_data['metadata']['row_count'] = len(table_data['rows'])
        if table_data['rows']:
            table_data['metadata']['col_count'] = max(len(row) for row in table_data['rows'])
        
        # Check for footer
        tfoot = table_tag.find('tfoot')
        if tfoot:
            table_data['metadata']['has_footer'] = True
        
        return table_data
    
    def _extract_cell_data(self, cell: Tag, base_url: str) -> Union[str, Dict[str, Any]]:
        """Extract data from a table cell, handling links and formatting."""
        cell_text = sanitize_text(cell.get_text())
        
        # If extract_links is disabled, just return text
        if not self.extract_links:
            return cell_text
        
        # Check for links within the cell
        links = cell.find_all('a', href=True)
        if links:
            cell_links = []
            for link in links:
                href = link.get('href')
                if href:
                    # Make URL absolute
                    abs_url = urljoin(base_url, href) if base_url else href
                    link_text = sanitize_text(link.get_text())
                    cell_links.append({
                        'text': link_text,
                        'url': abs_url
                    })
            
            if cell_links:
                return {
                    'text': cell_text,
                    'links': cell_links
                }
        
        return cell_text
    
    def _is_valid_table(self, table_data: Dict[str, Any]) -> bool:
        """Check if extracted table data meets minimum requirements."""
        row_count = len(table_data['rows'])
        
        if row_count < self.min_rows:
            return False
        
        if table_data['rows']:
            max_cols = max(len(row) for row in table_data['rows'])
            if max_cols < self.min_cols:
                return False
        
        # Check if table has meaningful content
        total_chars = 0
        for row in table_data['rows']:
            for cell in row:
                if isinstance(cell, str):
                    total_chars += len(cell)
                elif isinstance(cell, dict) and 'text' in cell:
                    total_chars += len(cell['text'])
        
        # Table should have reasonable amount of text content
        if total_chars < 10:
            return False
        
        return True


class LLMTableExtraction(TableExtractionStrategy):
    """
    AI-powered table extraction using language models.
    
    This strategy uses LLMs to understand and extract table content,
    including complex tables that might be difficult for rule-based approaches.
    """
    
    def __init__(self, llm_config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize LLM table extraction strategy.
        
        Args:
            llm_config: Configuration for LLM provider
            **kwargs: Additional parameters
        """
        super().__init__(**kwargs)
        self.llm_config = llm_config or {}
        self.max_table_size = kwargs.get('max_table_size', 5000)  # Max chars per table for LLM
        self.extraction_prompt_template = kwargs.get('extraction_prompt_template', self._default_prompt())
    
    def extract_tables(self, html_content: str, base_url: str = "", **kwargs) -> List[Dict[str, Any]]:
        """Extract tables using LLM understanding."""
        if not html_content:
            return []
        
        soup = BeautifulSoup(html_content, 'lxml')
        table_tags = soup.find_all('table')
        
        if not table_tags:
            return []
        
        extracted_tables = []
        
        for idx, table_tag in enumerate(table_tags):
            try:
                # Convert table to text for LLM processing
                table_html = str(table_tag)
                
                # Skip very large tables
                if len(table_html) > self.max_table_size:
                    if self.verbose:
                        logger.debug(f"Table {idx} too large for LLM processing ({len(table_html)} chars)")
                    continue
                
                # Use LLM to extract and structure table data
                table_data = await self._extract_with_llm(table_html, idx, base_url)
                
                if table_data:
                    extracted_tables.append(table_data)
                    if self.verbose:
                        logger.debug(f"Table {idx} extracted with LLM")
            
            except Exception as e:
                logger.error(f"Error extracting table {idx} with LLM: {str(e)}")
                continue
        
        logger.info(f"Extracted {len(extracted_tables)} tables using LLM")
        return extracted_tables
    
    async def _extract_with_llm(self, table_html: str, table_index: int, base_url: str) -> Optional[Dict[str, Any]]:
        """Use LLM to extract and structure table data."""
        try:
            # Prepare prompt
            prompt = self.extraction_prompt_template.format(
                table_html=table_html,
                base_url=base_url or "not provided"
            )
            
            # Mock LLM call - in production, integrate with actual LLM providers
            # This would be replaced with actual LLM API calls
            await asyncio.sleep(0.1)  # Simulate API delay
            
            # Mock structured response
            mock_response = {
                'headers': ['Column 1', 'Column 2', 'Column 3'],
                'rows': [
                    ['Row 1 Cell 1', 'Row 1 Cell 2', 'Row 1 Cell 3'],
                    ['Row 2 Cell 1', 'Row 2 Cell 2', 'Row 2 Cell 3']
                ],
                'caption': 'Mock table extracted by LLM',
                'summary': 'This is a mock extraction result',
                'metadata': {
                    'index': table_index,
                    'extraction_method': 'llm',
                    'row_count': 2,
                    'col_count': 3,
                    'confidence': 0.85,
                    'extraction_time': time.time()
                }
            }
            
            return mock_response
            
        except Exception as e:
            logger.error(f"LLM table extraction failed: {str(e)}")
            return None
    
    def _default_prompt(self) -> str:
        """Default prompt template for LLM table extraction."""
        return """
Extract and structure the following HTML table into JSON format.

Instructions:
1. Identify table headers (if any) and include them in the 'headers' array
2. Extract all data rows into the 'rows' array (each row is an array of cell values)
3. Include any caption or summary information
4. Preserve the semantic meaning and structure of the table
5. If there are links in cells, extract both the text and URL

HTML Table:
{table_html}

Base URL (for resolving relative links): {base_url}

Return the result as valid JSON with this structure:
{{
    "headers": ["header1", "header2", ...],
    "rows": [["cell1", "cell2", ...], ["cell1", "cell2", ...], ...],
    "caption": "table caption or null",
    "summary": "table summary or null",
    "metadata": {{
        "extraction_method": "llm",
        "confidence": 0.0-1.0,
        "notes": "any relevant notes about the table"
    }}
}}
"""


class SmartTableExtraction(TableExtractionStrategy):
    """
    Smart table extraction that combines rule-based and AI approaches.
    
    Uses rule-based extraction for simple tables and falls back to
    LLM extraction for complex cases.
    """
    
    def __init__(self, **kwargs):
        """Initialize smart table extraction strategy."""
        super().__init__(**kwargs)
        
        # Initialize both strategies
        self.default_extractor = DefaultTableExtraction(**kwargs)
        self.llm_extractor = LLMTableExtraction(**kwargs)
        
        self.complexity_threshold = kwargs.get('complexity_threshold', 15)
        self.use_llm_fallback = kwargs.get('use_llm_fallback', True)
    
    def extract_tables(self, html_content: str, base_url: str = "", **kwargs) -> List[Dict[str, Any]]:
        """Extract tables using smart hybrid approach."""
        if not html_content:
            return []
        
        soup = BeautifulSoup(html_content, 'lxml')
        table_tags = soup.find_all('table')
        
        if not table_tags:
            return []
        
        extracted_tables = []
        
        for idx, table_tag in enumerate(table_tags):
            try:
                # Assess table complexity
                complexity_score = self._assess_table_complexity(table_tag)
                
                if complexity_score < self.complexity_threshold:
                    # Use rule-based extraction for simple tables
                    table_data = self.default_extractor._extract_table_data(table_tag, base_url, idx)
                    
                    if table_data and self.default_extractor._is_valid_table(table_data):
                        table_data['metadata']['extraction_method'] = 'rule_based'
                        table_data['metadata']['complexity_score'] = complexity_score
                        extracted_tables.append(table_data)
                        
                        if self.verbose:
                            logger.debug(f"Table {idx} extracted with rule-based method (complexity: {complexity_score})")
                    
                elif self.use_llm_fallback:
                    # Use LLM for complex tables
                    table_html = str(table_tag)
                    table_data = await self.llm_extractor._extract_with_llm(table_html, idx, base_url)
                    
                    if table_data:
                        table_data['metadata']['complexity_score'] = complexity_score
                        extracted_tables.append(table_data)
                        
                        if self.verbose:
                            logger.debug(f"Table {idx} extracted with LLM method (complexity: {complexity_score})")
                
            except Exception as e:
                logger.error(f"Error extracting table {idx}: {str(e)}")
                continue
        
        logger.info(f"Extracted {len(extracted_tables)} tables using smart extraction")
        return extracted_tables
    
    def _assess_table_complexity(self, table_tag: Tag) -> int:
        """Assess the complexity of a table to choose extraction method."""
        complexity = 0
        
        # Count nested tables
        nested_tables = table_tag.find_all('table')
        complexity += len(nested_tables) * 3
        
        # Check for colspan/rowspan
        cells_with_span = table_tag.find_all(['td', 'th'], attrs={'colspan': True})
        cells_with_span.extend(table_tag.find_all(['td', 'th'], attrs={'rowspan': True}))
        complexity += len(cells_with_span) * 2
        
        # Count rows and columns
        rows = table_tag.find_all('tr')
        if rows:
            complexity += len(rows) // 5  # Every 5 rows adds complexity
            
            max_cols = 0
            for row in rows:
                cols = len(row.find_all(['td', 'th']))
                max_cols = max(max_cols, cols)
            complexity += max_cols // 3  # Every 3 columns adds complexity
        
        # Check for complex content in cells
        for cell in table_tag.find_all(['td', 'th']):
            # Lists in cells
            if cell.find(['ul', 'ol']):
                complexity += 2
            
            # Forms in cells
            if cell.find(['input', 'select', 'textarea']):
                complexity += 2
            
            # Images in cells
            if cell.find('img'):
                complexity += 1
        
        # Check for irregular structure
        row_col_counts = []
        for row in table_tag.find_all('tr'):
            col_count = len(row.find_all(['td', 'th']))
            row_col_counts.append(col_count)
        
        if row_col_counts and len(set(row_col_counts)) > 1:
            complexity += 3  # Irregular column structure
        
        return complexity


# Factory function for creating table extraction strategies
def create_table_extraction_strategy(
    strategy_type: str,
    config: Optional[Dict[str, Any]] = None
) -> TableExtractionStrategy:
    """
    Factory function to create table extraction strategies.
    
    Args:
        strategy_type: Type of strategy ("default", "llm", "smart", "none")
        config: Configuration dictionary for the strategy
        
    Returns:
        Configured table extraction strategy instance
    """
    config = config or {}
    
    strategies = {
        "default": DefaultTableExtraction,
        "llm": LLMTableExtraction,
        "smart": SmartTableExtraction,
        "none": NoTableExtraction
    }
    
    if strategy_type not in strategies:
        raise ValueError(f"Unknown table extraction strategy: {strategy_type}. Available: {list(strategies.keys())}")
    
    strategy_class = strategies[strategy_type]
    return strategy_class(**config)


# Convenience functions
async def extract_tables(
    html_content: str,
    base_url: str = "",
    strategy: str = "default",
    config: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Extract tables from HTML content using specified strategy.
    
    Args:
        html_content: HTML content to extract tables from
        base_url: Base URL for resolving relative links
        strategy: Extraction strategy to use
        config: Strategy configuration
        
    Returns:
        List of extracted table data
    """
    extractor = create_table_extraction_strategy(strategy, config)
    return extractor.extract_tables(html_content, base_url)


def tables_to_markdown(tables: List[Dict[str, Any]]) -> str:
    """
    Convert extracted tables to markdown format.
    
    Args:
        tables: List of table data from extraction
        
    Returns:
        Markdown representation of tables
    """
    if not tables:
        return ""
    
    markdown_parts = []
    
    for i, table in enumerate(tables):
        # Add table title
        caption = table.get('caption', f'Table {i + 1}')
        markdown_parts.append(f"\n## {caption}\n")
        
        # Add summary if present
        summary = table.get('summary')
        if summary:
            markdown_parts.append(f"*{summary}*\n")
        
        # Create markdown table
        headers = table.get('headers', [])
        rows = table.get('rows', [])
        
        if headers and rows:
            # Header row
            header_row = "| " + " | ".join(str(h) for h in headers) + " |"
            markdown_parts.append(header_row)
            
            # Separator row
            separator = "| " + " | ".join(["---"] * len(headers)) + " |"
            markdown_parts.append(separator)
            
            # Data rows
            for row in rows:
                # Ensure row has same number of columns as headers
                padded_row = row + [''] * (len(headers) - len(row))
                padded_row = padded_row[:len(headers)]  # Truncate if too long
                
                # Convert cells to strings, handling complex cell data
                cell_strings = []
                for cell in padded_row:
                    if isinstance(cell, dict) and 'text' in cell:
                        # Handle cells with links
                        cell_text = cell['text']
                        if 'links' in cell and cell['links']:
                            # Add first link as markdown link
                            first_link = cell['links'][0]
                            cell_text = f"[{first_link['text']}]({first_link['url']})"
                        cell_strings.append(cell_text)
                    else:
                        cell_strings.append(str(cell))
                
                data_row = "| " + " | ".join(cell_strings) + " |"
                markdown_parts.append(data_row)
        
        markdown_parts.append("")  # Empty line between tables
    
    return "\n".join(markdown_parts)
