"""CDK application entry point."""

from __future__ import annotations

import os
from pathlib import Path

# Keep jsii's extracted packages inside the project. This avoids relying on a
# machine-specific writable user cache.
os.environ.setdefault(
    "JSII_RUNTIME_PACKAGE_CACHE_ROOT",
    str(Path(__file__).resolve().parents[1] / ".jsii-cache"),
)

import aws_cdk as cdk

from infra.hello_stack import HelloLambdaStack


app = cdk.App()

HelloLambdaStack(
    app,
    "HelloLambdaStack",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"),
        region=os.getenv("CDK_DEFAULT_REGION", "us-east-1"),
    ),
)

app.synth()

