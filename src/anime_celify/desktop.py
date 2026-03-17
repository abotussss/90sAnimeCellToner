from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from anime_celify.config import resolve_preset
from anime_celify.models import TransformRunLog
from anime_celify.pipeline import transform_video


class DesktopFlowError(RuntimeError):
    """Raised when the local desktop flow cannot obtain paths or run."""


@dataclass(frozen=True)
class DesktopTransformRequest:
    input_path: Path
    output_path: Path
    preset_name: str = "cyber_noir_95"
    config_path: Path | None = None
    auto_tune: bool = True
    log_path: Path | None = None


def default_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_celified.mp4")


def run_desktop_request(request: DesktopTransformRequest) -> TransformRunLog:
    preset_definition = resolve_preset(
        preset_name=request.preset_name if request.config_path is None else None,
        config_path=request.config_path,
    )
    return transform_video(
        input_path=request.input_path,
        output_path=request.output_path,
        preset_definition=preset_definition,
        auto_tune=request.auto_tune,
        log_path=request.log_path,
    )


def launch_desktop_flow(
    input_path: Path | None = None,
    output_path: Path | None = None,
    preset_name: str = "cyber_noir_95",
    config_path: Path | None = None,
    auto_tune: bool = True,
    log_path: Path | None = None,
) -> TransformRunLog:
    selected_input = input_path or choose_input_file()
    selected_output = output_path or choose_output_file(default_output_path(selected_input))
    request = DesktopTransformRequest(
        input_path=selected_input,
        output_path=selected_output,
        preset_name=preset_name,
        config_path=config_path,
        auto_tune=auto_tune,
        log_path=log_path,
    )
    return run_desktop_request(request)


def choose_input_file() -> Path:
    system = platform.system()
    if system == "Darwin":
        return _choose_file_macos()
    if system == "Linux":
        return _choose_file_linux()
    if system == "Windows":
        return _choose_file_windows()
    raise DesktopFlowError(f"Native file selection is not supported on this platform: {system}")


def choose_output_file(default_path: Path) -> Path:
    system = platform.system()
    if system == "Darwin":
        return _choose_save_file_macos(default_path)
    if system == "Linux":
        return _choose_save_file_linux(default_path)
    if system == "Windows":
        return _choose_save_file_windows(default_path)
    raise DesktopFlowError(f"Native save dialog is not supported on this platform: {system}")


def _run_dialog_command(command: list[str]) -> str:
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        if "User canceled" in stderr or "cancel" in stderr.lower():
            raise DesktopFlowError("File selection was cancelled.")
        raise DesktopFlowError(stderr or "Native file selection failed.")
    result = completed.stdout.strip()
    if not result:
        raise DesktopFlowError("File selection was cancelled.")
    return result


def _choose_file_macos() -> Path:
    return Path(
        _run_dialog_command(
            [
                "osascript",
                "-e",
                'POSIX path of (choose file with prompt "Select an input mp4 file" of type {"public.mpeg-4"})',
            ]
        )
    )


def _choose_save_file_macos(default_path: Path) -> Path:
    safe_name = default_path.name.replace('"', "")
    script = (
        'set targetFile to choose file name with prompt "Choose output mp4 file" '
        f'default name "{safe_name}"\n'
        "POSIX path of targetFile"
    )
    return Path(_run_dialog_command(["osascript", "-e", script]))


def _choose_file_linux() -> Path:
    if shutil.which("zenity"):
        return Path(
            _run_dialog_command(
                [
                    "zenity",
                    "--file-selection",
                    "--title=Select an input mp4 file",
                    "--file-filter=MP4 files | *.mp4",
                ]
            )
        )
    raise DesktopFlowError("No supported Linux file chooser found. Install zenity or use the CLI.")


def _choose_save_file_linux(default_path: Path) -> Path:
    if shutil.which("zenity"):
        return Path(
            _run_dialog_command(
                [
                    "zenity",
                    "--file-selection",
                    "--save",
                    "--confirm-overwrite",
                    f"--filename={default_path}",
                    "--title=Choose output mp4 file",
                ]
            )
        )
    raise DesktopFlowError("No supported Linux file chooser found. Install zenity or use the CLI.")


def _choose_file_windows() -> Path:
    script = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "$dialog = New-Object System.Windows.Forms.OpenFileDialog;"
        '$dialog.Filter = "MP4 files (*.mp4)|*.mp4";'
        '$dialog.Title = "Select an input mp4 file";'
        "if ($dialog.ShowDialog() -ne 'OK') { exit 1 };"
        "Write-Output $dialog.FileName"
    )
    return Path(_run_dialog_command(["powershell", "-NoProfile", "-Command", script]))


def _choose_save_file_windows(default_path: Path) -> Path:
    script = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "$dialog = New-Object System.Windows.Forms.SaveFileDialog;"
        '$dialog.Filter = "MP4 files (*.mp4)|*.mp4";'
        '$dialog.Title = "Choose output mp4 file";'
        f'$dialog.FileName = "{default_path.name}";'
        "if ($dialog.ShowDialog() -ne 'OK') { exit 1 };"
        "Write-Output $dialog.FileName"
    )
    return Path(_run_dialog_command(["powershell", "-NoProfile", "-Command", script]))


def run() -> None:
    run_log = launch_desktop_flow()
    print(
        f"Transformed {run_log.input_path.name} -> {run_log.output_path.name} using {run_log.preset_name}"
        + (" with auto-tune." if run_log.auto_tune_enabled else ".")
    )
