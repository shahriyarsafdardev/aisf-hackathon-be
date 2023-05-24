import os
import urllib.parse
import dotenv
from fastapi import APIRouter, Request, HTTPException, status, Depends
import httpx
from app.utils import (
    get_hashed_password,
    create_access_token,
    verify_password
)
from app.services.postgres_db import create_new_user, fetch_user, fetch_user_by_id, find_user
from fastapi.responses import RedirectResponse

dotenv.load_dotenv()
router = APIRouter()


@router.post('/login')
async def login(request: Request):
    data = await request.json()
    user = fetch_user(data['email'])
    if len(user) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )
    hashed_pass = user[0][2]
    if not verify_password(data['password'], hashed_pass):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )
    return {
        "access_token": create_access_token(user[0][0])
    }


@router.post('/signup')
async def create_user(request: Request):
    data = await request.json()
    users_count = find_user(data['email'])
    if users_count == 0:
        create_new_user(data['email'], get_hashed_password(
            data['password']), data['firstname'], data['lastname'])
    else:
        return {"message": "User already exists"}

    return {"message": "Success"}


@router.get("/oauth/authorize")
async def oauth(request: Request):
    query_string = str(request.query_params)
    parts = query_string.split('&')
    kvps = {}
    for part in parts:
        k, v = part.split('=')
        v = v.replace("%2F", "/").replace("%3A", ":")
        kvps[k] = v
    print("OAuth key value pairs from the ChatGPT Request: ", kvps)
    url = kvps["redirect_uri"]
    print("URL: ", url)
    login_url = f"{os.getenv('FRONTEND_URL')}/login"
    encoded_url = urllib.parse.quote_plus(url)
    redirect_url = f"{login_url}?url={encoded_url}"

    return RedirectResponse(url=redirect_url)


@router.post("/oauth/token")
async def oauth_exchange(request: Request):
    data = await request.json()
    user = fetch_user_by_id(data['code'])
    if len(user) is None:
        return {"Incorret email or password!"}

    return {
        "access_token": create_access_token(user[0][0]),
        "token_type": "bearer"
    }


@router.post('/verify_user')
async def login(request: Request):
    data = await request.json()
    user = fetch_user(data['email'])
    if len(user) == 0:
        return {"user_id": None}

    hashed_pass = user[0][2]
    if not verify_password(data['password'], hashed_pass):
        return {"user_id": None}

    return {"user_id": user[0][0]}


@router.post('/gpt_google_login')
async def gpt_google_login(request: Request):
    data = await request.json()
    try:
        user_id = verify_google_user(data.get('id_token'))

        return {"user_id": user_id}

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=400, detail='Invalid Google sign-in token')

    except Exception as e:
        raise HTTPException(status_code=500, detail='Internal server error')


@router.post('/google_login')
async def google_login(request: Request):
    data = await request.json()
    try:
        user_id = verify_google_user(data.get('id_token'))

        return {
            "access_token": create_access_token(user_id)
        }

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=400, detail='Invalid Google sign-in token')

    except Exception as e:
        raise HTTPException(status_code=500, detail='Internal server error')


def verify_google_user(google_token: str):
    response = httpx.get(
        f'https://oauth2.googleapis.com/tokeninfo?id_token={google_token}')
    response.raise_for_status()
    token_info = response.json()

    email = token_info.get('email')
    user_count = find_user(email)
    if user_count == 0:
        firstname = token_info.get('given_name')
        lastname = token_info.get('family_name')

        create_new_user(email, get_hashed_password(
            os.getenv('DEFAULT_PASSWORD')), firstname, lastname)

    user = fetch_user(email)
    return user[0][0]
