"""
Main module for the Cyndi Taylor Website Bot.

This module ties together all the components of the agent.
"""

import os
import logging
import json
from typing import Dict, Any, Optional

from dotenv import load_dotenv

from agent.agent import WebsiteAgent
from agent.llm import create_anthropic_client, get_system_prompt
from agent.tools import AVAILABLE_TOOLS
from agent.telemetry import setup_telemetry, get_tracer

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main(instructions: str) -> Dict[str, Any]:
    """
    Main function to run the agent with the given instructions.
    
    Args:
        instructions: Instructions for the agent
        
    Returns:
        Dictionary with the result of the agent run
    """
    # Set up telemetry
    setup_telemetry()
    tracer = get_tracer()
    
    # Create a span for the agent run
    with tracer.start_as_current_span("agent_run") as span:
        span.set_attribute("instructions", instructions)
        
        try:
            # Create Anthropic client
            llm_client = create_anthropic_client()
            
            # Create agent
            agent = WebsiteAgent(llm_client, AVAILABLE_TOOLS)
            
            # Run agent loop
            actions = agent.run_agent_loop(instructions)
            
            # Record actions in span
            span.set_attribute("actions_count", len(actions))
            span.set_attribute("actions", json.dumps(actions))
            
            return {
                "success": True,
                "actions": actions
            }
            
        except Exception as e:
            logger.error(f"Error running agent: {str(e)}")
            span.record_exception(e)
            
            return {
                "success": False,
                "error": str(e)
            }

if __name__ == "__main__":
    # Example usage
    instructions = "Update the title of the homepage to 'Cyndi Taylor - Artist'"
    result = main(instructions)
    print(json.dumps(result, indent=2))
