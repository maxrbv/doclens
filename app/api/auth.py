from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import ACCESS_COOKIE, CurrentUser, SessionDep, SettingsDep
from app.core.config import Settings
from app.schemas import LoginRequest, UserRead
from app.services.auth import authenticate, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


def _cookie_params(settings: Settings) -> dict:
    return {
        "key": ACCESS_COOKIE,
        "httponly": True,
        "samesite": "lax",
        "secure": settings.app_env == "prod",
        "path": "/",
    }


@router.post("/login")
async def login(
    payload: LoginRequest,
    response: Response,
    session: SessionDep,
    settings: SettingsDep,
) -> UserRead:
    user = await authenticate(session, payload.email, payload.password.get_secret_value())
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    response.set_cookie(
        value=create_access_token(user.id, settings),
        max_age=settings.jwt_ttl_minutes * 60,
        **_cookie_params(settings),
    )
    return UserRead.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, settings: SettingsDep) -> None:
    response.delete_cookie(**_cookie_params(settings))


@router.get("/me")
async def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)
