"""Process entry point: `python -m real_estate` — the Typer CLI (doc07)."""

from real_estate.composition import build_app


def main() -> None:
    build_app()()


if __name__ == "__main__":
    main()
