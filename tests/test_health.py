from datetime import datetime, timedelta, timezone

from arcgis_toolkit.health import LayerCheck, check_layer, evaluate

NOW = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)


def make_check(**overrides):
    values = dict(service="svc", layer="lyr", ok=True, feature_count=100,
                  response_ms=150.0, last_edit=NOW - timedelta(hours=3))
    values.update(overrides)
    return LayerCheck(**values)


def test_check_layer_reads_count_and_last_edit(make_layer):
    check = check_layer("svc", make_layer(count=42))
    assert check.ok and check.feature_count == 42
    assert check.last_edit is not None
    assert check.response_ms >= 0


def test_check_layer_reports_errors_instead_of_raising(make_layer):
    check = check_layer("svc", make_layer(fail=True))
    assert not check.ok
    assert "unavailable" in check.error


def test_ok():
    assert evaluate(make_check(), NOW).status == "OK"


def test_stale_when_data_is_old():
    status = evaluate(make_check(last_edit=NOW - timedelta(hours=72)), NOW, max_age_hours=48)
    assert status.status == "STALE"
    assert "72 h" in status.detail


def test_slow():
    assert evaluate(make_check(response_ms=5000), NOW, slow_ms=2000).status == "SLOW"


def test_error_wins_over_everything():
    status = evaluate(make_check(ok=False, error="boom", last_edit=NOW - timedelta(days=10)), NOW)
    assert status.status == "ERROR"


def test_missing_edit_date_is_ok_but_noted():
    status = evaluate(make_check(last_edit=None), NOW)
    assert status.status == "OK"
    assert "no edit date" in status.detail