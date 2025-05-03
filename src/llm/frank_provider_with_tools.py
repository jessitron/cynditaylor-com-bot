import json
import re
from typing import Dict, Any, List, Optional, Callable

from .provider import LLMProvider


class ToolDefinition:
    """Definition of a tool that the LLM can use."""
    
    def __init__(self, name: str, description: str, function: Callable):
        """
        Initialize a tool definition.
        
        Args:
            name: Name of the tool
            description: Description of what the tool does
            function: Function to call when the tool is used
        """
        self.name = name
        self.description = description
        self.function = function


class FrankProviderWithTools(LLMProvider):
    """
    Implementation of LLMProvider for the 'Frank' LLM with tool usage.
    This simulates an LLM that can request to use tools to complete tasks.
    """
    
    def __init__(self, model: str = "default", max_iterations: int = 10):
        """
        Initialize the Frank LLM provider with tools.
        
        Args:
            model: The model to use for generation
            max_iterations: Maximum number of iterations for tool usage
        """
        self.model = model
        self.max_iterations = max_iterations
        self.tools = {}
        self.conversation_history = []
    
    def register_tool(self, tool: ToolDefinition):
        """
        Register a tool that the LLM can use.
        
        Args:
            tool: The tool definition to register
        """
        self.tools[tool.name] = tool
    
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate a response from Frank LLM based on the prompt.
        
        Args:
            prompt: The input prompt to send to the LLM
            **kwargs: Additional parameters for the API call
            
        Returns:
            The generated text response from the LLM
        """
        # Reset conversation history for a new prompt
        self.conversation_history = []
        
        # Add the initial prompt to the conversation history
        self.conversation_history.append({"role": "user", "content": prompt})
        
        # Start the conversation loop
        for i in range(self.max_iterations):
            # Generate a response based on the conversation history
            response = self._generate_response()
            
            # Add the response to the conversation history
            self.conversation_history.append({"role": "assistant", "content": response})
            
            # Check if the response contains a tool call
            tool_call = self._extract_tool_call(response)
            if tool_call:
                # Execute the tool
                tool_name = tool_call["name"]
                tool_args = tool_call["arguments"]
                
                if tool_name in self.tools:
                    tool_result = self.tools[tool_name].function(**tool_args)
                    
                    # Add the tool result to the conversation history
                    self.conversation_history.append({
                        "role": "tool",
                        "name": tool_name,
                        "content": json.dumps(tool_result)
                    })
                else:
                    # Tool not found
                    self.conversation_history.append({
                        "role": "tool",
                        "name": tool_name,
                        "content": json.dumps({"error": f"Tool '{tool_name}' not found"})
                    })
            else:
                # No tool call, return the final response
                return response
        
        # If we reach the maximum number of iterations, return the last response
        return self.conversation_history[-1]["content"]
    
    def _generate_response(self) -> str:
        """
        Generate a response based on the conversation history.
        
        Returns:
            The generated response
        """
        # Get the last user message
        last_user_message = None
        for message in reversed(self.conversation_history):
            if message["role"] == "user":
                last_user_message = message["content"]
                break
        
        if not last_user_message:
            return "I don't have any instructions to work with."
        
        # Check if this is the first response
        is_first_response = all(message["role"] != "assistant" for message in self.conversation_history)
        
        # If this is the first response, analyze the instruction
        if is_first_response:
            return self._handle_initial_instruction(last_user_message)
        
        # Check if we have tool results in the history
        tool_results = [message for message in self.conversation_history if message["role"] == "tool"]
        
        if tool_results:
            # Process the tool results
            return self._handle_tool_results(tool_results[-1], last_user_message)
        
        # Default response
        return "I need more information to proceed."
    
    def _handle_initial_instruction(self, instruction: str) -> str:
        """
        Handle the initial instruction from the user.
        
        Args:
            instruction: The user's instruction
            
        Returns:
            The response with potential tool calls
        """
        # Extract the actual instruction from the prompt
        instruction_match = re.search(r"INSTRUCTION:\s*(.*?)(?:\n\n|$)", instruction, re.DOTALL)
        if instruction_match:
            instruction = instruction_match.group(1).strip()
        
        # Determine what files we need to look at
        if "hero section" in instruction.lower() or "tagline" in instruction.lower():
            return """I'll help you update the hero section with a new tagline. First, I need to see what files are available in the website directory.

```tool
{
  "name": "list_files",
  "arguments": {
    "directory": "."
  }
}
```"""
        
        elif "contact" in instruction.lower() or "email" in instruction.lower():
            return """I'll help you update the contact information. First, I need to see what files are available in the website directory.

```tool
{
  "name": "list_files",
  "arguments": {
    "directory": "."
  }
}
```"""
        
        elif "gallery" in instruction.lower() or "image" in instruction.lower() or "painting" in instruction.lower():
            return """I'll help you update the gallery. First, I need to see what files are available in the website directory.

```tool
{
  "name": "list_files",
  "arguments": {
    "directory": "."
  }
}
```"""
        
        elif "style" in instruction.lower() or "color" in instruction.lower() or "design" in instruction.lower():
            return """I'll help you update the styling. First, I need to see what files are available in the website directory.

```tool
{
  "name": "list_files",
  "arguments": {
    "directory": "."
  }
}
```"""
        
        # Default response for other instructions
        return """I'll help you with that. First, I need to see what files are available in the website directory.

```tool
{
  "name": "list_files",
  "arguments": {
    "directory": "."
  }
}
```"""
    
    def _handle_tool_results(self, tool_result: Dict[str, Any], instruction: str) -> str:
        """
        Handle the results of a tool call.
        
        Args:
            tool_result: The result of the tool call
            instruction: The original instruction
            
        Returns:
            The next response with potential tool calls
        """
        tool_name = tool_result["name"]
        content = json.loads(tool_result["content"])
        
        # Handle list_files results
        if tool_name == "list_files":
            files = content.get("files", [])
            
            # Look for specific files based on the instruction
            if "hero section" in instruction.lower() or "tagline" in instruction.lower():
                if "index.html" in files:
                    return """I found the index.html file, which likely contains the hero section. Let me read its contents.

```tool
{
  "name": "read_file",
  "arguments": {
    "file_path": "index.html"
  }
}
```"""
            
            elif "contact" in instruction.lower() or "email" in instruction.lower():
                if "contact.html" in files:
                    return """I found the contact.html file, which likely contains the contact information. Let me read its contents.

```tool
{
  "name": "read_file",
  "arguments": {
    "file_path": "contact.html"
  }
}
```"""
            
            elif "gallery" in instruction.lower():
                if "gallery.html" in files:
                    return """I found the gallery.html file. Let me read its contents.

```tool
{
  "name": "read_file",
  "arguments": {
    "file_path": "gallery.html"
  }
}
```"""
            
            elif "style" in instruction.lower() or "color" in instruction.lower():
                if "css/styles.css" in files:
                    return """I found the styles.css file. Let me read its contents.

```tool
{
  "name": "read_file",
  "arguments": {
    "file_path": "css/styles.css"
  }
}
```"""
            
            # Default to index.html if no specific file is identified
            if "index.html" in files:
                return """I found the index.html file. Let me read its contents to understand the website structure.

```tool
{
  "name": "read_file",
  "arguments": {
    "file_path": "index.html"
  }
}
```"""
            
            return "I couldn't find any relevant files to modify."
        
        # Handle read_file results
        elif tool_name == "read_file":
            file_path = next((arg for message in self.conversation_history 
                             if message["role"] == "assistant" 
                             for arg in re.findall(r'"file_path":\s*"([^"]+)"', message["content"])), None)
            
            if not file_path:
                return "I couldn't determine which file I just read."
            
            file_content = content.get("content", "")
            
            # Process based on file type and instruction
            if file_path.endswith(".html"):
                if "hero section" in instruction.lower() or "tagline" in instruction.lower():
                    # Look for the hero section in the HTML
                    hero_match = re.search(r'<div class="hero-content">.*?<p>(.*?)</p>', file_content, re.DOTALL)
                    if hero_match:
                        current_tagline = hero_match.group(1).strip()
                        new_tagline = "Bringing your memories to life through art"
                        
                        # Extract the new tagline from the instruction if available
                        tagline_match = re.search(r"tagline:?\s*['\"](.*?)['\"]", instruction)
                        if tagline_match:
                            new_tagline = tagline_match.group(1).strip()
                        
                        # Modify the content
                        modified_content = re.sub(
                            r'(<div class="hero-content">.*?<p>)(.*?)(</p>)',
                            f'\\1{new_tagline}\\3',
                            file_content,
                            flags=re.DOTALL
                        )
                        
                        return f"""I found the hero section with the current tagline: "{current_tagline}".
I'll update it to: "{new_tagline}".

Here's my proposed change:

```tool
{{
  "name": "write_file",
  "arguments": {{
    "file_path": "{file_path}",
    "content": {json.dumps(modified_content)}
  }}
}}
```"""
                
                elif "contact" in instruction.lower() or "email" in instruction.lower():
                    # Look for email addresses in the HTML
                    email_match = re.search(r'mailto:(.*?)[\'"]', file_content)
                    if email_match:
                        current_email = email_match.group(1).strip()
                        new_email = "contact@cynditaylor.com"
                        
                        # Extract the new email from the instruction if available
                        email_extract = re.search(r"email:?\s*['\"](.*?)['\"]", instruction)
                        if email_extract:
                            new_email = email_extract.group(1).strip()
                        
                        # Modify the content
                        modified_content = file_content.replace(f'mailto:{current_email}', f'mailto:{new_email}')
                        modified_content = modified_content.replace(current_email, new_email)
                        
                        return f"""I found the contact information with the current email: "{current_email}".
I'll update it to: "{new_email}".

Here's my proposed change:

```tool
{{
  "name": "write_file",
  "arguments": {{
    "file_path": "{file_path}",
    "content": {json.dumps(modified_content)}
  }}
}}
```"""
            
            elif file_path.endswith(".css") and ("style" in instruction.lower() or "color" in instruction.lower()):
                # Look for color definitions in the CSS
                primary_color_match = re.search(r'--primary-color:\s*(#[0-9a-fA-F]{6});', file_content)
                if primary_color_match:
                    current_color = primary_color_match.group(1).strip()
                    new_color = "#4a4a4a"
                    
                    # Extract the new color from the instruction if available
                    color_extract = re.search(r"color:?\s*['\"](#[0-9a-fA-F]{6})['\"]", instruction)
                    if color_extract:
                        new_color = color_extract.group(1).strip()
                    
                    # Modify the content
                    modified_content = file_content.replace(f'--primary-color: {current_color};', f'--primary-color: {new_color};')
                    
                    return f"""I found the primary color definition with the current value: "{current_color}".
I'll update it to: "{new_color}".

Here's my proposed change:

```tool
{{
  "name": "write_file",
  "arguments": {{
    "file_path": "{file_path}",
    "content": {json.dumps(modified_content)}
  }}
}}
```"""
            
            return f"I've analyzed the file {file_path}, but I'm not sure what changes to make based on the instruction: '{instruction}'."
        
        # Handle write_file results
        elif tool_name == "write_file":
            file_path = next((arg for message in self.conversation_history 
                             if message["role"] == "assistant" 
                             for arg in re.findall(r'"file_path":\s*"([^"]+)"', message["content"])), None)
            
            if content.get("success", False):
                return f"""I've successfully updated the file {file_path} according to the instruction.

Now I'll commit the changes to the repository.

```tool
{{
  "name": "commit_changes",
  "arguments": {{
    "message": "Update {file_path} based on instruction: {instruction[:50]}..."
  }}
}}
```"""
            else:
                return f"I tried to update the file {file_path}, but there was an error: {content.get('message', 'Unknown error')}."
        
        # Handle commit_changes results
        elif tool_name == "commit_changes":
            if content.get("success", False):
                return f"""I've successfully committed the changes to the repository with the message: "{content.get('message', '')}".

The task has been completed successfully. Here's a summary of what I did:

1. Analyzed the instruction: "{instruction}"
2. Identified the relevant files to modify
3. Made the necessary changes
4. Committed the changes to the repository

Is there anything else you'd like me to help with?"""
            else:
                return f"I tried to commit the changes, but there was an error: {content.get('message', 'Unknown error')}."
        
        # Default response for unknown tool results
        return f"I received the result of the {tool_name} tool, but I'm not sure how to proceed. Can you provide more specific instructions?"
    
    def _extract_tool_call(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Extract a tool call from the response.
        
        Args:
            response: The response to extract the tool call from
            
        Returns:
            A dictionary containing the tool name and arguments, or None if no tool call is found
        """
        tool_match = re.search(r'```tool\s*(.*?)```', response, re.DOTALL)
        if not tool_match:
            return None
        
        try:
            tool_json = json.loads(tool_match.group(1))
            return {
                "name": tool_json.get("name", ""),
                "arguments": tool_json.get("arguments", {})
            }
        except json.JSONDecodeError:
            return None
    
    def get_name(self) -> str:
        """
        Get the name of the LLM provider.
        
        Returns:
            The name of the LLM provider
        """
        return f"Frank with Tools ({self.model})"
