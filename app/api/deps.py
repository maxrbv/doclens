import logging
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.models import User
from app.services.auth import decode_access_token

logger = logging.getLogger(__name__)

ACCESS_COOKIE = "access_token"

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Не авторизован")


async def get_current_user(
    session: SessionDep,
    settings: SettingsDep,
    access_token: Annotated[str | None, Cookie(alias=ACCESS_COOKIE)] = None,
) -> User:
    if not access_token:
        raise _unauthorized()

    user_id = decode_access_token(access_token, settings)
    if user_id is None:
        logger.info("auth rejected", extra={"reason": "invalid_or_expired_token"})
        raise _unauthorized()

    user = await session.get(User, user_id)
    if user is None:
        logger.info("auth rejected", extra={"reason": "user_not_found"})
        raise _unauthorized()

    if not user.is_active:
        logger.info("auth rejected", extra={"reason": "user_inactive"})
        raise _unauthorized()

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
