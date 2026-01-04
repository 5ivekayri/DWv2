"""Minimal Django-like management command support for the stub framework."""
from __future__ import annotations

import argparse
import importlib
import sys
from typing import Any


class CommandError(Exception):
    """Raised when command execution fails."""


class OutputWrapper:
    def __init__(self, stream) -> None:
        self._stream = stream

    def write(self, msg: str) -> None:  # noqa: D401
        """Write the provided message to the wrapped stream."""
        self._stream.write(f"{msg}\n")


class BaseCommand:
    """Lightweight approximation of Django's BaseCommand."""

    help = ""

    def __init__(self) -> None:
        self.stdout = OutputWrapper(sys.stdout)
        self.stderr = OutputWrapper(sys.stderr)

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:  # noqa: D401
        """Hook for subclasses to register arguments."""

    def handle(self, *args: Any, **options: Any) -> Any:  # noqa: D401
        """Execute the command."""
        raise NotImplementedError

    def create_parser(self, prog_name: str, subcommand: str) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog=f"{prog_name} {subcommand}", description=self.help)
        self.add_arguments(parser)
        return parser

    def run_from_argv(self, argv: list[str]) -> Any:
        parser = self.create_parser(argv[0], argv[1])
        options = vars(parser.parse_args(argv[2:]))
        return self.handle(**options)


def execute_from_command_line(argv: list[str] | None = None) -> Any:
    argv = argv or sys.argv
    if len(argv) < 2:
        raise CommandError("No command provided")

    command_name = argv[1].replace("-", "_")
    module_path = f"backend.api.management.commands.{command_name}"
    try:
        module = importlib.import_module(module_path)
        command_class = getattr(module, "Command")
    except Exception as exc:  # pragma: no cover - safety
        raise CommandError(f"Unknown command: {command_name}") from exc

    command = command_class()
    return command.run_from_argv(argv)


__all__ = ["BaseCommand", "CommandError", "execute_from_command_line"]
