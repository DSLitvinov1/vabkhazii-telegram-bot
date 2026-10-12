import base64
import hashlib

from nacl.secret import SecretBox


def _key(api_hash, bot_token):
    material = (api_hash.strip() + "|" + bot_token.strip()).encode("utf-8")
    return hashlib.blake2b(material, digest_size=SecretBox.KEY_SIZE).digest()


def encrypt_session(session, api_hash, bot_token):
    box = SecretBox(_key(api_hash, bot_token))
    encrypted = box.encrypt(session.encode("utf-8"))
    return base64.urlsafe_b64encode(bytes(encrypted)).decode("ascii")


def decrypt_session(payload, api_hash, bot_token):
    raw = base64.urlsafe_b64decode(payload.encode("ascii"))
    box = SecretBox(_key(api_hash, bot_token))
    return box.decrypt(raw).decode("utf-8")
