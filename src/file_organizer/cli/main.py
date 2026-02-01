import typer
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

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

app = typer.Typer(
    name="file-organizer",
    help="AI-powered file organization tool"
)
console = Console()


def get_operation_mode(mode: str) -> OperationMode:
    """Convert string to OperationMode enum."""
    mode_map = {
        "move": OperationMode.MOVE,
        "copy": OperationMode.COPY,
        "dry_run": OperationMode.DRY_RUN,
        "dry-run": OperationMode.DRY_RUN,
    }
    return mode_map.get(mode.lower(), OperationMode.DRY_RUN)


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
            FolderObject(
                folder_path=base_path / "Keys",
                description="Access keys for several providers"
            ),
        ],
        default_folder=base_path / "Other"
    )


def setup_extractor_registry() -> ExtractorRegistry:
    """Create and configure the extractor registry."""
    registry = ExtractorRegistry()
    registry.register(CSVExtractor())
    # registry.register(PDFExtractor())
    # registry.register(TextExtractor())
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
):
    """
    Organize files in a directory using AI classification.
    
    Examples:
        file-organizer organize ./Downloads
        file-organizer organize ./Downloads --mode copy
        file-organizer organize ./Downloads --mode move --yes
    """
    
    # Setup output directory
    output_base = output or Path("./organized")
    
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
        folders_config = create_default_folders(output_base)
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
    
    # Confirm execution
    if not auto_execute:
        confirm = typer.confirm(f"\nProceed with {mode} operation?")
        if not confirm:
            console.print("[yellow]Operation cancelled.[/yellow]")
            raise typer.Exit(0)
    
    # Execute operations
    console.print(f"\n[bold]Executing {mode} operations...[/bold]")
    executor = OperationExecutor()
    results = executor.execute_batch(operations)
    
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
    
    Examples:
        file-organizer scan ./Downloads
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
        # Format size
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
    
    # Summary by type
    console.print("\n[bold]Summary by type:[/bold]")
    type_counts = {}
    for file in files:
        type_name = file.content_type.value
        type_counts[type_name] = type_counts.get(type_name, 0) + 1
    
    for type_name, count in sorted(type_counts.items()):
        console.print(f"  {type_name}: {count}")


@app.command()
def providers():
    """List available AI providers."""
    
    console.print("\n[bold]Available AI Providers:[/bold]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Provider", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Default Model")
    
    # Check OpenAI
    import os
    openai_key = os.environ.get("OPENAI_API_KEY")
    openai_status = "[green]Configured[/green]" if openai_key else "[red]Not configured[/red] OPENAI_API_KEY is required"
    table.add_row("openai", openai_status, "gpt-4o-mini")
    
    # anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    # anthropic_status = "[green]Configured[/green]" if anthropic_key else "[red]Not configured[/red]"
    # table.add_row("anthropic", anthropic_status, "claude-sonnet-4-20250514")
    
    console.print(table)
    
    console.print("\n[dim]Set API keys as environment variables:[/dim]")
    console.print("  export OPENAI_API_KEY=your-key-here")
    # console.print("  export ANTHROPIC_API_KEY=your-key-here")


@app.command()
def version():
    """Show version information."""
    console.print("[bold]File Organizer[/bold] v0.1.0")


if __name__ == "__main__":
    app()