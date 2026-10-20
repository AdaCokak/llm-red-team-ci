"""A minimal Lambda stack used to learn the CDK lifecycle."""

from __future__ import annotations

from pathlib import Path

import aws_cdk as cdk
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from constructs import Construct


LAMBDA_SOURCE = Path(__file__).parent / "lambda" / "hello"


class HelloLambdaStack(cdk.Stack):
    """One Lambda and its short-lived log group."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs: object) -> None:
        super().__init__(scope, construct_id, **kwargs)

        function = lambda_.Function(
            self,
            "HelloFunction",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset(str(LAMBDA_SOURCE)),
            architecture=lambda_.Architecture.ARM_64,
            memory_size=128,
            timeout=cdk.Duration.seconds(5),
            description="Minimal Lambda for learning the CDK deployment lifecycle",
        )

        logs.LogGroup(
            self,
            "HelloFunctionLogGroup",
            log_group_name=f"/aws/lambda/{function.function_name}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        cdk.CfnOutput(
            self,
            "HelloFunctionName",
            value=function.function_name,
            description="Generated name of the learning Lambda function",
        )

