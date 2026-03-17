from __future__ import annotations

import json
from pathlib import Path

import typer
import yaml

from anime_celify.config import ConfigError, list_presets, resolve_preset, show_preset_yaml
from anime_celify.desktop import launch_desktop_flow
from anime_celify.pipeline import analyze_video, transform_video
from anime_celify.probe import ProbeError
from anime_celify.utils.logging import configure_logging

app = typer.Typer(no_args_is_help=True, add_completion=False)
presets_app = typer.Typer(no_args_is_help=True)
app.add_typer(presets_app, name="presets")


def _handle_error(exc: Exception) -> None:
    typer.secho(str(exc), fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1) from exc


@app.callback()
def main(verbose: bool = typer.Option(False, "--verbose", help="Enable debug logging.")) -> None:
    configure_logging(verbose=verbose)


@app.command()
def transform(
    input_path: Path = typer.Argument(..., exists=True, readable=True),
    output_path: Path = typer.Option(..., "--output", "-o"),
    preset: str | None = typer.Option(None, "--preset"),
    config: Path | None = typer.Option(None, "--config"),
    auto_tune: bool = typer.Option(False, "--auto-tune"),
    log_path: Path | None = typer.Option(None, "--log-path"),
) -> None:
    try:
        preset_definition = resolve_preset(
            preset_name=preset or ("cyber_noir_95" if config is None else None),
            config_path=config,
        )
        run_log = transform_video(
            input_path=input_path,
            output_path=output_path,
            preset_definition=preset_definition,
            auto_tune=auto_tune,
            log_path=log_path,
        )
    except (ConfigError, ProbeError, RuntimeError) as exc:
        _handle_error(exc)
        return

    typer.echo(
        f"Transformed {input_path.name} -> {output_path.name} using {run_log.preset_name}"
        + (" with auto-tune." if run_log.auto_tune_enabled else ".")
    )


@app.command()
def analyze(
    input_path: Path = typer.Argument(..., exists=True, readable=True),
    preset: str = typer.Option("cyber_noir_95", "--preset"),
    output_path: Path | None = typer.Option(None, "--output"),
) -> None:
    try:
        preset_definition = resolve_preset(preset_name=preset)
        report = analyze_video(input_path=input_path, preset_definition=preset_definition)
    except (ConfigError, ProbeError, RuntimeError) as exc:
        _handle_error(exc)
        return

    payload = [item.model_dump(mode="json", exclude_none=True) for item in report]
    if output_path:
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        typer.echo(f"Analysis written to {output_path}")
    else:
        typer.echo(yaml.safe_dump(payload, sort_keys=False, allow_unicode=False))


@app.command("desktop")
def desktop(
    input_path: Path | None = typer.Option(None, "--input"),
    output_path: Path | None = typer.Option(None, "--output", "-o"),
    preset: str = typer.Option("cyber_noir_95", "--preset"),
    config: Path | None = typer.Option(None, "--config"),
    auto_tune: bool = typer.Option(True, "--auto-tune/--no-auto-tune"),
    log_path: Path | None = typer.Option(None, "--log-path"),
) -> None:
    try:
        run_log = launch_desktop_flow(
            input_path=input_path,
            output_path=output_path,
            preset_name=preset,
            config_path=config,
            auto_tune=auto_tune,
            log_path=log_path,
        )
    except (ConfigError, ProbeError, RuntimeError) as exc:
        _handle_error(exc)
        return

    typer.echo(
        f"Transformed {run_log.input_path.name} -> {run_log.output_path.name} using {run_log.preset_name}"
        + (" with auto-tune." if run_log.auto_tune_enabled else ".")
    )


@presets_app.command("list")
def presets_list() -> None:
    for preset_name in list_presets():
        typer.echo(preset_name)


@presets_app.command("show")
def presets_show(name: str) -> None:
    try:
        typer.echo(show_preset_yaml(name))
    except ConfigError as exc:
        _handle_error(exc)
