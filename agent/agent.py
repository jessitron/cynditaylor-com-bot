import os
import json
from typing import Dict, Any, List, Optional, Tuple

from llm.provider import LLMProvider
from agent.tools.file_tools import FileTools
from agent.tools.git_tools import GitTools


class WebsiteAgent:
    """
    Agent that can modify code in the cynditaylor-com website.
    """
    
    def __init__(self, llm_provider: LLMProvider, website_dir: str = "cynditaylor-com"):
        """
        Initialize the website agent.
        
        Args:
            llm_provider: The LLM provider to use for generating responses
            website_dir: Directory containing the website code
        """
        self.llm = llm_provider
        self.website_dir = website_dir
        self.file_tools = FileTools()
        self.git_tools = GitTools()
        
        # Ensure the website directory exists
        if not os.path.isdir(website_dir):
            raise ValueError(f"Website directory '{website_dir}' does not exist")
    
    def process_instruction(self, instruction: str) -> Dict[str, Any]:
        """
        Process an instruction to modify the website.
        
        Args:
            instruction: The instruction to process
            
        Returns:
            A dictionary containing the result of processing the instruction
        """
        # Step 1: Analyze the instruction using the LLM
        analysis_prompt = f"""
        You are an agent that modifies code in the cynditaylor-com website.
        Please analyze the following instruction and determine what changes need to be made:
        
        INSTRUCTION:
        {instruction}
        
        Respond with a JSON object containing:
        1. "files_to_modify": List of files that need to be modified
        2. "actions": List of specific actions to take for each file
        3. "reasoning": Your reasoning for these changes
        """
        
        analysis_response = self.llm.generate(analysis_prompt)
        
        # In a real implementation, we would parse the JSON response
        # For now, we'll use a placeholder
        try:
            analysis = json.loads(analysis_response)
        except json.JSONDecodeError:
            # If the response is not valid JSON, create a placeholder analysis
            analysis = {
                "files_to_modify": [],
                "actions": [],
                "reasoning": "Could not parse LLM response as JSON"
            }
        
        # Step 2: Execute the changes
        results = []
        for i, file_path in enumerate(analysis.get("files_to_modify", [])):
            full_path = os.path.join(self.website_dir, file_path)
            
            # Check if the file exists
            if not self.file_tools.file_exists(full_path):
                results.append({
                    "file": file_path,
                    "success": False,
                    "message": f"File does not exist: {file_path}"
                })
                continue
            
            # Get the action for this file
            action = analysis.get("actions", [])[i] if i < len(analysis.get("actions", [])) else None
            if not action:
                results.append({
                    "file": file_path,
                    "success": False,
                    "message": f"No action specified for file: {file_path}"
                })
                continue
            
            # Read the current content
            current_content = self.file_tools.read_file(full_path)
            
            # Generate the modified content using the LLM
            modification_prompt = f"""
            You are an agent that modifies code in the cynditaylor-com website.
            You need to modify the following file according to this action:
            
            FILE: {file_path}
            ACTION: {action}
            
            Current content of the file:
            ```
            {current_content}
            ```
            
            Please provide the complete new content for the file.
            Only output the new content, nothing else.
            """
            
            new_content = self.llm.generate(modification_prompt)
            
            # Write the new content
            success = self.file_tools.write_file(full_path, new_content)
            
            results.append({
                "file": file_path,
                "success": success,
                "message": f"File {'modified' if success else 'failed to modify'}: {file_path}"
            })
        
        # Step 3: Commit the changes (in a real implementation, this might be optional)
        if results and any(r["success"] for r in results):
            commit_message = f"Update website based on instruction: {instruction[:50]}..."
            commit_success, commit_message = self.git_tools.commit_changes(self.website_dir, commit_message)
            
            if commit_success:
                results.append({
                    "action": "commit",
                    "success": True,
                    "message": commit_message
                })
            else:
                results.append({
                    "action": "commit",
                    "success": False,
                    "message": commit_message
                })
        
        return {
            "instruction": instruction,
            "analysis": analysis,
            "results": results,
            "llm_provider": self.llm.get_name()
        }
    
    def execute_instruction(self, instruction: str) -> str:
        """
        Execute an instruction and return a human-readable summary.
        
        Args:
            instruction: The instruction to execute
            
        Returns:
            A human-readable summary of the execution
        """
        result = self.process_instruction(instruction)
        
        # Generate a summary using the LLM
        summary_prompt = f"""
        You are an agent that modifies code in the cynditaylor-com website.
        You have executed an instruction and need to provide a summary of what was done.
        
        INSTRUCTION:
        {instruction}
        
        EXECUTION RESULT:
        {json.dumps(result, indent=2)}
        
        Please provide a concise, human-readable summary of what was done.
        """
        
        summary = self.llm.generate(summary_prompt)
        return summary
