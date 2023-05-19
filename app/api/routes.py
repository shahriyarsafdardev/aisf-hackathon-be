from app.services.plugin import plugin_handler
from app.services.hubspot_service import set_hubspot_headers
from app.services.scrapping.documentation_parser import query_pinecone
from app.services.scrapping.scrapper import process_domain
from app.services.s3 import create_bulk_file
from app.services.postgres_db import create_new_user, fetch_user, find_user, get_connector_details, insert_connector
import yaml
import dotenv
import json
import httpx
import os
from psycopg2.errors import UniqueViolation
from fastapi.responses import JSONResponse
from fastapi import APIRouter, BackgroundTasks, Request, HTTPException, status, Depends
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from app.utils import (
    get_hashed_password,
    create_access_token,
    create_refresh_token,
    verify_password
)
from uuid import uuid4


dotenv.load_dotenv()
router = APIRouter()


@router.post('/login')
async def login(request: Request):
    data = await request.json()
    user = fetch_user(data['email'])
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )
    hashed_pass = user[0][1]
    if not verify_password(data['password'], hashed_pass):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )

    return {
        "access_token": create_access_token(data['email']),
        "refresh_token": create_refresh_token(data['email']),
    }


@router.post('/signup')
async def create_user(request: Request):
    data = await request.json()
    users_count = find_user(data['email'])
    if users_count == 0:
        create_new_user(data['email'], get_hashed_password(
            data['password']), str(uuid4()))
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
        json_file_path = 'app/templates/sphere/ai-plugin.json'
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
        yaml_file_path = 'app/templates/sphere/openapi.yaml'
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
