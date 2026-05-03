"""Print the secret string at GITHUB_TOKEN_SECRET_ARN to stdout.

Used by scripts/container-entrypoint at AgentCore boot. Kept tiny and
single-purpose so the entrypoint stays readable.
"""

import os

import boto3

print(
    boto3.client("secretsmanager")
    .get_secret_value(SecretId=os.environ["GITHUB_TOKEN_SECRET_ARN"])["SecretString"],
    end="",
)
