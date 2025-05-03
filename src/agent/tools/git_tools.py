import os
import subprocess
from typing import Tuple, Optional


class GitTools:
    """
    Tools for Git operations that the agent can use.
    """
    
    @staticmethod
    def clone_repo(repo_url: str, target_dir: str) -> Tuple[bool, str]:
        """
        Clone a Git repository.
        
        Args:
            repo_url: URL of the repository to clone
            target_dir: Directory to clone the repository into
            
        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ["git", "clone", repo_url, target_dir],
                check=True,
                capture_output=True,
                text=True
            )
            return True, f"Repository cloned successfully: {result.stdout}"
        except subprocess.CalledProcessError as e:
            return False, f"Error cloning repository: {e.stderr}"
    
    @staticmethod
    def commit_changes(repo_dir: str, message: str) -> Tuple[bool, str]:
        """
        Commit changes in a Git repository.
        
        Args:
            repo_dir: Directory of the repository
            message: Commit message
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Add all changes
            add_result = subprocess.run(
                ["git", "add", "."],
                cwd=repo_dir,
                check=True,
                capture_output=True,
                text=True
            )
            
            # Commit changes
            commit_result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=repo_dir,
                check=True,
                capture_output=True,
                text=True
            )
            
            return True, f"Changes committed successfully: {commit_result.stdout}"
        except subprocess.CalledProcessError as e:
            return False, f"Error committing changes: {e.stderr}"
    
    @staticmethod
    def push_changes(repo_dir: str, branch: str = "main") -> Tuple[bool, str]:
        """
        Push changes to a remote Git repository.
        
        Args:
            repo_dir: Directory of the repository
            branch: Branch to push to
            
        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ["git", "push", "origin", branch],
                cwd=repo_dir,
                check=True,
                capture_output=True,
                text=True
            )
            return True, f"Changes pushed successfully: {result.stdout}"
        except subprocess.CalledProcessError as e:
            return False, f"Error pushing changes: {e.stderr}"
    
    @staticmethod
    def pull_latest(repo_dir: str, branch: str = "main") -> Tuple[bool, str]:
        """
        Pull the latest changes from a remote Git repository.
        
        Args:
            repo_dir: Directory of the repository
            branch: Branch to pull from
            
        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ["git", "pull", "origin", branch],
                cwd=repo_dir,
                check=True,
                capture_output=True,
                text=True
            )
            return True, f"Latest changes pulled successfully: {result.stdout}"
        except subprocess.CalledProcessError as e:
            return False, f"Error pulling latest changes: {e.stderr}"
