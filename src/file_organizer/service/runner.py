# Copyright 2026 Ioannis Roumeliotis
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
Background runner for the file watcher service.
This script is spawned as a separate process by the CLI.
"""

import sys
from pathlib import Path


def setup_ai_provider(provider_name: str, model_name: str = None, base_url: str = None):
    """Setup AI provider based on config."""
    
    provider_name = provider_name.lower()
    
    try:
        if provider_name == "openai":
            from file_organizer.ai.providers.openai import OpenaiProvider
            provider = OpenaiProvider()
            provider.initialize_model(model=model_name or "gpt-4o-mini")
            return provider
        
        elif provider_name == "anthropic":
            from file_organizer.ai.providers.anthropic import AnthropicProvider
            provider = AnthropicProvider()
            provider.initialize_model(model=model_name or "claude-sonnet-4-20250514")
            return provider
        
        elif provider_name == "gemini":
            from file_organizer.ai.providers.gemini import GeminiProvider
            provider = GeminiProvider()
            provider.initialize_model(model=model_name or "gemini-2.0-flash")
            return provider
        
        elif provider_name == "deepinfra":
            from file_organizer.ai.providers.deepinfra import DeepInfraProvider
            provider = DeepInfraProvider()
            provider.initialize_model(model=model_name or "google/gemma-3-27b-it")
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
        
        elif provider_name == "ollama":
            from file_organizer.ai.providers.ollama import OllamaProvider
            provider = OllamaProvider()
            provider.initialize_model(model=model_name or "llama3.1:8b")
            return provider
        
        elif provider_name in ["openai-compatible", "local"]:
            if not base_url:
                raise ValueError("base_url is required for openai-compatible provider")
            from file_organizer.ai.providers.openai_compatible import OpenAICompatibleProvider
            provider = OpenAICompatibleProvider()
            provider.initialize_model(
                model=model_name or "local-model",
                base_url=base_url
            )
            return provider
        
        else:
            raise ValueError(f"Unknown provider: {provider_name}")
    
    except ConnectionError as e:
        raise RuntimeError(f"Connection Error: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to initialize {provider_name}: {e}")


def run_worker():
    """Main entry point for the background service."""
    
    from file_organizer.service.watcher import (
        load_service_config,
        setup_logging,
        FileWatcherService
    )
    from file_organizer.core.models import FoldersToClassify, FolderObject
    
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
            config.get("base_url")
        )
        
        if isinstance(ai_provider, str):
            logger.error(f"Failed to initialize AI provider: {ai_provider}")
            sys.exit(1)
        
        # Create service
        service = FileWatcherService(
            watch_directory=Path(config["watch_directory"]),
            folders_config=folders_config,
            ai_provider=ai_provider,
            cooldown_seconds=config.get("cooldown_seconds", 5),
            configuration_name=config.get("configuration_name"),
            dir_depth_search=config.get("dir_depth_search")
        )
        
        # Run the service (blocking)
        service.run()
        
    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_worker()