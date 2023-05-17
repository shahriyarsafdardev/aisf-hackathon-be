import boto3
from botocore.config import Config
import os
import dotenv


dotenv.load_dotenv()
config = Config(
    retries={
        'max_attempts': 10,
        'mode': 'standard'
    },
    max_pool_connections=50
)


s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('SPHERE_AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('SPHERE_AWS_SECRET_ACCESS_KEY'),
    config=config
)


def fetch_s3_plugin_files(company_name, file_name):
    try:
        s3_object = s3_client.get_object(Bucket=os.getenv(
            'SPHERE_AWS_S3_BUCKET_NAME'), Key=f"{company_name}/{file_name}")
        file_content = s3_object['Body'].read()

        return file_content
    except Exception as e:
        return None
