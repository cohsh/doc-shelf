from __future__ import annotations

import json
import logging
from pathlib import Path

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from doc_shelf import eml_extractor, library, pdf_extractor, reader_claude, reader_codex, storage
from doc_shelf.exceptions import DocShelfError, ReaderError, StorageError

console = Console()
logger = logging.getLogger("doc-shelf")


@click.group()
@click.option("--verbose", is_flag=True, help="Show detailed progress")
def cli(verbose: bool) -> None:
    """Doc Shelf - Organize and browse PDF/EML documents."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(message)s")


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option(
    "--reader",
    type=click.Choice(["none", "claude", "codex", "both"]),
    default="both",
    help="Which reader(s) to run",
)
@click.option("--shelf", "shelf_ids", multiple=True, help="Assign to shelf(s)")
@click.option("--output-dir", type=click.Path(), default="library", help="Output directory")
def add(
    file_path: str,
    reader: str,
    shelf_ids: tuple[str, ...],
    output_dir: str,
) -> None:
    """Add a PDF or EML document to the library."""
    extension = Path(file_path).suffix.lower()
    file_label = "PDF" if extension == ".pdf" else "EML" if extension == ".eml" else "document"
    console.print(f"[bold]Extracting text from {file_label}:[/bold] {file_path}")
    try:
        if extension == ".pdf":
            document = pdf_extractor.extract(file_path)
        elif extension == ".eml":
            document = eml_extractor.extract(file_path)
        else:
            console.print("[red]Error:[/red] Only PDF and EML files are supported.")
            raise SystemExit(1)
    except DocShelfError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)

    console.print(f"  Pages: {document.page_count}, Characters: {document.char_count}")
    readings: dict[str, dict] = {}

    if reader in ("claude", "both"):
        console.print("\n[bold blue]Running Claude reader...[/bold blue]")
        try:
            readings["claude"] = reader_claude.read(document)
            console.print("  [green]Claude reading complete.[/green]")
        except ReaderError as e:
            console.print(f"  [yellow]Claude reader failed:[/yellow] {e}")
            if reader == "claude":
                raise SystemExit(1)

    if reader in ("codex", "both"):
        console.print("\n[bold green]Running Codex reader...[/bold green]")
        try:
            readings["codex"] = reader_codex.read(document)
            console.print("  [green]Codex reading complete.[/green]")
        except ReaderError as e:
            console.print(f"  [yellow]Codex reader failed:[/yellow] {e}")
            if reader == "codex":
                raise SystemExit(1)

    if reader != "none" and not readings:
        console.print("[red]Error: No reader produced results.[/red]")
        raise SystemExit(1)

    console.print("\n[bold]Saving document...[/bold]")
    try:
        document_id = storage.save(
            document,
            output_dir,
            source_name=file_path,
            readings=readings,
        )
        library.update_index(
            document_id,
            output_dir,
            shelves=list(shelf_ids) if shelf_ids else None,
        )
    except DocShelfError as e:
        console.print(f"[red]Error saving:[/red] {e}")
        raise SystemExit(1)

    console.print(f"\n[bold green]Done![/bold green] Document ID: [cyan]{document_id}[/cyan]")
    if readings:
        console.print(f"  Readers:  {', '.join(readings.keys())}")
    console.print(f"  JSON:     {output_dir}/json/{document_id}.json")
    console.print(f"  Markdown: {output_dir}/markdown/{document_id}.md")


@cli.command("list")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format",
)
@click.option(
    "--sort",
    "sort_by",
    type=click.Choice(["title", "date", "pages"]),
    default="date",
    help="Sort order",
)
@click.option("--shelf", "shelf_id", default=None, help="Filter by shelf ID")
@click.option("--output-dir", type=click.Path(), default="library", help="Library directory")
def list_documents(fmt: str, sort_by: str, shelf_id: str | None, output_dir: str) -> None:
    """List documents in the library."""
    documents = library.list_documents_by_shelf(shelf_id, output_dir)

    if not documents:
        console.print("No documents in the library yet.")
        return

    if sort_by == "title":
        documents.sort(key=lambda d: d.get("title", "").lower())
    elif sort_by == "date":
        documents.sort(key=lambda d: d.get("uploaded_date", ""), reverse=True)
    elif sort_by == "pages":
        documents.sort(key=lambda d: d.get("page_count", 0), reverse=True)

    if fmt == "json":
        console.print(json.dumps(documents, ensure_ascii=False, indent=2))
        return

    table = Table(title="Doc Shelf")
    table.add_column("Title", style="cyan", max_width=50)
    table.add_column("Author", max_width=30)
    table.add_column("Pages", justify="center")
    table.add_column("Uploaded", justify="center")
    table.add_column("Readers", justify="center")

    for d in documents:
        table.add_row(
            d.get("title", "Untitled"),
            d.get("author", "Unknown"),
            str(d.get("page_count", 0)),
            d.get("uploaded_date", ""),
            ", ".join(d.get("readers_used", [])),
        )

    console.print(table)


@cli.command()
@click.argument("query")
@click.option(
    "--field",
    type=click.Choice(
        ["title", "author", "subject", "tags", "text", "readers", "readings", "all"]
    ),
    default="all",
    help="Search field",
)
@click.option("--shelf", "shelf_id", default=None, help="Filter by shelf ID")
@click.option("--output-dir", type=click.Path(), default="library", help="Library directory")
def search(query: str, field: str, shelf_id: str | None, output_dir: str) -> None:
    """Search documents in the library."""
    results = library.search(query, field=field, output_dir=output_dir, shelf=shelf_id)

    if not results:
        console.print(f"No documents found for query: '{query}'")
        return

    console.print(f"Found {len(results)} document(s):\n")
    for d in results:
        console.print(f"  [cyan]{d['document_id']}[/cyan]")
        console.print(f"    {d.get('title', 'Untitled')}")
        console.print(f"    {d.get('author', 'Unknown')} | {d.get('uploaded_date', '?')}")
        console.print()


@cli.command()
@click.argument("document_id")
@click.option("--raw", is_flag=True, help="Show raw markdown instead of rendered")
@click.option("--output-dir", type=click.Path(), default="library", help="Library directory")
def show(document_id: str, raw: bool, output_dir: str) -> None:
    """Show a document's markdown summary."""
    import os

    md_path = os.path.join(output_dir, "markdown", f"{document_id}.md")
    if not os.path.exists(md_path):
        console.print(f"[red]Document not found:[/red] {document_id}")
        raise SystemExit(1)

    with open(md_path, encoding="utf-8") as f:
        content = f.read()

    if raw:
        console.print(content)
    else:
        console.print(Markdown(content))


@cli.group()
def shelf() -> None:
    """Manage shelves."""


cli.add_command(shelf)


@shelf.command("list")
@click.option("--output-dir", type=click.Path(), default="library", help="Library directory")
def shelf_list(output_dir: str) -> None:
    """List all shelves."""
    shelves = library.list_shelves(output_dir)
    table = Table(title="Shelves")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("名前 (Ja)")
    table.add_column("Documents", justify="center")

    for s in shelves:
        label = s["shelf_id"]
        if s.get("is_virtual"):
            label += " (virtual)"
        table.add_row(
            label,
            s["name"],
            s.get("name_ja", ""),
            str(s.get("document_count", 0)),
        )

    console.print(table)


@shelf.command("create")
@click.argument("name")
@click.option("--name-ja", default="", help="Japanese name")
@click.option("--output-dir", type=click.Path(), default="library", help="Library directory")
def shelf_create(name: str, name_ja: str, output_dir: str) -> None:
    """Create a new shelf."""
    try:
        shelf_data = library.create_shelf(name, output_dir, name_ja=name_ja)
        console.print(
            f"[green]Created shelf:[/green] {shelf_data['shelf_id']} ({shelf_data['name']})"
        )
    except StorageError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@shelf.command("rename")
@click.argument("shelf_id")
@click.argument("new_name")
@click.option("--name-ja", default=None, help="New Japanese name")
@click.option("--output-dir", type=click.Path(), default="library", help="Library directory")
def shelf_rename(shelf_id: str, new_name: str, name_ja: str | None, output_dir: str) -> None:
    """Rename a shelf."""
    try:
        shelf_data = library.rename_shelf(shelf_id, new_name, output_dir, name_ja=name_ja)
        console.print(
            f"[green]Renamed to:[/green] {shelf_data['shelf_id']} ({shelf_data['name']})"
        )
    except StorageError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@shelf.command("delete")
@click.argument("shelf_id")
@click.option("--output-dir", type=click.Path(), default="library", help="Library directory")
def shelf_delete(shelf_id: str, output_dir: str) -> None:
    """Delete a shelf. Documents in the shelf become unsorted."""
    try:
        library.delete_shelf(shelf_id, output_dir)
        console.print(f"[green]Deleted shelf:[/green] {shelf_id}")
    except StorageError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@shelf.command("assign")
@click.argument("document_id")
@click.argument("shelf_ids", nargs=-1, required=True)
@click.option("--output-dir", type=click.Path(), default="library", help="Library directory")
def shelf_assign(document_id: str, shelf_ids: tuple[str, ...], output_dir: str) -> None:
    """Assign a document to shelves (replaces existing assignment)."""
    try:
        library.assign_document_to_shelves(document_id, list(shelf_ids), output_dir)
        console.print(
            f"[green]Assigned {document_id} to:[/green] {', '.join(shelf_ids)}"
        )
    except StorageError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@cli.command()
@click.option("--host", default="127.0.0.1", help="Bind host")
@click.option("--port", default=8000, type=int, help="Bind port")
@click.option("--output-dir", type=click.Path(), default="library", help="Library directory")
@click.option("--dev", is_flag=True, help="Enable CORS for Vite dev server on port 5173")
def serve(host: str, port: int, output_dir: str, dev: bool) -> None:
    """Start the web interface."""
    import uvicorn

    from doc_shelf.server.app import create_app

    app = create_app(output_dir=output_dir, dev_mode=dev)
    console.print("[bold]Starting Doc Shelf web UI[/bold]")
    console.print(f"  http://{host}:{port}")
    console.print(f"  Library: {output_dir}")
    if dev:
        console.print("  [yellow]Dev mode: CORS enabled for http://localhost:5173[/yellow]")

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    cli()
