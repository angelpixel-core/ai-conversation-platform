"""
Template canónico para Adaptadores de Consola CLI (Primary Adapter).
Reglas:
- Define la lógica de comandos de consola ejecutables vía terminal o pyproject.toml [project.scripts].
- Delega en los servicios de aplicación o herramientas sin lógica de infraestructura acoplada.
"""


def cli_entrypoint() -> None:
    """Función de entrada para comandos de consola."""
    print("Ejecutando comando CLI...")


if __name__ == "__main__":
    cli_entrypoint()
