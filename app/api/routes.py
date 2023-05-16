from fastapi import APIRouter, Request


router = APIRouter()

@router.get('/.well-known/ai-plugin.json')
async def get_ai_plugin_file(request: Request):
    return 'Hello World'


@router.get('/.well-known/openapi.yaml')
async def get_openapi_file(request: Request):
    return 'Hello World'

