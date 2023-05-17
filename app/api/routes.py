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

# Helper Method
def get_plugin_files(request: Request, file_name: str):
    company_name = request.url.netloc.split('.')[0]
    sub_domain, domain = request.url.netloc.split('.', 1)
    file_content = fetch_s3_plugin_files(company_name, file_name)
    if file_content is None:
        company_name = 'lever'
        sub_domain = 'lever'
        file_content = fetch_s3_plugin_files(company_name, file_name)
    return {
        'file_content': file_content,
        'sub_domain': sub_domain,
        'domain': domain
    }

@router.get('/.well-known/ai-plugin.json')
async def plugin_manifest(request: Request):
    try:
        response = get_plugin_files(request, 'ai-plugin.json')
        data = json.loads(response['file_content'])
        data['api']['url'] = f"{request.url.scheme}://{response['sub_domain']}.{response['domain']}/openapi.yaml"
    except Exception as e:
        return f"Error fetching the plugin file: {e}"

    return JSONResponse(content=data)

@router.get('/openapi.yaml')
async def plugin_spec(request: Request):
    try:
        response = get_plugin_files(request, 'openapi.yaml')
        data = yaml.safe_load(response['file_content'])
        data['servers'][0]['url'] = f"{request.url.scheme}://{response['sub_domain']}.{response['domain']}"
    except Exception as e:
        return f"Error fetching the plugin file: {e}"
    return JSONResponse(content=data)

@router.get('/opportunities')
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

@router.post('/ai-plugins/create')
async def create_ai_plugin(request: Request):
    return {"status": "success"}

@router.get('/ai-plugins/{company_name}')
async def get_ai_plugin(request: Request, company_name: str, poll_count: int):
    sub_domain = f"{request.url.scheme}://{company_name}.{request.url.netloc}"
    if int(poll_count) > 1:
        return sub_domain
    else:
        return None
