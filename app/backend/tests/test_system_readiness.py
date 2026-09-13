import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from support import BackendTestCase

from core.config import get_settings
from services.system_service import system_readiness_payload


class SystemReadinessTestCase(BackendTestCase):
    def test_local_readiness_does_not_require_https(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            uploads = root / "uploads"
            status = root / "status"
            uploads.mkdir()
            status.mkdir()
            now = datetime.now(timezone.utc).isoformat()
            for name in ("postgres-last-success", "uploads-last-success", "restore-test-last-success"):
                (status / name).write_text(now, encoding="utf-8")

            environment = {
                "DATABASE_URL": "sqlite+pysqlite:///:memory:",
                "BACKEND_INTERNAL_TOKEN": "test-internal-token",
                "AUTH_SECRET": "test-session-secret",
                "AUTH_ENABLED": "true",
                "AUTH_BACKEND_LOGIN": "true",
                "AUTH_COOKIE_SECURE": "false",
                "CONNECTORS_LIVE_MODE": "false",
                "CREDENTIAL_ENCRYPTION_KEY": "test-encryption-key",
                "UPLOAD_BACKUP_ENABLED": "true",
                "UPLOAD_STORAGE_PATH": str(uploads),
                "BACKUP_STATUS_DIR": str(status),
            }
            with patch.dict(os.environ, environment, clear=False):
                get_settings.cache_clear()
                result = system_readiness_payload(self.db)

            self.assertTrue(result["internal_use_ready"])
            self.assertTrue(result["ready_for_real_tokens"])
            self.assertFalse(result["external_access_ready"])
            self.assertEqual(result["internal_blockers"], [])
            self.assertEqual(result["platform_blockers"], [])
            self.assertNotIn("HTTPS", " ".join(result["blockers"]))
            self.assertIn("Internettoegang is uitgesteld", result["external_access_blockers"][0])
            self.assertIsNotNone(result["database_backup_last_success"])
            self.assertIsNotNone(result["upload_backup_last_success"])
            self.assertIsNotNone(result["restore_test_last_success"])
            get_settings.cache_clear()

    def test_token_storage_reports_encryption_separately_from_internal_use(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            uploads = root / "uploads"
            status = root / "status"
            uploads.mkdir()
            status.mkdir()
            now = datetime.now(timezone.utc).isoformat()
            for name in ("postgres-last-success", "uploads-last-success", "restore-test-last-success"):
                (status / name).write_text(now, encoding="utf-8")

            environment = {
                "DATABASE_URL": "sqlite+pysqlite:///:memory:",
                "BACKEND_INTERNAL_TOKEN": "test-internal-token",
                "AUTH_SECRET": "test-session-secret",
                "AUTH_ENABLED": "true",
                "AUTH_BACKEND_LOGIN": "true",
                "AUTH_COOKIE_SECURE": "false",
                "CONNECTORS_LIVE_MODE": "false",
                "CREDENTIAL_ENCRYPTION_KEY": "",
                "UPLOAD_BACKUP_ENABLED": "true",
                "UPLOAD_STORAGE_PATH": str(uploads),
                "BACKUP_STATUS_DIR": str(status),
            }
            with patch.dict(os.environ, environment, clear=False):
                get_settings.cache_clear()
                result = system_readiness_payload(self.db)

            self.assertTrue(result["internal_use_ready"])
            self.assertFalse(result["ready_for_real_tokens"])
            self.assertEqual(result["internal_blockers"], [])
            self.assertIn("CREDENTIAL_ENCRYPTION_KEY", " ".join(result["platform_blockers"]))
            get_settings.cache_clear()

    def test_future_backup_marker_is_not_accepted_as_recent_evidence(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            uploads = root / "uploads"
            status = root / "status"
            uploads.mkdir()
            status.mkdir()
            future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
            (status / "postgres-last-success").write_text(future, encoding="utf-8")
            environment = {
                "DATABASE_URL": "sqlite+pysqlite:///:memory:",
                "BACKEND_INTERNAL_TOKEN": "test-internal-token",
                "AUTH_SECRET": "test-session-secret",
                "AUTH_ENABLED": "true",
                "AUTH_BACKEND_LOGIN": "true",
                "UPLOAD_BACKUP_ENABLED": "true",
                "UPLOAD_STORAGE_PATH": str(uploads),
                "BACKUP_STATUS_DIR": str(status),
            }
            with patch.dict(os.environ, environment, clear=False):
                get_settings.cache_clear()
                result = system_readiness_payload(self.db)

            self.assertFalse(result["database_backup_recent"])
            self.assertIn("PostgreSQL-backup", " ".join(result["internal_blockers"]))
            get_settings.cache_clear()
