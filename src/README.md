# Cyndi Taylor Website Bot - Python Implementation

This directory contains the Python implementation of the Cyndi Taylor Website Bot.

## Structure

- `agent/`: Core agent functionality
  - `agent.py`: Main agent loop implementation
  - `llm.py`: Anthropic API client
  - `tools.py`: Tools for the agent to use
  - `telemetry.py`: OpenTelemetry integration for Honeycomb
- `main.py`: Main entry point for the agent

## Usage

1. Copy `.env.example` to `.env` and fill in the required values
2. Install dependencies: `pip install -r requirements.txt`
3. Run the agent: `python src/main.py`

## Testing

Run tests with pytest:

```bash
pytest
```

## Agent Loop

The agent loop works as follows:

1. Receive instructions (e.g., "Update the title of the homepage")
2. Make an LLM call to determine the next action
3. Parse tool calls from the LLM response
4. Execute the tool calls
5. Add the results to the conversation history
6. Repeat until the task is complete

## Tools

The agent has access to the following tools:

- `git_pull`: Pull the latest changes from the GitHub repository
- `git_push`: Commit and push changes to the GitHub repository
- `modify_file`: Modify a file in the website repository
- `read_file`: Read a file from the website repository

## Telemetry

The agent uses OpenTelemetry to log all actions to Honeycomb, allowing for monitoring and debugging.
