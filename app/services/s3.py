from logging import getLogger
import os
import boto3
from dotenv import load_dotenv
from botocore.config import Config
from app.core.logging import getLogger

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


def upload_to_s3(file, key):
    try:
        s3_client.upload_fileobj(file, bucket_name, key)
        logger.info(
            f"Uploaded file to s3 bucket {bucket_name} with key: {key}")
        return True
    except Exception as e:
        logger.error(f"Something went wrong while saving to S3: {e}")


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
