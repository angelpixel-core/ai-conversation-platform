"""
Template canónico para Pruebas Unitarias de Comandos CLI.
"""

from .cli_command import cli_entrypoint


def test_cli_entrypoint_executes() -> None:
    cli_entrypoint()
