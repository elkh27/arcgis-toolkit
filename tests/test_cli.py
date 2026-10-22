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