#!/usr/bin/env python3
"""
Main entry point for the Cyndi Taylor Website Bot.
This script initializes the agent and runs it with hard-coded instructions.
"""

import os
import sys
import logging
from dotenv import load_dotenv
from agent.agent import Agent
from agent.real_anthropic_adapter import RealAnthropicAdapter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def setup_environment():
    """
    Set up the environment by loading environment variables.
    """
    # Load environment variables from .env file if it exists
    load_dotenv()
    
    # Check if required environment variables are set
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.error("ANTHROPIC_API_KEY environment variable is not set")
        sys.exit(1)

def main():
    """
    Main function that initializes the agent and runs it with hard-coded instructions.
    """
    # Set up the environment
    setup_environment()
    
    try:
        # Initialize the Anthropic adapter
        anthropic_adapter = RealAnthropicAdapter()
        
        # Initialize the agent
        agent = Agent(anthropic_adapter=anthropic_adapter)
        
        # Hard-coded instructions for the agent
        instructions = """
        I need you to help me update the website. Here are the tasks:
        
        1. First, pull the latest changes from the repository.
        2. List all the files in the repository to get familiar with the structure.
        3. Read the README.md file to understand the project.
        4. Make a small change to the README.md file by adding a new line at the end saying "Updated by the Website Bot".
        5. Commit and push the changes to the repository.
        
        Please execute these tasks in order and let me know the results of each step.
        """
        
        # Run the agent with the instructions
        logger.info("Starting the agent with hard-coded instructions")
        result = agent.run(instructions)
        
        # Process the results
        logger.info("Agent execution completed")
        logger.info(f"Number of actions performed: {len(result['actions'])}")
        
        # Print the actions and their results
        for i, action in enumerate(result['actions']):
            logger.info(f"Action {i+1}: {action['tool']}")
            logger.info(f"Input: {action['input']}")
            logger.info(f"Result: {action['result']}")
            logger.info("-" * 50)
        
        return 0
    except Exception as e:
        logger.error(f"Error in main function: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
