from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.services.postgres_db import fetch_user_by_id
import os
import dotenv


dotenv.load_dotenv()
ALGORITHM = "HS256"

async def authenticate(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, os.getenv('JWT_SECRET_KEY'), algorithms=[ALGORITHM])
        user = fetch_user_by_id(payload['sub'])
        if len(user) == 0:
            raise HTTPException(status_code=401, detail="User Not found")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    return payload['sub']