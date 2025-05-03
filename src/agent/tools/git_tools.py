import subprocess
from typing import Dict, Any, Tuple

from .tool import Tool


class GitTools:
    """
    Tools for Git operations that the agent can use.
    This class is kept for backward compatibility.
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
            subprocess.run(
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


class CommitChangesTool(Tool):
    """Tool for committing changes to a Git repository."""

    @property
    def name(self) -> str:
        return "commit_changes"

    @property
    def description(self) -> str:
        return "Commit changes to the repository"

    def execute(self, repo_dir: str, message: str) -> Dict[str, Any]:
        """
        Commit changes in a Git repository.

        Args:
            repo_dir: Directory of the repository
            message: Commit message

        Returns:
            Dictionary with the result of the operation
        """
        try:
            # Add all changes
            subprocess.run(
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

            return {
                "success": True,
                "message": f"Changes committed successfully: {commit_result.stdout}"
            }
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "message": f"Error committing changes: {e.stderr}"
            }


class PushChangesTool(Tool):
    """Tool for pushing changes to a remote Git repository."""

    @property
    def name(self) -> str:
        return "push_changes"

    @property
    def description(self) -> str:
        return "Push changes to the remote repository"

    def execute(self, repo_dir: str, branch: str = "main") -> Dict[str, Any]:
        """
        Push changes to a remote Git repository.

        Args:
            repo_dir: Directory of the repository
            branch: Branch to push to

        Returns:
            Dictionary with the result of the operation
        """
        try:
            result = subprocess.run(
                ["git", "push", "origin", branch],
                cwd=repo_dir,
                check=True,
                capture_output=True,
                text=True
            )

            return {
                "success": True,
                "message": f"Changes pushed successfully: {result.stdout}"
            }
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "message": f"Error pushing changes: {e.stderr}"
            }


class CloneRepoTool(Tool):
    """Tool for cloning a Git repository."""

    @property
    def name(self) -> str:
        return "clone_repo"

    @property
    def description(self) -> str:
        return "Clone a Git repository"

    def execute(self, repo_url: str, target_dir: str) -> Dict[str, Any]:
        """
        Clone a Git repository.

        Args:
            repo_url: URL of the repository to clone
            target_dir: Directory to clone the repository into

        Returns:
            Dictionary with the result of the operation
        """
        try:
            result = subprocess.run(
                ["git", "clone", repo_url, target_dir],
                check=True,
                capture_output=True,
                text=True
            )

            return {
                "success": True,
                "message": f"Repository cloned successfully: {result.stdout}"
            }
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "message": f"Error cloning repository: {e.stderr}"
            }


class PullLatestTool(Tool):
    """Tool for pulling the latest changes from a remote Git repository."""

    @property
    def name(self) -> str:
        return "pull_latest"

    @property
    def description(self) -> str:
        return "Pull the latest changes from the remote repository"

    def execute(self, repo_dir: str, branch: str = "main") -> Dict[str, Any]:
        """
        Pull the latest changes from a remote Git repository.

        Args:
            repo_dir: Directory of the repository
            branch: Branch to pull from

        Returns:
            Dictionary with the result of the operation
        """
        try:
            result = subprocess.run(
                ["git", "pull", "origin", branch],
                cwd=repo_dir,
                check=True,
                capture_output=True,
                text=True
            )

            return {
                "success": True,
                "message": f"Latest changes pulled successfully: {result.stdout}"
            }
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "message": f"Error pulling latest changes: {e.stderr}"
            }
