import os
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import HTTPException
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
