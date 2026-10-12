import unittest

from tg_session_cache import decrypt_session, encrypt_session


class TelegramSessionCacheTests(unittest.TestCase):
    def test_round_trip(self):
        session = "1" + "A" * 352
        api_hash = "example-api-hash"
        bot_token = "123456:example-bot-token"

        encrypted = encrypt_session(session, api_hash, bot_token)

        self.assertNotIn(session, encrypted)
        self.assertEqual(
            decrypt_session(encrypted, api_hash, bot_token),
            session,
        )

    def test_wrong_key_is_rejected(self):
        session = "1" + "B" * 352
        encrypted = encrypt_session(
            session,
            "hash-one",
            "token-one",
        )

        with self.assertRaises(Exception):
            decrypt_session(
                encrypted,
                "hash-two",
                "token-one",
            )


if __name__ == "__main__":
    unittest.main()
