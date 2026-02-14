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

import typer
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import time

from file_organizer.core.scanner import DirectoryScanner
from file_organizer.core.orchestrator import FileOrganizer
from file_organizer.core.executor import OperationExecutor
from file_organizer.core.models import (
    FoldersToClassify,
    FolderObject,
    OperationMode,
    PendingStatus,
    AnalysisResult,
    FileInfo
)
from file_organizer.extractors.registry import ExtractorRegistry
from file_organizer.extractors.tabular_extractor import TabularExtractor
from file_organizer.extractors.text_extractor import TextExtractor
from file_organizer.extractors.document_extractor import DocumentExtractor
from file_organizer.extractors.image_extractor import ImageExtractor
from file_organizer.extractors.video_extractor import VideoExtractor
from file_organizer.extractors.archive_extractor import ArchiveExtractor
from file_organizer.extractors.binary_extractor import BinaryExtractor
from file_organizer.storage.database import get_session, init_database
from file_organizer.storage.repository import ConfigurationRepository, HistoryRepository
from file_organizer.service.watcher import (
    FileWatcherService,
    start_background_service,
    stop_service,
    get_service_status,
    is_service_running,
    get_log_file
)
from datetime import datetime
import subprocess
import warnings
from file_organizer.analyzers.registry import AnalyzerRegistry
from file_organizer.storage.repository import AnalysisRepository

warnings.filterwarnings("ignore", message="Pydantic serializer warnings")
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic.main")


app = typer.Typer(
    name="kypseli",
    help="AI-powered file organization hive"
)
console = Console()


# Initialize database on import
init_database()


def get_operation_mode(mode: str) -> OperationMode:
    """Convert string to OperationMode enum."""
    mode_map = {
        "move": OperationMode.MOVE,
        "copy": OperationMode.COPY,
        "dry_run": OperationMode.DRY_RUN,
        "dry-run": OperationMode.DRY_RUN,
    }
    return mode_map.get(mode.lower(), OperationMode.MOVE)


def create_default_folders(base_path: Path) -> FoldersToClassify:
    """Create default folder configuration."""
    return FoldersToClassify(
        folders=[
            FolderObject(
                folder_path=base_path / "Datasets",
                description="Data files like CSV, Excel, Parquet, Pickles and other tabular data"
            ),
            FolderObject(
                folder_path=base_path / "Documents",
                description="PDFs, Word documents, and other text documents"
            ),
            FolderObject(
                folder_path=base_path / "Code",
                description="Programming and script files like Python, JavaScript, etc."
            ),
            FolderObject(
                folder_path=base_path / "Images",
                description="Image files like PNG, JPG, JPEG, GIF"
            ),
            FolderObject(
                folder_path=base_path / "Videos",
                description="Video files like MP4, MOV, AVI"
            ),
            FolderObject(
                folder_path=base_path / "Archives",
                description="Compressed files like ZIP, TAR, RAR"
            ),
        ],
        default_folder=base_path / "Other"
    )


def setup_extractor_registry() -> ExtractorRegistry:
    """Create and configure the extractor registry."""
    registry = ExtractorRegistry()
    registry.register(TabularExtractor())
    registry.register(TextExtractor())
    registry.register(DocumentExtractor())
    registry.register(ImageExtractor())
    registry.register(VideoExtractor())
    registry.register(ArchiveExtractor())
    registry.register(BinaryExtractor())
    return registry

def register_analyzers(file_info: FileInfo) -> AnalyzerRegistry:

    from file_organizer.analyzers.tabular_analyzer import TabularAnalyzer
    from file_organizer.analyzers.text_analyzer import TextAnalyzer
    from file_organizer.analyzers.document_analyzer import DocumentAnalyzer
    from file_organizer.analyzers.archive_analyzer import ArchiveAnalyzer
    from file_organizer.analyzers.binary_analyzer import BinaryAnalyzer

    
    registry = AnalyzerRegistry()
    registry.register(TabularAnalyzer())
    registry.register(TextAnalyzer())
    registry.register(DocumentAnalyzer())
    registry.register(ArchiveAnalyzer())
    registry.register(BinaryAnalyzer())
    return registry.get_analyzer(file_info)



def setup_ai_provider(provider_name: str, model: Optional[str] = None, base_url: Optional[str] = None):
    """Create and initialize the AI provider."""
    
    provider_name = provider_name.lower()
    try:
        if provider_name == "openai":
            from file_organizer.ai.providers.openai import OpenaiProvider
            provider = OpenaiProvider()
            provider.initialize_model(model=model or "gpt-4o-mini")
            return provider
        
        elif provider_name == "anthropic":
            from file_organizer.ai.providers.anthropic import AnthropicProvider
            provider = AnthropicProvider()
            provider.initialize_model(model=model or "claude-sonnet-4-20250514")
            return provider
        
        elif provider_name == "gemini":
            from file_organizer.ai.providers.gemini import GeminiProvider
            provider = GeminiProvider()
            provider.initialize_model(model=model or "gemini-2.0-flash")
            return provider
        
        elif provider_name == "ollama":
            if not model:
                return "Model Name is required for Ollama, Make sure model is installed."

            from file_organizer.ai.providers.ollama import OllamaProvider
            provider = OllamaProvider()
            provider.initialize_model(model=model)
            return provider
        
        elif provider_name == "groq":
            from file_organizer.ai.providers.groq import GroqProvider
            provider = GroqProvider()
            provider.initialize_model(model=model or "llama-3.1-8b-instant")
            return provider
        
        elif provider_name == "mistral":
            from file_organizer.ai.providers.mistral import MistralProvider
            provider = MistralProvider()
            provider.initialize_model(model=model or "mistral-small-latest")
            return provider
        
        elif provider_name == "cohere":
            from file_organizer.ai.providers.cohere import CohereProvider
            provider = CohereProvider()
            provider.initialize_model(model=model or "command-r")
            return provider
        
        elif provider_name == "openai-compatible" or provider_name == "local":
            if not model or not base_url:
                return "Model name and base URL are required to run openai-compatible providers."
            
            from file_organizer.ai.providers.openai_compatible import OpenAICompatibleProvider
            provider = OpenAICompatibleProvider()
            provider.initialize_model(
                model=model,
                base_url=base_url
            )
            return provider
        
        elif provider_name == "deepinfra":
            from file_organizer.ai.providers.deepinfra import DeepInfraProvider
            provider = DeepInfraProvider()
            provider.initialize_model(model=model or "google/gemma-3-27b-it")
            return provider
        
        else:
            console.print(f"[red]Unknown provider: {provider_name}[/red]")
            raise typer.Exit(1)
        
    except ConnectionError as e:
        return f"Connection Error: {e}"
    
    except Exception as e:
        error_msg = str(e)
        
        # Provide helpful hints based on error type
        if "api_key" in error_msg.lower() or "apikey" in error_msg.lower():
            env_vars = {
                "openai": "OPENAI_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
                "gemini": "GOOGLE_API_KEY",
                "groq": "GROQ_API_KEY",
                "mistral": "MISTRAL_API_KEY",
                "cohere": "COHERE_API_KEY",
                "deepinfra": "DEEPINFRA_API_TOKEN",
            }
            env_var = env_vars.get(provider_name, "API_KEY")
            return f"Error: API key not configured. Set {env_var} environment variable."
        
        return f"Error: {error_msg[:200]}"


def create_folders_interactive(base_path: Path) -> FoldersToClassify:
    """Interactive folder creation wizard."""
    
    console.print("\n[bold blue]Folder Setup Wizard[/bold blue]\n")
    console.print("Create folders where your files will be organized.")
    console.print("Type [bold]'done'[/bold] when finished adding folders.\n")
    
    folders = []
    
    while True:
        folder_name = typer.prompt(
            "Folder name (or 'done' to finish)",
            default="done" if folders else ""
        )
        
        if folder_name.lower() == "done":
            if not folders:
                console.print("[yellow]You need at least one folder![/yellow]")
                continue
            break
        
        description = typer.prompt(
            f"Description for '{folder_name}' (optional, press Enter to skip)",
            default="",
            show_default=False
        )
        
        folder_path = base_path / folder_name
        
        folders.append(FolderObject(
            folder_path=folder_path,
            description=description if description else None
        ))
        
        console.print(f"[green]Added: {folder_name}[/green]\n")
    
    console.print("\n[bold]Default folder for files that don't match any category:[/bold]")
    default_name = typer.prompt("Default folder name", default="Other")
    default_folder = base_path / default_name
    
    # Show summary
    console.print("\n[bold]Your folder configuration:[/bold]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Folder", style="cyan")
    table.add_column("Description", style="green")
    
    for folder in folders:
        table.add_row(
            folder.folder_path.name,
            folder.description or "[dim]No description[/dim]"
        )
    table.add_row(f"{default_name} (default)", "[dim]Unmatched files[/dim]")
    
    console.print(table)
    
    if not typer.confirm("\nUse this configuration?"):
        console.print("[yellow]Let's start over...[/yellow]")
        return create_folders_interactive(base_path)
    
    return FoldersToClassify(
        folders=folders,
        default_folder=default_folder
    )

# ============== SERVICE COMMANDS ==============

service_app = typer.Typer(help="Manage the background file watcher service")
app.add_typer(service_app, name="service")


@service_app.command("worker", hidden=True)
def service_worker():
    """
    Internal command: specific entry point for the background process.
    """
    from file_organizer.service.runner import run_worker
    
    run_worker()

@service_app.command("start")
def service_start(
    directory: Path = typer.Argument(
        ...,
        help="Directory to watch for new files",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True
    ),
    config_name: Optional[str] = typer.Option(
        None,
        "--config", "-c",
        help="Use a saved configuration by name"
    ),
    use_defaults: bool = typer.Option(
        False,
        "--defaults", "-d",
        help="Use default folder configuration"
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Base directory for organized folders"
    ),
    provider: str = typer.Option(
        "openai",
        "--provider", "-p",
        help="AI provider to use"
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        help="Model to use"
    ),
    cooldown: int = typer.Option(
        5,
        "--cooldown",
        help="Seconds to wait before processing a new file"
    ),
    process_existing: bool = typer.Option(
        False,
        "--process-existing", "-x",
        help="Process existing files before starting watch"
    ),
    save_config: Optional[str] = typer.Option(
        None,
        "--save-config",
        help="Save the configuration with this name"
    ),
    base_url: Optional[str] = typer.Option(
        None,
        "--base-url",
        help="Base Url for ai provider"
    ),
    dir_depth_search: int = typer.Option(1, "--expore-depth", "-e", help="Number of directories to explore recursively (0 = only watch directory)"),
):
    """
    Start the background file watcher service.
    
    Examples:
        kypseli service start ./Downloads --config my_setup
        kypseli service start ./Downloads --defaults
        kypseli service start ./Downloads --defaults --process-existing
    """
    
    # Check if already running
    running, pid = is_service_running()
    if running:
        console.print(f"[yellow]Service is already running (PID: {pid})[/yellow]")
        console.print("Use [bold]kypseli service stop[/bold] to stop it first.")
        raise typer.Exit(1)
    
    output_base = output or Path("./organized")
    
    # Get folder configuration
    session = get_session()
    config_repo = ConfigurationRepository(session)
    
    used_config_name = None
    
    if config_name:
        folders_config = config_repo.get_folders_config(config_name)
        if not folders_config:
            console.print(f"[red]Configuration '{config_name}' not found.[/red]")
            session.close()
            raise typer.Exit(1)
        console.print(f"[green]Using saved configuration: {config_name}[/green]")
        used_config_name = config_name
    elif use_defaults:
        folders_config = create_default_folders(output_base)
        console.print("[dim]Using default folder configuration[/dim]")
    else:
        folders_config = create_folders_interactive(output_base)
    
    if save_config:
        description = typer.prompt("Configuration description (optional)", default="", show_default=False)
        config_repo.save(save_config, folders_config, description if description else None)
        console.print(f"[green]Configuration saved as '{save_config}'[/green]")
        used_config_name = save_config
    
    session.close()
    
    # Process existing files if requested (before backgrounding)
    if process_existing:
        console.print("[bold]Processing existing files...[/bold]")
        
        # Setup AI provider for processing existing files
        try:
            ai_provider = setup_ai_provider(provider, model, base_url)
            if isinstance(ai_provider,str):
                console.print(f"[dim]{ai_provider}[/dim]")
                return typer.Exit(1)
        except Exception as e:
            console.print(f"[dim]{e}[/dim]")
            raise typer.Exit(1)
            
        
        service = FileWatcherService(
            watch_directory=directory,
            folders_config=folders_config,
            ai_provider=ai_provider,
            cooldown_seconds=cooldown,
            configuration_name=used_config_name,
            dir_depth_search = dir_depth_search
        )
        
        results = service.process_existing()
        console.print(
            f"[dim]Processed: {results['successful']} successful, "
            f"{results['failed']} failed, {results['skipped']} skipped[/dim]"
        )
    
    # Start in background
    console.print("\n[bold]Starting background service...[/bold]")
    
    success, pid = start_background_service(
        watch_directory=directory,
        folders_config=folders_config,
        provider_name=provider,
        model_name=model,
        configuration_name=used_config_name,
        cooldown_seconds=cooldown,
        base_url=base_url,
        dir_depth_search=dir_depth_search
    )
    
    if success:
        console.print(Panel(
            f"[green]Service started successfully![/green]\n\n"
            f"[bold]PID:[/bold] {pid}\n"
            f"[bold]Watching:[/bold] {directory}\n"
            f"[bold]Log file:[/bold] {get_log_file()}\n\n"
            f"[dim]Use 'kypseli service status' to check status[/dim]\n"
            f"[dim]Use 'kypseli service stop' to stop the service[/dim]\n"
            f"[dim]Use 'kypseli service logs' to view logs[/dim]",
            title="Service Started"
        ))
    else:
        console.print("[red]Failed to start service. Check logs for details.[/red]")
        console.print(f"Log file: {get_log_file()}")
        raise typer.Exit(1)


@service_app.command("stop")
def service_stop():
    """Stop the background file watcher service."""
    
    running, pid = is_service_running()
    
    if not running:
        console.print("[yellow]Service is not running.[/yellow]")
        raise typer.Exit(0)
    
    console.print(f"[bold]Stopping service (PID: {pid})...[/bold]")
    
    if stop_service():
        console.print("[green]Service stopped successfully.[/green]")
    else:
        console.print("[red]Failed to stop service.[/red]")
        raise typer.Exit(1)


@service_app.command("status")
def service_status():
    """Show the status of the background service."""
    
    status = get_service_status()
    
    if status["running"]:
        status_text = f"[green]Running[/green] (PID: {status['pid']})"
    else:
        status_text = "[red]Stopped[/red]"
    
    config = status.get("config") or {}
    
    info_lines = [
        f"[bold]Status:[/bold] {status_text}",
        f"[bold]Platform:[/bold] {status.get('platform', 'Unknown')}",
        f"[bold]Log file:[/bold] {status['log_file']}"
    ]
    
    if config:
        info_lines.extend([
            "",
            f"[bold]Watching:[/bold] {config.get('watch_directory', 'N/A')}",
            f"[bold]Provider:[/bold] {config.get('provider_name', 'N/A')}",
            f"[bold]Model:[/bold] {config.get('model_name') or 'default'}",
            f"[bold]Config:[/bold] {config.get('configuration_name') or 'default'}",
            f"[bold]Cooldown:[/bold] {config.get('cooldown_seconds', 5)}s",
            f"[bold]Started:[/bold] {config.get('started_at', 'N/A')}"
        ])
    
    console.print(Panel(
        "\n".join(info_lines),
        title="Service Status"
    ))


@service_app.command("logs")
def service_logs(
    lines: int = typer.Option(
        50,
        "--lines", "-n",
        help="Number of lines to show"
    ),
    follow: bool = typer.Option(
        False,
        "--follow", "-f",
        help="Follow log output (like tail -f)"
    )
):
    """View the service logs."""
    import platform as plat
    
    log_file = get_log_file()
    
    if not log_file.exists():
        console.print("[yellow]No log file found. Service may not have been started yet.[/yellow]")
        raise typer.Exit(0)
    
    if follow:
        console.print(f"[dim]Following {log_file} (Ctrl+C to stop)...[/dim]\n")
        
        if plat.system() == "Windows":
            # Windows: use PowerShell Get-Content -Wait
            try:
                subprocess.run(
                    ["powershell", "-Command", f"Get-Content -Path '{log_file}' -Wait -Tail {lines}"],
                )
            except KeyboardInterrupt:
                pass
            except FileNotFoundError:
                # Fallback: manual tail -f implementation
                console.print("[dim]PowerShell not available, using fallback...[/dim]")
                try:
                    with open(log_file, 'r') as f:
                        # Go to end of file
                        f.seek(0, 2)
                        while True:
                            line = f.readline()
                            if line:
                                console.print(line.rstrip())
                            else:
                                time.sleep(0.5)
                except KeyboardInterrupt:
                    pass
        else:
            # Unix: use tail -f
            try:
                subprocess.run(["tail", "-f", "-n", str(lines), str(log_file)])
            except KeyboardInterrupt:
                pass
    else:
        try:
            with open(log_file, 'r') as f:
                all_lines = f.readlines()
                display_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                
                console.print(f"[dim]Showing last {len(display_lines)} lines from {log_file}[/dim]\n")
                
                for line in display_lines:
                    if "| ERROR" in line:
                        console.print(f"[red]{line.rstrip()}[/red]")
                    elif "| WARNING" in line:
                        console.print(f"[yellow]{line.rstrip()}[/yellow]")
                    elif "SUCCESS:" in line:
                        console.print(f"[green]{line.rstrip()}[/green]")
                    else:
                        console.print(line.rstrip())
        except IOError as e:
            console.print(f"[red]Error reading log file: {e}[/red]")


@service_app.command("restart")
def service_restart():
    """Restart the background service with the same configuration."""
    
    status = get_service_status()
    config = status.get("config")
    
    if not config:
        console.print("[red]No previous configuration found. Use 'service start' instead.[/red]")
        raise typer.Exit(1)
    
    # Stop if running
    if status["running"]:
        console.print("[bold]Stopping current service...[/bold]")
        stop_service()
        time.sleep(1)
    
    # Rebuild configuration
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
    
    # Start service
    console.print("[bold]Starting service...[/bold]")
    
    success, pid = start_background_service(
        watch_directory=Path(config["watch_directory"]),
        folders_config=folders_config,
        provider_name=config["provider_name"],
        model_name=config.get("model_name"),
        configuration_name=config.get("configuration_name"),
        cooldown_seconds=config.get("cooldown_seconds", 5),
        base_url= config.get("base_url", None),
        dir_depth_search=config.get("dir_depth_search", 1)
    )
    
    if success:
        console.print(f"[green]Service restarted successfully (PID: {pid})[/green]")
    else:
        console.print("[red]Failed to restart service.[/red]")
        raise typer.Exit(1)

# ============== MAIN COMMANDS ==============

@app.command()
def organize(
    directory: Path = typer.Argument(
        ...,
        help="Directory to organize",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True
    ),
    mode: str = typer.Option(
        "dry_run",
        "--mode", "-m",
        help="Operation mode: move, copy, or dry_run"
    ),
    provider: str = typer.Option(
        "openai",
        "--provider", "-p",
        help="AI provider to use: openai"
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        help="Model to use (provider-specific)"
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Base directory for organized folders (default: ./organized)"
    ),
    auto_execute: bool = typer.Option(
        False,
        "--yes", "-y",
        help="Execute operations without confirmation"
    ),
    use_defaults: bool = typer.Option(
        False,
        "--defaults", "-d",
        help="Use default folder configuration instead of interactive setup"
    ),
    config_name: Optional[str] = typer.Option(
        None,
        "--config", "-c",
        help="Use a saved configuration by name"
    ),
    save_config: Optional[str] = typer.Option(
        None,
        "--save-config",
        help="Save the configuration with this name after setup"
    ),
    analyze: bool = typer.Option(
        False,
        "--analyze", "-a",
        help="Analyze files"
    ),
    base_url: Optional[str] = typer.Option(
        None,
        "--base-url",
        help="Base Url for ai provider"
    ),
    dir_depth_search: int = typer.Option(1, "--expore-depth", "-e", help="Number of directories to explore recursively (0 = only watch directory)"),
):
    """
    Organize files in a directory using AI classification.
    
    Examples:
        kypseli organize ./Downloads
        kypseli organize ./Downloads --defaults
        kypseli organize ./Downloads --config my_setup
        kypseli organize ./Downloads --save-config work_config
    """
    
    output_base = output or Path("./organized")
    
    # Get folder configuration
    session = get_session()
    config_repo = ConfigurationRepository(session)
    
    used_config_name = None
    
    if config_name:
        # Load saved configuration
        folders_config = config_repo.get_folders_config(config_name)
        if not folders_config:
            console.print(f"[red]Configuration '{config_name}' not found.[/red]")
            console.print("Use [bold]kypseli config list[/bold] to see available configurations.")
            session.close()
            raise typer.Exit(1)
        console.print(f"[green]Using saved configuration: {config_name}[/green]\n")
        used_config_name = config_name
    elif use_defaults:
        folders_config = create_default_folders(output_base)
        console.print("[dim]Using default folder configuration[/dim]\n")
    else:
        folders_config = create_folders_interactive(output_base)
    
    # Save configuration if requested
    if save_config:
        description = typer.prompt("Configuration description (optional)", default="", show_default=False)
        config_repo.save(save_config, folders_config, description if description else None)
        console.print(f"[green]Configuration saved as '{save_config}'[/green]\n")
        used_config_name = save_config
    
    session.close()
    analysis_text = "active" if analyze else "inactive"
    
    console.print(Panel(
        f"[bold blue]Kypseli[/bold blue]\n\n"
        f"Directory: {directory}\n"
        f"Mode: {mode}\n"
        f"Provider: {provider}\n"
        f"Output: {output_base}\n"
        f"Analysis: {analysis_text}",
        title="Configuration"
    ))
    
    # Initialize components
    with console.status("[bold green]Initializing..."):
        scanner = DirectoryScanner(dir_depth_search)
        registry = setup_extractor_registry()
        try:
            ai_provider = setup_ai_provider(provider, model, base_url)
            if isinstance(ai_provider,str):
                console.print(f"[dim]{ai_provider}[/dim]")
                return typer.Exit(1)
        except Exception as e:
            console.print(f"[dim]{e}[/dim]")
            raise typer.Exit(1)
        operation_mode = get_operation_mode(mode)
        
        organizer = FileOrganizer(
            scanner=scanner,
            extractor_registry=registry,
            ai_provider=ai_provider,
            folders_config=folders_config,
            operation_mode=operation_mode
        )
    
    # Scan and process
    console.print("\n[bold]Scanning directory...[/bold]")
    
    with console.status("[bold green]Processing files with AI..."):
        operations = organizer.process_directory(directory)
    
    if not operations:
        console.print("[yellow]No files found to organize.[/yellow]")
        raise typer.Exit(0)
    
    # Display results
    console.print(f"\n[bold green]Found {len(operations)} files to organize:[/bold green]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("File", style="cyan")
    table.add_column("Category", style="green")
    table.add_column("Confidence", justify="right")
    table.add_column("Explanation", style="yellow")
    table.add_column("Destination", style="blue")

    
    for op in operations:
        confidence_str = f"{op.classification.confidence:.0%}" if op.classification.confidence else "N/A"
        explanation_str = op.classification.reasoning[:50] + "..."
        table.add_row(
            op.file_info.name,
            op.classification.category or "Unknown",
            confidence_str,
            explanation_str,
            str(op.classification.classified_path.name)
        )
    
    console.print(table)

    if analyze:
        file_infos = scanner.scan(directory=directory)
        for file_info in file_infos:

            analyzer = register_analyzers(file_info)
    
            if not analyzer:
                console.print(f"[yellow]Skipping {file_info.path.name}: No analyzer available for {file_info.content_type.value} files[/yellow]")
                continue
            
            # Setup AI provider (optional)
            ai_provider = None
            try:
                ai_provider = setup_ai_provider(provider, model, base_url)
                if isinstance(ai_provider,str):
                    console.print(f"[dim]{ai_provider}[/dim]")
                    return typer.Exit(1)
            except:
                console.print("[dim]AI provider not available, skipping AI descriptions[/dim]")
                raise typer.Exit(1)

            
            # Run analysis
            console.print(f"\n[bold]Analyzing {file_info.path.name}...[/bold]\n")
            
            with console.status("[bold green]Running analysis..."):
                result = analyzer.analyze(file_info, ai_provider)
            
            # Display results
            if result.error:
                console.print(f"[red]Error: {result.error}[/red]")
                raise typer.Exit(1)
            
            # Display based on analysis type
            if result.tabular:
                display_tabular_analysis(result)
            elif result.document:
                display_document_analysis(result)
            elif result.code:
                display_text_analysis(result)
            elif result.archive:
                display_archive_analysis(result)
            elif result.binary:
                display_binary_analysis(result)
            
            session = get_session()
            repo = AnalysisRepository(session)
            repo.save(result)
            session.close()
            console.print("\n[dim]Analysis saved to database[/dim]")
    
    # Handle execution
    if operation_mode == OperationMode.DRY_RUN:
        console.print("\n[yellow]Dry run mode - no files were moved.[/yellow]")
        console.print("Run with [bold]--mode move[/bold] or [bold]--mode copy[/bold] to execute.")
        return
    
    if not auto_execute:
        confirm = typer.confirm(f"\nProceed with {mode} operation?")
        if not confirm:
            console.print("[yellow]Operation cancelled.[/yellow]")
            raise typer.Exit(0)
    
    # Execute operations
    console.print(f"\n[bold]Executing {mode} operations...[/bold]")
    executor = OperationExecutor(configuration_name=used_config_name)
    results = executor.execute_batch(operations, log_to_database=True)
    
    # Show summary
    console.print(Panel(
        f"[green]Successful: {results['successful']}[/green]\n"
        f"[yellow]Skipped: {results['skipped']}[/yellow]\n"
        f"[red]Failed: {results['failed']}[/red]\n"
        f"[blue]Total: {results['total']}[/blue]",
        title="Results"
    ))


@app.command()
def scan(
    directory: Path = typer.Argument(
        ...,
        help="Directory to scan",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True
    ),
    dir_depth_search: int = typer.Option(1, "--expore-depth", "-e", help="Number of directories to explore recursively (0 = only watch directory)"),
):
    """
    Scan a directory and show file information without organizing.
    """
    
    scanner = DirectoryScanner(dir_depth_search)
    files = scanner.scan(directory)
    
    if not files:
        console.print("[yellow]No files found in directory.[/yellow]")
        raise typer.Exit(0)
    
    console.print(f"\n[bold green]Found {len(files)} files:[/bold green]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan")
    table.add_column("Extension", style="green")
    table.add_column("Size", justify="right")
    table.add_column("Type", style="blue")
    table.add_column("Modified", style="yellow")
    
    for file in files:
        if file.size < 1024:
            size_str = f"{file.size} B"
        elif file.size < 1024 * 1024:
            size_str = f"{file.size / 1024:.1f} KB"
        else:
            size_str = f"{file.size / (1024 * 1024):.1f} MB"
        
        table.add_row(
            file.name,
            file.extension,
            size_str,
            file.content_type.value,
            file.date_modified.strftime("%Y-%m-%d %H:%M")
        )
    
    console.print(table)
    
    console.print("\n[bold]Summary by type:[/bold]")
    type_counts = {}
    for file in files:
        type_name = file.content_type.value
        type_counts[type_name] = type_counts.get(type_name, 0) + 1
    
    for type_name, count in sorted(type_counts.items()):
        console.print(f"  {type_name}: {count}")


# ============== CONFIGURATION COMMANDS ==============

config_app = typer.Typer(help="Manage saved configurations")
app.add_typer(config_app, name="config")


@config_app.command("list")
def config_list():
    """List all saved configurations."""
    
    session = get_session()
    config_repo = ConfigurationRepository(session)
    configs = config_repo.list_all()
    session.close()
    
    if not configs:
        console.print("[yellow]No saved configurations found.[/yellow]")
        console.print("Create one with: [bold]kypseli organize ./folder --save-config my_config[/bold]")
        return
    
    console.print(f"\n[bold]Saved Configurations ({len(configs)}):[/bold]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Created", style="yellow")
    table.add_column("Updated", style="yellow")
    
    for config in configs:
        table.add_row(
            config.name,
            config.description or "[dim]No description[/dim]",
            config.created_at.strftime("%Y-%m-%d %H:%M") if config.created_at else "N/A",
            config.updated_at.strftime("%Y-%m-%d %H:%M") if config.updated_at else "N/A"
        )
    
    console.print(table)


@config_app.command("show")
def config_show(
    name: str = typer.Argument(..., help="Configuration name to show")
):
    """Show details of a saved configuration."""
    
    session = get_session()
    config_repo = ConfigurationRepository(session)
    
    config = config_repo.get_by_name(name)
    if not config:
        console.print(f"[red]Configuration '{name}' not found.[/red]")
        session.close()
        raise typer.Exit(1)
    
    folders_config = config_repo.get_folders_config(name)
    session.close()
    
    console.print(f"\n[bold blue]Configuration: {name}[/bold blue]\n")
    
    if config.description:
        console.print(f"Description: {config.description}\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Folder", style="cyan")
    table.add_column("Path", style="blue")
    table.add_column("Description", style="green")
    
    for folder in folders_config.folders:
        table.add_row(
            folder.folder_path.name,
            str(folder.folder_path),
            folder.description or "[dim]No description[/dim]"
        )
    
    table.add_row(
        f"{folders_config.default_folder.name} (default)",
        str(folders_config.default_folder),
        "[dim]Unmatched files[/dim]"
    )
    
    console.print(table)


@config_app.command("delete")
def config_delete(
    name: str = typer.Argument(..., help="Configuration name to delete")
):
    """Delete a saved configuration."""
    
    if not typer.confirm(f"Delete configuration '{name}'?"):
        console.print("[yellow]Cancelled.[/yellow]")
        raise typer.Exit(0)
    
    session = get_session()
    config_repo = ConfigurationRepository(session)
    
    if config_repo.delete(name):
        console.print(f"[green]Configuration '{name}' deleted.[/green]")
    else:
        console.print(f"[red]Configuration '{name}' not found.[/red]")
    
    session.close()


# ============== ANALYSIS COMMANDS ==============
analyze_app = typer.Typer(help="Analyze files and get insights")
app.add_typer(analyze_app, name="analyze")


@analyze_app.command("file")
def analyze_file(
    file_path: Path = typer.Argument(
        ...,
        help="File to analyze",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True
    ),
    provider: str = typer.Option(
        "openai",
        "--provider", "-p",
        help="AI provider for descriptions"
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        help="Model to use"
    ),
    save: bool = typer.Option(
        True,
        "--save/--no-save",
        help="Save analysis to database"
    ),
    base_url: Optional[str] = typer.Option(
        None,
        "--base-url",
        help="Base Url for ai provider"
    ),
):
    """Analyze a single file and show insights."""

    
    # Create file info
    scanner = DirectoryScanner()
    stat_info = file_path.stat()
    
    file_info = FileInfo(
        path=file_path,
        name=file_path.name,
        size=stat_info.st_size,
        extension=file_path.suffix,
        date_created=datetime.fromtimestamp(stat_info.st_ctime),
        date_modified=datetime.fromtimestamp(stat_info.st_mtime),
        content_type=scanner.get_content_type(file_path.suffix)
    )
    
    
    analyzer = register_analyzers(file_info)
    
    if not analyzer:
        console.print(f"[yellow]No analyzer available for {file_info.content_type.value} files[/yellow]")
        raise typer.Exit(1)
    
    # Setup AI provider (optional)
    ai_provider = None
    try:
        ai_provider = setup_ai_provider(provider, model, base_url)
        if isinstance(ai_provider,str):
            console.print(f"[dim]{ai_provider}[/dim]")
            return typer.Exit(1)
    except:
        console.print("[red]AI provider not available, skipping AI descriptions[/red]")
        raise typer.Exit(1)
        
    
    # Run analysis
    console.print(f"\n[bold]Analyzing {file_path.name}...[/bold]\n")
    
    with console.status("[bold green]Running analysis..."):
        result = analyzer.analyze(file_info, ai_provider)
    
    # Display results
    if result.error:
        console.print(f"[red]Error: {result.error}[/red]")
        raise typer.Exit(1)
    
    # Display based on analysis type
    if result.tabular:
        display_tabular_analysis(result)
    elif result.document:
        display_document_analysis(result)
    elif result.code:
        display_text_analysis(result)
    elif result.archive:
        display_archive_analysis(result)
    elif result.binary:
        display_binary_analysis(result)
    
    # Save to database
    if save:
        session = get_session()
        repo = AnalysisRepository(session)
        repo.save(result)
        session.close()
        console.print("\n[dim]Analysis saved to database[/dim]")

def display_text_analysis(result: AnalysisResult):
    analysis = result.code

    console.print(Panel(
        f"[bold yellow]Language:[/bold yellow] {analysis.language}\n"  
        f"[bold yellow]Line Count:[/bold yellow] {analysis.line_count:,}\n"
        f"[bold yellow]Import Statements:[/bold yellow] {analysis.import_statements}\n"
        f"[bold yellow]Functions:[/bold yellow] {analysis.functions}\n"
        f"[bold yellow]Classes:[/bold yellow] {analysis.classes}\n"
        f"[bold green]Complexity Estimate:[/bold green] {analysis.complexity_estimate}\n",
        title=f"[bold cyan]{result.file_info.name}[/bold cyan]",
        subtitle="Text Overview"
    ))

    if result.ai_description:
        console.print(Panel(
            result.ai_description,
            title="[bold]AI Analysis[/bold]",
            border_style="blue"
        ))

def display_binary_analysis(result: AnalysisResult):
    """Display binary analysis results."""
    
    analysis = result.binary
    
    if analysis.is_database:
        category = "Database"
        category_style = "blue"
    elif analysis.is_executable:
        category = "Executable"
        category_style = "red"
    elif analysis.is_library:
        category = "Library"
        category_style = "yellow"
    else:
        category = "Binary Data"
        category_style = "dim"
    
    overview_lines = [
        f"[bold]Type:[/bold] {analysis.binary_type}",
        f"[bold]Format:[/bold] {analysis.format_details or 'Unknown'}",
        f"[bold]Category:[/bold] [{category_style}]{category}[/{category_style}]",
    ]
    
    if analysis.architecture:
        overview_lines.append(f"[bold]Architecture:[/bold] {analysis.architecture}")
    
    if analysis.bit_depth:
        overview_lines.append(f"[bold]Bit Depth:[/bold] {analysis.bit_depth}-bit")
    
    if analysis.endianness:
        overview_lines.append(f"[bold]Endianness:[/bold] {analysis.endianness}")
    
    if analysis.entry_point:
        overview_lines.append(f"[bold]Entry Point:[/bold] {analysis.entry_point}")
    
    if analysis.file_version:
        overview_lines.append(f"[bold]Version:[/bold] {analysis.file_version}")
    
    if analysis.entropy is not None:
        entropy_color = "red" if analysis.is_packed else "green"
        packed_note = " (possibly packed)" if analysis.is_packed else ""
        overview_lines.append(f"[bold]Entropy:[/bold] [{entropy_color}]{analysis.entropy}/8.0{packed_note}[/{entropy_color}]")
    
    console.print(Panel(
        "\n".join(overview_lines),
        title=f"[bold cyan]{result.file_info.name}[/bold cyan]",
        subtitle="Binary Overview"
    ))
    
    if analysis.is_database and analysis.db_tables:
        console.print("\n[bold]Database Tables:[/bold]\n")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Table", style="cyan")
        table.add_column("Rows", justify="right", style="green")
        
        for tbl_name in analysis.db_tables[:20]:
            count = analysis.db_row_counts.get(tbl_name, -1)
            count_str = f"{count:,}" if count >= 0 else "Error"
            table.add_row(tbl_name, count_str)
        
        if len(analysis.db_tables) > 20:
            table.add_row("...", f"+{len(analysis.db_tables) - 20} more")
        
        console.print(table)
        
        if analysis.db_size_info:
            info = analysis.db_size_info
            console.print(f"\n[dim]Pages: {info.get('pages', 'N/A')} | "
                         f"Page Size: {info.get('page_size', 'N/A')} bytes | "
                         f"DB Size: {info.get('total_size', 'N/A')}[/dim]")
    
    if analysis.sections and not analysis.is_database:
        console.print("\n[bold]Sections/Segments:[/bold]\n")
        
        for section in analysis.sections[:15]:
            console.print(f"  [dim]•[/dim] {section}")
        
        if len(analysis.sections) > 15:
            console.print(f"  [dim]... and {len(analysis.sections) - 15} more[/dim]")
    
    if analysis.strings_preview:
        console.print("\n[bold]Extracted Strings (sample):[/bold]\n")
        
        for s in analysis.strings_preview[:15]:
            display_str = s[:70] + "..." if len(s) > 70 else s
            console.print(f"  [dim]•[/dim] {display_str}")
        
        if len(analysis.strings_preview) > 15:
            console.print(f"  [dim]... and {len(analysis.strings_preview) - 15} more[/dim]")
    
    if analysis.magic_bytes:
        console.print(f"\n[dim]Magic Bytes: {analysis.magic_bytes[:32]}...[/dim]")
    
    if result.ai_description:
        console.print(Panel(
            result.ai_description,
            title="[bold]AI Analysis[/bold]",
            border_style="blue"
        ))

def display_archive_analysis(result: AnalysisResult):
    """Display archive analysis results."""
    
    analysis = result.archive
    
    compression_str = f"{analysis.compression_ratio}% saved" if analysis.compression_ratio else "N/A"
    password_str = "Yes" if analysis.has_password else "No"
    
    console.print(Panel(
        f"[bold]Archive Type:[/bold] {analysis.archive_type or 'Unknown'}\n"
        f"[bold]Files:[/bold] {analysis.file_count:,}\n"
        f"[bold]Directories:[/bold] {analysis.directory_count:,}\n"
        f"[bold]Uncompressed Size:[/bold] {analysis.total_uncompressed_size}\n"
        f"[bold]Compression:[/bold] {compression_str}\n"
        f"[bold]Password Protected:[/bold] {password_str}",
        title=f"[bold cyan]{result.file_info.name}[/bold cyan]",
        subtitle="Archive Overview"
    ))
    
    # File types table
    if analysis.file_types:
        console.print("\n[bold]File Types:[/bold]\n")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Extension", style="cyan")
        table.add_column("Count", justify="right", style="green")
        
        for ext, count in sorted(analysis.file_types.items(), key=lambda x: -x[1])[:15]:
            table.add_row(ext, str(count))
        
        if len(analysis.file_types) > 15:
            table.add_row("...", f"+{len(analysis.file_types) - 15} more")
        
        console.print(table)
    
    if analysis.top_level_items:
        console.print("\n[bold]Top-Level Contents:[/bold]\n")
        
        for item in analysis.top_level_items[:20]:
            console.print(f"  [dim]•[/dim] {item}")
        
        if len(analysis.top_level_items) > 20:
            console.print(f"  [dim]... and {len(analysis.top_level_items) - 20} more[/dim]")
    
    if analysis.largest_file:
        console.print(f"\n[bold]Largest File:[/bold] {analysis.largest_file.get('name', 'Unknown')} ({analysis.largest_file.get('size', 'Unknown')})")
    
    if analysis.oldest_file or analysis.newest_file:
        console.print(f"\n[bold]File Dates:[/bold]")
        if analysis.oldest_file:
            console.print(f"  Oldest: {analysis.oldest_file}")
        if analysis.newest_file:
            console.print(f"  Newest: {analysis.newest_file}")
    
    if hasattr(analysis, 'note') and analysis.note:
        console.print(f"\n[yellow]Note: {analysis.note}[/yellow]")
    
    if result.ai_description:
        console.print(Panel(
            result.ai_description,
            title="[bold]AI Analysis[/bold]",
            border_style="blue"
        ))

def display_document_analysis(result: AnalysisResult):
    analysis = result.document

    topics = ", ".join(analysis.key_topics) if analysis.key_topics else "None detected"
    
    # Format optional integers
    pages = f"{analysis.page_count:,}" if analysis.page_count is not None else "N/A"

    console.print(Panel(
        f"[bold yellow]Language:[/bold yellow] {analysis.language}\n"
        f"[bold yellow]Pages:[/bold yellow] {pages}\n"
        f"[bold yellow]Word Count:[/bold yellow] {analysis.word_count:,}\n"
        f"[bold yellow]Char Count:[/bold yellow] {analysis.char_count:,}\n"
        f"[bold yellow]Key Topics:[/bold yellow] {topics}\n",
        title=f"[bold cyan]{result.file_info.name}[/bold cyan]",
        subtitle="Document Overview"
    ))

    if result.ai_description:
        console.print(Panel(
            result.ai_description,
            title="[bold]AI Analysis[/bold]",
            border_style="blue"
        ))

def display_tabular_analysis(result: AnalysisResult):
    """Display tabular analysis results."""
    
    analysis = result.tabular
    
    # Overview panel
    console.print(Panel(
        f"[bold]Rows:[/bold] {analysis.row_count:,}\n"
        f"[bold]Columns:[/bold] {analysis.column_count}\n"
        f"[bold]Memory:[/bold] {analysis.memory_usage}",
        title=f"[bold cyan]{result.file_info.name}[/bold cyan]",
        subtitle="Dataset Overview"
    ))
    
    # Columns table
    console.print("\n[bold]Columns & Data Types:[/bold]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Column", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Missing", justify="right")
    table.add_column("Missing %", justify="right")
    
    for col in analysis.columns[:30]:  # Limit display
        missing = analysis.missing_values.get(col, 0)
        missing_pct = analysis.missing_percentage.get(col, 0)
        
        # Color code missing values
        if missing_pct > 50:
            missing_style = "[red]"
        elif missing_pct > 20:
            missing_style = "[yellow]"
        else:
            missing_style = "[green]"
        
        table.add_row(
            col[:40],
            analysis.dtypes.get(col, "unknown"),
            str(missing),
            f"{missing_style}{missing_pct:.1f}%[/]"
        )
    
    if len(analysis.columns) > 30:
        table.add_row("...", "...", "...", "...")
    
    console.print(table)
    
    # AI Description
    if result.ai_description:
        console.print(Panel(
            result.ai_description,
            title="[bold]AI Analysis[/bold]",
            border_style="blue"
        ))


@analyze_app.command("dir")
def analyze_directory(
    directory: Path = typer.Argument(
        ...,
        help="Directory to analyze",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True
    ),
    provider: str = typer.Option(
        "openai",
        "--provider", "-p",
        help="AI provider"
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        help="Model to use"
    ),
    base_url: Optional[str] = typer.Option(
        None,
        "--base-url",
        help="Base Url for ai provider"
    ),
    dir_depth_search: int = typer.Option(1, "--expore-depth", "-e", help="Number of directories to explore recursively (0 = only watch directory)"),
):
    """Analyze all files in a directory."""
    scanner = DirectoryScanner(dir_depth_search)
    file_infos = scanner.scan(directory=directory)
    for file_info in file_infos:

        analyzer = register_analyzers(file_info)

        if not analyzer:
            console.print(f"[yellow]Skipping {file_info.path.name}: No analyzer available for {file_info.content_type.value} files[/yellow]")
            continue
        
        ai_provider = None
        try:
            ai_provider = setup_ai_provider(provider, model, base_url)
            if isinstance(ai_provider,str):
                console.print(f"[dim]{ai_provider}[/dim]")
                return typer.Exit(1)
        except:
            console.print("[dim]AI provider not available, skipping AI descriptions[/dim]")
            raise typer.Exit(1)

        
        # Run analysis
        console.print(f"\n[bold]Analyzing {file_info.path.name}...[/bold]\n")
        
        with console.status("[bold green]Running analysis..."):
            result = analyzer.analyze(file_info, ai_provider)
        
        # Display results
        if result.error:
            console.print(f"[red]Error: {result.error}[/red]")
            raise typer.Exit(1)
        
        # Display based on analysis type
        if result.tabular:
            display_tabular_analysis(result)
        elif result.document:
            display_document_analysis(result)
        elif result.code:
            display_text_analysis(result)
        elif result.archive:
            display_archive_analysis(result)
        elif result.binary:
            display_binary_analysis(result)
        
        session = get_session()
        repo = AnalysisRepository(session)
        repo.save(result)
        session.close()
        console.print("\n[dim]Analysis saved to database[/dim]")


@analyze_app.command("history")
def analyze_history(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of records"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full analysis details")
):
    """Show recent analysis history."""
    
    session = get_session()
    repo = AnalysisRepository(session)
    records = repo.get_recent(limit)
    session.close()
    
    if not records:
        console.print("[yellow]No analysis history found.[/yellow]")
        return
    
    console.print(f"\n[bold]Recent Analyses (last {len(records)}):[/bold]\n")
    
    if verbose:
        # Detailed view with full analysis
        for i, record in enumerate(records, 1):
            display_analysis_record(i, record)
            if i < len(records):
                console.print("")  # Spacing between records
    else:
        # Compact table view
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=4)
        table.add_column("File", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Summary", style="yellow")
        table.add_column("Date", style="dim")
        
        for i, record in enumerate(records, 1):
            # Get brief summary based on analysis type
            summary = get_analysis_summary(record)
            
            table.add_row(
                str(i),
                record.file_name[:35] + "..." if len(record.file_name) > 35 else record.file_name,
                record.analysis_type,
                summary[:50] + "..." if len(summary) > 50 else summary,
                record.analyzed_at.strftime("%m-%d %H:%M") if record.analyzed_at else "N/A"
            )
        
        console.print(table)
        console.print("\n[dim]Tip: Use --verbose or -v to see full analysis details[/dim]")


def get_analysis_summary(record) -> str:
    """Get a brief summary from an analysis record."""
    import json
    
    try:
        analysis_data = json.loads(record.analysis_json)
        
        if record.analysis_type == "tabular":
            tabular = analysis_data.get("tabular", {})
            rows = tabular.get("row_count", "?")
            cols = tabular.get("column_count", "?")
            return f"{rows:,} rows × {cols} columns" if isinstance(rows, int) else f"{rows} rows × {cols} columns"
        
        elif record.analysis_type == "document":
            document = analysis_data.get("document", {})
            pages = document.get("page_count", "?")
            words = document.get("word_count", "?")
            return f"{pages} pages, {words} words"
        
        elif record.analysis_type == "code":
            code = analysis_data.get("code", {})
            lines = code.get("line_count", "?")
            lang = code.get("language", "unknown")
            return f"{lang}, {lines} lines"
        
        elif record.analysis_type == "image":
            image = analysis_data.get("image", {})
            width = image.get("width", "?")
            height = image.get("height", "?")
            return f"{width}×{height}"
        
        elif record.analysis_type == "archive":
            archive = analysis_data.get("archive", {})
            count = archive.get("file_count", "?")
            return f"{count} files"
        
        else:
            return "N/A"
    
    except (json.JSONDecodeError, KeyError, TypeError):
        return "N/A"


def display_analysis_record(index: int, record):
    """Display a full analysis record with all details."""
    import json
    
    try:
        analysis_data = json.loads(record.analysis_json)
    except json.JSONDecodeError:
        analysis_data = {}
    
    date_str = record.analyzed_at.strftime("%Y-%m-%d %H:%M:%S") if record.analyzed_at else "N/A"
    
    # Header
    header = (
        f"[bold]File:[/bold] {record.file_name}\n"
        f"[bold]Path:[/bold] {record.file_path}\n"
        f"[bold]Size:[/bold] {format_size(record.file_size) if record.file_size else 'N/A'}\n"
        f"[bold]Type:[/bold] {record.analysis_type}\n"
        f"[bold]Analyzed:[/bold] {date_str}"
    )
    
    # Type-specific details
    details = ""
    
    if record.analysis_type == "tabular":
        details = format_tabular_details(analysis_data.get("tabular", {}))
    elif record.analysis_type == "document":
        details = format_document_details(analysis_data.get("document", {}))
    elif record.analysis_type == "code":
        details = format_code_details(analysis_data.get("code", {}))
    elif record.analysis_type == "image":
        details = format_image_details(analysis_data.get("image", {}))
    elif record.analysis_type == "archive":
        details = format_archive_details(analysis_data.get("archive", {}))
    
    # AI Description
    ai_section = ""
    if record.ai_description:
        ai_section = f"\n\n[bold]AI Analysis:[/bold]\n[italic]{record.ai_description}[/italic]"
    
    # Combine all sections
    full_content = header
    if details:
        full_content += f"\n\n[bold]Details:[/bold]\n{details}"
    if ai_section:
        full_content += ai_section
    
    console.print(Panel(
        full_content,
        title=f"[bold cyan]#{index} — {record.file_name}[/bold cyan]",
        border_style="dim"
    ))


def format_size(size_bytes: int) -> str:
    """Format file size to human readable."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def format_tabular_details(tabular: dict) -> str:
    """Format tabular analysis details."""
    if not tabular:
        return "No tabular data available"
    
    rows = tabular.get("row_count", "?")
    cols = tabular.get("column_count", "?")
    memory = tabular.get("memory_usage", "?")
    columns = tabular.get("columns", [])
    dtypes = tabular.get("dtypes", {})
    missing = tabular.get("missing_percentage", {})
    
    # Format rows/cols
    lines = [
        f"[green]Rows:[/green] {rows:,}" if isinstance(rows, int) else f"[green]Rows:[/green] {rows}",
        f"[green]Columns:[/green] {cols}",
        f"[green]Memory:[/green] {memory}",
        ""
    ]
    
    # Column details
    if columns:
        lines.append("[green]Columns:[/green]")
        for col in columns[:15]:  # Limit to 15 columns
            dtype = dtypes.get(col, "unknown")
            miss_pct = missing.get(col, 0)
            
            if miss_pct > 50:
                miss_color = "red"
            elif miss_pct > 20:
                miss_color = "yellow"
            else:
                miss_color = "green"
            
            lines.append(f"  • {col}: {dtype} [{miss_color}]{miss_pct:.1f}% missing[/{miss_color}]")
        
        if len(columns) > 15:
            lines.append(f"  ... and {len(columns) - 15} more columns")
    
    return "\n".join(lines)


def format_document_details(document: dict) -> str:
    """Format document analysis details."""
    if not document:
        return "No document data available"
    
    lines = []
    
    if document.get("page_count"):
        lines.append(f"[green]Pages:[/green] {document['page_count']}")
    if document.get("word_count"):
        lines.append(f"[green]Words:[/green] {document['word_count']:,}")
    if document.get("char_count"):
        lines.append(f"[green]Characters:[/green] {document['char_count']:,}")
    if document.get("language"):
        lines.append(f"[green]Language:[/green] {document['language']}")
    
    if document.get("key_topics"):
        lines.append(f"\n[green]Key Topics:[/green]")
        for topic in document["key_topics"][:10]:
            lines.append(f"  • {topic}")
    
    if document.get("summary"):
        lines.append(f"\n[green]Summary:[/green]\n{document['summary']}")
    
    return "\n".join(lines) if lines else "No details available"


def format_code_details(code: dict) -> str:
    """Format code analysis details."""
    if not code:
        return "No code data available"
    
    lines = []
    
    if code.get("language"):
        lines.append(f"[green]Language:[/green] {code['language']}")
    if code.get("line_count"):
        lines.append(f"[green]Lines:[/green] {code['line_count']:,}")
    if code.get("complexity_estimate"):
        lines.append(f"[green]Complexity:[/green] {code['complexity_estimate']}")
    
    if code.get("import_statements"):
        lines.append(f"\n[green]Imports:[/green]")
        for imp in code["import_statements"][:10]:
            lines.append(f"  • {imp}")
        if len(code["import_statements"]) > 10:
            lines.append(f"  ... and {len(code['import_statements']) - 10} more")
    
    if code.get("functions"):
        lines.append(f"\n[green]Functions:[/green]")
        for func in code["functions"][:10]:
            lines.append(f"  • {func}")
        if len(code["functions"]) > 10:
            lines.append(f"  ... and {len(code['functions']) - 10} more")
    
    if code.get("classes"):
        lines.append(f"\n[green]Classes:[/green]")
        for cls in code["classes"][:10]:
            lines.append(f"  • {cls}")
    
    return "\n".join(lines) if lines else "No details available"


def format_image_details(image: dict) -> str:
    """Format image analysis details."""
    if not image:
        return "No image data available"
    
    lines = []
    
    if image.get("width") and image.get("height"):
        lines.append(f"[green]Dimensions:[/green] {image['width']} × {image['height']}")
    if image.get("format"):
        lines.append(f"[green]Format:[/green] {image['format']}")
    if image.get("mode"):
        lines.append(f"[green]Mode:[/green] {image['mode']}")
    if image.get("file_size"):
        lines.append(f"[green]Size:[/green] {image['file_size']}")
    if image.get("has_exif"):
        lines.append(f"[green]EXIF Data:[/green] {'Yes' if image['has_exif'] else 'No'}")
    
    if image.get("exif_data"):
        lines.append(f"\n[green]EXIF:[/green]")
        for key, value in list(image["exif_data"].items())[:10]:
            lines.append(f"  • {key}: {value}")
    
    if image.get("description"):
        lines.append(f"\n[green]Description:[/green]\n{image['description']}")
    
    return "\n".join(lines) if lines else "No details available"


def format_archive_details(archive: dict) -> str:
    """Format archive analysis details."""
    if not archive:
        return "No archive data available"
    
    lines = []
    
    if archive.get("file_count"):
        lines.append(f"[green]Files:[/green] {archive['file_count']}")
    if archive.get("total_uncompressed_size"):
        lines.append(f"[green]Uncompressed Size:[/green] {archive['total_uncompressed_size']}")
    
    if archive.get("file_types"):
        lines.append(f"\n[green]File Types:[/green]")
        for ext, count in sorted(archive["file_types"].items(), key=lambda x: -x[1])[:10]:
            lines.append(f"  • {ext}: {count}")
    
    if archive.get("file_list"):
        lines.append(f"\n[green]Contents:[/green]")
        for f in archive["file_list"][:15]:
            lines.append(f"  • {f}")
        if len(archive["file_list"]) > 15:
            lines.append(f"  ... and {len(archive['file_list']) - 15} more files")
    
    return "\n".join(lines) if lines else "No details available"

# ============== HISTORY COMMANDS ==============

history_app = typer.Typer(help="View operation history")
app.add_typer(history_app, name="history")


@history_app.command("list")
def history_list(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of records to show"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full explanations")
):
    """Show recent operation history."""
    
    session = get_session()
    history_repo = HistoryRepository(session)
    records = history_repo.get_recent(limit=limit)
    session.close()
    
    if not records:
        console.print("[yellow]No operation history found.[/yellow]")
        return
    
    console.print(f"\n[bold]Recent Operations (last {len(records)}):[/bold]\n")
    
    if verbose:
        # Detailed view with full reasoning
        for i, record in enumerate(records, 1):
            status_color = {
                "success": "green",
                "failed": "red", 
                "skipped": "yellow"
            }.get(record.status, "white")
            
            confidence_str = f"{record.confidence:.0%}" if record.confidence else "N/A"
            date_str = record.executed_at.strftime("%Y-%m-%d %H:%M:%S") if record.executed_at else "N/A"
            
            panel_content = (
                f"[bold]File:[/bold] {record.file_name}\n"
                f"[bold]Source:[/bold] {record.source_path}\n"
                f"[bold]Destination:[/bold] {record.destination_path}\n"
                f"\n"
                f"[bold]Category:[/bold] {record.category or 'N/A'}\n"
                f"[bold]Confidence:[/bold] {confidence_str}\n"
                f"[bold]Mode:[/bold] {record.operation_mode}\n"
                f"[bold]Status:[/bold] [{status_color}]{record.status}[/{status_color}]\n"
                f"[bold]Date:[/bold] {date_str}\n"
                f"\n"
                f"[bold]Reasoning:[/bold]\n"
                f"[italic]{record.reasoning or 'No reasoning provided'}[/italic]"
            )
            
            console.print(Panel(
                panel_content,
                title=f"[bold cyan]#{i} — {record.file_name}[/bold cyan]",
                border_style="dim"
            ))
            
            if i < len(records):
                console.print("")  # Spacing between panels
    
    else:
        # Compact table view
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=4)
        table.add_column("File", style="cyan")
        table.add_column("Category", style="green")
        table.add_column("Confidence", justify="right")
        table.add_column("Status")
        table.add_column("Date", style="dim")
        
        for i, record in enumerate(records, 1):
            status_style = {
                "success": "[green]success[/green]",
                "failed": "[red]failed[/red]",
                "skipped": "[yellow]skipped[/yellow]"
            }.get(record.status, record.status)
            
            filename = record.file_name[:35] + "..." if len(record.file_name) > 35 else record.file_name
            confidence_str = f"{record.confidence:.0%}" if record.confidence else "N/A"
            date_str = record.executed_at.strftime("%m-%d %H:%M") if record.executed_at else "N/A"
            
            table.add_row(
                str(i),
                filename,
                record.category or "N/A",
                confidence_str,
                status_style,
                date_str
            )
        
        console.print(table)
        console.print("\n[dim]Tip: Use --verbose or -v to see full details and reasoning[/dim]")


@history_app.command("search")
def history_search(
    query: str = typer.Argument(..., help="Filename to search for")
):
    """Search for a file in operation history."""
    
    session = get_session()
    history_repo = HistoryRepository(session)
    records = history_repo.search_by_filename(query)
    session.close()
    
    if not records:
        console.print(f"[yellow]No records found matching '{query}'[/yellow]")
        return
    
    console.print(f"\n[bold]Found {len(records)} matches for '{query}':[/bold]\n")
    
    for record in records:
        status_color = {"success": "green", "failed": "red", "skipped": "yellow"}.get(record.status, "white")
        
        console.print(Panel(
            f"[bold]File:[/bold] {record.file_name}\n"
            f"[bold]Source:[/bold] {record.source_path}\n"
            f"[bold]Destination:[/bold] {record.destination_path}\n"
            f"[bold]Category:[/bold] {record.category or 'N/A'}\n"
            f"[bold]Confidence:[/bold] {record.confidence:.0%}" if record.confidence else "N/A" + "\n"
            f"[bold]Mode:[/bold] {record.operation_mode}\n"
            f"[bold]Status:[/bold] [{status_color}]{record.status}[/{status_color}]\n"
            f"[bold]Date:[/bold] {record.executed_at.strftime('%Y-%m-%d %H:%M:%S') if record.executed_at else 'N/A'}",
            title=record.file_name
        ))


@history_app.command("stats")
def history_stats():
    """Show operation statistics."""
    
    session = get_session()
    history_repo = HistoryRepository(session)
    stats = history_repo.get_stats()
    session.close()
    
    console.print(Panel(
        f"[bold]Total Operations:[/bold] {stats['total']}\n\n"
        f"[green]Successful:[/green] {stats['successful']}\n"
        f"[red]Failed:[/red] {stats['failed']}\n"
        f"[yellow]Skipped:[/yellow] {stats['skipped']}",
        title="Operation Statistics"
    ))


@app.command()
def providers():
    """List available AI providers."""
    
    console.print("\n[bold]Available AI Providers:[/bold]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Provider", style="cyan")
    table.add_column("Type", style="blue")
    table.add_column("Status")
    table.add_column("Default Model")
    
    import os
    
    # Cloud providers
    cloud_providers = [
        ("openai", "OPENAI_API_KEY", "gpt-4o-mini"),
        ("anthropic", "ANTHROPIC_API_KEY", "claude-sonnet-4-20250514"),
        ("gemini", "GOOGLE_API_KEY", "gemini-2.0-flash"),
        ("groq", "GROQ_API_KEY", "llama-3.1-8b-instant"),
        ("mistral", "MISTRAL_API_KEY", "mistral-small-latest"),
        ("cohere", "COHERE_API_KEY", "command-r"),
        ("deepinfra", "DEEPINFRA_API_TOKEN", "gemma-3-27b-it"),
    ]
    
    for name, env_var, default_model in cloud_providers:
        key = os.environ.get(env_var)
        
        # Check if provider package is installed
        package_available = check_provider_package(name)
        
        if not package_available:
            status = "[yellow]Package not installed[/yellow]"
        elif key:
            status = "[green]Configured[/green]"
        else:
            status = "[red]API key missing[/red]"
        
        table.add_row(name, "Cloud", status, default_model)
    
    # Ollama (local)
    ollama_status = check_ollama_status()
    table.add_row("ollama", "Local", ollama_status, "varies")
    
    # OpenAI-compatible
    table.add_row("openai-compatible", "Local", "[dim]Custom URL[/dim]", "varies")
    
    console.print(table)
    
    console.print("\n[dim]Use --provider <name> to select a provider[/dim]")


def check_provider_package(provider_name: str) -> bool:
    """Check if a provider's package is installed."""
    
    package_map = {
        "openai": "langchain_openai",
        "anthropic": "langchain_anthropic",
        "gemini": "langchain_google_genai",
        "groq": "langchain_groq",
        "mistral": "langchain_mistralai",
        "cohere": "langchain_cohere",
        "together": "langchain_together",
        "deepinfra": "langchain_community",
        "ollama": "langchain_ollama",
    }
    
    package = package_map.get(provider_name)
    if not package:
        return True  # Unknown, assume available
    
    try:
        __import__(package)
        return True
    except ImportError:
        return False


def check_ollama_status() -> str:
    """Check Ollama status safely."""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return f"[green]Running ({len(models)} models)[/green]"
    except Exception:
        pass
    
    return "[red]Not running[/red]"


@app.command()
def version():
    logo = r"""
              \     /
          \    o ^ o    /
            \ (     ) /
 ____________(%%%%%%%)____________
(     /   /  )%%%%%%%(  \   \     )
(___/___/__/           \__\___\___)
   (     /  /(%%%%%%%)\  \     )
    (__/___/ (%%%%%%%) \___\__)
            /(       )\
          /   (%%%%%)   \
               (%%%)
                 !
    """
    console.print(f"[bold yellow]{logo}[/bold yellow]")
    console.print("[bold cyan]KYPSELI[/bold cyan] [dim]v0.8.0[/dim]")
    console.print("[italic]The AI File Hive[/italic]\n")

if __name__ == "__main__":
    app()