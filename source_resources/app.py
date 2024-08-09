import os
from aws_cdk import (
    App,
    CfnOutput,
    Stack,
    aws_cognito as cognito,
    aws_iam as iam
)


try:
    user_pool_id = os.environ['USER_POOL_ID']
    user_pool_name = os.environ['USER_POOL_NAME']
    destination_account = os.environ['DESTINATION_ACCOUNT']
except KeyError as e:
    raise SystemExit(f"[ERROR] Missing required environment variable: {e}")

app = App()
stack = Stack(app, 'CognitoMigrationSource')

user_pool = cognito.UserPool.from_user_pool_id(
    stack, 'SourceUserPool',
    user_pool_id=user_pool_id
)

app_client = user_pool.add_client(
    'migration',
    auth_flows=cognito.AuthFlow(admin_user_password=True),
    user_pool_client_name='migration')

role = iam.Role(
    stack, 'CognitoMigrationRole',
    assumed_by=iam.PrincipalWithConditions(
        iam.ArnPrincipal(f"arn:aws:iam::{destination_account}:root"),
        conditions={
            'ArnLike': {
                'aws:PrincipalArn': [
                    f"arn:aws:iam::{destination_account}:role/cognito_migration_lambda_{user_pool_name}"
                ]
            }
        }
    ),
    role_name=f"cognito_migration_{user_pool_name}")

role.add_to_policy(iam.PolicyStatement(
    actions=[
        'cognito-idp:AdminInitiateAuth',
        'cognito-idp:AdminGetUser'],
    effect=iam.Effect.ALLOW,
    resources=[user_pool.user_pool_arn]))

CfnOutput(stack, 'RoleArn',
          value=role.role_arn,
          description='ARN of the role that needs to be assumed from the destination account')

CfnOutput(stack, 'AppClientId',
          value=app_client.user_pool_client_id,
          description='App Client ID needed by the Lambda in the destination')

app.synth()
