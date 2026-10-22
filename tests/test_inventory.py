from arcgis_toolkit.inventory import ItemRecord, collect, summarize_by_type, write_csv


def test_record_converts_units_and_dates(make_item):
    r = ItemRecord.from_item(make_item(size=5_000_000, created=1_700_000_000_000))
    assert r.size_mb == 5.0
    assert r.created == "2023-11-14"


def test_missing_or_negative_size_becomes_zero(make_item):
    assert ItemRecord.from_item(make_item(size=None)).size_mb == 0
    assert ItemRecord.from_item(make_item(size=-1)).size_mb == 0


def test_view_detected_from_type_keywords(make_item):
    assert ItemRecord.from_item(make_item(typeKeywords=["View Service"])).is_view
    assert not ItemRecord.from_item(make_item()).is_view


def test_collect_sorts_largest_first(fake_gis):
    titles = [r.title for r in collect(fake_gis)]
    assert titles[0] == "Big layer"
    assert len(titles) == 3


def test_collect_filters_by_type(fake_gis):
    records = collect(fake_gis, item_type="Web Map")
    assert [r.title for r in records] == ["Web map"]


def test_summary_by_type(fake_gis):
    summary = dict((t, (n, mb)) for t, n, mb in summarize_by_type(collect(fake_gis)))
    assert summary["Feature Service"] == (2, 50.0)


def test_write_csv(fake_gis, tmp_path):
    path = tmp_path / "inventory.csv"
    write_csv(collect(fake_gis), path)
    lines = path.read_text().splitlines()
    assert lines[0].startswith("id,title,type")
    assert len(lines) == 4