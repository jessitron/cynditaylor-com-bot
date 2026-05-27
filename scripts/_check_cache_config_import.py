#!/usr/bin/env python3
"""Verify the Strands CacheConfig import we wired into agent/cyndibot.py."""

from strands.models.bedrock import BedrockModel, CacheConfig

print("CacheConfig:", CacheConfig)
print("annotations:", getattr(CacheConfig, "__annotations__", None))

cfg = CacheConfig(strategy="auto")
print("instance:", cfg)

m = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    region_name="us-west-2",
    cache_config=cfg,
)
print("model config:", m.config)
