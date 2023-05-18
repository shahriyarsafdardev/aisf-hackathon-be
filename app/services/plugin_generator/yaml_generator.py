from app.core.logging import getLogger
import io
import re
from app.services.openai import ask_gpt
from app.services.pinecone_db import get_domain_name
from app.services.postgres_db import update_connector_low_code_export_url
from app.services.s3 import list_objects, upload_to_s3, get_s3_file_content, bucket_name
from app.services.plugin_generator.base_url_generator import get_base_url

logger = getLogger()
format = """  endpoint:
    get:
      operationId: {List_Activity_Types}
      summary: Returns a list of all activity type objects configured on the account
      responses:
        "200":
          description: OK
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/activity_types'"""


def make_slug(s):
    s = s.lower()
    s = re.sub(r'\.', '-', s)
    s = re.sub(r'[^a-z0-9 -]', '', s)
    s = re.sub(r'\s+', '-', s)
    s = s.strip()
    return s


async def create_plugin_yaml(connector_name, base_documentation_url):
    connector_domain = get_domain_name(
        base_documentation_url).replace('.', '-')
    connector_slug = make_slug(connector_name)
    folder_name = f"source-{connector_slug}"
    api_base_url = get_base_url(connector_domain, verbose=True)
    logger.info(f"base url: {api_base_url}")

    file_content = f"""openapi: 3.0.1
servers:
  url: {api_base_url}
"""

    file_keys = list_objects([f"{folder_name}/schemas/", '.json'])

    schemas = []

    for key in file_keys[:5]:
        schema = get_s3_file_content(key)

        if schema:
            schemas.extend(schema)

    query = f"""Below is a list of endpoints. Using each endpoint, make sure it's is of GET type and return an iterative data in response, complete my content below to be a working openAPI 3.0.1 yaml file for me. endpoint list: {schemas}\n my yaml content: {file_content}\n"""
    output = ask_gpt(query, 'gpt-4')

    upload_to_s3(io.BytesIO((file_content + output).encode('utf-8')),
                 f"{folder_name}/openapi.yaml")

    update_connector_low_code_export_url(
        f"https://{bucket_name}.s3.amazonaws.com/{folder_name}/openapi.yaml", base_documentation_url)

    logger.info(
        f"OpenAI yaml file link: https://{bucket_name}.s3.amazonaws.com/{folder_name}/openapi.yaml")

    return
