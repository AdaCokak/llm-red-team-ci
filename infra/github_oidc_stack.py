"""GitHub Actions OIDC trust and least-privilege CI role."""

from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from constructs import Construct

from infra.target_app_stack import FOUNDATION_MODEL_ID, MODEL_ID


class GitHubOidcStack(cdk.Stack):
    """Create temporary-credential access for one exact GitHub repository."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        github_owner: str,
        github_repo: str,
        provider_arn: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        if provider_arn:
            provider = iam.OpenIdConnectProvider.from_open_id_connect_provider_arn(
                self,
                "GitHubProvider",
                provider_arn,
            )
        else:
            provider = iam.OpenIdConnectProvider(
                self,
                "GitHubProvider",
                url="https://token.actions.githubusercontent.com",
                client_ids=["sts.amazonaws.com"],
            )
        principal = iam.WebIdentityPrincipal(
            provider.open_id_connect_provider_arn,
            conditions={
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                    "token.actions.githubusercontent.com:sub": (
                        f"repo:{github_owner}/{github_repo}:environment:production"
                    ),
                },
            },
        )
        role = iam.Role(
            self,
            "GitHubActionsRole",
            assumed_by=principal,
            description=f"Temporary CI/CD access for {github_owner}/{github_repo}",
            max_session_duration=cdk.Duration.hours(1),
        )

        reports_bucket = s3.Bucket(
            self,
            "ReportsBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            lifecycle_rules=[
                s3.LifecycleRule(expiration=cdk.Duration.days(90))
            ],
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )
        reports_bucket.grant_read_write(role)

        bootstrap_role_pattern = self.format_arn(
            service="iam",
            region="",
            resource="role",
            resource_name=f"cdk-hnb659fds-*-role-{self.account}-{self.region}",
        )
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["sts:AssumeRole"],
                resources=[bootstrap_role_pattern],
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["cloudformation:DescribeStacks"],
                resources=["*"],
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=[
                    self.format_arn(
                        service="bedrock",
                        resource="inference-profile",
                        resource_name=MODEL_ID,
                    ),
                    f"arn:{self.partition}:bedrock:*::foundation-model/{FOUNDATION_MODEL_ID}",
                ],
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:ApplyGuardrail"],
                resources=[
                    self.format_arn(
                        service="bedrock",
                        resource="guardrail",
                        resource_name="*",
                    )
                ],
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["execute-api:Invoke"],
                resources=[
                    self.format_arn(
                        service="execute-api",
                        resource="*",
                        resource_name="*/POST/draft",
                    )
                ],
            )
        )

        cdk.CfnOutput(self, "GitHubActionsRoleArn", value=role.role_arn)
        cdk.CfnOutput(self, "ReportsBucketName", value=reports_bucket.bucket_name)
