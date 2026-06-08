import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

logger = logging.getLogger(__name__)

PASSWORD_VIEW_NOT_CONFIGURED = "密码查看功能未配置"
PASSWORD_VIEW_RESET_REQUIRED = "需重置后可查看"
PASSWORD_VIEW_DECRYPT_FAILED = "密码查看失败，请重新重置密码"


def get_password_view_secret() -> str | None:
    secret = get_settings().password_view_secret
    if not secret or not secret.strip():
        return None
    return secret.strip()


def get_password_view_fernet() -> Fernet | None:
    secret = get_password_view_secret()
    if secret is None:
        return None

    raw_secret = secret.encode("utf-8")
    try:
        return Fernet(raw_secret)
    except (ValueError, TypeError):
        derived_key = base64.urlsafe_b64encode(hashlib.sha256(raw_secret).digest())
        return Fernet(derived_key)


def encrypt_viewable_password(password: str) -> str | None:
    fernet = get_password_view_fernet()
    if fernet is None:
        return None
    return fernet.encrypt(password.encode("utf-8")).decode("utf-8")


def build_password_display(ciphertext: str | None) -> tuple[str, bool]:
    fernet = get_password_view_fernet()
    if fernet is None:
        return PASSWORD_VIEW_NOT_CONFIGURED, False
    if not ciphertext:
        return PASSWORD_VIEW_RESET_REQUIRED, False
    try:
        return fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8"), True
    except (InvalidToken, UnicodeDecodeError, ValueError, TypeError):
        logger.warning("password view decrypt failed")
        return PASSWORD_VIEW_DECRYPT_FAILED, False
