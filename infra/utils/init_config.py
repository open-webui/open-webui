import os
from typing import Dict, List, TypedDict, Optional
from aws_cdk import Duration

class Config(TypedDict):
    aws_account: str
    aws_region: str
    stage: str

def init_config(stage: str, dotenv_path: str = None) -> Config:
    return {
        "app_name": "open-web-ui",
        "aws_account": os.getenv("AWS_ACCOUNT"),
        "aws_region": os.getenv("AWS_REGION"),
        "stage": stage,
    }
