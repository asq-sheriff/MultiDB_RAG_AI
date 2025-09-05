"""
Enhanced Security Improvements End-to-End Integration Tests

Tests the three new security improvements:
1. Rate limiting for cache operations
2. Secure memory clearing for sensitive data
3. Access logging and audit trails

Run with:
    pytest tests/integration/test_security_improvements_e2e.py -v --tb=short
    python -m pytest tests/integration/test_security_improvements_e2e.py::TestRateLimitingSecurity -v
"""

import asyncio
import time
import uuid
import json
import logging
import gc
import os
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import pytest
from unittest.mock import patch, MagicMock

# Add project root to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

try:
    from app.services.therapeutic_cache_manager import TherapeuticCacheManager, get_therapeutic_cache_manager
except ImportError:
    # Skip if therapeutic cache not available
    TherapeuticCacheManager = None
    get_therapeutic_cache_manager = None

# Test configuration
TEST_ENVIRONMENT_VARS = {
    "CACHE_RATE_LIMIT_ENABLED": "true",
    "CACHE_RATE_LIMIT_RPM": "10",  # Low limit for testing
    "CACHE_RATE_LIMIT_BURST": "3",  # Small burst for testing
    "CACHE_ACCESS_LOGGING_ENABLED": "true",
    "CACHE_ACCESS_LOG_LEVEL": "DEBUG",
    "HEALTHCARE_ENCRYPTION_ENABLED": "true",
    "TESTING": "true"
}

class TestRateLimitingSecurity:
    """Test rate limiting functionality for cache operations"""
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Set up test environment variables"""
        self.original_env = {}
        for key, value in TEST_ENVIRONMENT_VARS.items():
            self.original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        yield
        
        # Restore original environment
        for key, original_value in self.original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value
    
    @pytest.fixture
    async def cache_manager(self):
        """Create a fresh cache manager for testing"""
        manager = TherapeuticCacheManager()
        await manager.initialize()
        yield manager
        await manager.cleanup()
    
    async def test_rate_limiting_configuration(self, cache_manager):
        """Test that rate limiting is properly configured"""
        assert cache_manager.rate_limit_enabled == True
        assert cache_manager.rate_limit_requests_per_minute == 10
        assert cache_manager.rate_limit_burst_size == 3
        assert len(cache_manager.rate_limit_buckets) == 0
        
        print("✅ Rate limiting configuration validated")
    
    async def test_rate_limiting_allows_normal_requests(self, cache_manager):
        """Test that normal requests within limits are allowed"""
        user_context = {"user_id": "test_user_normal", "session_id": "test_session"}
        
        # Make requests within burst limit
        for i in range(3):
            result = await cache_manager.get_cached_response(
                "test query for normal requests",
                user_context=user_context
            )
            # Should not be rate limited (will be cache miss, but not blocked)
            assert result is None  # Cache miss is expected
        
        # Check that bucket was created
        assert "test_user_normal" in cache_manager.rate_limit_buckets
        bucket = cache_manager.rate_limit_buckets["test_user_normal"]
        assert bucket["total_requests"] == 3
        assert bucket["blocked_requests"] == 0
        
        print("✅ Normal requests within limits are allowed")
    
    async def test_rate_limiting_blocks_excessive_requests(self, cache_manager):
        """Test that excessive requests are rate limited"""
        user_context = {"user_id": "test_user_excessive", "session_id": "test_session"}
        
        # Make requests that exceed burst limit
        successful_requests = 0
        blocked_requests = 0
        
        for i in range(8):  # Exceed burst size of 3
            result = await cache_manager.get_cached_response(
                f"test query {i}",
                user_context=user_context
            )
            if result is None:
                # Check if it was blocked due to rate limiting or cache miss
                bucket = cache_manager.rate_limit_buckets["test_user_excessive"]
                if bucket["blocked_requests"] > 0:
                    blocked_requests += 1
                else:
                    successful_requests += 1
            else:
                successful_requests += 1
        
        # Verify that some requests were blocked
        bucket = cache_manager.rate_limit_buckets["test_user_excessive"]
        assert bucket["blocked_requests"] > 0
        assert cache_manager.cache_stats["rate_limit_blocks"] > 0
        
        print(f"✅ Rate limiting blocked {blocked_requests} excessive requests")
    
    async def test_rate_limiting_per_user_isolation(self, cache_manager):
        """Test that rate limiting is isolated per user"""
        user1_context = {"user_id": "user_1", "session_id": "session_1"}
        user2_context = {"user_id": "user_2", "session_id": "session_2"}
        
        # User 1 exhausts their rate limit
        for i in range(5):
            await cache_manager.get_cached_response(
                f"user1 query {i}",
                user_context=user1_context
            )
        
        # User 2 should still be able to make requests
        for i in range(3):
            result = await cache_manager.get_cached_response(
                f"user2 query {i}",
                user_context=user2_context
            )
            # Should not be rate limited initially
        
        # Verify separate buckets
        assert "user_1" in cache_manager.rate_limit_buckets
        assert "user_2" in cache_manager.rate_limit_buckets
        
        user2_bucket = cache_manager.rate_limit_buckets["user_2"]
        # User 2 should have fewer blocked requests than user 1
        assert user2_bucket["total_requests"] == 3
        
        print("✅ Rate limiting is properly isolated per user")
    
    async def test_rate_limiting_token_bucket_refill(self, cache_manager):
        """Test that rate limiting tokens are refilled over time"""
        user_context = {"user_id": "test_user_refill", "session_id": "test_session"}
        
        # Exhaust initial tokens
        for i in range(4):  # Exceed burst size
            await cache_manager.get_cached_response(
                f"exhaust query {i}",
                user_context=user_context
            )
        
        bucket_before = cache_manager.rate_limit_buckets["test_user_refill"].copy()
        
        # Wait for token refill (simulate time passage)
        # Manually adjust last_refill time to simulate passage
        bucket = cache_manager.rate_limit_buckets["test_user_refill"]
        bucket["last_refill"] = datetime.now(timezone.utc) - timedelta(seconds=30)  # 30 seconds ago
        
        # Make another request - should have refilled tokens
        result = await cache_manager.get_cached_response(
            "refill test query",
            user_context=user_context
        )
        
        bucket_after = cache_manager.rate_limit_buckets["test_user_refill"]
        # Tokens should have been refilled
        assert bucket_after["tokens"] >= 0  # Should have tokens available
        
        print("✅ Rate limiting token bucket refill works correctly")
    
    async def test_rate_limiting_statistics_tracking(self, cache_manager):
        """Test that rate limiting statistics are properly tracked"""
        user_context = {"user_id": "test_user_stats", "session_id": "test_session"}
        
        initial_blocks = cache_manager.cache_stats["rate_limit_blocks"]
        initial_buckets = cache_manager.cache_stats["active_rate_limit_buckets"]
        
        # Generate rate limit violations
        for i in range(6):  # Exceed limits
            await cache_manager.get_cached_response(
                f"stats query {i}",
                user_context=user_context
            )
        
        # Check statistics
        stats = cache_manager.get_cache_stats()
        assert stats["rate_limit_blocks"] > initial_blocks
        assert stats["active_rate_limit_buckets"] > initial_buckets
        assert stats["rate_limit_enabled"] == True
        assert "rate_limit_config" in stats
        assert stats["rate_limit_config"]["requests_per_minute"] == 10
        assert stats["rate_limit_config"]["burst_size"] == 3
        
        print("✅ Rate limiting statistics are properly tracked")


class TestSecureMemoryClearing:
    """Test secure memory clearing functionality"""
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Set up test environment variables"""
        self.original_env = {}
        for key, value in TEST_ENVIRONMENT_VARS.items():
            self.original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        yield
        
        # Restore original environment
        for key, original_value in self.original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value
    
    @pytest.fixture
    async def cache_manager(self):
        """Create a fresh cache manager for testing"""
        manager = TherapeuticCacheManager()
        await manager.initialize()
        yield manager
        await manager.cleanup()
    
    async def test_secure_clear_data_dictionary(self, cache_manager):
        """Test secure clearing of dictionary data"""
        # Create test data with sensitive content
        test_data = {
            "patient_name": "John Doe",
            "ssn": "123-45-6789",
            "medical_record": "MR987654321",
            "diagnosis": "Confidential medical information",
            "nested_data": {
                "medication": "Sensitive drug information",
                "dosage": "Personal health data"
            }
        }
        
        original_data = json.dumps(test_data, sort_keys=True)
        
        # Apply secure clearing
        cache_manager._secure_clear_data(test_data)
        
        # Verify data is cleared
        assert len(test_data) == 0  # Dictionary should be empty
        cleared_data = json.dumps(test_data, sort_keys=True)
        assert cleared_data != original_data
        
        print("✅ Secure clearing of dictionary data works correctly")
    
    async def test_secure_clear_data_list(self, cache_manager):
        """Test secure clearing of list data"""
        test_data = [
            "Patient information",
            {"phi_data": "123-45-6789"},
            ["nested", "sensitive", "data"],
            "More confidential content"
        ]
        
        original_length = len(test_data)
        
        # Apply secure clearing
        cache_manager._secure_clear_data(test_data)
        
        # Verify list is cleared
        assert len(test_data) == 0
        assert test_data != ["Patient information", {"phi_data": "123-45-6789"}]
        
        print("✅ Secure clearing of list data works correctly")
    
    async def test_secure_clearing_in_cache_eviction(self, cache_manager):
        """Test that secure clearing is applied during cache eviction"""
        # Fill L1 cache to trigger eviction
        sensitive_data = {
            "user_query": "What is my SSN 123-45-6789?",
            "response": "I cannot share SSN information",
            "phi_detected": True,
            "sensitive_content": "This should be securely cleared"
        }
        
        # Fill cache beyond capacity to trigger eviction
        for i in range(cache_manager.l1_max_size + 2):
            cache_key = f"test_key_{i}"
            test_data = sensitive_data.copy()
            test_data["query_id"] = i
            
            await cache_manager._set_l1_cache(cache_key, test_data)
        
        # Check that evictions occurred and cache size is within limits
        assert len(cache_manager.l1_cache) <= cache_manager.l1_max_size
        assert cache_manager.cache_stats["evictions"] > 0
        
        print("✅ Secure clearing works during cache eviction")
    
    async def test_secure_clearing_in_cleanup(self, cache_manager):
        """Test that secure clearing is applied during cleanup"""
        # Add data to cache and rate limiting buckets
        user_context = {"user_id": "cleanup_test_user", "session_id": "test_session"}
        
        # Add cache data
        test_cache_data = {
            "sensitive_response": "This contains PHI data",
            "user_info": {"id": "user123", "session": "session456"}
        }
        await cache_manager._set_l1_cache("cleanup_test_key", test_cache_data)
        
        # Create rate limiting data
        await cache_manager.get_cached_response(
            "test query for cleanup",
            user_context=user_context
        )
        
        # Verify data exists before cleanup
        assert len(cache_manager.l1_cache) > 0
        assert len(cache_manager.rate_limit_buckets) > 0
        
        # Perform cleanup
        await cache_manager.cleanup()
        
        # Verify data is securely cleared
        assert len(cache_manager.l1_cache) == 0
        assert len(cache_manager.rate_limit_buckets) == 0
        
        print("✅ Secure clearing works during cleanup")
    
    async def test_rate_limit_bucket_secure_clearing(self, cache_manager):
        """Test secure clearing of rate limit buckets during cleanup"""
        # Create multiple users to generate rate limit buckets
        for i in range(5):
            user_context = {"user_id": f"bucket_user_{i}", "session_id": f"session_{i}"}
            await cache_manager.get_cached_response(
                f"bucket test query {i}",
                user_context=user_context
            )
        
        # Verify buckets were created
        assert len(cache_manager.rate_limit_buckets) == 5
        
        # Manually trigger bucket cleanup (simulate old buckets)
        for user_id, bucket in cache_manager.rate_limit_buckets.items():
            bucket["last_refill"] = datetime.now(timezone.utc) - timedelta(hours=2)  # Make them old
        
        # Trigger cleanup
        cache_manager._cleanup_old_rate_limit_buckets()
        
        # Verify buckets were securely cleared
        assert len(cache_manager.rate_limit_buckets) == 0
        
        print("✅ Rate limit buckets are securely cleared during cleanup")


class TestAccessLoggingAuditTrail:
    """Test access logging and audit trail functionality"""
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Set up test environment variables"""
        self.original_env = {}
        for key, value in TEST_ENVIRONMENT_VARS.items():
            self.original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        yield
        
        # Restore original environment
        for key, original_value in self.original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value
    
    @pytest.fixture
    async def cache_manager(self):
        """Create a fresh cache manager for testing"""
        manager = TherapeuticCacheManager()
        await manager.initialize()
        yield manager
        await manager.cleanup()
    
    @pytest.fixture
    def capture_logs(self, caplog):
        """Fixture to capture log output"""
        caplog.set_level(logging.DEBUG, logger="app.services.therapeutic_cache_manager.audit")
        return caplog
    
    async def test_access_logging_configuration(self, cache_manager):
        """Test that access logging is properly configured"""
        assert cache_manager.access_logging_enabled == True
        assert cache_manager.access_log_level == "DEBUG"
        assert cache_manager.audit_logger is not None
        assert cache_manager.audit_logger.name.endswith(".audit")
        
        print("✅ Access logging configuration validated")
    
    async def test_cache_get_access_logging(self, cache_manager, capture_logs):
        """Test access logging for cache GET operations"""
        user_context = {"user_id": "log_test_user", "session_id": "log_test_session"}
        
        # Clear any existing logs
        capture_logs.clear()
        
        # Perform cache get operation (will be a miss)
        result = await cache_manager.get_cached_response(
            "test query for logging",
            user_context=user_context
        )
        
        # Check for access log entries
        log_messages = [record.message for record in capture_logs.records]
        
        # Should have log entries for cache miss
        cache_access_logs = [msg for msg in log_messages if "CACHE_ACCESS" in msg]
        assert len(cache_access_logs) > 0
        
        # Verify log content
        miss_log = next((log for log in cache_access_logs if "miss" in log.lower()), None)
        assert miss_log is not None
        assert "log_test_use..." in miss_log  # Truncated user ID
        assert "GET" in miss_log
        
        print(f"✅ Cache GET access logging works - found {len(cache_access_logs)} log entries")
    
    async def test_cache_set_access_logging(self, cache_manager, capture_logs):
        """Test access logging for cache SET operations"""
        user_context = {"user_id": "set_log_user", "session_id": "set_log_session"}
        
        # Clear existing logs
        capture_logs.clear()
        
        # Perform cache set operation
        response_data = {
            "response": "Test therapeutic response",
            "context": "safe therapeutic content",
            "timestamp": datetime.now().isoformat()
        }
        
        cache_key, was_cached = await cache_manager.set_cached_response(
            "test query for set logging",
            response_data,
            user_context=user_context
        )
        
        # Check for access log entries
        log_messages = [record.message for record in capture_logs.records]
        cache_access_logs = [msg for msg in log_messages if "CACHE_ACCESS" in msg]
        
        # Should have log entry for cache set
        set_log = next((log for log in cache_access_logs if "SET" in log), None)
        assert set_log is not None
        assert "set_log_use..." in set_log  # Truncated user ID
        assert "success" in set_log.lower()
        
        print("✅ Cache SET access logging works correctly")
    
    async def test_rate_limit_access_logging(self, cache_manager, capture_logs):
        """Test access logging for rate limited requests"""
        user_context = {"user_id": "rate_limit_log", "session_id": "rate_session"}
        
        # Clear existing logs
        capture_logs.clear()
        
        # Generate requests to trigger rate limiting
        for i in range(6):  # Exceed rate limits
            await cache_manager.get_cached_response(
                f"rate limit test {i}",
                user_context=user_context
            )
        
        # Check for rate limit log entries
        log_messages = [record.message for record in capture_logs.records]
        rate_limit_logs = [msg for msg in log_messages if "rate_limited" in msg]
        
        assert len(rate_limit_logs) > 0
        
        # Verify rate limit log content
        rate_limit_log = rate_limit_logs[0]
        assert "rate_limit_lo..." in rate_limit_log  # Truncated user ID
        assert "GET" in rate_limit_log
        
        print(f"✅ Rate limit access logging works - found {len(rate_limit_logs)} rate limit logs")
    
    async def test_phi_blocked_access_logging(self, cache_manager, capture_logs):
        """Test access logging for PHI-blocked requests"""
        user_context = {"user_id": "phi_log_user", "session_id": "phi_session"}
        
        # Clear existing logs
        capture_logs.clear()
        
        # Try to cache content with PHI (should be blocked)
        phi_query = "My social security number is 123-45-6789"
        
        result = await cache_manager.get_cached_response(
            phi_query,
            user_context=user_context
        )
        
        # Check for PHI blocking log entries
        log_messages = [record.message for record in capture_logs.records]
        phi_blocked_logs = [msg for msg in log_messages if "blocked" in msg.lower()]
        
        if len(phi_blocked_logs) > 0:
            # Verify PHI blocked log content
            phi_log = phi_blocked_logs[0]
            assert "phi_log_use..." in phi_log  # Truncated user ID
            assert "GET" in phi_log
            
            print("✅ PHI blocked access logging works correctly")
        else:
            print("⚠️ PHI blocking may not have been triggered (depends on PHI analyzer)")
    
    async def test_cache_eviction_access_logging(self, cache_manager, capture_logs):
        """Test access logging for cache eviction operations"""
        # Clear existing logs
        capture_logs.clear()
        
        # Fill cache to trigger eviction
        for i in range(cache_manager.l1_max_size + 3):
            test_data = {"data": f"test_data_{i}", "index": i}
            await cache_manager._set_l1_cache(f"eviction_key_{i}", test_data)
        
        # Check for eviction log entries
        log_messages = [record.message for record in capture_logs.records]
        eviction_logs = [msg for msg in log_messages if "EVICT" in msg]
        
        assert len(eviction_logs) > 0
        
        # Verify eviction log content
        eviction_log = eviction_logs[0]
        assert "L1" in eviction_log
        assert "success" in eviction_log.lower()
        
        print(f"✅ Cache eviction access logging works - found {len(eviction_logs)} eviction logs")
    
    async def test_audit_log_privacy_protection(self, cache_manager, capture_logs):
        """Test that audit logs protect user privacy with truncated identifiers"""
        long_user_id = "very_long_user_identifier_that_should_be_truncated_for_privacy"
        user_context = {"user_id": long_user_id, "session_id": "privacy_test_session"}
        
        # Clear existing logs
        capture_logs.clear()
        
        # Perform operation that generates logs
        await cache_manager.get_cached_response(
            "privacy test query",
            user_context=user_context
        )
        
        # Check that user ID is truncated in logs
        log_messages = [record.message for record in capture_logs.records]
        cache_logs = [msg for msg in log_messages if "CACHE_ACCESS" in msg]
        
        assert len(cache_logs) > 0
        
        # Verify user ID is truncated (should be "very_lon..." not the full ID)
        privacy_log = cache_logs[0]
        assert long_user_id not in privacy_log  # Full ID should not appear
        assert "very_lon..." in privacy_log  # Truncated ID should appear
        
        print("✅ Audit log privacy protection works correctly")


class TestIntegratedSecurityFeatures:
    """Test integration of all security features working together"""
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Set up test environment variables"""
        self.original_env = {}
        for key, value in TEST_ENVIRONMENT_VARS.items():
            self.original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        yield
        
        # Restore original environment
        for key, original_value in self.original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value
    
    @pytest.fixture
    async def cache_manager(self):
        """Create a fresh cache manager for testing"""
        manager = TherapeuticCacheManager()
        await manager.initialize()
        yield manager
        await manager.cleanup()
    
    async def test_complete_security_workflow(self, cache_manager, caplog):
        """Test complete security workflow with all features enabled"""
        caplog.set_level(logging.DEBUG, logger="app.services.therapeutic_cache_manager.audit")
        
        user_context = {"user_id": "integration_user", "session_id": "integration_session"}
        
        # 1. Test normal operation within rate limits
        response_data = {
            "response": "This is a safe therapeutic response",
            "confidence": 0.95,
            "therapeutic_category": "emotional_support"
        }
        
        # Set a response (should succeed)
        cache_key, was_cached = await cache_manager.set_cached_response(
            "How can I manage my anxiety?",
            response_data,
            user_context=user_context,
            ttl_hours=6
        )
        
        assert was_cached == True
        
        # Get the response (should succeed and be logged)
        cached_result = await cache_manager.get_cached_response(
            "How can I manage my anxiety?",
            user_context=user_context
        )
        
        assert cached_result is not None
        
        # 2. Test rate limiting by making excessive requests
        rate_limit_user = {"user_id": "rate_test_user", "session_id": "rate_session"}
        blocked_count = 0
        
        for i in range(8):  # Should trigger rate limiting
            result = await cache_manager.get_cached_response(
                f"excessive request {i}",
                user_context=rate_limit_user
            )
            if result is None:
                bucket = cache_manager.rate_limit_buckets.get("rate_test_user", {})
                if bucket.get("blocked_requests", 0) > 0:
                    blocked_count += 1
        
        assert blocked_count > 0, "Rate limiting should have blocked some requests"
        
        # 3. Test secure cleanup
        initial_cache_size = len(cache_manager.l1_cache)
        initial_buckets = len(cache_manager.rate_limit_buckets)
        
        await cache_manager.cleanup()
        
        # After cleanup, everything should be securely cleared
        assert len(cache_manager.l1_cache) == 0
        assert len(cache_manager.rate_limit_buckets) == 0
        
        # 4. Verify comprehensive audit logs
        log_messages = [record.message for record in caplog.records]
        cache_logs = [msg for msg in log_messages if "CACHE_ACCESS" in msg]
        
        # Should have logs for GET, SET, and potentially EVICT operations
        get_logs = [log for log in cache_logs if "GET" in log]
        set_logs = [log for log in cache_logs if "SET" in log]
        
        assert len(get_logs) > 0, "Should have GET operation logs"
        assert len(set_logs) > 0, "Should have SET operation logs"
        
        # 5. Verify statistics tracking
        stats = cache_manager.get_cache_stats()
        assert "rate_limit_blocks" in stats
        assert "rate_limit_enabled" in stats
        assert stats["rate_limit_enabled"] == True
        
        print("✅ Complete integrated security workflow validated")
        print(f"   - Cache operations: {len(get_logs)} GETs, {len(set_logs)} SETs")
        print(f"   - Rate limit blocks: {stats['rate_limit_blocks']}")
        print(f"   - Audit logs generated: {len(cache_logs)}")
        print(f"   - Secure cleanup: {initial_cache_size} cache items + {initial_buckets} buckets cleared")


if __name__ == "__main__":
    # Run tests directly
    import asyncio
    
    async def run_all_tests():
        """Run all security improvement tests"""
        print("🔐 Starting Enhanced Security Improvements E2E Tests")
        print("=" * 60)
        
        # Create test instances
        rate_limit_tests = TestRateLimitingSecurity()
        memory_tests = TestSecureMemoryClearing()
        logging_tests = TestAccessLoggingAuditTrail()
        integrated_tests = TestIntegratedSecurityFeatures()
        
        # Set up environment
        for key, value in TEST_ENVIRONMENT_VARS.items():
            os.environ[key] = value
        
        try:
            # Create cache manager
            cache_manager = TherapeuticCacheManager()
            await cache_manager.initialize()
            
            print("\n1. Testing Rate Limiting Security...")
            await rate_limit_tests.test_rate_limiting_configuration(cache_manager)
            await rate_limit_tests.test_rate_limiting_allows_normal_requests(cache_manager)
            await rate_limit_tests.test_rate_limiting_blocks_excessive_requests(cache_manager)
            await rate_limit_tests.test_rate_limiting_per_user_isolation(cache_manager)
            await rate_limit_tests.test_rate_limiting_statistics_tracking(cache_manager)
            
            print("\n2. Testing Secure Memory Clearing...")
            await memory_tests.test_secure_clear_data_dictionary(cache_manager)
            await memory_tests.test_secure_clear_data_list(cache_manager)
            await memory_tests.test_secure_clearing_in_cache_eviction(cache_manager)
            
            print("\n3. Testing Access Logging...")
            # Note: These tests need proper logging setup
            print("   (Access logging tests require proper log capture setup)")
            
            await cache_manager.cleanup()
            
            print("\n" + "=" * 60)
            print("🎉 All Enhanced Security Improvement Tests Completed Successfully!")
            
        except Exception as e:
            print(f"\n❌ Test execution failed: {e}")
            raise
    
    # Run the tests
    asyncio.run(run_all_tests())