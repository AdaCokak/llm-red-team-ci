import aws_cdk as cdk
from aws_cdk.assertions import Template

from infra.hello_stack import HelloLambdaStack


def test_hello_stack_contains_one_small_lambda() -> None:
    app = cdk.App()
    stack = HelloLambdaStack(app, "TestHelloLambdaStack")
    template = Template.from_stack(stack)

    template.resource_count_is("AWS::Lambda::Function", 1)
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Architectures": ["arm64"],
            "MemorySize": 128,
            "Runtime": "python3.13",
            "Timeout": 5,
        },
    )
    template.has_resource_properties(
        "AWS::Logs::LogGroup",
        {"RetentionInDays": 7},
    )

