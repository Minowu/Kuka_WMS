from datetime import datetime, timedelta
from typing import Optional

from jose import ExpiredSignatureError, JWTError, jwt
from jose.exceptions import JWTClaimsError
from passlib.context import CryptContext

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("wms.auth")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    to_encode["type"] = "access"
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    if not token or not isinstance(token, str):
        return None
    clean = token.strip()
    if clean.lower().startswith("bearer "):
        clean = clean[7:].strip()
    try:
        payload = jwt.decode(clean, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "access":
            logger.warning("Access token rejected: incorrect token type '%s' (expected 'access')", payload.get("type"))
            return None
        return payload
    except ExpiredSignatureError as e:
        logger.debug("Access token decode failed: token expired (%s)", e)
        return None
    except JWTClaimsError as e:
        logger.warning("Access token decode failed: invalid claims (%s)", e)
        return None
    except JWTError as e:
        logger.warning("Access token decode failed: invalid signature or malformed token (%s)", e)
        return None


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    to_encode["type"] = "refresh"

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.refresh_token_expire_minutes)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_refresh_token(token: str) -> Optional[dict]:
    if not token or not isinstance(token, str):
        return None
    clean = token.strip()
    if clean.lower().startswith("bearer "):
        clean = clean[7:].strip()
    try:
        payload = jwt.decode(clean, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "refresh":
            logger.warning("Refresh token rejected: incorrect token type '%s' (expected 'refresh')", payload.get("type"))
            return None
        return payload
    except ExpiredSignatureError as e:
        logger.debug("Refresh token decode failed: token expired (%s)", e)
        return None
    except JWTClaimsError as e:
        logger.warning("Refresh token decode failed: invalid claims (%s)", e)
        return None
    except JWTError as e:
        logger.warning("Refresh token decode failed: invalid signature or malformed token (%s)", e)
        return None
