from support import *

from cryptography.fernet import Fernet

from models import BambuPrinter, PlatformCredential, User
from tools.reencrypt_credentials import ENCRYPTED_PREFIX, RotationError, rotate_all, rotate_value


def encrypt(fernet: Fernet, value: str) -> str:
    return ENCRYPTED_PREFIX + fernet.encrypt(value.encode()).decode()


class ReencryptCredentialsTests(BackendTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.old = Fernet(Fernet.generate_key())
        self.new = Fernet(Fernet.generate_key())

    def decrypt_new(self, value: str) -> str:
        return self.new.decrypt(value.removeprefix(ENCRYPTED_PREFIX).encode()).decode()

    def test_value_encrypted_with_old_key_is_reencrypted(self) -> None:
        updated, outcome = rotate_value(encrypt(self.old, "geheim"), self.old, self.new)
        self.assertEqual(outcome, "reencrypted")
        self.assertEqual(self.decrypt_new(updated), "geheim")

    def test_value_already_on_new_key_is_untouched(self) -> None:
        value = encrypt(self.new, "geheim")
        updated, outcome = rotate_value(value, self.old, self.new)
        self.assertEqual(outcome, "already_new")
        self.assertEqual(updated, value)

    def test_plaintext_value_gets_encrypted(self) -> None:
        updated, outcome = rotate_value("platte-tekst", self.old, self.new)
        self.assertEqual(outcome, "encrypted_plaintext")
        self.assertEqual(self.decrypt_new(updated), "platte-tekst")

    def test_unknown_key_raises(self) -> None:
        stranger = Fernet(Fernet.generate_key())
        with self.assertRaises(RotationError):
            rotate_value(encrypt(stranger, "geheim"), self.old, self.new)

    def test_rotate_all_covers_credentials_mfa_and_printers_and_is_repeatable(self) -> None:
        platform = self.make_platform()
        credential = PlatformCredential(platform_id=platform.id, key_name="access_token", encrypted_value=encrypt(self.old, "token-1"))
        user = User(email="admin@example.com", password_hash="x", role="admin", is_active=True, totp_secret_encrypted=encrypt(self.old, "TOTPSECRET"))
        printer = BambuPrinter(name="P1S", host="192.168.1.20", serial_number="SN1", access_code_encrypted=encrypt(self.old, "12345678"))
        self.db.add_all([credential, user, printer])
        self.db.commit()

        first = rotate_all(self.db, self.old, self.new)
        self.db.commit()
        second = rotate_all(self.db, self.old, self.new)

        self.assertEqual(first.reencrypted, 3)
        self.assertEqual(first.failed, [])
        self.assertEqual(second.reencrypted, 0)
        self.assertEqual(second.already_new, 3)
        self.assertEqual(self.decrypt_new(credential.encrypted_value), "token-1")
        self.assertEqual(self.decrypt_new(user.totp_secret_encrypted), "TOTPSECRET")
        self.assertEqual(self.decrypt_new(printer.access_code_encrypted), "12345678")
