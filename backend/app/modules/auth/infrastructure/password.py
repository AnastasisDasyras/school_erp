from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class PasslibPasswordHasher:
    """Adapter implementing the PasswordHasher port using argon2 (via passlib)."""

    def hash(self, plain_password: str) -> str:
        return _pwd_context.hash(plain_password)

    def verify(self, plain_password: str, password_hash: str) -> bool:
        return _pwd_context.verify(plain_password, password_hash)
