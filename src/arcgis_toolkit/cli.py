"""Command-line entry point: `arcgis-toolkit --help`."""
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from . import inventory as inv
from . import storage as st
from .connection import DEFAULT_PORTAL, connect

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


if __name__ == "__main__":
    app()