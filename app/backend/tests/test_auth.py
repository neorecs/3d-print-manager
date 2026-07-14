from support import *

import time

from core.security import hash_password, verify_password
from core.credentials import decrypt_credential
from core.security import _totp_at_step
from models import AuditLog
from services.auth_service import authenticate_user, confirm_mfa_setup, create_admin_user, has_admin_user, start_mfa_setup


class AuthTestCase(BackendTestCase):
    def setUp(self) -> None:
        os.environ.setdefault("CREDENTIAL_ENCRYPTION_KEY", "4pmcM6TeV2L8D4WWuQV3XGjxM2aJ3qS4Ph3CEmE-hzA=")
        super().setUp()

    def test_password_hash_verifies_only_original_password(self) -> None:
        password_hash = hash_password("sterk-wachtwoord-123")

        self.assertTrue(verify_password("sterk-wachtwoord-123", password_hash))
        self.assertFalse(verify_password("ander-wachtwoord", password_hash))

    def test_admin_user_can_authenticate_and_writes_audit_log(self) -> None:
        user = create_admin_user(self.db, "Admin@Example.com", "sterk-wachtwoord-123", "Admin")

        self.assertTrue(has_admin_user(self.db))
        self.assertEqual(user.email, "admin@example.com")

        authenticated = authenticate_user(self.db, "admin@example.com", "sterk-wachtwoord-123")

        self.assertEqual(authenticated.id, user.id)
        self.assertIsNotNone(authenticated.last_login_at)
        audit_actions = [log.action for log in self.db.scalars(select(AuditLog).order_by(AuditLog.id)).all()]
        self.assertEqual(audit_actions, ["auth.admin_created", "auth.login_success"])

    def test_mfa_setup_stores_secret_encrypted_and_confirm_enables_mfa(self) -> None:
        user = create_admin_user(self.db, "admin@example.com", "sterk-wachtwoord-123", "Admin")

        setup = start_mfa_setup(self.db, "admin@example.com", "sterk-wachtwoord-123")

        self.db.refresh(user)
        self.assertFalse(user.mfa_enabled)
        self.assertNotEqual(user.totp_secret_encrypted, setup["secret"])
        self.assertEqual(decrypt_credential(user.totp_secret_encrypted), setup["secret"])
        self.assertTrue(setup["otpauth_url"].startswith("otpauth://totp/"))

        confirm_mfa_setup(self.db, "admin@example.com", "sterk-wachtwoord-123", _totp_at_step(setup["secret"], int(time.time() // 30)))

        self.db.refresh(user)
        self.assertTrue(user.mfa_enabled)
        audit_actions = [log.action for log in self.db.scalars(select(AuditLog).order_by(AuditLog.id)).all()]
        self.assertIn("auth.mfa_setup_started", audit_actions)
        self.assertIn("auth.mfa_enabled", audit_actions)
