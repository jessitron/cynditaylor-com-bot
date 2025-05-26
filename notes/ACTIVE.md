# Separate tool list, tool use and tool result

We are going to refactor the Conversation format.

Eliding the parts that aren't changing, the conversation will be more like

Conversation(
    tool_list: List[Tool],
    exchanges: List[Exchange]
)

The tool list is at the conversation level because it is something that is negotiated at the beginning of the conversation.

Exchange(
    prompt: TextPrompt OR ToolUseResults,
    response: FinalResponse OR ToolUseRequests,
)

TextPrompt has only a text field

ToolUseRequests is a list of ToolUse

ToolUse(
    tool_name: str,
    id: str,
    parameters: Dict[str, Any],
)

ToolUseResults is a list of ToolUseResult

ToolUseResult(
    id: str,
    result: Any,
)

FinalResponse has only a text field

## Implementation Plan

Do not include tests in this plan. I will worry about those later. 
Get the data structures right.

### Step 1: Define new data structures
1. Create `Tool` dataclass with minimal fields needed for tool description
2. Create `TextPrompt` dataclass with just `text` field
3. Create `ToolUse` dataclass with `tool_name`, `id`, and `parameters`
4. Create `ToolUseRequests` as a list wrapper for `ToolUse` objects
5. Create `ToolUseResult` dataclass with `id` and `result`
6. Create `ToolUseResults` as a list wrapper for `ToolUseResult` objects  
7. Create `FinalResponse` dataclass with just `text` field

### Step 2: Update Exchange structure
1. Modify `Exchange` to use union types: `prompt: TextPrompt | ToolUseResults`
2. Modify `Exchange` to use union types: `response: FinalResponse | ToolUseRequests`
3. Keep the `id` field on Exchange

### Step 3: Update Conversation structure
1. Add `tool_list: List[Tool]` field to Conversation
2. Keep existing `exchanges: List[Exchange]` but with new Exchange structure
3. Preserve other Conversation fields (system_prompt, version, etc.)

### Step 4: Update serialization methods
1. Update `to_dict()` method to handle new union types and tool_list
2. Update `from_dict()` method to reconstruct new data structures
3. Backwards compatibility is NOT needed.

### Step 5: Migration considerations
- The current ToolCall structure conflates tool use requests and results
- New structure separates tool requests (ToolUse) from results (ToolUseResult)
- Tool calls will be split across exchanges: request in one exchange's response, results in next exchange's prompt

## Summary of Accomplishments

✅ Completed implementation of refactored conversation format:

1. **New data structures defined**: Tool, TextPrompt, ToolUse, ToolUseRequests, ToolUseResult, ToolUseResults, FinalResponse
2. **Exchange updated**: Now uses union types for prompt (TextPrompt | ToolUseResults) and response (FinalResponse | ToolUseRequests)  
3. **Conversation updated**: Added tool_list field, updated to version 2.0
4. **Serialization updated**: Complete rewrite of to_dict() and from_dict() methods to handle new union types and tool_list

The refactoring breaks existing imports (Prompt, Response classes removed) but achieves the goal of properly separating tool use requests from tool use results across exchanges. Tests currently fail due to import errors, which is expected as the old types were removed.
