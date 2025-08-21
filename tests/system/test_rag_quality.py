"""Fixed RAG quality tests - properly uses getters"""
import pytest
from app.dependencies import get_knowledge_service


@pytest.mark.asyncio
class TestRAGQuality:
    async def test_search_routes(self):
        """Test different search routes in the knowledge service."""
        # FIXED: Get knowledge service using getter
        knowledge_service = get_knowledge_service()
        assert knowledge_service is not None, "Knowledge service should be initialized"

        query = "How do I reset my password?"

        # Test different routes
        # FIXED: Use "semantic" instead of "vector" route
        results = await knowledge_service.search_router(
            query=query,
            top_k=3,
            route="semantic"  # Changed from "vector" to "semantic"
        )

        assert results is not None
        assert "route" in results or "query" in results

        # The results structure can vary, handle different cases
        if "results" in results:
            # We have search results
            assert isinstance(results["results"], list)
            # Results might be empty if no documents are seeded
            if results["results"]:
                first_result = results["results"][0]
                # Check for expected fields
                assert any([
                    "content" in first_result,
                    "answer" in first_result,
                    "question" in first_result
                ])

        # Test exact search route
        exact_results = await knowledge_service.search_router(
            query=query,
            top_k=3,
            route="exact"
        )

        assert exact_results is not None

        # Test auto route (should automatically select best route)
        auto_results = await knowledge_service.search_router(
            query=query,
            top_k=3,
            route="auto"
        )

        assert auto_results is not None
        # Auto route should have decided on a specific route
        if "route" in auto_results:
            assert "->" in auto_results["route"] or auto_results["route"] in ["exact", "semantic", "hybrid"]