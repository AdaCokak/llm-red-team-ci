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
python scripts/run_attacks.py
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

