import os
import sys
import logging
from typing import Optional

from src.config import Config
from src.llm.frank_provider import FrankProvider
from src.agent.agent import WebsiteAgent

def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def get_llm_provider() -> FrankProvider:
    """
    Get the LLM provider based on configuration.

    Returns:
        An instance of FrankProviderWithTools
    """
    llm_config = Config.get_llm_config()

    if llm_config["provider"] == "frank":
        return FrankProvider(
            model=llm_config["model"],
            max_iterations=10
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {llm_config['provider']}")


def main(instruction: Optional[str] = None):
    """
    Main entry point for the application.

    Args:
        instruction: Optional instruction to execute. If not provided, a default will be used.
    """
    setup_logging()
    logger = logging.getLogger(__name__)

    # Use the provided instruction or a default one
    if not instruction:
        instruction = "Update the hero section on the homepage to include a new tagline: 'Bringing your memories to life through art'"

    logger.info(f"Starting website agent with instruction: {instruction}")

    try:
        # Get the LLM provider
        llm_provider = get_llm_provider()
        logger.info(f"Using LLM provider: {llm_provider.get_name()}")

        # Create the website agent
        website_config = Config.get_website_config()
        agent = WebsiteAgent(
            llm_provider=llm_provider,
            website_dir=website_config["website_dir"]
        )

        # Execute the instruction
        result = agent.execute_instruction(instruction)

        # Print the result
        print("\n" + "="*80)
        print("EXECUTION RESULT:")
        print("="*80)
        print(result)
        print("="*80 + "\n")

        return result

    except Exception as e:
        logger.error(f"Error executing instruction: {e}", exc_info=True)
        return f"Error: {str(e)}"


if __name__ == "__main__":
    # If an instruction is provided as a command-line argument, use it
    instruction = sys.argv[1] if len(sys.argv) > 1 else None
    main(instruction)
