import aws_cdk as cdk

from stacks.open_web_ui_ecr_stack import OpenWebUIECRStack

from utils import init_config, NamespaceService

app = cdk.App()

stage = 'dev'
config = init_config(stage=stage)

env = cdk.Environment(
    account=config.get("aws_account"),
    region=config.get("aws_region"),
)

namespace_service = NamespaceService(namespace_name=stage)

open_web_ui_ecr = OpenWebUIECRStack(
    app,
    namespace_service.namespace(f"{config.get('app_name')}-open-web-ui-ecr"),
    description="Open web ui ECR repository stack",
    config=config,
    env=env,
)
app.synth()
