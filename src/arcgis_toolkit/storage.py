"""Estimate monthly storage cost per item.

Rates:
  - ArcGIS Online credits (Esri "Understand credits" documentation):
      feature storage 2.4 credits per 10 MB per month,
      file storage 1.2 credits per 1 GB per month.
  - ArcGIS Location Platform monthly free tier:
      250 MB feature storage, 250 MB file/attachment/tile storage.
"""
from dataclasses import dataclass

from .inventory import ItemRecord

FEATURE_CREDITS_PER_10MB = 2.4
FILE_CREDITS_PER_GB = 1.2
LP_FREE_FEATURE_MB = 250
LP_FREE_FILE_MB = 250

FEATURE_TYPES = {"Feature Service"}


@dataclass(frozen=True)
class StorageLine:
    title: str
    type: str
    category: str          # "feature", "file" or "view"
    size_mb: float
    credits_per_month: float


def categorize(record: ItemRecord) -> str:
    if record.is_view:
        return "view"      # views read another layer's data and are not billed for storage
    return "feature" if record.type in FEATURE_TYPES else "file"


def credits_per_month(category: str, size_mb: float) -> float:
    if category == "feature":
        return size_mb / 10 * FEATURE_CREDITS_PER_10MB
    if category == "file":
        return size_mb / 1000 * FILE_CREDITS_PER_GB
    return 0.0


def estimate(records: list[ItemRecord]) -> list[StorageLine]:
    lines = []
    for r in records:
        category = categorize(r)
        lines.append(StorageLine(r.title, r.type, category, r.size_mb,
                                 round(credits_per_month(category, r.size_mb), 3)))
    return sorted(lines, key=lambda line: line.credits_per_month, reverse=True)


def totals(lines: list[StorageLine]) -> dict[str, float]:
    feature_mb = sum(line.size_mb for line in lines if line.category == "feature")
    file_mb = sum(line.size_mb for line in lines if line.category == "file")
    return {
        "feature_mb": round(feature_mb, 2),
        "file_mb": round(file_mb, 2),
        "credits_per_month": round(sum(line.credits_per_month for line in lines), 2),
        "lp_feature_pct": round(feature_mb / LP_FREE_FEATURE_MB * 100, 1),
        "lp_file_pct": round(file_mb / LP_FREE_FILE_MB * 100, 1),
    }