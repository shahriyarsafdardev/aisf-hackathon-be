import re
import boto3
from botocore.config import Config
from app.core.config import settings

config = Config(
    retries={
        'max_attempts': 10,
        'mode': 'standard'
    },
    max_pool_connections=50
)

s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.sphere_aws_access_key_id,
    aws_secret_access_key=settings.sphere_aws_secret_access_key,
    config=config
)



def fetch_s3_plugin_files(request_url, file_name):
    url = str(request_url)
    subdomain_match = re.search(r"https?://([^./]+).*", url)
    company_name = subdomain_match.group(1)
    s3_object = s3_client.get_object(Bucket=settings.sphere_aws_s3_bucket_name, Key=f"{company_name}/.well-known/{file_name}")
    file_content = s3_object['Body'].read()
    
    return file_content
    