"""
Background runner for the file watcher service.
This script is spawned as a separate process by the CLI.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from file_organizer.service.watcher import (
    load_service_config,
    get_log_file,
    setup_logging,
    FileWatcherService
)
from file_organizer.core.models import FoldersToClassify, FolderObject


def setup_ai_provider(provider_name: str, model_name: str = None, base_url:str = None):
    """Setup AI provider based on config."""
    if provider_name.lower() == "openai":
        from file_organizer.ai.providers.openai import OpenaiProvider
        provider = OpenaiProvider()
        provider.initialize_model(model=model_name or "gpt-4o-mini")
        return provider
    elif provider_name.lower() == "deepinfra":
        from file_organizer.ai.providers.deepinfra import DeepInfraProvider
        provider = DeepInfraProvider()
        provider.initialize_model(model=model_name or "google/gemma-3-27b-it")
        return provider
    elif provider_name.lower() == "anthropic":
        from file_organizer.ai.providers.anthropic import AnthropicProvider
        provider = AnthropicProvider()
        provider.initialize_model(model=model_name or "claude-sonnet-4-20250514")
        return provider
    elif provider_name.lower() == "gemini":
        from file_organizer.ai.providers.gemini import GeminiProvider
        provider = GeminiProvider()
        provider.initialize_model(model=model_name or "gemini-2.0-flash")
        return provider
    elif provider_name == "ollama":
        if not model_name:
            return "Model Name is required for Ollama, Make sure model is installed."
        from file_organizer.ai.providers.ollama import OllamaProvider
        provider = OllamaProvider()
        provider.initialize_model(model=model_name)
        return provider
    
    elif provider_name == "groq":
        from file_organizer.ai.providers.groq import GroqProvider
        provider = GroqProvider()
        provider.initialize_model(model=model_name or "llama-3.1-8b-instant")
        return provider
    
    elif provider_name == "mistral":
        from file_organizer.ai.providers.mistral import MistralProvider
        provider = MistralProvider()
        provider.initialize_model(model=model_name or "mistral-small-latest")
        return provider
    
    elif provider_name == "cohere":
        from file_organizer.ai.providers.cohere import CohereProvider
        provider = CohereProvider()
        provider.initialize_model(model=model_name or "command-r")
        return provider
    
    elif provider_name == "openai-compatible" or provider_name == "local":
        if not model_name or not base_url:
            return "Model name and base URL are required to run openai-compatible providers."
        
        from file_organizer.ai.providers.openai_compatible import OpenAICompatibleProvider
        provider = OpenAICompatibleProvider()
        provider.initialize_model(
            model=model_name,
            base_url=base_url
        )
        return provider
    
    else:
        raise ValueError(f"Unknown provider: {provider_name}")


def main():
    """Main entry point for the background service."""
    
    logger = setup_logging()
    
    # Load configuration
    config = load_service_config()
    
    if not config:
        logger.error("No service configuration found. Cannot start.")
        sys.exit(1)
    
    try:
        # Rebuild FoldersToClassify from config
        folders_config = FoldersToClassify(
            folders=[
                FolderObject(
                    folder_path=Path(f["folder_path"]),
                    description=f["description"]
                )
                for f in config["folders"]
            ],
            default_folder=Path(config["default_folder"])
        )
        
        # Setup AI provider
        ai_provider = setup_ai_provider(
            config["provider_name"],
            config.get("model_name"),
            config.get("base_url", None)
        )
        
        # Create service
        service = FileWatcherService(
            watch_directory=Path(config["watch_directory"]),
            folders_config=folders_config,
            ai_provider=ai_provider,
            cooldown_seconds=config.get("cooldown_seconds", 5),
            configuration_name=config.get("configuration_name")
        )
        
        # Run the service (blocking)
        service.run()
        
    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()