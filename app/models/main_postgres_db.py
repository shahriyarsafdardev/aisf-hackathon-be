from peewee import *
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from app.core.logging import getLogger
import os

load_dotenv()
logger = getLogger()

db = PostgresqlDatabase(
    os.getenv('RDS_HOSTNAME'),
    user=int(os.getenv('RDS_PORT')),
    password=os.getenv('RDS_DB_NAME'),
    host=os.getenv('RDS_USERNAME'),
    port=os.getenv('RDS_PASSWORD')
)


class BaseModel(Model):
    class Meta:
        database = db


class Users(BaseModel):
    email = CharField()
    password = CharField()  # Please consider encrypting passwords
    first_name = CharField()
    last_name = CharField()

    class Meta:
        table_name = 'users'


class ContentSources(BaseModel):
    # Define columns here

    class Meta:
        table_name = 'content_sources'


class UserContentSources(BaseModel):
    user_id = ForeignKeyField(Users, backref='users')
    content_source_id = ForeignKeyField(ContentSources, backref='content_sources')

    class Meta:
        table_name = 'user_content_sources'
