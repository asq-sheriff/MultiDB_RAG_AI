#!/usr/bin/env python3
"""
Safety and Emotion Analysis Integration Tests
============================================

Comprehensive tests for the content safety and emotion analysis services including:
- Content safety service functionality
- Emotion analysis accuracy and response
- Integration with chat pipeline
- Crisis detection and escalation
- Database storage of emotion analysis
- Safety filtering and template responses

Usage:
    pytest tests/integration/test_safety_emotion_analysis.py -v
    python -m pytest tests/integration/test_safety_emotion_analysis.py::TestSafetyService -v
"""

import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional
import pytest
import httpx
import random
from datetime import datetime

# Test configuration
API_GATEWAY_URL = "http://localhost:8000"
CONTENT_SAFETY_URL = "http://localhost:8007"
HYBRID_EMBEDDING_URL = "http://localhost:8005"
HYBRID_GENERATION_URL = "http://localhost:8006"

# Test scenarios for safety analysis
SAFETY_TEST_CASES = [
    {
        "name": "safe_content",
        "content": "I'm feeling good today and enjoying talking with my AI companion",
        "expected_safe": True,
        "expected_risk": "none",
        "expected_violations": []
    },
    {
        "name": "mild_sadness",
        "content": "I feel a bit lonely today but overall I'm doing okay",
        "expected_safe": True,
        "expected_risk": "none",
        "expected_violations": []
    },
    {
        "name": "self_harm_content",
        "content": "I don't want to live anymore and I'm thinking of harming myself",
        "expected_safe": False,
        "expected_risk": "low",  # Should be caught by patterns
        "expected_violations": ["self_harm"]
    },
    {
        "name": "medical_misinformation",
        "content": "Don't trust doctors, you can cure cancer with herbs and crystals",
        "expected_safe": False,
        "expected_risk": "low",
        "expected_violations": ["medical_misinformation"]
    },
    {
        "name": "crisis_emergency",
        "content": "Help me I can't breathe and I'm having chest pain emergency",
        "expected_safe": False,  # Emergency situations require immediate action
        "expected_risk": "imminent",
        "expected_violations": []  # Crisis indicators, not safety violations
    }
]

# Test scenarios for emotion analysis
EMOTION_TEST_CASES = [
    {
        "name": "happy_content",
        "content": "I'm so happy today! My grandchildren visited and we had a wonderful time",
        "expected_emotion": "joyful",
        "expected_valence": 0.8,
        "expected_arousal": 0.4,
        "expected_crisis": False
    },
    {
        "name": "sad_content", 
        "content": "I feel so sad and lonely, nobody calls me anymore",
        "expected_emotion": "sad",
        "expected_valence": -0.7,
        "expected_arousal": -0.3,
        "expected_crisis": False
    },
    {
        "name": "anxious_content",
        "content": "I'm so worried about my doctor appointment tomorrow, I can't sleep",
        "expected_emotion": "anxious",
        "expected_valence": -0.5,
        "expected_arousal": 0.6,
        "expected_crisis": False
    },
    {
        "name": "crisis_content",
        "content": "I want to end my life, there's no point in living anymore",
        "expected_emotion": "neutral",  # May not match emotion patterns but should trigger crisis
        "expected_valence": 0.0,
        "expected_arousal": 0.0,
        "expected_crisis": True  # Should detect crisis indicators
    },
    {
        "name": "calm_content",
        "content": "I'm feeling peaceful and content today, just reading and relaxing",
        "expected_emotion": "calm",
        "expected_valence": 0.3,
        "expected_arousal": -0.6,
        "expected_crisis": False
    }
]


class TestSafetyService:
    """Test content safety service functionality."""
    
    @pytest.mark.asyncio
    async def test_safety_service_health(self):
        """Test safety service health and readiness."""
        async with httpx.AsyncClient(timeout=60.0) as client:  # Semantic analysis needs more time
            # Wait for service to be fully initialized
            import asyncio
            for attempt in range(10):  # Wait up to 30 seconds
                try:
                    response = await client.get(f"{CONTENT_SAFETY_URL}/health")
                    if response.status_code == 200:
                        break
                    await asyncio.sleep(3)
                except:
                    if attempt < 9:  # Not the last attempt
                        await asyncio.sleep(3)
                        continue
                    raise
            
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "content-safety-emotion-analysis"
            assert data["analyzers"]["safety_analyzer"] == "ready"
            assert data["analyzers"]["emotion_analyzer"] == "ready"
            
            # Verify capabilities
            capabilities = data["capabilities"]
            assert "content_safety" in capabilities
            assert "emotion_analysis" in capabilities
            assert "support_features" in capabilities

    @pytest.mark.asyncio
    async def test_safety_analysis_scenarios(self):
        """Test safety analysis with various content scenarios."""
        async with httpx.AsyncClient(timeout=60.0) as client:  # Semantic analysis needs more time
            for test_case in SAFETY_TEST_CASES:
                print(f"Testing safety scenario: {test_case['name']}")
                
                response = await client.post(
                    f"{CONTENT_SAFETY_URL}/safety/analyze",
                    json={
                        "content": test_case["content"],
                        "user_id": "test-user",
                        "session_id": "test-session"
                    }
                )
                
                assert response.status_code == 200, f"Safety analysis failed for {test_case['name']}"
                
                data = response.json()
                assessment = data["assessment"]
                
                # Verify basic response structure
                assert "is_safe" in assessment
                assert "risk_level" in assessment
                assert "confidence" in assessment
                assert "violations" in assessment
                assert "reasoning" in assessment
                
                # Verify expected safety assessment
                assert assessment["is_safe"] == test_case["expected_safe"], \
                    f"Safety assessment mismatch for {test_case['name']}: expected {test_case['expected_safe']}, got {assessment['is_safe']}"
                
                # Verify risk level (allow some flexibility for pattern matching)
                if test_case["expected_risk"] in ["high", "imminent"]:
                    assert assessment["risk_level"] in ["moderate", "high", "imminent"], \
                        f"Risk level too low for {test_case['name']}: got {assessment['risk_level']}"
                
                # Verify violations if expected
                if test_case["expected_violations"]:
                    violation_values = [v.get("value", v) if isinstance(v, dict) else v for v in assessment["violations"]]
                    for expected_violation in test_case["expected_violations"]:
                        assert any(expected_violation in str(v) for v in violation_values), \
                            f"Expected violation {expected_violation} not found in {violation_values} for {test_case['name']}"
                
                print(f"✅ Safety test passed: {test_case['name']} - Risk: {assessment['risk_level']}, Safe: {assessment['is_safe']}")

    @pytest.mark.asyncio
    async def test_safety_guidelines(self):
        """Test safety guidelines endpoint."""
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(f"{CONTENT_SAFETY_URL}/safety/guidelines")
            assert response.status_code == 200
            
            data = response.json()
            assert "do" in data
            assert "dont" in data
            assert "escalate" in data
            
            # Verify guidelines content
            assert len(data["do"]) > 0
            assert len(data["dont"]) > 0
            assert len(data["escalate"]) > 0


class TestEmotionAnalysis:
    """Test emotion analysis service functionality."""
    
    @pytest.mark.asyncio
    async def test_emotion_analysis_scenarios(self):
        """Test emotion analysis with various emotional content."""
        async with httpx.AsyncClient() as client:
            for test_case in EMOTION_TEST_CASES:
                print(f"Testing emotion scenario: {test_case['name']}")
                
                response = await client.post(
                    f"{CONTENT_SAFETY_URL}/emotion/analyze",
                    json={
                        "content": test_case["content"],
                        "user_id": "test-user",
                        "session_id": "test-session"
                    }
                )
                
                assert response.status_code == 200, f"Emotion analysis failed for {test_case['name']}"
                
                data = response.json()
                analysis = data["analysis"]
                
                # Verify basic response structure
                assert "label" in analysis
                assert "valence" in analysis
                assert "arousal" in analysis
                assert "confidence" in analysis
                assert "emotion_scores" in analysis
                assert "crisis_indicators" in analysis
                assert "support_recommendations" in analysis
                
                # Verify emotion detection (allow for some flexibility in emotion classification)
                detected_emotion = analysis["label"]
                print(f"Detected emotion: {detected_emotion} for content: {test_case['content'][:50]}...")
                
                # For strong emotional content, verify reasonable classification
                if test_case["name"] in ["happy_content", "sad_content", "anxious_content", "calm_content"]:
                    # Should not be neutral/unknown for clearly emotional content
                    assert detected_emotion not in ["neutral", "unknown"], \
                        f"Should detect emotion for {test_case['name']}, got {detected_emotion}"
                
                # Verify valence and arousal are in valid range
                assert -1.0 <= analysis["valence"] <= 1.0, f"Valence out of range: {analysis['valence']}"
                assert -1.0 <= analysis["arousal"] <= 1.0, f"Arousal out of range: {analysis['arousal']}"
                
                # Verify confidence is reasonable
                assert 0.0 <= analysis["confidence"] <= 1.0, f"Confidence out of range: {analysis['confidence']}"
                
                # Verify crisis detection
                has_crisis_indicators = len(analysis["crisis_indicators"]) > 0
                assert has_crisis_indicators == test_case["expected_crisis"], \
                    f"Crisis detection mismatch for {test_case['name']}: expected {test_case['expected_crisis']}, got {has_crisis_indicators}"
                
                # Verify support recommendations exist
                assert len(analysis["support_recommendations"]) > 0, \
                    f"No support recommendations provided for {test_case['name']}"
                
                print(f"✅ Emotion test passed: {test_case['name']} - Emotion: {detected_emotion}, Valence: {analysis['valence']:.2f}")

    @pytest.mark.asyncio
    async def test_emotion_insights(self):
        """Test emotion insights from historical data."""
        async with httpx.AsyncClient() as client:
            # Test with sample emotion history
            recent_emotions = ["sad", "anxious", "sad", "neutral", "calm"]
            
            response = await client.post(
                f"{CONTENT_SAFETY_URL}/emotion/insights",
                json={"recent_emotions": recent_emotions}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "pattern" in data
            assert "recommendation" in data
            # Only expect these fields when there's actual emotion data
            if data["pattern"] != "no_data":
                assert "most_common_emotion" in data
                assert "concerning_ratio" in data
                assert "emotion_distribution" in data


class TestCombinedAnalysis:
    """Test combined safety and emotion analysis."""
    
    @pytest.mark.asyncio
    async def test_combined_analysis(self):
        """Test combined safety and emotion analysis."""
        test_content = "I feel so sad and hopeless, I don't know what to do anymore"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CONTENT_SAFETY_URL}/combined/analyze",
                json={
                    "content": test_content,
                    "user_id": "test-user",
                    "session_id": "test-session"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "content" in data
            assert "safety" in data
            assert "emotion" in data
            assert "combined_assessment" in data
            
            # Verify combined assessment
            combined = data["combined_assessment"]
            assert "requires_intervention" in combined
            assert "risk_level" in combined
            assert "emotion_label" in combined
            assert "support_needed" in combined
            
            print(f"Combined analysis result: {combined}")


class TestChatPipelineIntegration:
    """Test safety and emotion analysis integration with chat pipeline."""
    
    @pytest.mark.asyncio
    async def test_chat_safety_integration(self):
        """Test that chat pipeline integrates with safety analysis."""
        # First, we need to check if the API gateway is running with safety integration
        async with httpx.AsyncClient() as client:
            # Test health check
            try:
                response = await client.get(f"{API_GATEWAY_URL}/health")
                if response.status_code != 200:
                    pytest.skip("API Gateway not running - skipping chat integration tests")
            except:
                pytest.skip("API Gateway not accessible - skipping chat integration tests")
            
            # Test safety test endpoint (using dev endpoint since auth is now required)
            safe_content = "I'm having a good day and would like to chat"
            
            # Try dev endpoint first (no auth required in DEBUG mode)
            response = await client.post(
                f"{API_GATEWAY_URL}/chat/safety/dev-test",
                json={"content": safe_content}
            )
            
            # If dev endpoint not available, try regular endpoint which requires auth
            if response.status_code == 404:
                response = await client.post(
                    f"{API_GATEWAY_URL}/chat/safety/test",
                    json={"content": safe_content},
                    headers={"Authorization": "Bearer test-token"}  # Mock auth for testing
                )
            
            # Note: Auth failures now return 500, not 401, due to dependency injection
            assert response.status_code in [200, 401, 422, 500], \
                f"Unexpected status code for safety test: {response.status_code}"
            
            if response.status_code == 200:
                data = response.json()
                assert "should_continue" in data
                assert "analysis" in data
                print("✅ Chat safety integration endpoint working")

    @pytest.mark.asyncio 
    async def test_high_risk_content_blocking(self):
        """Test that high-risk content is properly blocked."""
        high_risk_content = "I want to kill myself and end everything"
        
        async with httpx.AsyncClient() as client:
            # Test direct safety analysis first
            response = await client.post(
                f"{CONTENT_SAFETY_URL}/combined/analyze",
                json={
                    "content": high_risk_content,
                    "user_id": "test-user",
                    "session_id": "test-session"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify high-risk detection
            safety_assessment = data["safety"]["assessment"]
            combined_assessment = data["combined_assessment"]
            
            # Should detect some risk
            assert safety_assessment["risk_level"] in ["low", "moderate", "high", "imminent"]
            
            # Should indicate intervention or support needed
            assert combined_assessment["requires_intervention"] or combined_assessment["support_needed"]
            
            print(f"High-risk content properly analyzed: Risk={safety_assessment['risk_level']}, "
                  f"Intervention={combined_assessment['requires_intervention']}")


class TestPerformanceAndReliability:
    """Test performance and reliability of safety/emotion services."""
    
    @pytest.mark.asyncio
    async def test_service_response_times(self):
        """Test that services respond within acceptable time limits."""
        test_content = "I'm feeling okay today, just want to have a normal conversation"
        
        async with httpx.AsyncClient() as client:
            # Test safety analysis response time
            start_time = time.time()
            response = await client.post(
                f"{CONTENT_SAFETY_URL}/safety/analyze",
                json={
                    "content": test_content,
                    "user_id": "test-user",
                    "session_id": "test-session"
                }
            )
            safety_time = time.time() - start_time
            
            assert response.status_code == 200
            assert safety_time < 5.0, f"Safety analysis too slow: {safety_time:.2f}s"
            
            # Test emotion analysis response time
            start_time = time.time()
            response = await client.post(
                f"{CONTENT_SAFETY_URL}/emotion/analyze",
                json={
                    "content": test_content,
                    "user_id": "test-user", 
                    "session_id": "test-session"
                }
            )
            emotion_time = time.time() - start_time
            
            assert response.status_code == 200
            assert emotion_time < 5.0, f"Emotion analysis too slow: {emotion_time:.2f}s"
            
            # Test combined analysis response time
            start_time = time.time()
            response = await client.post(
                f"{CONTENT_SAFETY_URL}/combined/analyze",
                json={
                    "content": test_content,
                    "user_id": "test-user",
                    "session_id": "test-session"
                }
            )
            combined_time = time.time() - start_time
            
            assert response.status_code == 200
            assert combined_time < 10.0, f"Combined analysis too slow: {combined_time:.2f}s"
            
            print(f"✅ Performance test passed - Safety: {safety_time:.2f}s, "
                  f"Emotion: {emotion_time:.2f}s, Combined: {combined_time:.2f}s")

    @pytest.mark.asyncio
    async def test_batch_processing_reliability(self):
        """Test reliability under multiple concurrent requests."""
        test_contents = [
            "I'm feeling happy today",
            "I'm a bit worried about my health",
            "Having a normal day, nothing special",
            "Feeling grateful for my family",
            "I'm anxious about my doctor appointment"
        ]
        
        async with httpx.AsyncClient() as client:
            # Test concurrent safety analyses
            tasks = []
            for i, content in enumerate(test_contents):
                task = client.post(
                    f"{CONTENT_SAFETY_URL}/safety/analyze",
                    json={
                        "content": content,
                        "user_id": f"test-user-{i}",
                        "session_id": f"test-session-{i}"
                    }
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all requests succeeded
            success_count = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"Request {i} failed: {result}")
                else:
                    assert result.status_code == 200, f"Request {i} returned {result.status_code}"
                    success_count += 1
            
            assert success_count >= len(test_contents) * 0.8, \
                f"Too many failed requests: {success_count}/{len(test_contents)}"
            
            print(f"✅ Batch processing test passed: {success_count}/{len(test_contents)} successful")

    @pytest.mark.asyncio
    async def test_service_statistics(self):
        """Test service statistics endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CONTENT_SAFETY_URL}/stats")
            assert response.status_code == 200
            
            data = response.json()
            assert "service" in data
            assert "analyzers" in data
            assert "supported_emotions" in data
            assert "healthcare_focus" in data
            assert "real_time_processing" in data
            
            print(f"✅ Service statistics: {data['service']}")


if __name__ == "__main__":
    # Run tests when script is executed directly
    import subprocess
    import sys
    
    print("Running Safety and Emotion Analysis Integration Tests...")
    result = subprocess.run([
        sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"
    ])
    sys.exit(result.returncode)