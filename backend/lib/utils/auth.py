import secrets
from typing import Optional
from fastapi import HTTPException, Cookie, Response, status
from pydantic import BaseModel

from lib.repositories.utils import get_redis_client
from lib.repositories.keys import CacheKeys
from lib.config.getters import get_web_credentials


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    status: str
    session: str


async def create_session(username: str) -> str:
    session_token = secrets.token_hex(32)
    redis = get_redis_client()
    
    await redis.set(
        CacheKeys.session(session_token),
        username,
        ex=86400
    )
    
    return session_token


async def verify_session(session: Optional[str]) -> bool:
    if not session:
        return False
    
    redis = get_redis_client()
    username = await redis.get(CacheKeys.session(session))
    
    if not username:
        return False
    
    creds = get_web_credentials()
    return username.decode() == creds.username


async def delete_session(session: str) -> None:
    redis = get_redis_client()
    await redis.delete(CacheKeys.session(session))


async def check_admin_auth(session: Optional[str] = Cookie(None)) -> None:
    is_valid = await verify_session(session)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please login first."
        )


async def login(credentials: LoginRequest, response: Response) -> LoginResponse:
    creds = get_web_credentials()
    
    if credentials.username != creds.username or credentials.password != creds.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    session_token = await create_session(credentials.username)
    
    response.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        samesite="lax",
        max_age=86400
    )
    
    return LoginResponse(status="ok", session=session_token)


async def logout(response: Response, session: Optional[str] = Cookie(None)) -> dict:
    if session:
        await delete_session(session)
    
    response.delete_cookie(key="session")
    
    return {"status": "ok", "message": "Logged out successfully"}


async def check_auth_status(session: Optional[str] = Cookie(None)) -> dict:
    is_valid = await verify_session(session)
    return {
        "authenticated": is_valid,
        "status": "ok" if is_valid else "unauthorized"
    }