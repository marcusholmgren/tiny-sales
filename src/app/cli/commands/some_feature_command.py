# Placeholder for a feature-specific CLI command
import typer

command_app = typer.Typer()

@command_app.command("example")
def example_command(name: str):
    typer.echo(f"Hello from feature command: {name}")

if __name__ == "__main__":
    command_app()
