import os
import glob
from typing import List, Optional


class FileTools:
    """
    Tools for file operations that the agent can use.
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
