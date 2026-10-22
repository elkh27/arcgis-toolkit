"""Command-line entry point: `arcgis-toolkit --help`."""
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from . import inventory as inv
from . import storage as st
from .connection import DEFAULT_PORTAL, connect
from datetime import datetime, timezone

from . import health as hl
from . import validate as vd
from .services import find_service, org_feature_services

app = typer.Typer(help="Admin toolkit for ArcGIS Online and ArcGIS Location Platform.",
                  no_args_is_help=True)
console = Console()

PortalOption = typer.Option(DEFAULT_PORTAL, "--portal", help="Portal URL")


@app.command()
def inventory(
    item_type: Optional[str] = typer.Option(None, "--type", help='Only this item type, e.g. "Feature Service"'),
    csv_path: Optional[Path] = typer.Option(None, "--csv", help="Also save the inventory to a CSV file"),
    portal: str = PortalOption,
):
    """List every item in the organization with owner, access, size and dates."""
    records = inv.collect(connect(portal), item_type)

    table = Table(title=f"Inventory: {len(records)} items")
    for col in ("Title", "Type", "Owner", "Access", "Size (MB)", "Modified", "Views"):
        table.add_column(col, justify="right" if col in ("Size (MB)", "Views") else "left")
    for r in records:
        table.add_row(r.title, r.type + (" (view)" if r.is_view else ""), r.owner, r.access,
                      f"{r.size_mb:.2f}", r.modified, str(r.views))
    console.print(table)

    summary = Table(title="By type")
    for col in ("Type", "Items", "Total (MB)"):
        summary.add_column(col)
    for item_type_name, count, size in inv.summarize_by_type(records):
        summary.add_row(item_type_name, str(count), f"{size:.2f}")
    console.print(summary)

    if csv_path:
        inv.write_csv(records, csv_path)
        console.print(f"[green]Saved {csv_path}[/green]")


@app.command("storage-report")
def storage_report(portal: str = PortalOption):
    """Estimate monthly storage cost: ArcGIS Online credits and Location Platform free-tier use."""
    lines = st.estimate(inv.collect(connect(portal)))

    table = Table(title="Storage by item")
    for col in ("Title", "Type", "Category", "Size (MB)", "Credits / month"):
        table.add_column(col)
    for line in lines:
        table.add_row(line.title, line.type, line.category,
                      f"{line.size_mb:.2f}", f"{line.credits_per_month:.2f}")
    console.print(table)

    t = st.totals(lines)
    console.print(f"Feature storage: {t['feature_mb']} MB "
                  f"({t['lp_feature_pct']}% of the Location Platform free tier)")
    console.print(f"File storage:    {t['file_mb']} MB "
                  f"({t['lp_file_pct']}% of the Location Platform free tier)")
    console.print(f"[bold]If this were ArcGIS Online: ~{t['credits_per_month']} credits / month[/bold]")

STATUS_STYLE = {"OK": "green", "SLOW": "yellow", "STALE": "red", "ERROR": "bold red"}


@app.command()
def health(
    service: Optional[str] = typer.Option(None, "--service", help="Only check this service title"),
    max_age_hours: float = typer.Option(48, help="Flag layers whose data is older than this"),
    slow_ms: float = typer.Option(2000, help="Flag layers slower than this to answer a count query"),
    portal: str = PortalOption,
):
    """Check that every hosted feature layer responds, how fast, and whether its data is fresh.

    Exits with code 1 if any layer is in ERROR or STALE, so it can drive alerts in CI.
    """
    gis = connect(portal)
    now = datetime.now(timezone.utc)
    results = [hl.evaluate(c, now, max_age_hours, slow_ms)
               for c in hl.check_services(org_feature_services(gis, service))]

    table = Table(title=f"Health check: {len(results)} layers")
    for col in ("Service", "Layer", "Status", "Response (ms)", "Last data edit (UTC)", "Detail"):
        table.add_column(col)
    for r in results:
        c = r.check
        table.add_row(
            c.service, c.layer, f"[{STATUS_STYLE[r.status]}]{r.status}[/]",
            f"{c.response_ms:.0f}" if c.response_ms is not None else "-",
            c.last_edit.strftime("%Y-%m-%d %H:%M") if c.last_edit else "-",
            r.detail,
        )
    console.print(table)

    problems = [r for r in results if r.status in ("ERROR", "STALE")]
    if problems:
        console.print(f"[red]{len(problems)} layer(s) need attention[/red]")
        raise typer.Exit(code=1)
    console.print("[green]All layers healthy[/green]")


@app.command("schema-snapshot")
def schema_snapshot(
    service: str = typer.Argument(..., help="Feature service title"),
    output: Path = typer.Argument(..., help="JSON file to write"),
    portal: str = PortalOption,
):
    """Save a service's current schema as the expected definition."""
    try:
        item = find_service(connect(portal), service)
    except LookupError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2)
    layers = vd.describe_layers(item)
    vd.write_schema(item.title, layers, output)
    console.print(f"[green]Saved schema of {len(layers)} layer(s) to {output}[/green]")


@app.command()
def validate(
    schema_file: Path = typer.Argument(..., exists=True, help="Expected schema JSON"),
    portal: str = PortalOption,
):
    """Compare a service's live schema with the expected definition and report drift.

    Exits with code 1 if any error-level difference is found.
    """
    expected = vd.read_schema(schema_file)
    try:
        item = find_service(connect(portal), expected["service"])
    except LookupError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2)

    issues = vd.compare(expected["layers"], vd.describe_layers(item))
    if not issues:
        console.print(f"[green]No schema drift in {expected['service']}[/green]")
        return

    table = Table(title=f"Schema drift in {expected['service']}")
    for col in ("Severity", "Layer", "Issue"):
        table.add_column(col)
    for i in issues:
        style = "red" if i.severity == "error" else "yellow"
        table.add_row(f"[{style}]{i.severity}[/]", i.layer, i.message)
    console.print(table)

    if any(i.severity == "error" for i in issues):
        raise typer.Exit(code=1)
if __name__ == "__main__":
    app()