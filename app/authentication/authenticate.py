from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import os
import dotenv


dotenv.load_dotenv()
ALGORITH = "HS256"


async def authenticate(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, os.getenv(
            'JWT_SECRET_KEY'), algorithms=[ALGORITH])
        # You can add additional checks or processing of the payload here if needed
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    return payload
