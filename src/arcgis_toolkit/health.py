"""Check that hosted feature layers respond, how fast, and whether their data is fresh."""
import time
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class LayerCheck:
    service: str
    layer: str
    ok: bool
    feature_count: int | None
    response_ms: float | None
    last_edit: datetime | None
    error: str = ""


@dataclass(frozen=True)
class LayerStatus:
    check: LayerCheck
    status: str   # OK, SLOW, STALE or ERROR
    detail: str


def check_layer(service_title: str, layer) -> LayerCheck:
    """Run a count query and read the last data edit. Failures are reported, never raised."""
    name = "?"
    try:
        props = layer.properties
        name = props.get("name", "?")
        start = time.perf_counter()
        count = layer.query(where="1=1", return_count_only=True)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # editingInfo.lastEditDate tracks data edits; the item's "modified" date does not
        last_ms = (props.get("editingInfo") or {}).get("lastEditDate")
        last_edit = datetime.fromtimestamp(last_ms / 1000, tz=timezone.utc) if last_ms else None
        return LayerCheck(service_title, name, True, int(count), round(elapsed_ms, 1), last_edit)
    except Exception as exc:
        return LayerCheck(service_title, name, False, None, None, None, str(exc)[:200])


def check_services(items) -> list[LayerCheck]:
    checks = []
    for item in items:
        try:
            layers = item.layers
        except Exception as exc:
            checks.append(LayerCheck(item.title, "(service)", False, None, None, None, str(exc)[:200]))
            continue
        checks.extend(check_layer(item.title, layer) for layer in layers)
    return checks


def evaluate(check: LayerCheck, now: datetime,
             max_age_hours: float = 48, slow_ms: float = 2000) -> LayerStatus:
    """Turn raw measurements into a status. Order matters: ERROR > STALE > SLOW > OK."""
    if not check.ok:
        return LayerStatus(check, "ERROR", check.error)
    if check.last_edit is not None:
        age_hours = (now - check.last_edit).total_seconds() / 3600
        if age_hours > max_age_hours:
            return LayerStatus(check, "STALE", f"last data edit {age_hours:.0f} h ago")
    if check.response_ms > slow_ms:
        return LayerStatus(check, "SLOW", f"count query took {check.response_ms:.0f} ms")
    detail = f"{check.feature_count:,} features"
    if check.last_edit is None:
        detail += ", no edit date recorded"
    return LayerStatus(check, "OK", detail)
