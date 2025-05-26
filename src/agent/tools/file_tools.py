import os
import glob
from typing import List, Dict, Any, Optional

from .tool import Tool


class FileTools:
    """
    Collection of file operation tools.
    This class is kept for backward compatibility.
    """

    @staticmethod
    def read_file(file_path: str) -> str:
        """
        Read the contents of a file.

        Args:
            file_path: Path to the file to read

        Returns:
            The contents of the file as a string
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    @staticmethod
    def write_file(file_path: str, content: str) -> bool:
        """
        Write content to a file.

        Args:
            file_path: Path to the file to write
            content: Content to write to the file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Error writing to file {file_path}: {e}")
            return False

    @staticmethod
    def list_files(directory: str, pattern: Optional[str] = None) -> List[str]:
        """
        List files in a directory, optionally filtered by a pattern.

        Args:
            directory: Directory to list files from
            pattern: Optional glob pattern to filter files

        Returns:
            List of file paths
        """
        if pattern:
            return glob.glob(os.path.join(directory, pattern))
        else:
            return [os.path.join(directory, f) for f in os.listdir(directory)
                   if os.path.isfile(os.path.join(directory, f))]

    @staticmethod
    def file_exists(file_path: str) -> bool:
        """
        Check if a file exists.

        Args:
            file_path: Path to the file to check

        Returns:
            True if the file exists, False otherwise
        """
        return os.path.isfile(file_path)


class ListFilesTool(Tool):
    """Tool for listing files in a directory."""

    def __init__(self, base_directory: str = "."):
        self.base_directory = base_directory

    @property
    def name(self) -> str:
        return "list_files"

    @property
    def description(self) -> str:
        return "List files in a directory"

    def execute(self, directory: str = ".", pattern: Optional[str] = None) -> Dict[str, Any]:
        """
        List files in a directory.

        Args:
            directory: Directory to list files from
            pattern: Optional glob pattern to filter files

        Returns:
            Dictionary with the list of files
        """
        try:
            # Resolve directory relative to base_directory
            full_directory = os.path.join(self.base_directory, directory)
            
            if pattern:
                files = glob.glob(os.path.join(full_directory, pattern))
                # Return relative paths from base_directory
                files = [os.path.relpath(f, self.base_directory) for f in files]
            else:
                files = [os.path.join(directory, f) for f in os.listdir(full_directory)
                       if os.path.isfile(os.path.join(full_directory, f))]

            return {
                "success": True,
                "files": files
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }


class ReadFileTool(Tool):
    """Tool for reading the contents of a file."""

    def __init__(self, base_directory: str = "."):
        self.base_directory = base_directory

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the contents of a file"

    def execute(self, file_path: str) -> Dict[str, Any]:
        """
        Read the contents of a file.

        Args:
            file_path: Path to the file to read

        Returns:
            Dictionary with the file content
        """
        try:
            # Resolve file_path relative to base_directory
            full_file_path = os.path.join(self.base_directory, file_path)
            
            if not os.path.isfile(full_file_path):
                return {
                    "success": False,
                    "message": f"File does not exist: {file_path}"
                }

            with open(full_file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return {
                "success": True,
                "content": content
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }


class WriteFileTool(Tool):
    """Tool for writing content to a file."""

    def __init__(self, base_directory: str = "."):
        self.base_directory = base_directory

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to a file"

    def execute(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        Write content to a file.

        Args:
            file_path: Path to the file to write
            content: Content to write to the file

        Returns:
            Dictionary with the result of the operation
        """
        try:
            # Resolve file_path relative to base_directory
            full_file_path = os.path.join(self.base_directory, file_path)
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(full_file_path), exist_ok=True)

            with open(full_file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return {
                "success": True,
                "message": f"File written: {file_path}"
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }
