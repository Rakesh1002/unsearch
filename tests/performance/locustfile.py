"""
Load testing configuration using Locust.
Run with: locust -f locustfile.py --host http://localhost:8000
"""
import json
import random
import time
from locust import HttpUser, task, between, events
from locust.env import Environment
from locust.stats import StatsCSVFileWriter
import os


# Configuration
API_KEY = os.getenv("LOAD_TEST_API_KEY", "test-api-key")
SEARCH_QUERIES = [
    "Python programming",
    "machine learning algorithms",
    "web scraping techniques",
    "FastAPI tutorial",
    "data science tools",
    "artificial intelligence",
    "cloud computing AWS",
    "Docker containers",
    "Kubernetes orchestration",
    "microservices architecture",
    "REST API design",
    "GraphQL vs REST",
    "database optimization",
    "Redis caching strategies",
    "PostgreSQL performance",
]

SEARCH_ENGINES = [
    ["google"],
    ["bing"],
    ["duckduckgo"],
    ["google", "bing"],
    ["google", "bing", "duckduckgo"],
]


class UnSearchUser(HttpUser):
    """
    Simulates a user interacting with the UnSearch API.
    """
    wait_time = between(1, 5)  # Wait 1-5 seconds between requests
    
    def on_start(self):
        """Called when a user starts."""
        self.client.headers.update({
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        })
        
        # Test authentication
        response = self.client.get("/health", name="Health Check")
        if response.status_code != 200:
            print(f"Warning: Health check returned {response.status_code}")
    
    @task(10)
    def search_without_scraping(self):
        """Perform a search without content scraping (most common)."""
        query = random.choice(SEARCH_QUERIES)
        engines = random.choice(SEARCH_ENGINES)
        max_results = random.randint(5, 20)
        
        payload = {
            "query": query,
            "engines": engines,
            "max_results": max_results,
            "scrape_content": False,
            "cache_ttl": 3600
        }
        
        with self.client.post(
            "/api/v1/search",
            json=payload,
            name="Search (No Scraping)",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "results" not in data:
                    response.failure("No results in response")
                elif len(data["results"]) == 0:
                    response.failure("Empty results")
            elif response.status_code == 429:
                # Rate limited - this is expected under load
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(3)
    def search_with_scraping(self):
        """Perform a search with content scraping (resource intensive)."""
        query = random.choice(SEARCH_QUERIES)
        engines = ["google"]  # Single engine for scraping tests
        max_results = random.randint(3, 5)  # Fewer results for scraping
        
        payload = {
            "query": query,
            "engines": engines,
            "max_results": max_results,
            "scrape_content": True,
            "include_images": True,
            "include_links": True,
            "cache_ttl": 3600
        }
        
        with self.client.post(
            "/api/v1/search",
            json=payload,
            name="Search (With Scraping)",
            catch_response=True,
            timeout=30  # Longer timeout for scraping
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "results" in data:
                    # Check if scraping worked
                    scraped_count = sum(1 for r in data["results"] if r.get("scraped_content"))
                    if scraped_count == 0:
                        response.failure("No content was scraped")
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(2)
    def search_with_caching(self):
        """Test caching by repeating the same search."""
        # Use a limited set of queries for cache testing
        cache_queries = SEARCH_QUERIES[:5]
        query = random.choice(cache_queries)
        
        payload = {
            "query": query,
            "engines": ["google"],
            "max_results": 10,
            "scrape_content": False,
            "cache_ttl": 3600
        }
        
        # First request
        with self.client.post(
            "/api/v1/search",
            json=payload,
            name="Search (Cache Test)",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                
                # Second request (should be cached)
                time.sleep(0.5)
                with self.client.post(
                    "/api/v1/search",
                    json=payload,
                    name="Search (Cached)",
                    catch_response=True
                ) as cached_response:
                    if cached_response.status_code == 200:
                        cached_data = cached_response.json()
                        if cached_data.get("cached", False):
                            # Successfully hit cache
                            pass
                        else:
                            # Not cached - might be OK in high load
                            pass
    
    @task(1)
    def check_health(self):
        """Periodically check API health."""
        with self.client.get(
            "/health",
            name="Health Check",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") not in ["healthy", "degraded"]:
                    response.failure("Unexpected health status")
    
    @task(1)
    def check_metrics(self):
        """Check metrics endpoint."""
        with self.client.get(
            "/metrics",
            name="Metrics",
            catch_response=True
        ) as response:
            # Metrics might be protected or disabled
            if response.status_code in [200, 401, 404]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


class AdminUser(HttpUser):
    """
    Simulates an admin user checking system status.
    """
    wait_time = between(10, 30)  # Less frequent checks
    weight = 1  # Fewer admin users
    
    def on_start(self):
        """Set up admin headers."""
        self.client.headers.update({
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        })
    
    @task
    def check_system_health(self):
        """Check overall system health."""
        endpoints = ["/health", "/metrics", "/docs"]
        
        for endpoint in endpoints:
            with self.client.get(
                endpoint,
                name=f"Admin: {endpoint}",
                catch_response=True
            ) as response:
                if response.status_code in [200, 307, 401, 404]:
                    response.success()


class MobileUser(HttpUser):
    """
    Simulates mobile app users with different patterns.
    """
    wait_time = between(2, 8)
    weight = 3  # Mobile users are common
    
    def on_start(self):
        """Mobile client setup."""
        self.client.headers.update({
            "X-API-Key": API_KEY,
            "Content-Type": "application/json",
            "User-Agent": "UnSearch-Mobile/1.0"
        })
    
    @task(10)
    def quick_search(self):
        """Quick searches typical of mobile users."""
        query = random.choice(SEARCH_QUERIES)
        
        payload = {
            "query": query,
            "engines": ["google"],  # Mobile users might use single engine
            "max_results": 5,  # Fewer results for mobile
            "scrape_content": False,
            "cache_ttl": 7200  # Longer cache for mobile
        }
        
        with self.client.post(
            "/api/v1/search",
            json=payload,
            name="Mobile: Quick Search",
            catch_response=True,
            timeout=10
        ) as response:
            if response.status_code == 200:
                data = response.json()
                # Mobile expects fast responses
                if response.elapsed.total_seconds() > 3:
                    response.failure("Response too slow for mobile")
            elif response.status_code == 429:
                response.success()


# Custom event handlers for detailed reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts."""
    print(f"Load test starting...")
    print(f"Target host: {environment.host}")
    print(f"Users: {environment.parsed_options.num_users}")
    print(f"Spawn rate: {environment.parsed_options.spawn_rate}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops."""
    print("\nLoad test completed!")
    print("\nFinal Statistics:")
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Failure rate: {environment.stats.total.fail_ratio:.2%}")
    print(f"Average response time: {environment.stats.total.avg_response_time:.0f}ms")
    print(f"Median response time: {environment.stats.total.median_response_time:.0f}ms")
    
    # Save detailed stats
    if environment.parsed_options and hasattr(environment.parsed_options, 'html_file'):
        stats_writer = StatsCSVFileWriter(
            environment,
            percentiles_to_report=[50, 90, 95, 99]
        )


# Standalone test scenarios for different load patterns
class StressTestUser(HttpUser):
    """
    User for stress testing - generates maximum load.
    """
    wait_time = between(0.1, 0.5)  # Minimal wait time
    
    def on_start(self):
        self.client.headers["X-API-Key"] = API_KEY
    
    @task
    def stress_search(self):
        """Rapid-fire search requests."""
        payload = {
            "query": f"stress test {random.randint(1, 1000)}",
            "engines": ["google"],
            "max_results": 1,
            "scrape_content": False,
            "cache_ttl": 0  # No caching for stress test
        }
        
        self.client.post(
            "/api/v1/search",
            json=payload,
            name="Stress Test"
        )


class SpikeTestUser(HttpUser):
    """
    User for spike testing - sudden traffic increases.
    """
    wait_time = between(0.5, 1)
    
    def on_start(self):
        self.client.headers["X-API-Key"] = API_KEY
    
    @task
    def spike_search(self):
        """Burst of requests."""
        # Simulate spike pattern
        if random.random() < 0.3:  # 30% chance of burst
            for _ in range(5):  # Send 5 rapid requests
                payload = {
                    "query": f"spike test {time.time()}",
                    "engines": ["google"],
                    "max_results": 3,
                    "scrape_content": False
                }
                
                self.client.post(
                    "/api/v1/search",
                    json=payload,
                    name="Spike Test"
                )
                time.sleep(0.1)


# Configuration for different test scenarios
TEST_SCENARIOS = {
    "normal": {
        "users": 50,
        "spawn_rate": 2,
        "run_time": "5m",
        "description": "Normal load test"
    },
    "stress": {
        "users": 200,
        "spawn_rate": 10,
        "run_time": "10m",
        "description": "Stress test with high load"
    },
    "spike": {
        "users": 100,
        "spawn_rate": 50,
        "run_time": "3m",
        "description": "Spike test with sudden traffic"
    },
    "endurance": {
        "users": 30,
        "spawn_rate": 1,
        "run_time": "60m",
        "description": "Endurance test over extended period"
    }
}


if __name__ == "__main__":
    """
    Run load test programmatically.
    Usage: python locustfile.py [scenario]
    """
    import sys
    from locust.env import Environment
    from locust.stats import stats_printer, stats_history
    import gevent
    
    # Get scenario from command line
    scenario = sys.argv[1] if len(sys.argv) > 1 else "normal"
    config = TEST_SCENARIOS.get(scenario, TEST_SCENARIOS["normal"])
    
    print(f"\nRunning {config['description']}")
    print(f"Users: {config['users']}, Spawn rate: {config['spawn_rate']}, Duration: {config['run_time']}\n")
    
    # Setup Environment
    env = Environment(user_classes=[UnSearchUser, MobileUser], host="http://localhost:8000")
    env.create_local_runner()
    
    # Start test
    env.runner.start(config["users"], spawn_rate=config["spawn_rate"])
    
    # Run for specified time
    duration = int(config["run_time"][:-1]) * (60 if "m" in config["run_time"] else 1)
    gevent.spawn(stats_printer(env.stats))
    gevent.spawn(stats_history, env.runner)
    
    env.runner.greenlet.join(timeout=duration)
    env.runner.quit()
    
    # Print final stats
    print("\n" + "="*50)
    print("Test completed!")
    print(f"Total requests: {env.stats.total.num_requests}")
    print(f"Failure rate: {env.stats.total.fail_ratio:.2%}")
    print(f"Avg response time: {env.stats.total.avg_response_time:.0f}ms")
    print("="*50)
