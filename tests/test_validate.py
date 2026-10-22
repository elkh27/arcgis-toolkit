from types import SimpleNamespace

from arcgis_toolkit.validate import compare, describe_layers

EXPECTED = {
    "hourly_forecast": {
        "geometryType": "esriGeometryPoint",
        "fields": {"OBJECTID": "esriFieldTypeOID", "ts_utc": "esriFieldTypeDate"},
        "timeField": "ts_utc",
    }
}


def actual(**changes):
    layer = {
        "geometryType": "esriGeometryPoint",
        "fields": {"OBJECTID": "esriFieldTypeOID", "ts_utc": "esriFieldTypeDate"},
        "timeField": "ts_utc",
    }
    layer.update(changes)
    return {"hourly_forecast": layer}


def messages(issues):
    return [(i.severity, i.message) for i in issues]


def test_identical_schema_has_no_issues():
    assert compare(EXPECTED, actual()) == []


def test_missing_field_is_an_error():
    issues = compare(EXPECTED, actual(fields={"OBJECTID": "esriFieldTypeOID"}))
    assert ("error", "field 'ts_utc' is missing") in messages(issues)


def test_changed_type_is_an_error():
    issues = compare(EXPECTED, actual(fields={"OBJECTID": "esriFieldTypeOID",
                                              "ts_utc": "esriFieldTypeString"}))
    assert issues[0].severity == "error"
    assert "esriFieldTypeString" in issues[0].message


def test_extra_field_is_a_warning():
    fields = {"OBJECTID": "esriFieldTypeOID", "ts_utc": "esriFieldTypeDate",
              "notes": "esriFieldTypeString"}
    assert messages(compare(EXPECTED, actual(fields=fields))) == [("warning", "unexpected field 'notes'")]


def test_lost_time_settings_is_an_error():
    issues = compare(EXPECTED, actual(timeField=None))
    assert any("time field" in i.message for i in issues)


def test_missing_layer():
    assert messages(compare(EXPECTED, {})) == [("error", "layer is missing")]


def test_describe_layers_from_fake_item(make_layer):
    item = SimpleNamespace(layers=[make_layer(name="zones", geometry="esriGeometryPolygon",
                                              time_field=None)])
    described = describe_layers(item)
    assert described["zones"]["geometryType"] == "esriGeometryPolygon"
    assert described["zones"]["fields"]["zone_id"] == "esriFieldTypeInteger"
    assert described["zones"]["timeField"] is None