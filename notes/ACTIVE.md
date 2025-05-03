# Active work for Augment Agent right now

In this file, we will formulate a plan together. Separately, you will implement it.

Our goal is to re-implement how Frank responds so that a conversation history, once recorded,
could be replayed back; Frank will respond as the LLM in the conversation history as long as the
prompts it gets follow the conversation history too.

Put your plan here:

# Plan for Frank LLM Conversation History Replay

## Overview
We need to modify the FrankProvider to support replaying responses from a recorded conversation history. The provider should match incoming prompts against the conversation history and return the corresponding response if a match is found.

## Implementation Steps

1. **Create a Conversation History Model**
   - Create a new class `ConversationHistory` to store and manage conversation records
   - Include methods to load conversation history from a file and match prompts

2. **Modify FrankProvider**
   - Add support for initializing with a conversation history
   - Update the `generate` method to check if the prompt matches any in the conversation history
   - Return the corresponding response if a match is found, otherwise fall back to the current behavior

3. **Create Conversation History Storage**
   - Implement a way to store and load conversation histories (JSON format)
   - Include metadata like timestamps, conversation ID, etc.

4. **Update Configuration**
   - Add configuration options to specify a conversation history file
   - Add a flag to enable/disable conversation history replay mode

5. **Add Testing**
   - Create unit tests for the conversation history matching functionality
   - Test edge cases like partial matches, no matches, etc.

## Detailed Implementation

### 1. Conversation History Model

```python
class ConversationHistory:
    def __init__(self, records=None):
        self.records = records or []

    @classmethod
    def from_file(cls, file_path):
        # Load conversation history from a JSON file

    def find_matching_response(self, prompt):
        # Find a response that matches the given prompt

    def add_record(self, prompt, response):
        # Add a new record to the conversation history
```

### 2. FrankProvider Modifications

```python
class FrankProvider(LLMProvider):
    def __init__(self, model="default", conversation_history=None):
        self.model = model
        self.conversation_history = conversation_history

    def generate(self, prompt, **_):
        # Check if we have a matching prompt in the conversation history
        if self.conversation_history:
            matching_response = self.conversation_history.find_matching_response(prompt)
            if matching_response:
                return matching_response

        # Fall back to the current behavior if no match is found
        instruction = self._extract_instruction(prompt)
        response = self._generate_response(instruction)
        return response
```

### 3. Configuration Updates

```python
# In config.py
FRANK_CONVERSATION_HISTORY = os.environ.get("FRANK_CONVERSATION_HISTORY", "")
FRANK_REPLAY_MODE = os.environ.get("FRANK_REPLAY_MODE", "false").lower() == "true"

# In the Config class
@classmethod
def get_llm_config(cls):
    if cls.LLM_PROVIDER.lower() == "frank":
        return {
            "provider": "frank",
            "model": cls.FRANK_MODEL,
            "conversation_history": cls.FRANK_CONVERSATION_HISTORY,
            "replay_mode": cls.FRANK_REPLAY_MODE
        }
```

### 4. Main.py Updates

```python
def get_llm_provider():
    llm_config = Config.get_llm_config()

    if llm_config["provider"] == "frank":
        # Load conversation history if specified
        conversation_history = None
        if llm_config.get("replay_mode") and llm_config.get("conversation_history"):
            conversation_history = ConversationHistory.from_file(llm_config["conversation_history"])

        return FrankProvider(
            model=llm_config["model"],
            conversation_history=conversation_history
        )
```



