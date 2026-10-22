"""Collect a flat inventory of all content in the signed-in user's organization."""
import csv
from collections import defaultdict
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from pathlib import Path


def _ms_to_date(ms) -> str:
    """ArcGIS timestamps are milliseconds since the Unix epoch (UTC)."""
    if not ms:
        return ""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


@dataclass(frozen=True)
class ItemRecord:
    id: str
    title: str
    type: str
    owner: str
    access: str
    size_mb: float
    is_view: bool
    created: str
    modified: str
    views: int
    url: str

    @classmethod
    def from_item(cls, item) -> "ItemRecord":
        """Build a record from an arcgis Item (or any object with the same attributes)."""
        size = getattr(item, "size", 0) or 0
        keywords = getattr(item, "typeKeywords", None) or []
        return cls(
            id=item.id,
            title=item.title,
            type=item.type,
            owner=getattr(item, "owner", ""),
            access=getattr(item, "access", ""),
            size_mb=round(max(size, 0) / 1_000_000, 3),  # size can be missing or -1
            is_view="View Service" in keywords,
            created=_ms_to_date(getattr(item, "created", None)),
            modified=_ms_to_date(getattr(item, "modified", None)),
            views=int(getattr(item, "numViews", 0) or 0),
            url=getattr(item, "url", "") or "",
        )


def collect(gis, item_type: str | None = None, max_items: int = 10_000) -> list[ItemRecord]:
    """Return every item in the organization, largest first."""
    org_id = gis.users.me.orgId
    items = gis.content.search(query=f"orgid:{org_id}", item_type=item_type, max_items=max_items)
    records = [ItemRecord.from_item(i) for i in items]
    return sorted(records, key=lambda r: r.size_mb, reverse=True)


def summarize_by_type(records: list[ItemRecord]) -> list[tuple[str, int, float]]:
    """Count and total size per item type, largest total first."""
    counts: dict[str, int] = defaultdict(int)
    sizes: dict[str, float] = defaultdict(float)
    for r in records:
        counts[r.type] += 1
        sizes[r.type] += r.size_mb
    return sorted(((t, counts[t], round(sizes[t], 3)) for t in counts),
                  key=lambda row: row[2], reverse=True)


def write_csv(records: list[ItemRecord], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[fld.name for fld in fields(ItemRecord)])
        writer.writeheader()
        writer.writerows(asdict(r) for r in records)