"""
Unit tests to verify BeautifulSoup parsing is offloaded to a thread pool and does not block the FastAPI event loop.
"""
import asyncio
import time
import pytest
from unittest.mock import Mock, AsyncMock, patch

# Mock sent_tokenize to avoid requiring download of punkt_tab in tests
def mock_sent_tokenize(text):
    return [s.strip() for s in text.split('.') if s.strip()]

patch('app.utils.text_processing.sent_tokenize', side_effect=mock_sent_tokenize).start()

from app.services.scraping import ContentScrapingService
from app.models.requests import ScrapingConfig
from bs4 import BeautifulSoup
from app.utils.text_processing import sanitize_text

# A complex sample HTML for checking consistency
SAMPLE_HTML = """
<html>
<head>
    <title>Test Page Title</title>
    <meta name="description" content="This is a test description.">
    <meta name="author" content="Jane Doe">
    <meta name="keywords" content="test, scraping, nonblocking">
    <meta property="og:title" content="OG Title">
    <meta property="og:description" content="OG Description">
    <meta name="twitter:card" content="summary">
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": "JSON-LD Name"
    }
    </script>
    <style>
        body { font-family: sans-serif; }
    </style>
    <script>
        console.log("This should be removed!");
    </script>
</head>
<body>
    <header>
        <h1>Main Header</h1>
    </header>
    <main>
        <article>
            <h2>Article Heading</h2>
            <p>This is the first paragraph of the main article content.</p>
            <p>This is the second paragraph of the main article content.</p>
        </article>
    </main>
    <aside>
        <p>Sidebar content</p>
    </aside>
    <footer>
        <p>Footer content</p>
        <a href="/about-us">About Us</a>
        <a href="https://example.org/privacy">Privacy Policy</a>
        <img src="/logo.png" alt="Logo">
        <img src="https://example.org/tracker.gif" width="1" height="1" alt="tracker">
    </footer>
</body>
</html>
"""

@pytest.fixture
async def scraping_service():
    """Create scraping service for testing."""
    service = ContentScrapingService()
    await service.initialize()
    yield service
    await service.close()

@pytest.mark.asyncio
async def test_extraction_consistency(scraping_service):
    """Verify that offloaded scraping returns identical results to standard parsing."""
    config = ScrapingConfig(
        urls=["https://example.com/test"],
        extract_images=True,
        extract_links=True
    )
    
    # Scrape via the service (which uses the executor under the hood)
    scraped = await scraping_service._scrape_page_payload(
        url="https://example.com/test",
        html=SAMPLE_HTML,
        config=config
    )
    
    assert scraped.extraction_success is True
    assert scraped.title == "Test Page Title"
    assert "This is the first paragraph" in scraped.text
    assert "This should be removed" not in scraped.text
    
    # Check metadata
    assert scraped.metadata.title == "Test Page Title"
    assert scraped.metadata.description == "This is a test description."
    assert scraped.metadata.author == "Jane Doe"
    assert scraped.metadata.keywords == ["test", "scraping", "nonblocking"]
    assert scraped.metadata.og_data.get("title") == "OG Title"
    assert scraped.metadata.og_data.get("description") == "OG Description"
    assert scraped.metadata.twitter_data.get("card") == "summary"
    assert scraped.metadata.json_ld.get("name") == "JSON-LD Name"
    
    # Check links and images (excluding tracking pixels)
    # Check links and images (excluding tracking pixels)
    links_str = [str(link) for link in scraped.links]
    images_str = [str(img) for img in scraped.images]
    assert "https://example.com/about-us" in links_str
    assert "https://example.org/privacy" in links_str
    assert "https://example.com/logo.png" in images_str
    # Tracker should be filtered out
    assert "https://example.org/tracker.gif" not in images_str


@pytest.mark.asyncio
async def test_non_blocking_event_loop(scraping_service):
    """Verify that concurrent scraping of huge HTML documents does not block the async event loop."""
    # Construct a large HTML (approx. 185KB) to force BeautifulSoup to consume CPU cycles.
    large_body = "<p>Some text content for parsing.</p>\n" * 500
    huge_html = f"<html><head><title>Huge Page</title></head><body>{large_body}</body></html>"
    
    config = ScrapingConfig(
        urls=["https://example.com/large"],
        extract_images=False,
        extract_links=False
    )
    
    # Ticking background task to monitor event loop latency
    tick_deltas = []
    keep_ticking = True
    
    async def ticker():
        last_time = time.perf_counter()
        while keep_ticking:
            await asyncio.sleep(0.002)
            now = time.perf_counter()
            delta = now - last_time
            tick_deltas.append(delta)
            last_time = now

    ticker_task = asyncio.create_task(ticker())
    # Allow the ticker to start running
    await asyncio.sleep(0.05)
    
    # Trigger 3 concurrent scrapes of the HTML document
    start_scrape = time.perf_counter()
    scrape_tasks = [
        scraping_service._scrape_page_payload(
            url=f"https://example.com/large_{i}",
            html=huge_html,
            config=config
        )
        for i in range(3)
    ]
    
    results = await asyncio.gather(*scrape_tasks)
    scrape_duration = time.perf_counter() - start_scrape
    
    # Stop the ticker
    keep_ticking = False
    await ticker_task
    
    # Verify that all scrapes succeeded
    for res in results:
        assert res.extraction_success is True
        assert res.title == "Huge Page"
        
    # Analyse loop delay.
    # Standard ticker sleep is 2ms, so delta should be around 2-5ms.
    # If the BeautifulSoup parser blocked the event loop synchronously, we would see at least one delta of several hundred ms.
    blocking_ticks = [d for d in tick_deltas if d > 0.30] # ticks delayed by more than 300ms
    
    print(f"Total scraping duration for 3 large tasks: {scrape_duration:.3f}s")
    print(f"Total ticks recorded: {len(tick_deltas)}")
    print(f"Max tick delta: {max(tick_deltas):.6f}s")
    print(f"Number of ticks > 300ms: {len(blocking_ticks)}")
    if blocking_ticks:
        print(f"Top 5 delays: {sorted(blocking_ticks, reverse=True)[:5]}")
        
    # Assert that the event loop was not blocked for > 300ms by BeautifulSoup
    assert len(blocking_ticks) == 0, f"Event loop was blocked! Max delay: {max(tick_deltas)*1000:.2f}ms"
