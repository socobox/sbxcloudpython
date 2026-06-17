"""Offline tests for QueryBuilder / Find request-shape compatibility."""

from sbxpy.QueryBuilder import QueryBuilder as Qb


def _find_builder():
    # mimic Find: domain + model, default page/size, empty where
    return Qb().set_domain(129).set_model("variety")


def test_default_compile_has_no_new_keys():
    """Backward-compat #1: a plain query must not emit any of the new keys."""
    q = _find_builder().compile()
    assert q == {"domain": 129, "row_model": "variety", "page": 1, "size": 1000, "where": []}
    for new_key in ("select", "array_type", "timezone", "sort", "fields"):
        assert new_key not in q


def test_select_only_when_called():
    q = _find_builder().select(["variety_name", "inactive"]).compile()
    assert q["select"] == ["variety_name", "inactive"]


def test_select_empty_is_noop():
    q = _find_builder().select([]).compile()
    assert "select" not in q


def test_array_type():
    q = _find_builder().set_array_type("column_oriented").compile()
    assert q["array_type"] == "column_oriented"


def test_timezone():
    q = _find_builder().set_timezone("America/New_York").compile()
    assert q["timezone"] == "America/New_York"


def test_add_sort_uppercases_order_and_accumulates():
    q = (
        _find_builder()
        .add_sort("_META.updated", "desc")
        .add_sort("_META.created", "ASC")
        .compile()
    )
    assert q["sort"] == [
        {"field": "_META.updated", "order": "DESC"},
        {"field": "_META.created", "order": "ASC"},
    ]


def test_insert_builder_strips_find_only_keys():
    """compile() must drop find-only keys on an insert/rows payload."""
    q = Qb().set_domain(129).set_model("variety")
    # simulate accidental find-only keys present alongside rows
    q.select(["a"]).set_array_type("column_oriented").set_timezone("UTC").add_sort("a")
    q.add_object({"variety_name": "Rose"})
    compiled = q.compile()
    assert "rows" in compiled
    for find_only_key in ("select", "array_type", "timezone", "sort", "where", "order_by"):
        assert find_only_key not in compiled
