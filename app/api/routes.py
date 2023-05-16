from fastapi import APIRouter, Request, HTTPException, Path, Query
from fastapi.responses import JSONResponse
import os
import httpx
import json
import dotenv
import yaml
from app.services.s3 import fetch_s3_plugin_files

dotenv.load_dotenv()
router = APIRouter()

@router.get('/.well-known/ai-plugin.json')
async def plugin_manifest(request: Request):
    try:
        file_content = fetch_s3_plugin_files(request.url, 'ai-plugin.json')
        data = json.loads(file_content)
    except Exception as e:
        return f"Error fetching the plugin file: {e}"

    return JSONResponse(content=data)

@router.get('/.well-known/openapi.yaml')
async def plugin_spec(request: Request):
    try:
        file_content = fetch_s3_plugin_files(request.url, 'openapi.yaml')
        data = yaml.safe_load(file_content)
    except Exception as e:
        return f"Error fetching the plugin file: {e}"

    return JSONResponse(content=data)

@router.get('/opportunities')
async def get_opportunities():
    url = "https://api.lever.co/v1/opportunities"

    api_key = os.getenv('LEVER_API_KEY')

    async with httpx.AsyncClient() as client:
        response = await client.get(url, auth=(api_key, ""))

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code)

    return response.json()

@router.post('/ai-plugins/create')
async def create_ai_plugin(request: Request):
    return {"status": "success"}

@router.get('/ai-plugins/{company_name}')
async def get_ai_plugin(company_name: str, poll_count: int):
    if int(poll_count) > 10:
        return f"{company_name}.base_url"
    else:
        return None
