from arcgis_toolkit.inventory import collect
from arcgis_toolkit.storage import credits_per_month, estimate, totals


def test_feature_storage_rate():
    # 50 MB of feature storage = 5 x 10 MB x 2.4 credits
    assert credits_per_month("feature", 50) == 12.0


def test_file_storage_rate():
    # 1 GB of file storage = 1.2 credits
    assert credits_per_month("file", 1000) == 1.2


def test_views_cost_nothing():
    assert credits_per_month("view", 500) == 0


def test_estimate_categories_and_order(fake_gis):
    lines = estimate(collect(fake_gis))
    assert lines[0].title == "Big layer"
    assert {line.title: line.category for line in lines} == {
        "Big layer": "feature", "A view": "view", "Web map": "file",
    }


def test_totals_against_location_platform_free_tier(fake_gis):
    t = totals(estimate(collect(fake_gis)))
    assert t["feature_mb"] == 50.0
    assert t["lp_feature_pct"] == 20.0   # 50 of 250 MB