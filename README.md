# cognito-migration
A pair of CDK-based apps to deploy some resources to implement a Cognito seamless user migration, that is, a migration in which the users can keep their current passwords.

The code is split in two apps, one aimed at destination resources and the other at source resources. Why? Because it makes the operation more flexible by not imposing a specific way of provisioning AWS credentials per environment.

## Source
#### Environment variables
* `USER_POOL_ID`: The ID of the source user pool.
* `USER_POOL_NAME`: The name of the source user pool.
* `DESTINATION_ACCOUNT`: The account number of the destination account. Can be the same as the source account if the migration is within the same account.

#### Resources created
* An app client named `migration` using the `ALLOW_ADMIN_USER_PASSWORD_AUTH` authentication flow.
* A role named `cognito_migration_{user_pool_name}` which allows a role named `cognito_migration_lambda_{user_pool_name}` in the destination account to perform the `AdminInitiateAuth` and `AdminGetUser` actions.

#### Outputs
* `RoleArn`: ARN of the role that needs to be assumed from the destination account.
* `AppClientId`: App (`migration`) Client ID needed by the Lambda in the destination.

## Destination
#### Environment variables
* `DESTINATION_USER_POOL_ARN`: The ARN of the destination user pool to limit which user pool can invoke the Lambda.
* `SOURCE_APP_CLIENT_ID`: The source's `AppClientId` output.
* `SOURCE_REGION`: The source region, because you might be migrating from a user pool in a different region.
* `SOURCE_ROLE_ARN`: The source's `RoleArn` output.
* `SOURCE_USER_POOL_ID`: The ID of the source user pool.
* `USER_POOL_NAME`: The name of the source user pool.

#### Resources created
* An IAM role named `cognito_migration_lambda_{user_pool_name}` with a policy that allows assuming the `SOURCE_ROLE_ARN`.
* A Lambda function named `cognito_migration_{user_pool_name}` using this role and allowing Cognito to invoke it.

#### Outputs
* `LambdaArn`: The Lambda ARN is required for configuring the user-migration trigger in the destination user pool.

## Configuring the destination user pool
Once you have deployed both CDK apps, you still need to configure your destination user pool. This is out of the scope of this repo, but bear in mind there are two mandatory things:
* You need to configure the user migration trigger.
* Your app must use the `ALLOW_USER_PASSWORD_AUTH` while the migration is in process.

#### Sample CDK code with the bare minimum
```
import os
from aws_cdk import (
    App,
    Stack,
    aws_cognito as cognito,
    aws_lambda as lambda_
)

app = App()
stack = Stack(app, 'CognitoUserPool')

try:
    migration_lambda_arn = os.environ['MIGRATION_LAMBDA_ARN']
except KeyError:
    raise SystemExit('[ERROR] Missing MIGRATION_LAMBDA_ARN variable')

migration_lambda = lambda_.Function.from_function_arn(
    stack, 'MigrationLambda',
    migration_lambda_arn)

user_pool = cognito.UserPool(
    stack, 'UserPool',
    lambda_triggers=cognito.UserPoolTriggers(
        user_migration=migration_lambda
    ),
    user_pool_name='new_user_pool')

user_pool.add_client(
    'app-client',
    # This auth flow should be removed when the migration is over
    auth_flows=cognito.AuthFlow(user_password=True),
    user_pool_client_name='app-client')

app.synth()
```
## How does the migration work?
The migration in which the users keep their current passwords involves checking whether the user exists in the new user pool, and if they do not, validate their credentials with the old user pool and create a new entity in the new user pool.

To be able to do this, we have to slightly decrease the security posture by disabling the `USER_SRP_AUTH` authentication flow. This doesn't mean the application will be vulnerable, but as the credentials are sent over the network, even if encrypted, it's considered less secure than using the SRP protocol which doesn't send any credentials at all.

When the migration is complete, you should reenable this method and disable the `ALLOW_USER_PASSWORD_AUTH`.

#### Recommended strategy
Depending on how often your users sign in, set a relatively short timeframe for the migration keeping the credentials. Up to a month should be enough.

After this period, change the authentication flow back to the default `USER_SRP_AUTH` and migrate the rest of the users who have not signed in during the migration period using a traditional export/import. These users will need to reset their passwords though.

#### References
* https://aws.amazon.com/blogs/security/approaches-for-migrating-users-to-amazon-cognito-user-pools/
* https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-import-using-lambda.html
* https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-lambda-migrate-user.html#cognito-user-pools-lambda-trigger-syntax-user-migration