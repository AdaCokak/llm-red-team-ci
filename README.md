# LLM Red-Team Pipeline in CI

This learning project builds an automated security regression pipeline for a
small Amazon Bedrock application. It tests known attacks; it does not prove
that an LLM application is secure.

## Current stage: direct Bedrock baseline

The first stage calls Bedrock from a local Python process, runs five attacks,
and checks whether the fake canary `ZEBRA-7731` appears in a response.

Configuration is supplied through environment variables:

- `AWS_REGION` — defaults to `us-east-1`.
- `BEDROCK_MODEL_ID` — a model or inference-profile ID available to the AWS account.

Do not store AWS access keys in this repository.

## Local setup

Create an isolated Python environment:

```bash
python3 -m venv .venv
```

Activate it in the current terminal:

```bash
source .venv/bin/activate
```

Install the project and development tools:

```bash
python -m pip install -e '.[dev]'
```

Confirm the active AWS identity without changing anything:

```bash
aws sts get-caller-identity
```

List the current Bedrock inference profiles instead of guessing a model ID:

```bash
aws bedrock list-inference-profiles \
  --region us-east-1 \
  --type-equals SYSTEM_DEFINED \
  --query 'inferenceProfileSummaries[].{Name:inferenceProfileName,Id:inferenceProfileId,Status:status}' \
  --output table
```

Set configuration for this terminal session:

```bash
export AWS_REGION=us-east-1
export BEDROCK_MODEL_ID=us.amazon.nova-micro-v1:0
```

Run the five attacks:

```bash
PYTHONPATH=src python scripts/run_attacks.py
```

The final command invokes a paid Bedrock model. It sends five short requests
with output capped at 300 tokens each. There are no persistent model resources
to shut down after the script exits.

## Baseline result

The first run produced zero exact canary leaks. This is not a security claim:
the indirect-injection response also made an unsupported statement about opened
items, demonstrating why deterministic leakage checks need human review and
additional rule checks.

## Automated tests

Run the fast local checks, which make no AWS calls and cost nothing:

```bash
pytest -m 'not bedrock'
```

Run only the live attack suite after setting `BEDROCK_MODEL_ID`:

```bash
pytest -m bedrock
```

The second command invokes Bedrock once for every selected attack. A critical
canary or protected-prompt leak produces a non-zero exit code suitable for a CI
gate. The deterministic judge can miss paraphrased or behavioural violations,
so its passing result is intentionally described as narrow rather than secure.

## CDK learning stack

The first infrastructure stack contains one small ARM Lambda and a CloudWatch
log group with seven-day retention. Install the locally pinned CDK CLI and the
Python infrastructure dependencies:

```bash
npm_config_cache=.npm-cache npm install
python -m pip install -e '.[dev,infra]'
```

Generate and inspect the CloudFormation template locally:

```bash
npm run cdk -- synth HelloLambdaStack
```

Synthesis does not deploy or create AWS resources. Deployment and destruction
are intentionally documented only after the template and stack tests pass.

Verify the destination and bootstrap CDK once for this account and region:

```bash
export CDK_DEFAULT_ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
export CDK_DEFAULT_REGION=us-east-1
npm run cdk -- bootstrap "aws://${CDK_DEFAULT_ACCOUNT}/${CDK_DEFAULT_REGION}" --profile default
```

Bootstrap creates the reusable `CDKToolkit` stack, including an S3 asset bucket,
deployment roles, and an ECR repository. It has no continuously running compute,
but stored assets can incur a very small storage charge.

Review the proposed CloudFormation and IAM changes:

```bash
npm run cdk -- diff HelloLambdaStack --profile default
```

Deploy after reviewing the diff:

```bash
npm run cdk -- deploy HelloLambdaStack --profile default
```

The deployment command asks for confirmation if it detects security-sensitive
changes. The stack creates one Lambda, its least-privilege logging role, and a
seven-day CloudWatch log group. Lambda has no idle compute charge.

Remove the learning stack when it is no longer needed:

```bash
npm run cdk -- destroy HelloLambdaStack --profile default
```

This deletes the Lambda, role, and log group after confirmation. It intentionally
leaves the shared `CDKToolkit` bootstrap stack in place for later project stacks.

