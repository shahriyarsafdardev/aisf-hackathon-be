from uuid import uuid4
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
from app.services.postgres_db import create_new_user, fetch_user, fetch_user_by_id, find_user, get_connector_details, insert_connector
import urllib.parse
from app.services.plugin import plugin_handler
from app.services.hubspot_service import set_hubspot_headers
from app.services.scrapping.documentation_parser import query_pinecone
from app.services.scrapping.scrapper import process_domain
from app.services.s3 import create_bulk_file
<< << << < Updated upstream
== == == =
>>>>>> > Stashed changes


dotenv.load_dotenv()
router = APIRouter()


@router.get('/login')
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
        "access_token": create_access_token(data['email'])
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


@router.post('/ai-plugins/create')
async def create_ai_plugin(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    try:
        start_url = data['documentation_start_url']
        base_url = data['documentation_base_url']
        insert_connector(
            data['name'], start_url, base_url)

        create_bulk_file(base_url)

        background_tasks.add_task(
            plugin_handler, data['name'], start_url, base_url)

        return {"status": "success"}

    except UniqueViolation as e:
        raise HTTPException(
            status_code=400, detail="A connector with the same name or start url already exists.")


@router.get('/ai-plugins/{company_name}')
async def get_ai_plugin(company_name: str, poll_count: int):
    res = get_connector_details(company_name)
    if res[2]:
        return res[2]
    else:
        return None


@router.get('/lever/opportunities')
async def get_opportunities():
    url = "https://api.lever.co/v1/opportunities"
    api_key = os.getenv('LEVER_API_KEY')
    params = {
        'limit': 20
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, auth=(api_key, ""), params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code)

    return response.json()


@router.get('/lever/postings')
async def get_postings():
    url = "https://api.lever.co/v1/postings"
    api_key = os.getenv('LEVER_API_KEY')
    params = {
        'limit': 25
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, auth=(api_key, ""), params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code)
    data = response.json()['data']
    for item in data:
        item['content']['description'] = item['content']['description'][0:100]
        item['content']['descriptionHtml'] = item['content']['descriptionHtml'][0:100]
    return data


@router.get('/lever/users')
async def get_users():
    url = "https://api.lever.co/v1/users"
    api_key = os.getenv('LEVER_API_KEY')
    params = {
        'limit': 50
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, auth=(api_key, ""), params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code)
    return response.json()


@router.get('/lever/opportunities/{opportunity_id}/interviews')
async def get_users():
    url = "https://api.lever.co/v1/opportunities/{opportunity_id}/interviews"
    api_key = os.getenv('LEVER_API_KEY')
    params = {
        'limit': 50
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, auth=(api_key, ""), params=params)


@router.get('/hubspot/contacts')
async def get_hubspot_contacts():
    url = "https://api.hubapi.com/crm/v3/objects/contacts"
    headers = set_hubspot_headers()

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code)

    return response.json()


@router.get('/hubspot/companies')
async def get_hubspot_companies():
    url = "https://api.hubapi.com/crm/v3/objects/companies"
    headers = set_hubspot_headers()

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code)

    return response.json()


@router.get('/query')
async def sphere_query(query: str):
    answer = query_pinecone(query)
    return {"answer": answer}


# Use while creating sphere auth plugin
OPENAI_CLIENT_ID = "abc123"
OPENAI_CLIENT_SECRET = "abc123"


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
    # if request["client_id"] != OPENAI_CLIENT_ID:
    #     raise RuntimeError("bad client ID")
    # if request["client_secret"] != OPENAI_CLIENT_SECRET:
    #     raise RuntimeError("bad client secret")

    data = await request.json()
    user = fetch_user_by_id(data['code'])
    if len(user) is None:
        return {"Incorret email or password!"}

    return {
        "access_token": create_access_token(user[0][1]),
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
async def content_sources():
    return get_content_sources()


@router.get('/user_content_sources')
async def user_content_sources(user_id: str):
    return get_content_sources_for_user(user_id)


@router.post('/subscribe_content_source')
async def subscribe_content_source(request: Request):
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
async def unsubscribe_content_source(request: Request):
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
