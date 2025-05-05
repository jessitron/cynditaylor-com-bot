#!/usr/bin/env python3
"""
Script to visualize conversation history in a cowsay-like format.
"""

import os
import sys
import json
import argparse
import textwrap
from typing import Dict, Any, List


# ASCII art for the cow (agent)
COW_TEMPLATE = r"""
        \   ^__^
         \  (oo)\_______
            (__)\       )\/\
                ||----w |
                ||     ||
"""

# ASCII art for the dragon (Frank LLM)
DRAGON_TEMPLATE = r"""
                           /\    /\
                          /  \__/  \
                         /         \
                        /           \
      /\               /             \
     /  \             /               \
    /    \           /                 \
   /      \         /                   \
  /        \_______/                     \
 /                                        \
/                                          \
"""


def create_speech_bubble(text: str, width: int = 60, is_cow: bool = True) -> str:
    """
    Create a speech bubble with the given text.

    Args:
        text: The text to put in the speech bubble
        width: The maximum width of the speech bubble
        is_cow: Whether the speech bubble is for the cow (left-aligned) or dragon (right-aligned)

    Returns:
        The speech bubble as a string
    """
    # Wrap the text to the specified width
    wrapped_lines = textwrap.wrap(text, width=width)

    # Find the length of the longest line
    max_length = max(len(line) for line in wrapped_lines)

    # Create the top border
    bubble = [" " + "_" * (max_length + 2)]

    # Create the middle lines
    if len(wrapped_lines) == 1:
        bubble.append("< " + wrapped_lines[0] + " " * (max_length - len(wrapped_lines[0])) + " >")
    else:
        bubble.append("/ " + wrapped_lines[0] + " " * (max_length - len(wrapped_lines[0])) + " \\")
        for i in range(1, len(wrapped_lines) - 1):
            bubble.append("| " + wrapped_lines[i] + " " * (max_length - len(wrapped_lines[i])) + " |")
        bubble.append("\\ " + wrapped_lines[-1] + " " * (max_length - len(wrapped_lines[-1])) + " /")

    # Create the bottom border
    bubble.append(" " + "-" * (max_length + 2))

    # Join the lines
    result = "\n".join(bubble)

    # If it's for the dragon (right-aligned), add padding to the left
    if not is_cow:
        # Calculate the padding needed to right-align the bubble
        terminal_width = get_terminal_width()
        padding = terminal_width - max_length - 4  # 4 for the bubble borders
        if padding < 0:
            padding = 0

        # Add the padding to each line
        result = "\n".join(" " * padding + line for line in result.split("\n"))

    return result


def get_terminal_width() -> int:
    """
    Get the width of the terminal.

    Returns:
        The width of the terminal in characters
    """
    try:
        return os.get_terminal_size().columns
    except (AttributeError, OSError):
        return 80  # Default width


def print_conversation(exchange: Dict[str, Any], terminal_width: int = 80) -> None:
    """
    Print a single exchange in the conversation.

    Args:
        exchange: The exchange to print
        terminal_width: The width of the terminal
    """
    # Get the prompt and response
    prompt = exchange["prompt"]
    response = exchange["response"]

    # Get the new portion of the prompt, or use the full text if not available
    prompt_text = prompt.get("new_text", prompt["prompt_text"])
    response_text = response["response_text"]

    # Create the speech bubbles
    cow_bubble = create_speech_bubble(prompt_text, width=terminal_width // 2 - 10, is_cow=True)
    dragon_bubble = create_speech_bubble(response_text, width=terminal_width // 2 - 10, is_cow=False)

    # Print the speech bubbles
    print(cow_bubble)
    print(COW_TEMPLATE)
    print("\n" + "=" * terminal_width + "\n")
    print(dragon_bubble)
    print(DRAGON_TEMPLATE)
    print("\n" + "=" * terminal_width + "\n")

    # Print any tool calls
    if "tool_calls" in response and response["tool_calls"]:
        print("Tool Calls:")
        for tool_call in response["tool_calls"]:
            print(f"  Tool: {tool_call['tool_name']}")
            print(f"  Parameters: {json.dumps(tool_call['parameters'], indent=2)}")
            if 'result' in tool_call:
                print(f"  Result: {json.dumps(tool_call['result'], indent=2)}")
            print()
        print("=" * terminal_width + "\n")


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(description="Visualize conversation history in a cowsay-like format.")
    parser.add_argument("file", help="Path to the conversation history file")
    args = parser.parse_args()

    # Check if the file exists
    if not os.path.exists(args.file):
        print(f"Error: File '{args.file}' does not exist.")
        sys.exit(1)

    # Read the conversation history
    try:
        with open(args.file, "r") as f:
            conversation = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: File '{args.file}' is not a valid JSON file.")
        sys.exit(1)

    # Check if the conversation history has the expected format
    if "exchanges" not in conversation:
        print(f"Error: File '{args.file}' does not have the expected format.")
        sys.exit(1)

    # Get the terminal width
    terminal_width = get_terminal_width()

    # Print the conversation header
    print("\n" + "=" * terminal_width)
    print(f"Conversation ID: {conversation.get('conversation_id', 'Unknown')}")
    print(f"Timestamp: {conversation.get('timestamp', 'Unknown')}")
    print("=" * terminal_width + "\n")

    # Print each exchange
    for exchange in conversation["exchanges"]:
        print_conversation(exchange, terminal_width)


if __name__ == "__main__":
    main()
