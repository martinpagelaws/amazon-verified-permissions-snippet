from aws_cdk import (
    Aws as _aws,
    CfnOutput as _output,
    Stack,
    aws_apigatewayv2 as _apigw,
    aws_iam as _iam,
    aws_cognito as _cognito,
    aws_dynamodb as _dynamodb,
    aws_lambda as _lambda,
    aws_logs as _logs,
    aws_verifiedpermissions as _avp
)
from constructs import Construct

import json
import os

class SimplePostsStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        """
        APPLICATION
        """

        dynamodb_post_table = _dynamodb.Table(
            self, "PostTable",
            partition_key = _dynamodb.Attribute(name = "userId", type = _dynamodb.AttributeType.STRING),
            sort_key = _dynamodb.Attribute(name = "postId", type = _dynamodb.AttributeType.STRING),
            billing_mode = _dynamodb.BillingMode.PAY_PER_REQUEST
        )

        dynamodb_post_table_author_index = dynamodb_post_table.add_global_secondary_index(
            index_name = "author_postid_index",
            partition_key = _dynamodb.Attribute(name = "author", type = _dynamodb.AttributeType.STRING),
            sort_key = _dynamodb.Attribute(name = "postId", type = _dynamodb.AttributeType.STRING)
        )

        dynamodb_post_table_post_index = dynamodb_post_table.add_global_secondary_index(
            index_name = "postid_time_index",
            partition_key = _dynamodb.Attribute(name = "postId", type = _dynamodb.AttributeType.STRING),
            sort_key = _dynamodb.Attribute(name = "time", type = _dynamodb.AttributeType.STRING)
        )

        apigw_api = _apigw.CfnApi(
            self, "ApiGwThreadApi",
            description = "Handles all requests between clients and the application",
            name = construct_id + "Api",
            protocol_type = "HTTP"
        )

        lambda_func_main_exec_role = _iam.Role(
            self, "MainRole",
            assumed_by = _iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies = [
                _iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
            inline_policies = {
                "DynamoDbPolicy": _iam.PolicyDocument(
                    statements = [
                        _iam.PolicyStatement(
                            effect = _iam.Effect.ALLOW,
                            actions = ["dynamodb:*"],
                            resources = [
                                dynamodb_post_table.table_arn,
                                f"{dynamodb_post_table.table_arn}/index/author_postid_index",
                                f"{dynamodb_post_table.table_arn}/index/postid_time_index"
                            ]
                        ),
                        _iam.PolicyStatement(
                            effect = _iam.Effect.ALLOW,
                            actions = [
                                "verifiedpermissions:isauthorized",
                                "verifiedpermissions:isauthorizedwithtoken"
                            ],
                            resources = ["*"]
                        )
                    ]
                )
            }
        )

        lambda_func_main = _lambda.Function(
            self, "Main",
            runtime = _lambda.Runtime.PYTHON_3_10,
            code = _lambda.Code.from_asset("./lambda/main"),
            handler = "main.handler",
            role = lambda_func_main_exec_role,
            log_retention = _logs.RetentionDays.FIVE_DAYS,
            environment = {
                "TableName": dynamodb_post_table.table_name
            },
            layers = [
                _lambda.LayerVersion(
                    self, "LambdaLayer",
                    code = _lambda.Code.from_asset("./layers/main/"),
                    compatible_runtimes = [_lambda.Runtime.PYTHON_3_10]
                )
            ]
        )

        apigw_integration_main = _apigw.CfnIntegration(
            self, "ApiGwThreadIntegrationMain",
            api_id = apigw_api.attr_api_id,
            integration_type = "AWS_PROXY",
            integration_uri = lambda_func_main.function_arn,
            integration_method = "GET",
            payload_format_version = "2.0"
        )

        # Cloudwatch log group for API Gateway logs
        cloudwatch_apigw_log_group = _logs.LogGroup(
            self, "ApiGwThreadLogs"
        )

        apigw_stage = _apigw.CfnStage(
            self, "ApiGwThreadStage",
            api_id = apigw_api.attr_api_id,
            stage_name = "v1",
            auto_deploy = True,
            access_log_settings = _apigw.CfnStage.AccessLogSettingsProperty(
                destination_arn = cloudwatch_apigw_log_group.log_group_arn,
                format = (
                    '{'
                        '"requestId": "$context.requestId",'
                        '"path": "$context.path",'
                        '"routeKey": "$context.routeKey",'
                        '"ip": "$context.identity.sourceIp",'
                        '"requestTime": "$context.requestTime",'
                        '"httpMethod": "$context.httpMethod",'
                        '"statusCode": "$context.status"'
                    '}'
                )
            ),
        )

        cognito_up = _cognito.UserPool(
            self, "UserPool",
            sign_in_aliases = _cognito.SignInAliases(username = True),
            custom_attributes = {
                "appRole": _cognito.StringAttribute(min_len = 5, max_len = 15, mutable = True)
            }
        )

        cognito_up_client = cognito_up.add_client(
            "AppClient",
            o_auth = _cognito.OAuthSettings(
                flows = _cognito.OAuthFlows(
                    authorization_code_grant = True
                ),
                scopes = [_cognito.OAuthScope.OPENID],
                #callback_urls = [apigw_route_main_url]
                callback_urls = ["http://localhost"]
            ),
            auth_flows = _cognito.AuthFlow(
                user_password = True,
                user_srp = True,
                admin_user_password = True,
                custom = True
            ),
            supported_identity_providers = [_cognito.UserPoolClientIdentityProvider.COGNITO]
        )

        cognito_up_domain = cognito_up.add_domain(
            "CognitoDomain",
            cognito_domain = _cognito.CognitoDomainOptions(
                domain_prefix = apigw_api.attr_api_id
            )
        )

        apigw_authorizer = _apigw.CfnAuthorizer(
            self, "ApiGwThreadAuthorizer",
            api_id = apigw_api.attr_api_id,
            authorizer_type = "JWT",
            name = "Authorizer",
            identity_source = ["$request.header.Authorization"],
            jwt_configuration = _apigw.CfnAuthorizer.JWTConfigurationProperty(
                audience = [cognito_up_client.user_pool_client_id],
                issuer = f"https://cognito-idp.{_aws.REGION}.amazonaws.com/{cognito_up.user_pool_id}"
            )
        )

        apigw_route_main = _apigw.CfnRoute(
            self, "ApiGwThreadRouteMain",
            api_id = apigw_api.attr_api_id,
            route_key = "GET /",
            target = "integrations/" + apigw_integration_main.ref,
            authorization_type = "JWT",
            authorizer_id = apigw_authorizer.attr_authorizer_id
        )
        apigw_route_main_url = f"{apigw_api.attr_api_endpoint}/{apigw_stage.stage_name}/"

        apigw_route_posts_post = _apigw.CfnRoute(
            self, "ApiGwThreadRouteThreadPost",
            api_id = apigw_api.attr_api_id,
            route_key = "POST /posts",
            target = "integrations/" + apigw_integration_main.ref,
            authorization_type = "JWT",
            authorizer_id = apigw_authorizer.attr_authorizer_id
        )

        apigw_route_posts_get = _apigw.CfnRoute(
            self, "ApiGwThreadRouteThreadGet",
            api_id = apigw_api.attr_api_id,
            route_key = "GET /posts",
            target = "integrations/" + apigw_integration_main.ref,
            authorization_type = "JWT",
            authorizer_id = apigw_authorizer.attr_authorizer_id
        )

        apigw_route_posts_delete = _apigw.CfnRoute(
            self, "ApiGwThreadRouteThreadDelete",
            api_id = apigw_api.attr_api_id,
            route_key = "DELETE /posts/{postId}",
            target = "integrations/" + apigw_integration_main.ref,
            authorization_type = "JWT",
            authorizer_id = apigw_authorizer.attr_authorizer_id
        )

        lambda_func_main.add_permission(
            "ApiGwMainRoutePermission",
            principal = _iam.ServicePrincipal("apigateway.amazonaws.com"),
            source_arn = f"arn:aws:execute-api:{_aws.REGION}:{_aws.ACCOUNT_ID}:{apigw_api.ref}/*/*/*"
        )

        apigw_deployment = _apigw.CfnDeployment(
            self, "ApiGwThreadDeployment",
            api_id = apigw_api.attr_api_id,
        )
        apigw_deployment.add_dependency(apigw_route_main)


        """
        VERIFIED PERMISSIONS
        """

        with open(f"{os.getcwd()}/cdk/policy_store/schema.json", "r") as f:
            schema_definition = json.load(f)

        avp_policy_store = _avp.CfnPolicyStore(
            self, "SimplePostsPolicyStore",
            validation_settings = _avp.CfnPolicyStore.ValidationSettingsProperty(
                mode = "STRICT"
            ),
            schema = _avp.CfnPolicyStore.SchemaDefinitionProperty(
                cedar_json = json.dumps(schema_definition)
            )
        )

        lambda_func_main.add_environment(key = "PolicyStoreId", value = avp_policy_store.attr_policy_store_id)


        # Add an identity source, so we can base the permission validation on the identity token

        avp_policy_store_id_source = _avp.CfnIdentitySource(
            self, "SimplePostsIdentitySource",
            configuration = _avp.CfnIdentitySource.IdentitySourceConfigurationProperty(
                cognito_user_pool_configuration = _avp.CfnIdentitySource.CognitoUserPoolConfigurationProperty(
                    user_pool_arn = cognito_up.user_pool_arn,
                    client_ids = [cognito_up_client.user_pool_client_id]
                )
            ),

            policy_store_id = avp_policy_store.attr_policy_store_id,
            principal_entity_type = "SimplePosts::User"
        )


        # TODO: Policy creation should loop through all available documents and create accordingly

        with open(f"{os.getcwd()}/cdk/policy_store/all_users.cedar", "r") as f:
            avp_policy_all_users_statement = f.read()

        avp_policy_all_users = _avp.CfnPolicy(
            self, "AllUsersPolicy",
            definition = _avp.CfnPolicy.PolicyDefinitionProperty(
                static = _avp.CfnPolicy.StaticPolicyDefinitionProperty(
                    statement = avp_policy_all_users_statement,
                    description = "All users can create posts and read all posts"
                )
            ),
            policy_store_id = avp_policy_store.attr_policy_store_id
        )

        with open(f"{os.getcwd()}/cdk/policy_store/post_owners.cedar", "r") as f:
            avp_policy_post_owners_statement = f.read()

        avp_policy_post_owners = _avp.CfnPolicy(
            self, "PostOwnerPolicy",
            definition = _avp.CfnPolicy.PolicyDefinitionProperty(
                static = _avp.CfnPolicy.StaticPolicyDefinitionProperty(
                    statement = avp_policy_post_owners_statement,
                    description = "Post owners can delete their posts"
                )
            ),
            policy_store_id = avp_policy_store.attr_policy_store_id
        )

        with open(f"{os.getcwd()}/cdk/policy_store/admin_delete_posts.cedar", "r") as f:
            avp_policy_admin_delete_posts_statement = f.read()

        avp_policy_admin_delete_posts = _avp.CfnPolicy(
            self, "AdminDeletePostsPolicy",
            definition = _avp.CfnPolicy.PolicyDefinitionProperty(
                static = _avp.CfnPolicy.StaticPolicyDefinitionProperty(
                    statement = avp_policy_admin_delete_posts_statement,
                    description = "Admins can delete anyone's posts"
                )
            ),
            policy_store_id = avp_policy_store.attr_policy_store_id
        )

        # Creating an arbitrary deny policy so admins can't create posts - showcases how explicit forbid beats everything

        with open(f"{os.getcwd()}/cdk/policy_store/admin_restriction.cedar", "r") as f:
            avp_policy_admin_restriction_statement = f.read()

        avp_policy_admin_restriction = _avp.CfnPolicy(
            self, "AdminRestrictionPolicy",
            definition = _avp.CfnPolicy.PolicyDefinitionProperty(
                static = _avp.CfnPolicy.StaticPolicyDefinitionProperty(
                    statement = avp_policy_admin_restriction_statement,
                    description = "Admins cannot create posts"
                )
            ),
            policy_store_id = avp_policy_store.attr_policy_store_id
        )


        """
        STACK OUTPUTS
        """

        _output(
            self, "ApiGwMainUrl",
            value = apigw_route_main_url
        )

        _output(
            self, "PolicyStoreId",
            value = avp_policy_store.attr_policy_store_id
        )

        _output(
            self, "CognitoUserPoolId",
            value = cognito_up.user_pool_id
        )

        _output (
            self, "CognitoAppClientId",
            value = cognito_up_client.user_pool_client_id
        )
