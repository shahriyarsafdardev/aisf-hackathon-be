from uuid import uuid4
from app.services.openai import create_embedding
from app.services.pinecone_db import get_topk_with_filters
from app.utils import (
    get_hashed_password,
    create_access_token,
    verify_password
)
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from fastapi import APIRouter, BackgroundTasks, Request, HTTPException, Response, status, Depends
from fastapi.responses import JSONResponse
from psycopg2.errors import UniqueViolation
import os
import httpx
import json
import dotenv
import yaml
from app.services.postgres_db import add_user_content_source, get_connector_details, get_content_sources, get_content_sources_for_user, insert_connector, remove_user_content_source
from app.services.postgres_db import create_new_user, fetch_user, fetch_user_by_id, find_user, get_connector_details, insert_connector, get_user_content_source_ids
import urllib.parse
from app.authentication.authenticate import authenticate


dotenv.load_dotenv()
router = APIRouter()

# Note that we should gradually transition our routes into distinct files
# I have started this work with ai_plugin_routes.py, auth_routes.py and content_source_routes.py


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


def get_base_url(request: Request):
    port = request.url.netloc.split(":")[1]
    return {"port": port, "base_url": f"{request.url.scheme}://{request.url.netloc}"}


@router.get('/.well-known/ai-plugin.json')
async def plugin_manifest(request: Request):
    try:
        base_url = {"base_url": f"{request.url.scheme}://{request.url.netloc}"}
        json_file_path = 'app/templates/sphere_auth/ai-plugin.json'
        # base_url = get_base_url(request)
        # if base_url['port'] == '8000':
        #     json_file_path = 'app/templates/lever/ai-plugin.json'
        # if base_url['port'] == '8001':
        #     json_file_path = 'app/templates/hubspot/ai-plugin.json'
        # if base_url['port'] == '8002':
        #     json_file_path = 'app/templates/sphere/ai-plugin.json'
        with open(json_file_path, 'r') as json_file:
            data = json.load(json_file)
        data['api']['url'] = f"{base_url['base_url']}/openapi.yaml"
    except Exception as e:
        return f"Error fetching the plugin file: {e}"

    return JSONResponse(content=data)


@router.get('/openapi.yaml')
async def plugin_spec(request: Request):
    try:
        base_url = {"base_url": f"{request.url.scheme}://{request.url.netloc}"}
        yaml_file_path = 'app/templates/sphere_auth/openapi.yaml'
        # base_url = get_base_url(request)
        # if base_url['port'] == '8000':
        #     yaml_file_path = 'app/templates/lever/openapi.yaml'
        # if base_url['port'] == '8001':
        #     yaml_file_path = 'app/templates/hubspot/openapi.yaml'
        # if base_url['port'] == '8002':
        #     yaml_file_path = 'app/templates/sphere/openapi.yaml'
        with open(yaml_file_path, 'r') as yaml_file:
            data = yaml.safe_load(yaml_file)
        data['servers'][0]['url'] = base_url['base_url']
    except Exception as e:
        return f"Error fetching the plugin file: {e}"
    return JSONResponse(content=data)


@router.get('/query')
async def sphere_query(query: str, payload: dict = Depends(authenticate)):
    user_id = payload
    content_source_ids = get_user_content_source_ids(user_id)

    if not content_source_ids:
        return {"answer": "No content"}

    filters = {
        'content_source_id': {'$in': content_source_ids}
    }

    embedded_query = create_embedding(query)
    answer = get_topk_with_filters(embedded_query, filters)

    return {"answer": answer}


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


@router.get('/content_sources')
async def content_sources(payload: dict = Depends(authenticate)):
    return get_content_sources()


@router.get('/user_content_sources')
async def user_content_sources(user_id: str, payload: dict = Depends(authenticate)):
    return get_content_sources_for_user(user_id)


@router.post('/subscribe_content_source')
async def subscribe_content_source(request: Request, payload: dict = Depends(authenticate)):
    data = await request.json()
    response = add_user_content_source(
        data['user_id'], data['content_source_id'])
    if response:
        return JSONResponse(
            status_code=200,
            content={'status': "success",
                     "message": "Subscribed to content successfully!"}
        )
    else:
        raise HTTPException(
            status_code=400,
            detail={"status": "failure", "error": "Something went wrong!"}
        )


@router.delete('/unsubscribe_content_source')
async def unsubscribe_content_source(request: Request, payload: dict = Depends(authenticate)):
    data = await request.json()
    response = remove_user_content_source(
        data['user_id'], data['content_source_id'])
    if response:
        return JSONResponse(
            status_code=200,
            content={'status': "success",
                     "message": "Unsubscribed from content successfully!"}
        )
    else:
        raise HTTPException(
            status_code=400,
            detail={"status": "failure", "error": "Something went wrong!"}
        )


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
