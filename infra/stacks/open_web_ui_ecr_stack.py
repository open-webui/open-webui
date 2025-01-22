
from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_ecr_assets as ecr_assets,
    aws_ecs as ecs,
)
import datetime
from constructs import Construct
from aws_cdk import aws_ecr
import cdk_ecr_deployment as ecrdeploy
import os

from utils import Config


class OpenWebUIECRStack(Stack):
    config: Config

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: Config,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.repository = None
        self.job_image = None
        self.config = config

        self.create_ecr_repository()
        self.create_ecs_image()

    def create_ecr_repository(self):
        repo_name = f"{self.stack_name}".lower()

        self.repository = aws_ecr.Repository(
            self,
            repo_name,
            repository_name=repo_name,
            removal_policy=RemovalPolicy.DESTROY,
            empty_on_delete=True,
        )

    def create_ecs_image(self):
        image_asset_name = f"{self.stack_name}-image"

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

        image_asset = ecr_assets.DockerImageAsset(
            self,
            image_asset_name,
            directory=os.path.join(os.path.dirname(__file__), "..", ".."),
            file="Dockerfile.open_web_ui",
        )
        ecrdeploy.ECRDeployment(
            self,
            id="DeployDockerImage",
            src=ecrdeploy.DockerImageName(image_asset.image_uri),
            dest=ecrdeploy.DockerImageName(
                f"{self.repository.repository_uri}:latest"
            ),
        )

        self.job_image = ecs.ContainerImage.from_ecr_repository(
            self.repository, tag="latest"
        )
