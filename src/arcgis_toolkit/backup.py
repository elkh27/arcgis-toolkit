"""Back up hosted feature layers to local GeoJSON files, with a manifest for verification."""
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from .validate import describe_layers

STAMP_FORMAT = "%Y%m%dT%H%M%SZ"


def _geojson_text(feature_set) -> str:
    # FeatureSet.to_geojson is a property in arcgis 2.x; accept a method too, to be safe
    gj = feature_set.to_geojson
    return gj() if callable(gj) else gj


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def backup_service(item, out_dir: Path, now: datetime) -> Path:
    """Write every layer of the service to GeoJSON plus a manifest. Returns the backup folder."""
    folder = out_dir / f"{item.title}_{now.strftime(STAMP_FORMAT)}"
    folder.mkdir(parents=True)

    entries = []
    for layer in item.layers:
        name = layer.properties["name"]
        expected = layer.query(where="1=1", return_count_only=True)
        text = _geojson_text(layer.query(where="1=1", out_sr=4326))
        written = len(json.loads(text)["features"])
        # A partial backup is worse than none, because it looks like protection
        if written != expected:
            raise RuntimeError(f"{name}: wrote {written} features but the server has {expected}")

        path = folder / f"{name}.geojson"
        path.write_text(text)
        entries.append({"layer": name, "file": path.name, "features": written,
                        "bytes": path.stat().st_size, "sha256": _sha256(path)})

    manifest = {
        "service": item.title,
        "item_id": item.id,
        "created_utc": now.isoformat(),
        "layers": entries,
        "schema": describe_layers(item),
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return folder


def backups_to_delete(folders: list[Path], service: str, keep: int) -> list[Path]:
    """Backups of this service older than the newest `keep`. Other services are never touched."""
    pattern = re.compile(rf"{re.escape(service)}_\d{{8}}T\d{{6}}Z")
    mine = sorted(f for f in folders if f.is_dir() and pattern.fullmatch(f.name))
    return mine[:-keep] if len(mine) > keep else []


def verify(folder: Path) -> list[str]:
    """Check that every file in the manifest exists, is unchanged and has the right feature count."""
    manifest_path = folder / "manifest.json"
    if not manifest_path.exists():
        return ["manifest.json is missing"]
    manifest = json.loads(manifest_path.read_text())

    problems = []
    for entry in manifest["layers"]:
        path = folder / entry["file"]
        if not path.exists():
            problems.append(f"{entry['file']} is missing")
            continue
        if _sha256(path) != entry["sha256"]:
            problems.append(f"{entry['file']} has changed since the backup (checksum mismatch)")
        elif len(json.loads(path.read_text())["features"]) != entry["features"]:
            problems.append(f"{entry['file']} has the wrong number of features")
    return problems
