import os
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import HTTPException
import httpx
import json
import dotenv
import yaml

dotenv.load_dotenv()
router = APIRouter()

@router.get('/.well-known/ai-plugin.json')
async def get_ai_plugin_file(request: Request):
    json_file_path = 'app/templates/ai-plugin.json'
    with open(json_file_path, 'r') as json_file:
        data = json.load(json_file)

    return JSONResponse(content=data)

@router.get('/.well-known/openapi.yaml')
async def get_openapi_file(request: Request):
    yaml_file_path = 'app/templates/openapi.yaml'
    with open(yaml_file_path, 'r') as yaml_file:
        data = yaml.safe_load(yaml_file)

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
