"""CLI Primary Adapter for generating static OpenAPI schema and ReDoc HTML."""

import json
from pathlib import Path
from string import Template

from src.main import create_app


def generate_static_docs(output_dir: Path | str = "public") -> None:
    """Export OpenAPI schema and standalone ReDoc HTML page."""
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    app = create_app()
    openapi_schema = app.openapi()

    # 1. Export openapi.json
    json_path = target_dir / "openapi.json"
    json_path.write_text(json.dumps(openapi_schema, indent=2), encoding="utf-8")

    # 2. Export index.html using template
    title = openapi_schema.get("info", {}).get("title", "API Documentation")
    template_path = Path(__file__).parent / "templates" / "redoc.html"
    template = Template(template_path.read_text(encoding="utf-8"))

    html_content = template.substitute(title=title, spec_url="openapi.json")
    html_path = target_dir / "index.html"
    html_path.write_text(html_content, encoding="utf-8")
    print(f"✅ Generated static OpenAPI docs in '{target_dir}' directory.")


def cli_main() -> None:
    """CLI Entrypoint."""
    generate_static_docs()


if __name__ == "__main__":
    cli_main()
