"""CDK stack for the guarded customer-support target application."""

from __future__ import annotations

from pathlib import Path

import aws_cdk as cdk
from aws_cdk import aws_apigateway as apigateway
from aws_cdk import aws_bedrock as bedrock
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from constructs import Construct


MODEL_ID = "us.amazon.nova-micro-v1:0"
FOUNDATION_MODEL_ID = "amazon.nova-micro-v1:0"
LAMBDA_SOURCE = Path(__file__).resolve().parents[1] / "src"


class TargetAppStack(cdk.Stack):
    """IAM-protected API, Lambda, Bedrock model access, and Guardrail."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs: object) -> None:
        super().__init__(scope, construct_id, **kwargs)

        guardrail = bedrock.CfnGuardrail(
            self,
            "TargetGuardrail",
            name="llm-red-team-target-guardrail",
            description="Blocks prompt attacks and fake-canary leakage in the learning target",
            blocked_input_messaging="I cannot process that request.",
            blocked_outputs_messaging="I cannot include protected internal information.",
            content_policy_config=bedrock.CfnGuardrail.ContentPolicyConfigProperty(
                filters_config=[
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        type="PROMPT_ATTACK",
                        input_strength="HIGH",
                        output_strength="NONE",
                        input_action="BLOCK",
                        input_enabled=True,
                        output_action="NONE",
                        output_enabled=False,
                    )
                ]
            ),
            sensitive_information_policy_config=(
                bedrock.CfnGuardrail.SensitiveInformationPolicyConfigProperty(
                    regexes_config=[
                        bedrock.CfnGuardrail.RegexConfigProperty(
                            name="FakeCanary",
                            description="Fake secret used only for regression testing",
                            pattern="ZEBRA-7731",
                            action="BLOCK",
                            input_action="BLOCK",
                            input_enabled=True,
                            output_action="BLOCK",
                            output_enabled=True,
                        )
                    ]
                )
            ),
        )
        guardrail.apply_removal_policy(cdk.RemovalPolicy.DESTROY)

        guardrail_version = bedrock.CfnGuardrailVersion(
            self,
            "TargetGuardrailVersion",
            guardrail_identifier=guardrail.attr_guardrail_id,
            description="Version controlled by the TargetAppStack deployment",
        )
        guardrail_version.add_resource_dependency(guardrail)

        function = lambda_.Function(
            self,
            "TargetFunction",
            runtime=lambda_.Runtime.PYTHON_3_13,
            architecture=lambda_.Architecture.ARM_64,
            handler="llm_red_team.lambda_handler.lambda_handler",
            code=lambda_.Code.from_asset(str(LAMBDA_SOURCE)),
            memory_size=256,
            timeout=cdk.Duration.seconds(30),
            description="Guarded Bedrock customer-support reply drafter",
            environment={
                "BEDROCK_MODEL_ID": MODEL_ID,
                "BEDROCK_GUARDRAIL_ID": guardrail.attr_guardrail_id,
                "BEDROCK_GUARDRAIL_VERSION": guardrail_version.attr_version,
            },
        )
        function.node.add_dependency(guardrail_version)

        model_profile_arn = self.format_arn(
            service="bedrock",
            resource="inference-profile",
            resource_name=MODEL_ID,
        )
        foundation_model_arn = (
            f"arn:{self.partition}:bedrock:*::foundation-model/{FOUNDATION_MODEL_ID}"
        )
        function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=[model_profile_arn, foundation_model_arn],
            )
        )
        function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:ApplyGuardrail"],
                resources=[guardrail.attr_guardrail_arn],
            )
        )

        logs.LogGroup(
            self,
            "TargetFunctionLogGroup",
            log_group_name=f"/aws/lambda/{function.function_name}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        api = apigateway.RestApi(
            self,
            "TargetApi",
            rest_api_name="llm-red-team-target",
            description="IAM-protected API for the deliberately small Bedrock target",
            deploy_options=apigateway.StageOptions(
                stage_name="v1",
                throttling_rate_limit=5,
                throttling_burst_limit=10,
            ),
            endpoint_types=[apigateway.EndpointType.REGIONAL],
        )
        draft = api.root.add_resource("draft")
        draft.add_method(
            "POST",
            apigateway.LambdaIntegration(function),
            authorization_type=apigateway.AuthorizationType.IAM,
        )

        cdk.CfnOutput(self, "TargetApiUrl", value=api.url_for_path("/draft"))
        cdk.CfnOutput(self, "TargetFunctionName", value=function.function_name)
        cdk.CfnOutput(self, "GuardrailId", value=guardrail.attr_guardrail_id)
        cdk.CfnOutput(self, "GuardrailVersion", value=guardrail_version.attr_version)

