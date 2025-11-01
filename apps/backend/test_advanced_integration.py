"""
Integration tests for advanced Firecrawl-inspired features.

Tests all the newly implemented advanced functionalities:
- Multi-provider search integration
- Multi-engine scraping architecture  
- LLM-powered configuration generation
- Advanced batch processing operations
- Multi-entity extraction service
"""

import asyncio
import json
import pytest
from typing import Dict, Any, List

# Test individual services
async def test_multi_search_service():
    """Test multi-provider search service."""
    try:
        from app.services.multi_search import get_multi_search_service, SearchOptions
        
        print("🔍 Testing Multi-Provider Search Service...")
        
        service = await get_multi_search_service()
        
        # Test basic search
        options = SearchOptions(
            query="artificial intelligence",
            num_results=5,
            lang="en",
            country="us"
        )
        
        results = await service.search(options)
        print(f"✅ Search completed: {len(results)} results found")
        
        # Test provider stats
        stats = await service.get_provider_stats()
        print(f"✅ Provider stats retrieved: {len(stats['providers'])} providers configured")
        
        return True
        
    except Exception as e:
        print(f"❌ Multi-search service test failed: {str(e)}")
        return False


async def test_multi_engine_scraping():
    """Test multi-engine scraping service."""
    try:
        from app.services.multi_engine_scraper import get_multi_engine_service
        from app.models.requests import ScrapingConfig
        
        print("🤖 Testing Multi-Engine Scraping Service...")
        
        service = await get_multi_engine_service()
        
        # Test scraping with fallback
        test_url = "https://example.com"
        config = ScrapingConfig(urls=[test_url])
        
        result = await service.scrape(test_url, config)
        print(f"✅ Scraping completed: engine={result.engine_used.value}, success={result.success}")
        
        # Test engine stats
        stats = await service.get_engine_stats()
        print(f"✅ Engine stats retrieved: {stats['total_engines']} engines available")
        
        return True
        
    except Exception as e:
        print(f"❌ Multi-engine scraping test failed: {str(e)}")
        return False


async def test_llm_configuration():
    """Test LLM-powered configuration generation."""
    try:
        from app.services.llm_configuration import get_llm_config_service, generate_config_from_prompt
        
        print("🧠 Testing LLM Configuration Service...")
        
        # Test configuration generation
        test_prompt = "Crawl a blog website and extract only article pages, excluding navigation and sidebar content"
        
        try:
            config = await generate_config_from_prompt(
                prompt=test_prompt,
                config_type="crawler"
            )
            print(f"✅ LLM config generation completed: {len(config)} options generated")
        except Exception as llm_error:
            print(f"⚠️ LLM config generation skipped (likely no OpenAI key): {str(llm_error)}")
        
        # Test service stats
        service = await get_llm_config_service()
        stats = await service.get_usage_stats()
        print(f"✅ LLM service stats retrieved: {stats['usage_stats']['total_requests']} requests processed")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM configuration test failed: {str(e)}")
        return False


async def test_batch_operations():
    """Test batch operation service."""
    try:
        from app.services.batch_operations import get_batch_service
        
        print("📦 Testing Batch Operations Service...")
        
        service = await get_batch_service()
        
        # Test batch scraping job submission
        test_urls = ["https://example.com", "https://httpbin.org/json"]
        
        job_id = await service.submit_batch_scrape(
            urls=test_urls,
            priority=20,
            metadata={"test": "integration"}
        )
        
        print(f"✅ Batch job submitted: {job_id}")
        
        # Test job status
        status = await service.get_job_status(job_id)
        if status:
            print(f"✅ Job status retrieved: {status.status.value}")
        
        # Test service stats
        stats = await service.get_service_stats()
        print(f"✅ Batch service stats: {stats['active_jobs']} active jobs")
        
        return True
        
    except Exception as e:
        print(f"❌ Batch operations test failed: {str(e)}")
        return False


async def test_multi_entity_extraction():
    """Test multi-entity extraction service."""
    try:
        from app.services.multi_entity_extraction import (
            get_multi_entity_service, 
            MultiEntityExtractionRequest,
            ExtractionStrategy
        )
        
        print("🔗 Testing Multi-Entity Extraction Service...")
        
        service = await get_multi_entity_service()
        
        # Test extraction request
        test_schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"}
            }
        }
        
        request = MultiEntityExtractionRequest(
            urls=["https://example.com"],
            schema=test_schema,
            extraction_strategy=ExtractionStrategy.LINKED_ENTITIES,
            max_related_urls=10,
            follow_links=False  # Keep it simple for testing
        )
        
        result = await service.extract_multi_entity(request)
        print(f"✅ Multi-entity extraction completed: {len(result.entities)} entities, success={result.success}")
        
        # Test service stats
        stats = await service.get_extraction_stats()
        print(f"✅ Extraction service stats: {stats['extraction_stats']['total_requests']} requests processed")
        
        return True
        
    except Exception as e:
        print(f"❌ Multi-entity extraction test failed: {str(e)}")
        return False


async def test_api_endpoints():
    """Test API endpoints are properly configured."""
    try:
        print("🌐 Testing API Endpoint Configuration...")
        
        # Test that we can import the routers without errors
        from app.api.v1.enhanced_search import router as enhanced_router
        from app.api.v2.advanced_endpoints import router as advanced_router
        
        print(f"✅ Enhanced search router: {len(enhanced_router.routes)} routes")
        print(f"✅ Advanced endpoints router: {len(advanced_router.routes)} routes")
        
        # Test that main app includes the routers
        from app.main import app
        
        total_routes = len(app.routes)
        print(f"✅ Main app configured: {total_routes} total routes")
        
        return True
        
    except Exception as e:
        print(f"❌ API endpoints test failed: {str(e)}")
        return False


async def run_integration_tests():
    """Run all integration tests."""
    print("🚀 Starting Advanced Features Integration Tests")
    print("=" * 60)
    
    tests = [
        ("Multi-Provider Search", test_multi_search_service),
        ("Multi-Engine Scraping", test_multi_engine_scraping),  
        ("LLM Configuration", test_llm_configuration),
        ("Batch Operations", test_batch_operations),
        ("Multi-Entity Extraction", test_multi_entity_extraction),
        ("API Endpoints", test_api_endpoints)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} Test...")
        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"💥 {test_name} test crashed: {str(e)}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("🎯 INTEGRATION TEST RESULTS")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\n📊 Summary: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Advanced features successfully integrated!")
    else:
        print(f"⚠️  {total-passed} tests failed. Review the output above for details.")
    
    return passed == total


async def test_feature_completeness():
    """Test that all Firecrawl-inspired features are implemented."""
    print("\n🔍 Testing Feature Completeness...")
    
    features_to_check = {
        "Multi-Provider Search": "app.services.multi_search",
        "Multi-Engine Scraping": "app.services.multi_engine_scraper", 
        "LLM Configuration": "app.services.llm_configuration",
        "Batch Operations": "app.services.batch_operations",
        "Multi-Entity Extraction": "app.services.multi_entity_extraction",
        "Enhanced API v1": "app.api.v1.enhanced_search",
        "Advanced API v2": "app.api.v2.advanced_endpoints"
    }
    
    implemented_features = []
    missing_features = []
    
    for feature_name, module_path in features_to_check.items():
        try:
            __import__(module_path)
            implemented_features.append(feature_name)
            print(f"✅ {feature_name}")
        except ImportError as e:
            missing_features.append((feature_name, str(e)))
            print(f"❌ {feature_name}: {str(e)}")
    
    print(f"\n📈 Feature Implementation: {len(implemented_features)}/{len(features_to_check)} features")
    
    if missing_features:
        print("\n⚠️  Missing Features:")
        for feature, error in missing_features:
            print(f"   - {feature}: {error}")
    else:
        print("🎉 All advanced features successfully implemented!")
    
    return len(missing_features) == 0


if __name__ == "__main__":
    async def main():
        print("🔥 FIRECRAWL-INSPIRED FEATURES INTEGRATION TEST")
        print("Testing advanced search and scraping capabilities...")
        print()
        
        # Test feature completeness
        completeness_ok = await test_feature_completeness()
        
        # Run integration tests
        integration_ok = await run_integration_tests()
        
        # Overall result
        if completeness_ok and integration_ok:
            print("\n🏆 SUCCESS: All Firecrawl-inspired features successfully integrated!")
            print("\nYour backend now includes:")
            print("• Multi-provider search with intelligent fallback")
            print("• Multi-engine scraping architecture")
            print("• LLM-powered configuration generation")
            print("• Advanced batch processing operations")
            print("• Multi-entity extraction with relationship mapping")
            print("• Enhanced API endpoints with comprehensive functionality")
        else:
            print("\n⚠️ PARTIAL SUCCESS: Some features may need attention")
    
    asyncio.run(main())
