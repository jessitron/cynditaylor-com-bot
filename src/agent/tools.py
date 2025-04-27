"""
Tools for the Cyndi Taylor Website Bot.

This module defines the tools that the agent can use to perform actions,
such as modifying website code, interacting with GitHub, etc.
"""

import logging
import os
import subprocess
from typing import Dict, Any, List, Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def git_pull(repo_path: str) -> Dict[str, Any]:
    """
    Pull the latest changes from the GitHub repository.
    
    Args:
        repo_path: Path to the local repository
        
    Returns:
        Dictionary with the result of the operation
    """
    try:
        # Change to the repository directory
        os.chdir(repo_path)
        
        # Run git pull
        result = subprocess.run(
            ["git", "pull"],
            capture_output=True,
            text=True,
            check=True
        )
        
        return {
            "success": True,
            "output": result.stdout,
            "error": result.stderr
        }
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "output": e.stdout,
            "error": e.stderr
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def git_push(repo_path: str, commit_message: str) -> Dict[str, Any]:
    """
    Commit and push changes to the GitHub repository.
    
    Args:
        repo_path: Path to the local repository
        commit_message: Commit message
        
    Returns:
        Dictionary with the result of the operation
    """
    try:
        # Change to the repository directory
        os.chdir(repo_path)
        
        # Add all changes
        add_result = subprocess.run(
            ["git", "add", "."],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Commit changes
        commit_result = subprocess.run(
            ["git", "commit", "-m", commit_message],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Push changes
        push_result = subprocess.run(
            ["git", "push"],
            capture_output=True,
            text=True,
            check=True
        )
        
        return {
            "success": True,
            "add_output": add_result.stdout,
            "commit_output": commit_result.stdout,
            "push_output": push_result.stdout,
            "error": add_result.stderr + commit_result.stderr + push_result.stderr
        }
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "output": e.stdout,
            "error": e.stderr
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def modify_file(file_path: str, content: str) -> Dict[str, Any]:
    """
    Modify a file in the website repository.
    
    Args:
        file_path: Path to the file to modify
        content: New content for the file
        
    Returns:
        Dictionary with the result of the operation
    """
    try:
        with open(file_path, 'w') as f:
            f.write(content)
            
        return {
            "success": True,
            "file_path": file_path
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def read_file(file_path: str) -> Dict[str, Any]:
    """
    Read a file from the website repository.
    
    Args:
        file_path: Path to the file to read
        
    Returns:
        Dictionary with the result of the operation
    """
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
        return {
            "success": True,
            "file_path": file_path,
            "content": content
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# Dictionary of available tools
AVAILABLE_TOOLS = {
    "git_pull": git_pull,
    "git_push": git_push,
    "modify_file": modify_file,
    "read_file": read_file
}
