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

Put the plan here. Do not implement it yet.
