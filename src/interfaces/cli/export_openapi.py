"""CLI Primary Adapter for generating static OpenAPI schema and ReDoc HTML."""

import json
from pathlib import Path

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

    # 2. Export index.html (ReDoc standalone interface)
    title = openapi_schema.get("info", {}).get("title", "API Documentation")
    html_content = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <title>{title}</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700" rel="stylesheet">
    <style>
      body {{
        margin: 0;
        padding: 0;
      }}
    </style>
  </head>
  <body>
    <redoc spec-url='openapi.json'></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"> </script>
  </body>
</html>
"""
    html_path = target_dir / "index.html"
    html_path.write_text(html_content, encoding="utf-8")
    print(f"✅ Generated static OpenAPI docs in '{target_dir}' directory.")


def cli_main() -> None:
    """CLI Entrypoint."""
    generate_static_docs()


if __name__ == "__main__":
    cli_main()
