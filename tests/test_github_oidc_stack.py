import aws_cdk as cdk
from aws_cdk import assertions

from infra.github_oidc_stack import GitHubOidcStack


def test_oidc_trust_is_scoped_to_one_repository() -> None:
    app = cdk.App()
    stack = GitHubOidcStack(
        app,
        "TestOidc",
        github_owner="ada",
        github_repo="llm-red-team",
        env=cdk.Environment(account="123456789012", region="us-east-1"),
    )
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties(
        "Custom::AWSCDKOpenIdConnectProvider",
        {
            "ClientIDList": ["sts.amazonaws.com"],
            "Url": "https://token.actions.githubusercontent.com",
        },
    )
    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "AssumeRolePolicyDocument": assertions.Match.object_like(
                {
                    "Statement": assertions.Match.array_with(
                        [
                            assertions.Match.object_like(
                                {
                                    "Condition": assertions.Match.object_like(
                                        {
                                            "StringEquals": assertions.Match.object_like(
                                                {
                                                    "token.actions.githubusercontent.com:sub": (
                                                        "repo:ada/llm-red-team:"
                                                        "environment:production"
                                                    )
                                                }
                                            )
                                        }
                                    )
                                }
                            )
                        ]
                    )
                }
            )
        },
    )


def test_existing_oidc_provider_can_be_imported() -> None:
    app = cdk.App()
    stack = GitHubOidcStack(
        app,
        "TestImportedOidc",
        github_owner="ada",
        github_repo="llm-red-team",
        provider_arn=(
            "arn:aws:iam::123456789012:oidc-provider/"
            "token.actions.githubusercontent.com"
        ),
        env=cdk.Environment(account="123456789012", region="us-east-1"),
    )
    template = assertions.Template.from_stack(stack)

    template.resource_count_is("Custom::AWSCDKOpenIdConnectProvider", 0)
    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "AssumeRolePolicyDocument": assertions.Match.object_like(
                {
                    "Statement": assertions.Match.array_with(
                        [
                            assertions.Match.object_like(
                                {
                                    "Principal": {
                                        "Federated": (
                                            "arn:aws:iam::123456789012:oidc-provider/"
                                            "token.actions.githubusercontent.com"
                                        )
                                    }
                                }
                            )
                        ]
                    )
                }
            )
        },
    )
