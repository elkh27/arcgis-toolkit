import json
from datetime import datetime, timezone

import pytest

from arcgis_toolkit.backup import backup_service, backups_to_delete, verify

NOW = datetime(2026, 10, 22, 15, 30, tzinfo=timezone.utc)


@pytest.fixture
def service(make_item, make_layer):
    return make_item(id="abc", title="demo", layers=[
        make_layer(name="zones", count=3, geometry="esriGeometryPolygon", time_field=None),
        make_layer(name="hourly", count=5),
    ])


def test_backup_writes_layers_and_manifest(service, tmp_path):
    folder = backup_service(service, tmp_path, NOW)
    assert folder.name == "demo_20261022T153000Z"
    manifest = json.loads((folder / "manifest.json").read_text())
    assert [(e["layer"], e["features"]) for e in manifest["layers"]] == [("zones", 3), ("hourly", 5)]
    assert manifest["schema"]["zones"]["geometryType"] == "esriGeometryPolygon"
    assert (folder / "hourly.geojson").exists()


def test_backup_fails_when_features_are_lost(make_item, make_layer, tmp_path):
    item = make_item(title="demo", layers=[make_layer(count=10, returned=7)])
    with pytest.raises(RuntimeError, match="wrote 7 features but the server has 10"):
        backup_service(item, tmp_path, NOW)


def test_retention_keeps_newest_and_ignores_other_services(tmp_path):
    names = ["demo_20261020T000000Z", "demo_20261021T000000Z", "demo_20261022T000000Z",
             "demo_v2_20261019T000000Z", "notes"]
    for n in names:
        (tmp_path / n).mkdir()
    to_delete = backups_to_delete(list(tmp_path.iterdir()), "demo", keep=2)
    assert [p.name for p in to_delete] == ["demo_20261020T000000Z"]


def test_verify_passes_on_untouched_backup(service, tmp_path):
    assert verify(backup_service(service, tmp_path, NOW)) == []


def test_verify_detects_a_modified_file(service, tmp_path):
    folder = backup_service(service, tmp_path, NOW)
    path = folder / "zones.geojson"
    path.write_text(path.read_text().replace("-73.9", "-74.0"))
    assert any("checksum mismatch" in p for p in verify(folder))


def test_verify_detects_a_missing_file(service, tmp_path):
    folder = backup_service(service, tmp_path, NOW)
    (folder / "hourly.geojson").unlink()
    assert verify(folder) == ["hourly.geojson is missing"]
