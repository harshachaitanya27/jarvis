"""JWT implementation of AuthProvider.

Verifies a bearer access token's signature and expiry and returns the caller's
identity. Token *issuance* lives in the auth service; this adapter only reads
tokens, so routes can depend on verification without knowing how they are made.
"""

import jwt

from app.core.interfaces.auth import AuthError, AuthProvider, Principal


class JWTAuthProvider(AuthProvider):
    def __init__(self, secret: str, algorithm: str = "HS256"):
        if not secret:
            raise RuntimeError("JWT_SECRET is not set; cannot verify access tokens")
        self._secret = secret
        self._algorithm = algorithm

    async def verify(self, token: str) -> Principal:
        try:
            claims = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except jwt.ExpiredSignatureError as exc:
            raise AuthError("token expired") from exc
        except jwt.PyJWTError as exc:
            raise AuthError("invalid token") from exc

        user_id = claims.get("sub")
        if not user_id:
            raise AuthError("token missing subject")
        return Principal(user_id=user_id, email=claims.get("email"))
