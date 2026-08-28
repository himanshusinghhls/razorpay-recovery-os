import datetime
import jwt
from typing import Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from apps.api.app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

class TokenRequest(BaseModel):
    api_key: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(req: TokenRequest) -> Any:
    if req.api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Incorrect API Key")
    
    expires_delta = datetime.timedelta(minutes=15)
    expire = datetime.datetime.now(datetime.timezone.utc) + expires_delta
    to_encode = {"sub": "frontend_client", "exp": expire}
    
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    
    return {"access_token": encoded_jwt, "token_type": "bearer"}
