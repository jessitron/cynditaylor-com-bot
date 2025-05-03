#!/usr/bin/env python3
"""
Run the Cyndi Taylor Website Bot with OpenTelemetry instrumentation.
"""
import os
import sys
import subprocess

# Set OpenTelemetry environment variables
os.environ["OTEL_SERVICE_NAME"] = "cynditaylor-com-bot"
os.environ["OTEL_EXPORTER_OTLP_PROTOCOL"] = "http/protobuf"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "https://api.honeycomb.io:443"
# The HONEYCOMB_API_KEY should be set in the environment
if "HONEYCOMB_API_KEY" in os.environ:
    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"x-honeycomb-team={os.environ['HONEYCOMB_API_KEY']}"
os.environ["OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED"] = "true"

if __name__ == "__main__":
    # Get the instruction from command line arguments
    instruction = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Build the command to run
    cmd = ["opentelemetry-instrument", "python", "-m", "src.main"]
    if instruction:
        cmd.append(instruction)
    
    # Run the command
    subprocess.run(cmd)
