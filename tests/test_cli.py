from typer.testing import CliRunner

from arcgis_toolkit import cli

runner = CliRunner()


def test_inventory_command(fake_gis, monkeypatch):
    monkeypatch.setattr(cli, "connect", lambda portal: fake_gis)
    result = runner.invoke(cli.app, ["inventory"])
    assert result.exit_code == 0, result.output
    assert "Big layer" in result.output
    assert "3 items" in result.output


def test_storage_report_command(fake_gis, monkeypatch):
    monkeypatch.setattr(cli, "connect", lambda portal: fake_gis)
    result = runner.invoke(cli.app, ["storage-report"])
    assert result.exit_code == 0, result.output
    assert "12.00" in result.output
    assert "20.0%" in result.output

from conftest import HOUR_MS, NOW_MS, gis_with


def test_health_ok(fake_gis, monkeypatch):
    monkeypatch.setattr(cli, "connect", lambda portal: fake_gis)
    result = runner.invoke(cli.app, ["health"])
    assert result.exit_code == 0, result.output
    assert "All layers healthy" in result.output


def test_health_fails_on_stale_data(make_item, make_layer, monkeypatch):
    stale = make_layer(last_edit_ms=NOW_MS - 100 * HOUR_MS)
    gis = gis_with([make_item(title="Daily layer", layers=[stale])])
    monkeypatch.setattr(cli, "connect", lambda portal: gis)
    result = runner.invoke(cli.app, ["health", "--max-age-hours", "26"])
    assert result.exit_code == 1
    assert "STALE" in result.output


def test_snapshot_then_validate_has_no_drift(fake_gis, monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "connect", lambda portal: fake_gis)
    path = tmp_path / "schema.json"
    assert runner.invoke(cli.app, ["schema-snapshot", "Big layer", str(path)]).exit_code == 0
    result = runner.invoke(cli.app, ["validate", str(path)])
    assert result.exit_code == 0, result.output
    assert "No schema drift" in result.output


def test_validate_detects_drift(fake_gis, monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "connect", lambda portal: fake_gis)
    path = tmp_path / "schema.json"
    runner.invoke(cli.app, ["schema-snapshot", "Big layer", str(path)])
    # Simulate an expected field that someone deleted from the live layer
    path.write_text(path.read_text().replace('"zone_id"', '"zone_code"'))
    result = runner.invoke(cli.app, ["validate", str(path)])
    assert result.exit_code == 1
    assert "zone_code" in result.output


def test_unknown_service_exits_with_code_2(fake_gis, monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "connect", lambda portal: fake_gis)
    result = runner.invoke(cli.app, ["schema-snapshot", "Nope", str(tmp_path / "x.json")])
    assert result.exit_code == 2