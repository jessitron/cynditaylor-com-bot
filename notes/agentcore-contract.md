# AgentCore Runtime contract (research, frozen)

Research done 2026-04-17. Confidence annotations are from the research sub-agent's report. Sources cited inline.

## HTTP contract

- `POST /invocations` — `Content-Type: application/json`. Request body is whatever JSON you want; AgentCore forwards the `InvokeAgentRuntime` payload through untouched. Docs' example uses `{"prompt": "..."}`. Response is either JSON or `text/event-stream` SSE for streaming.
- `GET /ping` — returns `200` with `{"status": "Healthy" | "HealthyBusy", "time_of_last_update": <unix_ts>}`.
- Bind to `0.0.0.0:8080`.
- Container platform: **`linux/arm64`**.
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-http-protocol-contract.html

## Session identity

- `runtimeSessionId` arrives on every invocation as header **`X-Amzn-Bedrock-AgentCore-Runtime-Session-Id`**.
- Same header is used for WebSocket upgrade.
- Plan: set this to mom's email address (already decided in ACTIVE.md).

## Session filesystem (preview, March 2026)

- Config: `filesystemConfigurations: [{ sessionStorage: { mountPath: "/mnt/workspace" } }]`.
- `mountPath` must start with `/mnt`.
- Per-session-persistent (NOT per-invocation). Survives stop/resume of the same `runtimeSessionId`; restored from durable storage on resume.
- Cap: **1 GB per session**.
- Our use: `/mnt/workspace/cynditaylor-com` is the shelled-out `git clone` location; the agent's `site_tools.sync_workspace` just needs `CYNDIBOT_WORKSPACE=/mnt/workspace/cynditaylor-com` in the container env.
- https://aws.amazon.com/about-aws/whats-new/2026/03/bedrock-agentcore-runtime-session-storage/
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-persistent-filesystems.html

## Control plane

- The CLI/SDK client is `aws bedrock-agentcore-control`, NOT `aws bedrock-agent-core`. The runtime-invoke side uses `bedrock-agentcore`.
- Minimum `create-agent-runtime` call (boto3 shape):
  ```python
  client = boto3.client("bedrock-agentcore-control", region_name="us-west-2")
  client.create_agent_runtime(
      agentRuntimeName="cyndibot",
      agentRuntimeArtifact={
          "containerConfiguration": {
              "containerUri": "414852377253.dkr.ecr.us-west-2.amazonaws.com/cyndibot:latest"
          }
      },
      networkConfiguration={"networkMode": "PUBLIC"},
      roleArn="arn:aws:iam::414852377253:role/CyndibotAgentRuntime",
      lifecycleConfiguration={"idleRuntimeSessionTimeout": 300, "maxLifetime": 1800},
      filesystemConfigurations=[
          {"sessionStorage": {"mountPath": "/mnt/workspace"}}
      ],
  )
  ```
- `protocolConfiguration` is optional; HTTP is default.
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/getting-started-custom.html

## Execution-role IAM

Beyond the obvious `bedrock:InvokeModel*`, the role needs these AgentCore-adjacent statements:

- `ecr:BatchGetImage`, `ecr:GetDownloadUrlForLayer`, `ecr:GetAuthorizationToken`
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`, `logs:DescribeLogStreams`, `logs:DescribeLogGroups` — scoped to `/aws/bedrock-agentcore/runtimes/*`
- X-Ray `Put*` / `Get*` (`xray:PutTraceSegments`, etc.)
- `cloudwatch:PutMetricData` scoped to namespace `bedrock-agentcore`
- `bedrock-agentcore:GetWorkloadAccessToken*`

Plus what OUR agent actually does:

- `s3:GetObject` + `s3:PutObject` on `arn:aws:s3:::cyndibot-incoming-emails/*`
- `ses:SendEmail` for `bot@cyndibot.jessitron.honeydemo.io`

Trust policy: principal `bedrock-agentcore.amazonaws.com` with `aws:SourceAccount` + `aws:SourceArn` conditions (prevents the confused-deputy pattern).

- Full baseline policy: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html

## Python packaging (Strands-specific)

PyPI package **`bedrock-agentcore`** provides the server shim. Minimal entry point:

```python
from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent

app = BedrockAgentCoreApp()
agent = Agent(...)

@app.entrypoint
def invoke(payload):
    return {"result": str(agent(payload["prompt"]).message)}

if __name__ == "__main__":
    app.run()
```

The decorator handles `/invocations` + `/ping` + session header extraction. Rolling our own FastAPI route is also documented if we want more control.

- https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/runtime/quickstart.html
- Custom FastAPI alternative: https://dev.to/aws-heroes/amazon-bedrock-agentcore-runtime-part-4-using-custom-agent-with-strands-agents-sdk-201o

## Starter toolkit status

`bedrock-agentcore-starter-toolkit` is marked legacy as of early 2026; AWS is pointing new projects at `aws/agentcore-cli`. We're rolling our own Dockerfile + CLI scripts so we're not reliant on either, but it's worth a look before adding toolkit dependencies.

- https://github.com/aws/bedrock-agentcore-starter-toolkit (legacy)

## Multi-protocol note

The service contract now supports A2A (port 9000) and AGUI (port 8080) alongside HTTP/MCP. We use plain HTTP/MCP; no action needed.

- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-service-contract.html

## Unverified / decide-at-build-time

- `filesystemConfigurations` didn't show up in the devguide's custom-runtime example, only in the preview What's-New + persistent-filesystems page. **Confirm it's an accepted field by running `aws bedrock-agentcore-control create-agent-runtime help` before scripting infra.**
- `protocolConfiguration` is omitted in the getting-started example. Assume HTTP is default; confirm if the API rejects the call without it.
