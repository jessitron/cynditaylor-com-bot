"""
Telemetry module for the Cyndi Taylor Website Bot.

This module handles OpenTelemetry integration for logging to Honeycomb.
"""

import os
import logging
from typing import Dict, Any, Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_telemetry(service_name: str = "cynditaylor-website-bot") -> None:
    """
    Set up OpenTelemetry for logging to Honeycomb.
    
    Args:
        service_name: Name of the service for telemetry
    """
    # Check if Honeycomb API key is set
    honeycomb_api_key = os.environ.get("HONEYCOMB_API_KEY")
    if not honeycomb_api_key:
        logger.warning("HONEYCOMB_API_KEY environment variable not set, telemetry disabled")
        return
    
    # Set up the tracer provider
    resource = Resource(attributes={
        SERVICE_NAME: service_name
    })
    
    trace_provider = TracerProvider(resource=resource)
    
    # Set up the OTLP exporter for Honeycomb
    otlp_exporter = OTLPSpanExporter(
        endpoint="https://api.honeycomb.io:443",
        headers={
            "x-honeycomb-team": honeycomb_api_key
        }
    )
    
    # Add the exporter to the provider
    trace_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    
    # Set the provider as the global provider
    trace.set_tracer_provider(trace_provider)
    
    logger.info("Telemetry set up successfully")

def get_tracer(name: str = "cynditaylor-website-bot") -> trace.Tracer:
    """
    Get a tracer for the specified name.
    
    Args:
        name: Name for the tracer
        
    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)
