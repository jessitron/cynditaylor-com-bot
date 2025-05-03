import json
import re
from typing import Dict, Any, Optional

from .provider import LLMProvider


class FrankProvider(LLMProvider):
    """
    Implementation of LLMProvider for the 'Frank' LLM.
    This is a local implementation that simulates an LLM by providing realistic responses
    to specific prompts used in the website agent.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "default"):
        """
        Initialize the Frank LLM provider.

        Args:
            api_key: API key for authentication (not required for Frank)
            model: The model to use for generation
        """
        self.model = model

    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate a response from Frank LLM based on the prompt.

        Args:
            prompt: The input prompt to send to the LLM
            **kwargs: Additional parameters for the API call

        Returns:
            The generated text response from the LLM
        """
        # Check if this is an analysis prompt
        if "analyze the following instruction" in prompt.lower():
            return self._handle_analysis_prompt(prompt)

        # Check if this is a modification prompt
        elif "modify the following file" in prompt.lower():
            return self._handle_modification_prompt(prompt)

        # Check if this is a summary prompt
        elif "provide a concise, human-readable summary" in prompt.lower():
            return self._handle_summary_prompt(prompt)

        # Default response for unrecognized prompts
        return "I'm not sure how to respond to this prompt. Please provide a specific instruction for the website agent."

    def _handle_analysis_prompt(self, prompt: str) -> str:
        """Handle prompts asking to analyze an instruction."""
        # Extract the instruction from the prompt
        instruction_match = re.search(r"INSTRUCTION:\s*(.*?)(?:\n\n|$)", prompt, re.DOTALL)
        if not instruction_match:
            return json.dumps({
                "files_to_modify": [],
                "actions": [],
                "reasoning": "Could not extract instruction from prompt"
            })

        instruction = instruction_match.group(1).strip()

        # Check for common instruction patterns and provide appropriate responses
        if "hero section" in instruction.lower() or "tagline" in instruction.lower():
            return json.dumps({
                "files_to_modify": ["index.html"],
                "actions": ["Update the hero section with the new tagline"],
                "reasoning": "The instruction asks to update the hero section with a new tagline, which is located in index.html"
            })

        elif "contact" in instruction.lower() or "email" in instruction.lower():
            return json.dumps({
                "files_to_modify": ["contact.html"],
                "actions": ["Update the contact information with the new email address"],
                "reasoning": "The instruction asks to update contact information, which is located in contact.html"
            })

        elif "gallery" in instruction.lower() or "image" in instruction.lower() or "painting" in instruction.lower():
            return json.dumps({
                "files_to_modify": ["gallery.html"],
                "actions": ["Add or update images in the gallery"],
                "reasoning": "The instruction involves gallery content, which is managed in gallery.html"
            })

        elif "style" in instruction.lower() or "color" in instruction.lower() or "design" in instruction.lower():
            return json.dumps({
                "files_to_modify": ["css/styles.css"],
                "actions": ["Update the styling according to the instruction"],
                "reasoning": "The instruction involves styling changes, which are defined in css/styles.css"
            })

        # Default response for other instructions
        return json.dumps({
            "files_to_modify": ["index.html"],
            "actions": ["Make changes according to the instruction"],
            "reasoning": f"The instruction '{instruction}' seems to require changes to the main page"
        })

    def _handle_modification_prompt(self, prompt: str) -> str:
        """Handle prompts asking to modify a file."""
        # Extract the file path and action from the prompt
        file_match = re.search(r"FILE:\s*(.*?)(?:\n|$)", prompt)
        action_match = re.search(r"ACTION:\s*(.*?)(?:\n|$)", prompt)
        content_match = re.search(r"```\s*(.*?)```", prompt, re.DOTALL)

        if not (file_match and action_match and content_match):
            return "Could not extract necessary information from the prompt."

        file_path = file_match.group(1).strip()
        action = action_match.group(1).strip()
        current_content = content_match.group(1).strip()

        # Handle different file types
        if file_path.endswith(".html"):
            return self._modify_html_content(file_path, action, current_content)
        elif file_path.endswith(".css"):
            return self._modify_css_content(file_path, action, current_content)
        else:
            # For other file types, just return the original content
            return current_content

    def _modify_html_content(self, file_path: str, action: str, content: str) -> str:
        """Modify HTML content based on the action."""
        if "hero section" in action.lower() or "tagline" in action.lower():
            # Update the hero section with a new tagline
            if "<div class=\"hero-content\">" in content:
                # Find the hero content section
                hero_pattern = r"(<div class=\"hero-content\">.*?<p>)(.*?)(</p>.*?</div>)"
                modified_content = re.sub(
                    hero_pattern,
                    r"\1Bringing your memories to life through art\3",
                    content,
                    flags=re.DOTALL
                )
                return modified_content

        elif "contact" in action.lower() or "email" in action.lower():
            # Update email address
            if "info@cynditaylor.com" in content:
                return content.replace("info@cynditaylor.com", "contact@cynditaylor.com")

        # If no specific modification is matched, return the original content
        return content

    def _modify_css_content(self, file_path: str, action: str, content: str) -> str:
        """Modify CSS content based on the action."""
        if "style" in action.lower() or "color" in action.lower():
            # Update primary color
            if "--primary-color:" in content:
                return content.replace("--primary-color: #3a3a3a;", "--primary-color: #4a4a4a;")

        # If no specific modification is matched, return the original content
        return content

    def _handle_summary_prompt(self, prompt: str) -> str:
        """Handle prompts asking for a summary of execution."""
        # Extract the instruction and result from the prompt
        instruction_match = re.search(r"INSTRUCTION:\s*(.*?)(?:\n\n|$)", prompt, re.DOTALL)
        result_match = re.search(r"EXECUTION RESULT:\s*(.*?)(?:\n\n|$)", prompt, re.DOTALL)

        if not (instruction_match and result_match):
            return "I executed the instruction, but couldn't generate a detailed summary."

        instruction = instruction_match.group(1).strip()
        result_json = result_match.group(1).strip()

        try:
            # Try to parse the result as JSON
            result = json.loads(result_json)

            # Generate a summary based on the results
            successful_files = [r["file"] for r in result.get("results", [])
                               if r.get("success") and "file" in r]

            if successful_files:
                file_list = ", ".join(successful_files)
                return f"I successfully executed the instruction: '{instruction}'. Modified the following files: {file_list}. The changes have been committed to the repository."
            else:
                return f"I attempted to execute the instruction: '{instruction}', but no files were successfully modified."

        except json.JSONDecodeError:
            # If we can't parse the JSON, provide a generic summary
            return f"I executed the instruction: '{instruction}'. The changes have been applied to the website."

    def get_name(self) -> str:
        """
        Get the name of the LLM provider.

        Returns:
            The name of the LLM provider
        """
        return f"Frank ({self.model})"
