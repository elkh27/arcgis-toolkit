"""Shared test fixtures: fake ArcGIS objects, so tests never touch the network."""
from types import SimpleNamespace

import pytest


@pytest.fixture
def make_item():
    def _make(**overrides):
        item = dict(
            id="item1", title="Layer", type="Feature Service", owner="ellie",
            access="private", size=5_000_000, typeKeywords=[],
            created=1_700_000_000_000, modified=1_760_000_000_000,
            numViews=3, url="https://example.com/layer",
        )
        item.update(overrides)
        return SimpleNamespace(**item)
    return _make


@pytest.fixture
def fake_gis(make_item):
    items = [
        make_item(id="1", title="Big layer", size=50_000_000),
        make_item(id="2", title="A view", size=0, typeKeywords=["View Service"]),
        make_item(id="3", title="Web map", type="Web Map", size=20_000),
    ]

    def search(query, item_type=None, max_items=10_000):
        assert query == "orgid:ORG123"
        return [i for i in items if item_type in (None, i.type)]

    return SimpleNamespace(
        content=SimpleNamespace(search=search),
        users=SimpleNamespace(me=SimpleNamespace(orgId="ORG123", username="ellie")),
    )