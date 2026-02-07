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
    PendingStatus
)
from file_organizer.extractors.registry import ExtractorRegistry
from file_organizer.extractors.csv_extractor import CSVExtractor
from file_organizer.ai.providers.openai import OpenaiProvider
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

import subprocess



app = typer.Typer(
    name="file-organizer",
    help="AI-powered file organization tool"
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
                description="Data files like CSV, Excel, Parquet, and other tabular data"
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
    registry.register(CSVExtractor())
    return registry


def setup_ai_provider(provider_name: str, model: Optional[str] = None):
    """Create and initialize the AI provider."""
    if provider_name.lower() == "openai":
        provider = OpenaiProvider()
        provider.initialize_model(model=model or "gpt-4o-mini")
        return provider
    else:
        console.print(f"[red]Unknown provider: {provider_name}[/red]")
        raise typer.Exit(1)


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
        "--process-existing", "-e",
        help="Process existing files before starting watch"
    ),
    save_config: Optional[str] = typer.Option(
        None,
        "--save-config",
        help="Save the configuration with this name"
    ),
):
    """
    Start the background file watcher service.
    
    Examples:
        file-organizer service start ./Downloads --config my_setup
        file-organizer service start ./Downloads --defaults
        file-organizer service start ./Downloads --defaults --process-existing
    """
    
    # Check if already running
    running, pid = is_service_running()
    if running:
        console.print(f"[yellow]Service is already running (PID: {pid})[/yellow]")
        console.print("Use [bold]file-organizer service stop[/bold] to stop it first.")
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
        ai_provider = setup_ai_provider(provider, model)
        
        service = FileWatcherService(
            watch_directory=directory,
            folders_config=folders_config,
            ai_provider=ai_provider,
            cooldown_seconds=cooldown,
            configuration_name=used_config_name
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
        cooldown_seconds=cooldown
    )
    
    if success:
        console.print(Panel(
            f"[green]Service started successfully![/green]\n\n"
            f"[bold]PID:[/bold] {pid}\n"
            f"[bold]Watching:[/bold] {directory}\n"
            f"[bold]Log file:[/bold] {get_log_file()}\n\n"
            f"[dim]Use 'file-organizer service status' to check status[/dim]\n"
            f"[dim]Use 'file-organizer service stop' to stop the service[/dim]\n"
            f"[dim]Use 'file-organizer service logs' to view logs[/dim]",
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
        cooldown_seconds=config.get("cooldown_seconds", 5)
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
):
    """
    Organize files in a directory using AI classification.
    
    Examples:
        file-organizer organize ./Downloads
        file-organizer organize ./Downloads --defaults
        file-organizer organize ./Downloads --config my_setup
        file-organizer organize ./Downloads --save-config work_config
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
            console.print("Use [bold]file-organizer config list[/bold] to see available configurations.")
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
    
    console.print(Panel(
        f"[bold blue]File Organizer[/bold blue]\n\n"
        f"Directory: {directory}\n"
        f"Mode: {mode}\n"
        f"Provider: {provider}\n"
        f"Output: {output_base}",
        title="Configuration"
    ))
    
    # Initialize components
    with console.status("[bold green]Initializing..."):
        scanner = DirectoryScanner()
        registry = setup_extractor_registry()
        ai_provider = setup_ai_provider(provider, model)
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
    table.add_column("Destination", style="blue")
    
    for op in operations:
        confidence_str = f"{op.classification.confidence:.0%}" if op.classification.confidence else "N/A"
        table.add_row(
            op.file_info.name,
            op.classification.category or "Unknown",
            confidence_str,
            str(op.classification.classified_path.name)
        )
    
    console.print(table)
    
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
):
    """
    Scan a directory and show file information without organizing.
    """
    
    scanner = DirectoryScanner()
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
        console.print("Create one with: [bold]file-organizer organize ./folder --save-config my_config[/bold]")
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


# ============== HISTORY COMMANDS ==============

history_app = typer.Typer(help="View operation history")
app.add_typer(history_app, name="history")


@history_app.command("list")
def history_list(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of records to show")
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
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("File", style="cyan")
    table.add_column("Category", style="green")
    table.add_column("Mode", style="blue")
    table.add_column("Status")
    table.add_column("Date", style="yellow")
    
    for record in records:
        status_style = {
            "success": "[green]success[/green]",
            "failed": "[red]failed[/red]",
            "skipped": "[yellow]skipped[/yellow]"
        }.get(record.status, record.status)
        
        table.add_row(
            record.file_name[:30] + "..." if len(record.file_name) > 30 else record.file_name,
            record.category or "N/A",
            record.operation_mode,
            status_style,
            record.executed_at.strftime("%Y-%m-%d %H:%M") if record.executed_at else "N/A"
        )
    
    console.print(table)


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
    table.add_column("Status", style="green")
    table.add_column("Default Model")
    
    import os
    openai_key = os.environ.get("OPENAI_API_KEY")
    openai_status = "[green]Configured[/green]" if openai_key else "[red]Not configured[/red]"
    table.add_row("openai", openai_status, "gpt-4o-mini")
    
    console.print(table)
    
    console.print("\n[dim]Set API keys as environment variables:[/dim]")
    console.print("  export OPENAI_API_KEY=your-key-here")


@app.command()
def version():
    """Show version information."""
    console.print("[bold]File Organizer[/bold] v0.1.0")


if __name__ == "__main__":
    app()