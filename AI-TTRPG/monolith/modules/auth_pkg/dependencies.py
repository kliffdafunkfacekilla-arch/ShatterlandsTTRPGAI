from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Dict, Any
from .utils import verify_token

# This scheme looks for the token in the Authorization header: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    FastAPI dependency that validates the Bearer token and returns the user payload.
    """
    return verify_token(token)
