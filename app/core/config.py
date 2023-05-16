from pydantic import BaseSettings


class Settings(BaseSettings):
    sphere_aws_access_key_id: str
    sphere_aws_secret_access_key: str
    sphere_aws_s3_bucket_name: str


    class Config:
        env_file = ".env"


settings = Settings()
