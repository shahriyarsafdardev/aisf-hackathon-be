from app.services.scrapping.scrapper import process_domain
from app.services.s3 import create_bulk_file
from app.services.postgres_db import insert_connector
import yaml
import dotenv
import json
import httpx
import os
from psycopg2.errors import UniqueViolation
from fastapi.responses import JSONResponse
from fastapi import APIRouter, BackgroundTasks, Request, HTTPException
from fastapi import APIRouter, Request, HTTPException


dotenv.load_dotenv()
router = APIRouter()


def base_url(request: Request):
    return f"{request.url.scheme}://{request.url.netloc}"


@router.get('/.well-known/ai-plugin.json')
async def plugin_manifest(request: Request):
    try:
        json_file_path = 'app/templates/ai-plugin.json'
        with open(json_file_path, 'r') as json_file:
            data = json.load(json_file)
        data['api']['url'] = f"{base_url(request)}/openapi.yaml"
    except Exception as e:
        return f"Error fetching the plugin file: {e}"

    return JSONResponse(content=data)


@router.get('/openapi.yaml')
async def plugin_spec(request: Request):
    try:
        yaml_file_path = 'app/templates/openapi.yaml'
        with open(yaml_file_path, 'r') as yaml_file:
            data = yaml.safe_load(yaml_file)
        data['servers'][0]['url'] = base_url(request)
    except Exception as e:
        return f"Error fetching the plugin file: {e}"
    return JSONResponse(content=data)


@router.post('/ai-plugins/create')
async def create_ai_plugin(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    # try:
    #     start_url = data['documentation_start_url']
    #     base_url = data['documentation_base_url']
    #     insert_connector(
    #         data['name'], start_url, base_url)

    #     create_bulk_file(base_url)

    #     background_tasks.add_task(
    #         process_domain, base_url, [start_url], base_url)

    return {"status": "success"}

    # except UniqueViolation as e:
    #     raise HTTPException(
    #         status_code=400, detail="A connector with the same name or start url already exists.")


@router.get('/ai-plugins/{company_name}')
async def get_ai_plugin(request: Request, company_name: str, poll_count: int):
    if int(poll_count) > 10:
        return base_url(request)
    else:
        return None


@router.get('/opportunities')
async def get_opportunities():
    url = "https://api.lever.co/v1/opportunities"
    api_key = os.getenv('LEVER_API_KEY')
    params = {
        'limit': 25
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, auth=(api_key, ""), params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code)

    return response.json()


@router.get('/postings')
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


@router.get('/users')
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
    breakpoint()
    return response.json()


@router.get('/opportunities/{opportunity_id}/interviews')
async def get_users():
    url = "https://api.lever.co/v1/opportunities/{opportunity_id}/interviews"
    api_key = os.getenv('LEVER_API_KEY')
    params = {
        'limit': 50
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, auth=(api_key, ""), params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code)

    return response.json()
