import os
from typing import Dict, Any


class Config:
    """
    Configuration settings for the application.
    """

    # LLM settings
    LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "frank")
    FRANK_MODEL = os.environ.get("FRANK_MODEL", "default")

    # Website settings
    WEBSITE_DIR = os.environ.get("WEBSITE_DIR", "cynditaylor-com")

    # Git settings
    GIT_REPO_URL = os.environ.get("GIT_REPO_URL", "https://github.com/username/cynditaylor-com.git")
    GIT_BRANCH = os.environ.get("GIT_BRANCH", "main")

    @classmethod
    def get_llm_config(cls) -> Dict[str, Any]:
        """
        Get the configuration for the LLM provider.

        Returns:
            Dictionary of LLM configuration settings
        """
        if cls.LLM_PROVIDER.lower() == "frank":
            return {
                "provider": "frank",
                "model": cls.FRANK_MODEL
            }
        else:
            raise ValueError(f"Unsupported LLM provider: {cls.LLM_PROVIDER}")

    @classmethod
    def get_website_config(cls) -> Dict[str, Any]:
        """
        Get the configuration for the website.

        Returns:
            Dictionary of website configuration settings
        """
        return {
            "website_dir": cls.WEBSITE_DIR,
            "git_repo_url": cls.GIT_REPO_URL,
            "git_branch": cls.GIT_BRANCH
        }
