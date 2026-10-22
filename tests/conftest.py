"""Shared test fixtures: fake ArcGIS objects, so tests never touch the network."""
import json
import time
from types import SimpleNamespace

import pytest

NOW_MS = int(time.time() * 1000)
HOUR_MS = 3_600_000


@pytest.fixture
def make_layer():
    def _make(name="hourly_forecast", count=100, last_edit_ms=NOW_MS - HOUR_MS,
              geometry="esriGeometryPoint", fields=None, time_field="ts_utc",
              fail=False, returned=None):
        props = {
            "name": name,
            "geometryType": geometry,
            "fields": fields or [
                {"name": "OBJECTID", "type": "esriFieldTypeOID"},
                {"name": "zone_id", "type": "esriFieldTypeInteger"},
                {"name": "ts_utc", "type": "esriFieldTypeDate"},
            ],
            "timeInfo": {"startTimeField": time_field} if time_field else None,
            "editingInfo": {"lastEditDate": last_edit_ms} if last_edit_ms else None,
        }

        def query(where="1=1", return_count_only=False, **kwargs):
            if fail:
                raise RuntimeError("Service unavailable")
            if return_count_only:
                return count
            # `returned` lets a test simulate a query that silently loses features
            n = count if returned is None else returned
            fc = {"type": "FeatureCollection", "features": [
                {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-73.9, 40.7]},
                 "properties": {"zone_id": i}} for i in range(n)]}
            return SimpleNamespace(features=[None] * n, to_geojson=json.dumps(fc))

        return SimpleNamespace(properties=props, query=query)
    return _make


@pytest.fixture
def make_item():
    def _make(**overrides):
        item = dict(
            id="item1", title="Layer", type="Feature Service", owner="ellie",
            access="private", size=5_000_000, typeKeywords=[],
            created=1_700_000_000_000, modified=1_760_000_000_000,
            numViews=3, url="https://example.com/layer", layers=[],
        )
        item.update(overrides)
        return SimpleNamespace(**item)
    return _make


def gis_with(items):
    """A fake GIS whose content search returns the given items."""
    def search(query, item_type=None, max_items=10_000):
        assert query == "orgid:ORG123"
        return [i for i in items if item_type in (None, i.type)]

    return SimpleNamespace(
        content=SimpleNamespace(search=search),
        users=SimpleNamespace(me=SimpleNamespace(orgId="ORG123", username="ellie")),
    )


@pytest.fixture
def fake_gis(make_item, make_layer):
    return gis_with([
        make_item(id="1", title="Big layer", size=50_000_000, layers=[make_layer()]),
        make_item(id="2", title="A view", size=0, typeKeywords=["View Service"],
                  layers=[make_layer(name="view_layer")]),
        make_item(id="3", title="Web map", type="Web Map", size=20_000),
    ])
