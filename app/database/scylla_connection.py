import os
import sys
import logging
from typing import Optional, List
import time

if sys.version_info >= (3, 12):
    os.environ["CASS_DRIVER_NO_EXTENSIONS"] = "1"
    os.environ["CASS_DRIVER_NO_CYTHON"] = "1"
    os.environ["CASS_DRIVER_NO_MURMUR3"] = "1"
    os.environ["CASS_DRIVER_EVENT_LOOP_IMPL"] = "asyncio"

logger = logging.getLogger(__name__)

logging.getLogger("cassandra.cluster").setLevel(logging.ERROR)
logging.getLogger("cassandra.pool").setLevel(logging.ERROR)


def _try_import_driver():
    """Try to import the ScyllaDB driver with compatibility settings."""
    try:
        from cassandra.cluster import Cluster, Session
        from cassandra.auth import PlainTextAuthProvider
        from cassandra.policies import DCAwareRoundRobinPolicy

        return True, (Cluster, Session, PlainTextAuthProvider, DCAwareRoundRobinPolicy)
    except Exception as e:
        logger.error("Failed to load ScyllaDB driver: %s", str(e))
        raise ImportError(f"Could not load ScyllaDB driver: {e}")


try:
    (
        _import_success,
        (Cluster, Session, PlainTextAuthProvider, DCAwareRoundRobinPolicy),
    ) = _try_import_driver()
except ImportError as e:
    logger.error("ScyllaDB driver import failed: %s", str(e))
    raise


class ScyllaDBConnection:
    """ScyllaDB connection management with process isolation"""

    _instance: Optional["ScyllaDBConnection"] = None
    _cluster: Optional[Cluster] = None
    _session: Optional[Session] = None
    _keyspace: Optional[str] = None
    _process_id: Optional[int] = None

    def __new__(cls) -> "ScyllaDBConnection":
        """Singleton with process isolation"""
        current_pid = os.getpid()

        if cls._process_id and cls._process_id != current_pid:
            logger.info(
                f"Process change detected ({cls._process_id} -> {current_pid}), resetting singleton"
            )
            cls._force_reset()

        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._process_id = current_pid

        return cls._instance

    @classmethod
    def reset_singleton(cls):
        """Reset singleton with cleanup"""
        try:
            if cls._instance is not None:
                try:
                    if cls._cluster is not None:
                        cls._cluster.shutdown()
                        logger.debug("Cluster shutdown completed")
                except Exception as e:
                    logger.debug(f"Cluster shutdown warning: {e}")

            cls._instance = None
            cls._cluster = None
            cls._session = None
            cls._keyspace = None
            cls._process_id = None

            import gc

            for _ in range(3):
                gc.collect()
                time.sleep(0.1)

            logger.info("ScyllaDB singleton reset complete")

        except Exception as e:
            logger.warning(f"Reset warning: {e}")

    @classmethod
    def _force_reset(cls):
        """Force reset without logging"""
        try:
            if cls._cluster is not None:
                cls._cluster.shutdown()
        except Exception:
            pass

        cls._instance = None
        cls._cluster = None
        cls._session = None
        cls._keyspace = None
        cls._process_id = None

    def _get_scylla_hosts(self) -> List[str]:
        """Get ScyllaDB hosts"""
        docker_host = os.getenv("SCYLLA_HOST")
        if docker_host:
            logger.info(f"Using Docker ScyllaDB host: {docker_host}")
            return [docker_host]

        custom_host = os.getenv("SCYLLADB_HOST")
        if custom_host:
            logger.info(f"Using custom ScyllaDB host: {custom_host}")
            return [custom_host]

        return ["127.0.0.1"]

    def _get_scylla_port(self) -> int:
        """Get ScyllaDB port"""
        return int(os.getenv("SCYLLA_PORT", os.getenv("SCYLLADB_PORT", "9042")))

    def connect(self, force_reconnect: bool = False) -> None:
        """Connect to ScyllaDB"""
        if force_reconnect:
            self._complete_cleanup()

        if (
            not force_reconnect
            and self._cluster is not None
            and self._session is not None
        ):
            try:
                self._session.execute("SELECT release_version FROM system.local")
                logger.debug("ScyllaDB connection already active and healthy")
                return
            except Exception as e:
                logger.warning(f"Existing connection is stale: {e}")
                self._complete_cleanup()

        try:
            hosts = self._get_scylla_hosts()
            port = self._get_scylla_port()

            logger.info(f"Connecting to ScyllaDB: {hosts}:{port}")

            load_balancing_policy = DCAwareRoundRobinPolicy(local_dc="datacenter1")

            cluster_kwargs = {
                "contact_points": hosts,
                "port": port,
                "load_balancing_policy": load_balancing_policy,
                "protocol_version": 4,
                "control_connection_timeout": 30,
                "connect_timeout": 30,
            }

            request_timeout = 60
            if not (sys.version_info >= (3, 12)):
                cluster_kwargs["compression"] = True

            username = os.getenv("SCYLLA_USERNAME") or os.getenv("SCYLLADB_USERNAME")
            password = os.getenv("SCYLLA_PASSWORD") or os.getenv("SCYLLADB_PASSWORD")

            if username and password:
                cluster_kwargs["auth_provider"] = PlainTextAuthProvider(
                    username=username, password=password
                )
                logger.info("Using ScyllaDB authentication")

            self._cluster = Cluster(**cluster_kwargs)
            self._session = self._cluster.connect()
            self._session.default_timeout = request_timeout

            result = self._session.execute("SELECT release_version FROM system.local")
            version = result.one()

            if version:
                logger.info(
                    f"ScyllaDB connected successfully: {version.release_version}"
                )
            else:
                raise ConnectionError("Connection test failed")

        except Exception as e:
            error_msg = f"Failed to connect to ScyllaDB: {type(e).__name__}: {str(e)}"
            logger.error(error_msg)

            if "NoHostAvailable" in str(e) or "timeout" in str(e).lower():
                logger.error(f"Hosts attempted: {hosts}:{port}")

            self._complete_cleanup()
            raise ConnectionError(
                f"Cannot connect to ScyllaDB cluster: {str(e)}"
            ) from e

    def _complete_cleanup(self):
        """Cleanup connections"""
        try:
            if self._cluster is not None:
                try:
                    self._cluster.shutdown()
                    logger.debug("Cluster shutdown completed")
                except Exception as e:
                    logger.debug(f"Cluster shutdown warning: {e}")

            self._cluster = None
            self._session = None
            self._keyspace = None

            import gc

            gc.collect()
            time.sleep(0.1)

        except Exception as e:
            logger.debug(f"Cleanup warning: {e}")

    def ensure_keyspace(self, keyspace: str) -> None:
        """Ensure keyspace exists with appropriate replication"""
        if not self.is_connected():
            raise RuntimeError("Not connected to ScyllaDB. Call connect() first.")

        try:
            if self._keyspace != keyspace:
                logger.info(f"Creating/ensuring keyspace: {keyspace}")

                old_timeout = self._session.default_timeout
                self._session.default_timeout = 120

                try:
                    # Since we have 3 nodes, use replication factor of 3
                    create_keyspace_query = f"""
                    CREATE KEYSPACE IF NOT EXISTS {keyspace}
                    WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 3}}
                    """
                    self._session.execute(create_keyspace_query)
                    self._session.set_keyspace(keyspace)
                    self._keyspace = keyspace

                    logger.info(f"Keyspace '{keyspace}' ready with RF=3")

                finally:
                    self._session.default_timeout = old_timeout

        except Exception as e:
            logger.error("Failed to ensure keyspace '%s': %s", keyspace, str(e))
            raise

    def get_session(self) -> Session:
        """Get session with health check"""
        if self._session is None:
            raise RuntimeError("Not connected to ScyllaDB. Call connect() first.")

        try:
            self._session.execute("SELECT release_version FROM system.local")
        except Exception as e:
            logger.warning(f"Session health check failed: {e}")
            raise RuntimeError(
                "ScyllaDB session is not healthy. Reconnection may be needed."
            )

        return self._session

    def disconnect(self) -> None:
        """Disconnect from ScyllaDB"""
        try:
            self._complete_cleanup()
            logger.info("ScyllaDB disconnected")
        except Exception as e:
            logger.error("Error during disconnect: %s", str(e))

    def is_connected(self) -> bool:
        """Check connection status"""
        if self._session is None or self._cluster is None:
            return False

        try:
            self._session.execute("SELECT release_version FROM system.local")
            return True
        except Exception:
            return False

    def get_connection_info(self) -> dict:
        """Get current connection information"""
        return {
            "connected": self.is_connected(),
            "hosts": self._get_scylla_hosts(),
            "port": self._get_scylla_port(),
            "keyspace": self._keyspace,
            "process_id": os.getpid(),
            "instance_id": id(self),
        }


scylla_manager: Optional[ScyllaDBConnection] = None


def get_scylla_manager() -> "ScyllaDBConnection":
    global scylla_manager
    if scylla_manager is None:
        scylla_manager = ScyllaDBConnection()
    return scylla_manager


__all__ = ["ScyllaDBConnection", "scylla_manager"]
