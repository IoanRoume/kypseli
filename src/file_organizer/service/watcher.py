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
import os
import sys
import time
import signal
import logging
import subprocess
import json
import platform
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from file_organizer.core.scanner import DirectoryScanner
from file_organizer.core.orchestrator import FileOrganizer
from file_organizer.core.executor import OperationExecutor
from file_organizer.core.models import (
    FoldersToClassify,
    FolderObject,
    OperationMode,
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
from file_organizer.ai.base import BaseAIProvider


def get_service_dir() -> Path:
    """Get the service directory for logs and pid file."""
    service_dir = Path.home() / ".file_organizer" / "service"
    service_dir.mkdir(parents=True, exist_ok=True)
    return service_dir


def get_pid_file() -> Path:
    """Get path to PID file."""
    return get_service_dir() / "watcher.pid"


def get_log_file() -> Path:
    """Get path to log file."""
    return get_service_dir() / "watcher.log"


def get_config_file() -> Path:
    """Get path to service config file."""
    return get_service_dir() / "watcher_config.json"


def setup_logging() -> logging.Logger:
    """Setup logging to file."""
    log_file = get_log_file()
    
    logger = logging.getLogger("file_organizer_service")
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    logger.handlers = []
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    
    # Format
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    return logger


def is_service_running() -> tuple[bool, Optional[int]]:
    """Check if service is already running. Returns (is_running, pid)."""
    pid_file = get_pid_file()
    
    if not pid_file.exists():
        return False, None
    
    try:
        pid = int(pid_file.read_text().strip())
        
        if platform.system() == "Windows":
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if str(pid) in result.stdout and "INFO:" not in result.stdout:
                    return True, pid
                else:
                    pid_file.unlink(missing_ok=True)
                    return False, None
            except subprocess.TimeoutExpired:
                # Assume running if we can't check
                return True, pid
        else:
            # Unix: use kill with signal 0
            os.kill(pid, 0)
            return True, pid
            
    except (ValueError, ProcessLookupError, PermissionError, OSError):
        pid_file.unlink(missing_ok=True)
        return False, None


def write_pid_file():
    """Write current PID to file."""
    pid_file = get_pid_file()
    pid_file.write_text(str(os.getpid()))


def remove_pid_file():
    """Remove PID file."""
    pid_file = get_pid_file()
    pid_file.unlink(missing_ok=True)


def save_service_config(
    watch_directory: Path,
    folders_config: FoldersToClassify,
    provider_name: str,
    model_name: Optional[str],
    configuration_name: Optional[str],
    cooldown_seconds: int,
    base_url: Optional[str] = None,
    dir_depth_search: Optional[int] = 2
):
    """Save service configuration to file."""
    config_file = get_config_file()
    
    config = {
        "watch_directory": str(watch_directory),
        "folders": [
            {
                "folder_path": str(f.folder_path),
                "description": f.description
            }
            for f in folders_config.folders
        ],
        "default_folder": str(folders_config.default_folder),
        "provider_name": provider_name,
        "model_name": model_name,
        "configuration_name": configuration_name,
        "cooldown_seconds": cooldown_seconds,
        "started_at": datetime.now().isoformat(),
        "dir_depth_search": dir_depth_search,
        "base_url" : base_url
    }
    
    config_file.write_text(json.dumps(config, indent=2))


def load_service_config() -> Optional[dict]:
    """Load service configuration from file."""
    config_file = get_config_file()
    
    if not config_file.exists():
        return None
    
    try:
        return json.loads(config_file.read_text())
    except (json.JSONDecodeError, IOError):
        return None


def remove_service_config():
    """Remove service configuration file."""
    config_file = get_config_file()
    config_file.unlink(missing_ok=True)


class OrganizeEventHandler(FileSystemEventHandler):
    """Handles file system events and triggers organization."""
    
    def __init__(
        self,
        organizer: FileOrganizer,
        executor: OperationExecutor,
        scanner: DirectoryScanner,
        logger: logging.Logger,
        cooldown_seconds: int = 5,
        watch_directory: Path = None,
        max_depth: int = 1
    ):
        super().__init__()
        self.organizer = organizer
        self.executor = executor
        self.scanner = scanner
        self.logger = logger
        self.cooldown_seconds = cooldown_seconds
        self.watch_directory = watch_directory
        self.max_depth = max_depth
        
        self._processed_files: dict[str, datetime] = {}
        self._processing_lock = False
    
    def _get_depth(self, file_path: Path) -> int:
        """Calculate how deep a file is relative to watch directory."""
        try:
            relative = file_path.relative_to(self.watch_directory)
            return len(relative.parts) - 1 
        except ValueError:
            return 999
    
    def _should_process(self, file_path: Path) -> bool:
        """Check if file should be processed."""
        
        if self.watch_directory and self.max_depth >= 0:
            depth = self._get_depth(file_path)
            if depth > self.max_depth:
                self.logger.debug(f"SKIP (too deep): {file_path.name} at depth {depth}")
                return False
        
        if file_path.name.startswith('.'):
            return False
        
        temp_extensions = ['.tmp', '.temp', '.part', '.crdownload', '.partial', '.download']
        if file_path.suffix.lower() in temp_extensions:
            return False
        
        file_key = str(file_path)
        if file_key in self._processed_files:
            last_processed = self._processed_files[file_key]
            if datetime.now() - last_processed < timedelta(seconds=self.cooldown_seconds):
                return False
        
        if not file_path.exists():
            return False
        
        try:
            initial_size = file_path.stat().st_size
            if initial_size == 0:
                return False
            
            time.sleep(0.5)
            if not file_path.exists():
                return False
            
            current_size = file_path.stat().st_size
            if current_size != initial_size:
                return False
        except (OSError, IOError):
            return False
        
        return True
    
    def _create_file_info(self, file_path: Path) -> Optional[FileInfo]:
        """Create FileInfo object for a file."""
        try:
            stat_info = file_path.stat()
            return FileInfo(
                path=file_path,
                name=file_path.name,
                size=stat_info.st_size,
                extension=file_path.suffix,
                date_created=datetime.fromtimestamp(stat_info.st_ctime),
                date_modified=datetime.fromtimestamp(stat_info.st_mtime),
                content_type=self.scanner.get_content_type(file_path.suffix)
            )
        except (OSError, IOError) as e:
            self.logger.error(f"Could not read file info for {file_path}: {e}")
            return None
    
    def _process_file(self, file_path: Path):
        """Process a single file."""
        
        if self._processing_lock:
            return
        
        if not self._should_process(file_path):
            return
        
        self._processing_lock = True
        
        try:
            self.logger.info(f"NEW FILE: {file_path.name}")
            
            file_info = self._create_file_info(file_path)
            if not file_info:
                return
            
            operation = self.organizer.process_file(file_info)
            
            if not operation:
                self.logger.warning(f"SKIP: No extractor for {file_path.name}")
                return
            
            success, status, error = self.executor.execute(operation)
            
            self._processed_files[str(file_path)] = datetime.now()
            
            if success:
                self.logger.info(
                    f"SUCCESS: {file_path.name} -> {operation.classification.classified_path.name}/ "
                    f"(category: {operation.classification.category}, "
                    f"confidence: {operation.classification.confidence:.0%})"
                )
            else:
                self.logger.warning(f"{status.upper()}: {file_path.name} - {error or 'Unknown'}")
        
        except Exception as e:
            self.logger.error(f"ERROR processing {file_path.name}: {e}")
        
        finally:
            self._processing_lock = False
    
    def on_created(self, event):
        """Called when a file is created."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        time.sleep(1)
        self._process_file(file_path)
    
    def on_moved(self, event):
        """Called when a file is moved into the watched directory."""
        if event.is_directory:
            return
        
        file_path = Path(event.dest_path)
        self._process_file(file_path)


class FileWatcherService:
    """Background service that watches a directory and auto-organizes new files."""
    
    def __init__(
        self,
        watch_directory: Path,
        folders_config: FoldersToClassify,
        ai_provider: BaseAIProvider,
        cooldown_seconds: int = 5,
        configuration_name: Optional[str] = None,
        dir_depth_search: int = 2
    ):
        self.watch_directory = watch_directory
        self.folders_config = folders_config
        self.ai_provider = ai_provider
        self.cooldown_seconds = cooldown_seconds
        self.configuration_name = configuration_name
        self.dir_depth_search = dir_depth_search
        
        self.logger = setup_logging()
        
        self.scanner = DirectoryScanner(dir_depth_search)
        self.registry = self._setup_registry()
        self.organizer = FileOrganizer(
            scanner=self.scanner,
            extractor_registry=self.registry,
            ai_provider=self.ai_provider,
            folders_config=self.folders_config,
            operation_mode=OperationMode.MOVE
        )
        self.executor = OperationExecutor(configuration_name=configuration_name)
        
        self.observer = None
        self.event_handler = None
        self._running = False
    
    def _setup_registry(self) -> ExtractorRegistry:
        """Setup extractor registry."""
        registry = ExtractorRegistry()
        registry.register(TabularExtractor())
        registry.register(TextExtractor())
        registry.register(DocumentExtractor())
        registry.register(ImageExtractor())
        registry.register(VideoExtractor())
        registry.register(ArchiveExtractor())
        registry.register(BinaryExtractor())
        return registry
    
    def _signal_handler(self, signum, frame):
        """Handle termination signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def run(self):
        """Run the service (blocking). Called by the background process."""
        
        if not self.watch_directory.exists():
            self.logger.error(f"Watch directory does not exist: {self.watch_directory}")
            return
        
        # Write PID file
        write_pid_file()
        
        # Setup signal handlers
        if platform.system() != "Windows":
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)

        watch_recursive = self.dir_depth_search > 0
        
        self.logger.info("=" * 60)
        self.logger.info("KYPSELI SERVICE STARTED")
        self.logger.info("=" * 60)
        self.logger.info(f"PID: {os.getpid()}")
        self.logger.info(f"Platform: {platform.system()}")
        self.logger.info(f"Watching: {self.watch_directory}")
        self.logger.info(f"Recursive: {watch_recursive} (depth: {self.dir_depth_search})")
        self.logger.info(f"Config: {self.configuration_name or 'default'}")
        self.logger.info(f"Cooldown: {self.cooldown_seconds}s")
        self.logger.info("=" * 60)
        
        self._running = True
        
        self.event_handler = OrganizeEventHandler(
            organizer=self.organizer,
            executor=self.executor,
            scanner=self.scanner,
            logger=self.logger,
            cooldown_seconds=self.cooldown_seconds,
            watch_directory=self.watch_directory,
            max_depth=self.dir_depth_search
        )
        
        self.observer = Observer()
        self.observer.schedule(
            self.event_handler,
            str(self.watch_directory),
            recursive=watch_recursive
        )
        self.observer.start()
        
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        except Exception as e:
            self.logger.error(f"Service error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the service."""
        
        self._running = False
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        self.logger.info("=" * 60)
        self.logger.info("KYPSELI SERVICE STOPPED")
        self.logger.info("=" * 60)
        
        remove_pid_file()
    
    def process_existing(self):
        """Process all existing files in the watch directory."""
        
        self.logger.info(f"Processing existing files in {self.watch_directory}...")
        
        operations = self.organizer.process_directory(self.watch_directory)
        
        if not operations:
            self.logger.info("No existing files to process.")
            return {"successful": 0, "failed": 0, "skipped": 0, "total": 0}
        
        self.logger.info(f"Found {len(operations)} files to organize.")
        
        results = self.executor.execute_batch(operations, log_to_database=True)
        
        self.logger.info(
            f"Existing files processed: {results['successful']} successful, "
            f"{results['failed']} failed, {results['skipped']} skipped"
        )
        
        return results


def start_background_service(
    watch_directory: Path,
    folders_config: FoldersToClassify,
    provider_name: str,
    model_name: Optional[str],
    configuration_name: Optional[str],
    cooldown_seconds: int,
    base_url: Optional[str] = None,
    dir_depth_search: Optional[int] = 2
) -> tuple[bool, Optional[int]]:
    """Start the service as a background process. Cross-platform."""
    
    # Check if already running
    running, pid = is_service_running()
    if running:
        return False, pid
    
    # Save config for the background process to read
    save_service_config(
        watch_directory=watch_directory,
        folders_config=folders_config,
        provider_name=provider_name,
        model_name=model_name,
        configuration_name=configuration_name,
        cooldown_seconds=cooldown_seconds,
        base_url=base_url,
        dir_depth_search=dir_depth_search
    )
    
    # Determine how to launch the worker
    if getattr(sys, 'frozen', False):
        executable = sys.executable
        cmd = [executable, "service", "worker"]
    else:
        # Running as Python script
        runner_script = Path(__file__).parent / "runner.py"
        cmd = [sys.executable, str(runner_script)]
    
    # Platform-specific process creation
    if platform.system() == "Windows":
        # Windows: use CREATE_NO_WINDOW and DETACHED_PROCESS
        DETACHED_PROCESS = 0x00000008
        CREATE_NO_WINDOW = 0x08000000
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        
        # Use shell=False and proper flags
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        
        process = subprocess.Popen(
            cmd,
            creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            startupinfo=startupinfo,
            close_fds=True
        )
        
        # On Windows, write the PID immediately since we know it
        pid_file = get_pid_file()
        pid_file.write_text(str(process.pid))
        
        # Give it a moment to start
        time.sleep(2)
        
        # Check if process is still running
        if process.poll() is None:
            return True, process.pid
        else:
            # Process died, clean up
            pid_file.unlink(missing_ok=True)
            return False, None
    else:
        # Unix (Linux/macOS): use nohup-style approach
        log_file = get_log_file()
        
        with open(log_file, 'a') as log:
            process = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=log,
                stdin=subprocess.DEVNULL,
                start_new_session=True
            )
        
        # Wait for PID file to be created by the worker
        for _ in range(10): 
            time.sleep(0.5)
            running, pid = is_service_running()
            if running:
                return True, pid

        if process.poll() is None:  
            return True, process.pid

        return False, None


def stop_service() -> bool:
    """Stop the running service. Cross-platform."""
    
    running, pid = is_service_running()
    
    if not running:
        remove_pid_file()
        remove_service_config()
        return False
    
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
                timeout=10
            )
        else:
            os.kill(pid, signal.SIGTERM)
        
        # Wait for process to stop
        for _ in range(10):
            time.sleep(0.5)
            running, _ = is_service_running()
            if not running:
                break
        
        # Force kill if still running (Unix only, Windows /F already forces)
        if platform.system() != "Windows":
            try:
                os.kill(pid, 0)  # Check if still alive
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        
        remove_pid_file()
        remove_service_config()
        return True
    
    except subprocess.TimeoutExpired:
        # Force cleanup
        remove_pid_file()
        remove_service_config()
        return True
    except (ProcessLookupError, PermissionError, OSError):
        remove_pid_file()
        remove_service_config()
        return True


def get_service_status() -> dict:
    """Get current service status."""
    
    running, pid = is_service_running()
    config = load_service_config()
    log_file = get_log_file()
    
    status = {
        "running": running,
        "pid": pid,
        "config": config,
        "log_file": str(log_file),
        "log_exists": log_file.exists(),
        "platform": platform.system()
    }
    
    if log_file.exists():
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                status["recent_logs"] = lines[-20:] if len(lines) > 20 else lines
        except IOError:
            status["recent_logs"] = []
    
    return status