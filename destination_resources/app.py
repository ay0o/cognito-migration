import os
from aws_cdk import (
    App,
    CfnOutput,
    Stack,
    aws_iam as iam,
    aws_lambda as lambda_
)


try:
    destination_user_pool_arn = os.environ['DESTINATION_USER_POOL_ARN']
    source_app_client_id = os.environ['SOURCE_APP_CLIENT_ID']
    source_region = os.environ['SOURCE_REGION']
    source_role_arn = os.environ['SOURCE_ROLE_ARN']
    source_user_pool_id = os.environ['SOURCE_USER_POOL_ID']
    user_pool_name = os.environ['USER_POOL_NAME']
except KeyError as e:
    raise SystemExit(f"[ERROR] Missing required environment variable: {e}")

app = App()
stack = Stack(app, 'CognitoMigrationDestination')

lambda_role = iam.Role(
    stack, 'CognitoMigrationLambdaRole',
    assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
    role_name=f"cognito_migration_lambda_{user_pool_name}")

lambda_role.add_managed_policy(
    iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole')
)

lambda_role.add_to_policy(iam.PolicyStatement(
    actions=['sts:AssumeRole'],
    effect=iam.Effect.ALLOW,
    resources=[source_role_arn]
))

lambda_function = lambda_.Function(
    stack, 'CognitoMigrationLambda',
    function_name=f"cognito_migration_{user_pool_name}",
    handler='lambda_function.lambda_handler',
    runtime=lambda_.Runtime.PYTHON_3_12,
    role=lambda_role,
    code=lambda_.Code.from_asset('lambda_code'),
    environment={
        'SOURCE_USER_POOL_ID': source_user_pool_id,
        'SOURCE_APP_CLIENT_ID': source_app_client_id,
        'SOURCE_REGION': source_region,
        'SOURCE_ROLE_ARN': source_role_arn})

lambda_function.add_permission(
    'AllowCognitoInvoke',
    principal=iam.ServicePrincipal('cognito-idp.amazonaws.com'),
    action='lambda:InvokeFunction',
    source_arn=destination_user_pool_arn)

CfnOutput(
    stack, "LambdaArn",
    value=lambda_function.function_arn,
    description='The Lambda ARN is required for configuring the user-migration trigger in the destination user pool'
)

app.synth()
