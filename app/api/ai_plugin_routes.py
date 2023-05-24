from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from app.services.openai import create_embedding
from app.services.pinecone_db import get_topk_with_filters
from app.services.postgres_db import get_user_content_source_ids
from app.authentication.authenticate import authenticate
import json
import yaml

router = APIRouter()


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
