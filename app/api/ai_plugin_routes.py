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
        base_url = f"{request.url.scheme}://{request.url.netloc}"
        with open('.well-known/ai-plugin.json', 'r') as json_file:
            ai_plugin_json = json.load(json_file)
        ai_plugin_json['api']['url'] = f"{base_url}/openapi.yaml"
        ai_plugin_json['auth']['client_url'] = f"{base_url}/oauth/authorize"
        ai_plugin_json['auth']['authorization_url'] = f"{base_url}/oauth/token"
    except Exception as e:
        return f"Error fetching the plugin file: {e}"
    return JSONResponse(content=ai_plugin_json)


@router.get('/openapi.yaml')
async def plugin_spec(request: Request):
    try:
        base_url = f"{request.url.scheme}://{request.url.netloc}"
        with open('.well-known/openapi.yaml', 'r') as yaml_file:
            open_api_json = yaml.safe_load(yaml_file)
        open_api_json['servers'][0]['url'] = base_url
    except Exception as e:
        return f"Error fetching the plugin file: {e}"
    return JSONResponse(content=open_api_json)


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
