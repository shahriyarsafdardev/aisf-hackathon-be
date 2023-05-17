from logging import getLogger
import os
import io
import re
import boto3
from dotenv import load_dotenv
from botocore.config import Config
from app.core.logging import getLogger
from app.services.pinecone_db import get_domain_name

load_dotenv()
logger = getLogger()

config = Config(
    retries={
        'max_attempts': 10,
        'mode': 'standard'
    },
    max_pool_connections=50
)

bucket_name = os.getenv('SPHERE_AWS_S3_BUCKET_NAME')


s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('SPHERE_AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('SPHERE_AWS_SECRET_ACCESS_KEY'),
    config=config
)


def fetch_s3_plugin_files(request_url, file_name):
    url = str(request_url)
    subdomain_match = re.search(r"https?://([^./]+).*", url)
    company_name = subdomain_match.group(1)
    s3_object = s3_client.get_object(
        Bucket=bucket_name, Key=f"{company_name}/.well-known/{file_name}")
    file_content = s3_object['Body'].read()

    return file_content


def upload_to_s3(file, key):
    try:
        s3_client.upload_fileobj(file, bucket_name, key)
        logger.info(
            f"Uploaded file to s3 bucket {bucket_name} with key: {key}")
        return True
    except Exception as e:
        logger.error(f"Something went wrong while saving to S3: {e}")


def create_bulk_file(url):
    domain_name = get_domain_name(url)
    filename = domain_name + '-bulk-text.txt'
    file_obj = io.BytesIO(
        '##Bulk text for domain pages##'.encode('utf-8'))
    upload_to_s3(file_obj, filename)


def remove_and_append_unique_lines(text, centralized_s3_key):
    try:
        centralized_s3_obj = s3_client.get_object(
            Bucket=bucket_name, Key=centralized_s3_key)
        centralized_content = centralized_s3_obj['Body'].read().decode('utf-8')

        existing_lines = centralized_content.splitlines()
        new_lines = text.splitlines()

        unique_lines = [
            line for line in new_lines if line not in existing_lines]

        updated_content = centralized_content + "\n".join(unique_lines)

        file_obj = io.BytesIO(updated_content.encode('utf-8'))

        upload_to_s3(file_obj, centralized_s3_key)

        return "\n".join(unique_lines)

    except Exception as e:
        logger.error(
            f"An error occurred while finding repetition:{centralized_s3_key} {e}")
        return


def list_objects(file_name_filters=[]):
    keys = []
    kwargs = {'Bucket': bucket_name}
    while True:
        resp = s3_client.list_objects_v2(**kwargs)
        if 'Contents' in resp:
            for obj in resp['Contents']:
                if all(filter in obj['Key'] for filter in file_name_filters):
                    keys.append(obj['Key'])
        try:
            kwargs['ContinuationToken'] = resp['NextContinuationToken']
        except KeyError:
            break
    return keys


def read_object(key):
    try:
        s3_object = s3_client.get_object(Bucket=bucket_name, Key=key)
        return s3_object['Body'].read().decode('utf-8')
    except Exception as e:
        logger.error(f"Something went wrong while reading from S3: {e}")


def get_s3_file_content(key):
    try:
        s3_obj = s3_client.get_object(Bucket=bucket_name, Key=key)
        content = s3_obj['Body'].read().decode('utf-8')
        return content
    except Exception as e:
        logger.error(f"An error occurred while getting the file content: {e}")
        return None


def delete_s3_file(key):
    try:
        s3_client.delete_object(Bucket=bucket_name, Key=key)
        logger.info(
            f"Deleted file from s3 bucket {bucket_name} with key: {key}")

    except Exception as e:
        logger.error(f"An error occurred while deleting the file: {e}")


def create_folder(folder_name):
    try:
        s3_client.put_object(Bucket=bucket_name, Key=(folder_name+'/'))
        logger.info(
            f"Created folder in s3 bucket {bucket_name} with folder name: {folder_name}")
    except Exception as e:
        logger.error(f"Something went wrong while creating folder in S3: {e}")


def count_schema_files(connector_name):
    paginator = s3_client.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(
        Bucket=bucket_name, Prefix=f"source-{connector_name}/schemas/")

    file_count = 0
    for page in page_iterator:
        file_count += len([obj for obj in page.get('Contents',
                          []) if not obj['Key'].endswith('/')])

    return file_count


def delete_s3_folder(folder_key):
    try:
        objects_to_delete = s3_client.list_objects(
            Bucket=bucket_name, Prefix=folder_key)

        if 'Contents' not in objects_to_delete:
            logger.info(
                f"No objects found under the prefix {folder_key}. Nothing to delete.")
            return

        delete_keys = {'Objects': []}
        delete_keys['Objects'] = [{'Key': obj['Key']}
                                  for obj in objects_to_delete['Contents']]

        s3_client.delete_objects(Bucket=bucket_name, Delete=delete_keys)
        logger.info(
            f"Deleted folder from s3 bucket {bucket_name} with folder key: {folder_key}")

    except Exception as e:
        logger.error(f"An error occurred while deleting the folder: {e}")
