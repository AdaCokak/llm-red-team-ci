import aws_cdk as cdk
from aws_cdk.assertions import Match, Template

from infra.target_app_stack import MODEL_ID, TargetAppStack


def _template() -> Template:
    app = cdk.App()
    stack = TargetAppStack(app, "TestTargetAppStack")
    return Template.from_stack(stack)


def test_target_stack_has_guardrail_and_version() -> None:
    template = _template()

    template.resource_count_is("AWS::Bedrock::Guardrail", 1)
    template.resource_count_is("AWS::Bedrock::GuardrailVersion", 1)
    template.has_resource_properties(
        "AWS::Bedrock::Guardrail",
        {
            "ContentPolicyConfig": {
                "FiltersConfig": [
                    Match.object_like(
                        {
                            "Type": "PROMPT_ATTACK",
                            "InputStrength": "HIGH",
                            "InputAction": "BLOCK",
                        }
                    )
                ]
            },
            "SensitiveInformationPolicyConfig": {
                "RegexesConfig": [
                    Match.object_like({"Name": "FakeCanary", "Pattern": "ZEBRA-7731"})
                ]
            },
        },
    )


def test_target_lambda_is_small_and_guarded() -> None:
    template = _template()

    template.resource_count_is("AWS::Lambda::Function", 1)
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Architectures": ["arm64"],
            "MemorySize": 256,
            "Runtime": "python3.13",
            "Timeout": 30,
            "Environment": {
                "Variables": Match.object_like({"BEDROCK_MODEL_ID": MODEL_ID})
            },
        },
    )
    template.has_resource_properties("AWS::Logs::LogGroup", {"RetentionInDays": 7})


def test_target_api_requires_iam_authentication() -> None:
    template = _template()

    template.has_resource_properties(
        "AWS::ApiGateway::Method",
        {"HttpMethod": "POST", "AuthorizationType": "AWS_IAM"},
    )
