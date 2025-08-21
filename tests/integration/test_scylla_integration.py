"""Fixed ScyllaDB integration tests - handles when ScyllaDB is not available"""
import pytest
import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from app.dependencies import get_scylla_manager  # FIXED: Use getter


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def scylla_session():
    """Get ScyllaDB session for testing - handles unavailable ScyllaDB"""
    # FIXED: Use getter function
    scylla_manager = get_scylla_manager()

    # Check if ScyllaDB is actually available (not a mock)
    if scylla_manager is None or not hasattr(scylla_manager, 'connect'):
        pytest.skip("ScyllaDB not available in test environment")

    # Check if it's a mock
    if hasattr(scylla_manager, '__class__') and 'Mock' in scylla_manager.__class__.__name__:
        pytest.skip("ScyllaDB is mocked in test environment")

    if not scylla_manager.is_connected():
        try:
            scylla_manager.connect()
        except Exception as e:
            pytest.skip(f"Could not connect to ScyllaDB: {e}")

    # Create test keyspace
    try:
        scylla_manager.ensure_keyspace("test_ks")
    except Exception as e:
        pytest.skip(f"Could not create test keyspace: {e}")

    yield scylla_manager.get_session()


@pytest.mark.integration
class TestScyllaDBIntegration:
    """Test ScyllaDB integration - skips if ScyllaDB not available"""

    def test_connection(self):
        """Test ScyllaDB connection"""
        # FIXED: Use getter and check if available
        scylla_manager = get_scylla_manager()

        if scylla_manager is None:
            pytest.skip("ScyllaDB manager not available")

        # Check if it's a mock
        if hasattr(scylla_manager, '__class__') and 'Mock' in scylla_manager.__class__.__name__:
            pytest.skip("ScyllaDB is mocked in test environment")

        if not hasattr(scylla_manager, 'is_connected'):
            pytest.skip("ScyllaDB manager doesn't have is_connected method")

        # Try to connect if not connected
        if not scylla_manager.is_connected():
            try:
                scylla_manager.connect()
            except Exception as e:
                pytest.skip(f"Could not connect to ScyllaDB: {e}")

        assert scylla_manager.is_connected()

        conn_info = scylla_manager.get_connection_info()
        assert conn_info["connected"] is True

    def test_create_table(self, scylla_session):
        """Test creating a table"""
        if scylla_session is None:
            pytest.skip("ScyllaDB session not available")

        # Create test table
        scylla_session.execute("""
            CREATE TABLE IF NOT EXISTS test_table (
                id UUID PRIMARY KEY,
                name TEXT,
                created_at TIMESTAMP
            )
        """)

        # Verify table exists by trying to query it
        try:
            result = scylla_session.execute("SELECT COUNT(*) FROM test_table")
            assert result is not None
        except Exception as e:
            pytest.fail(f"Table creation failed: {e}")

    def test_crud_operations(self, scylla_session):
        """Test CRUD operations"""
        if scylla_session is None:
            pytest.skip("ScyllaDB session not available")

        # Ensure table exists
        scylla_session.execute("""
            CREATE TABLE IF NOT EXISTS test_table (
                id UUID PRIMARY KEY,
                name TEXT,
                created_at TIMESTAMP
            )
        """)

        test_id = uuid4()
        test_name = "Test Entry"
        test_time = datetime.now(timezone.utc)

        # Insert
        scylla_session.execute("""
            INSERT INTO test_table (id, name, created_at) 
            VALUES (%s, %s, %s)
        """, (test_id, test_name, test_time))

        # Read
        result = scylla_session.execute("""
            SELECT * FROM test_table WHERE id = %s
        """, (test_id,))

        row = result.one()
        assert row is not None
        assert row.name == test_name

        # Update
        new_name = "Updated Entry"
        scylla_session.execute("""
            UPDATE test_table SET name = %s WHERE id = %s
        """, (new_name, test_id))

        result = scylla_session.execute("""
            SELECT name FROM test_table WHERE id = %s
        """, (test_id,))

        row = result.one()
        assert row.name == new_name

        # Delete
        scylla_session.execute("""
            DELETE FROM test_table WHERE id = %s
        """, (test_id,))

        result = scylla_session.execute("""
            SELECT * FROM test_table WHERE id = %s
        """, (test_id,))

        assert result.one() is None

    def test_conversation_history_table(self, scylla_session):
        """Test conversation history table (from your schema)"""
        if scylla_session is None:
            pytest.skip("ScyllaDB session not available")

        # Create conversation history table
        scylla_session.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                session_id UUID,
                timestamp TIMESTAMP,
                message_id UUID,
                user_id UUID,
                actor TEXT,
                message TEXT,
                embedding_used BOOLEAN,
                tokens_used INT,
                response_time_ms INT,
                model_used TEXT,
                confidence DOUBLE,
                feedback_score INT,
                metadata MAP<TEXT, TEXT>,
                PRIMARY KEY (session_id, timestamp, message_id)
            ) WITH CLUSTERING ORDER BY (timestamp DESC, message_id ASC)
        """)

        # Insert test conversation
        session_id = uuid4()
        message_id = uuid4()
        user_id = uuid4()

        scylla_session.execute("""
            INSERT INTO conversation_history (
                session_id, timestamp, message_id, user_id,
                actor, message, embedding_used, tokens_used
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            session_id,
            datetime.now(timezone.utc),
            message_id,
            user_id,
            "user",
            "Test message",
            True,
            100
        ))

        # Query conversation
        result = scylla_session.execute("""
            SELECT * FROM conversation_history 
            WHERE session_id = %s
        """, (session_id,))

        rows = list(result)
        assert len(rows) == 1
        assert rows[0].message == "Test message"