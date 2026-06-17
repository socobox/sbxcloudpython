"""Offline tests for column-oriented response reconstruction + SBXResponse."""

from typing import Optional

from sbxpy.domain import SBXModel
from sbxpy.sbx import SBXResponse, column_to_objects


# matches the example in docs/FIND-SELECT-AND-ARRAY-TYPE.md
COLUMN_RESPONSE = {
    "headers": [
        "_KEY",
        "_META.created_time",
        "_META.updated_time",
        "variety_name",
        "inactive",
    ],
    "data": [
        ["abc-123", "2024-01-01T00:00:00.000Z", "2024-01-02T00:00:00.000Z", "Rose", False],
        ["def-456", "2024-01-03T00:00:00.000Z", "2024-01-04T00:00:00.000Z", "Tulip", False],
    ],
}


class Variety(SBXModel):
    _model = "variety"
    variety_name: Optional[str] = None
    inactive: Optional[bool] = None


def test_column_to_objects_reconstructs_with_nested_meta():
    rows = column_to_objects(COLUMN_RESPONSE)
    assert rows == [
        {
            "_KEY": "abc-123",
            "_META": {
                "created_time": "2024-01-01T00:00:00.000Z",
                "updated_time": "2024-01-02T00:00:00.000Z",
            },
            "variety_name": "Rose",
            "inactive": False,
        },
        {
            "_KEY": "def-456",
            "_META": {
                "created_time": "2024-01-03T00:00:00.000Z",
                "updated_time": "2024-01-04T00:00:00.000Z",
            },
            "variety_name": "Tulip",
            "inactive": False,
        },
    ]


def test_column_to_objects_passes_legacy_list_through():
    legacy = [{"_KEY": "x", "variety_name": "Rose"}]
    assert column_to_objects(legacy) is legacy


def test_column_to_objects_empty_page_returns_empty():
    assert column_to_objects({"headers": ["_KEY"], "data": []}) == []


def test_sbxresponse_keeps_results_raw():
    resp = SBXResponse(success=True, results=COLUMN_RESPONSE)
    # .results is untouched (raw column shape)
    assert resp.results == COLUMN_RESPONSE


def test_sbxresponse_accessors_handle_column_layout():
    resp = SBXResponse(success=True, results=COLUMN_RESPONSE)
    assert resp.has_results() is True
    objs = resp.to_objects()
    assert len(objs) == 2
    varieties = resp.all(Variety)
    assert [v.variety_name for v in varieties] == ["Rose", "Tulip"]
    first = resp.first(Variety)
    assert first.key == "abc-123"
    # _META is exposed via the `meta` alias
    assert first.meta is not None
    assert first.meta.created_time is not None


def test_sbxresponse_legacy_list_still_works():
    legacy = [{"_KEY": "k1", "variety_name": "Rose", "inactive": False}]
    resp = SBXResponse(success=True, results=legacy)
    assert resp.has_results() is True
    assert resp.all(Variety)[0].variety_name == "Rose"
    assert resp.first(Variety).key == "k1"


def test_merge_tolerates_mixed_layouts():
    legacy_page = {"success": True, "results": [{"_KEY": "k1", "variety_name": "Rose"}]}
    column_page = {"success": True, "results": COLUMN_RESPONSE}
    merged = SBXResponse.merge([legacy_page, column_page])
    assert merged.success is True
    # 1 legacy + 2 reconstructed
    assert len(merged.results) == 3
    assert all(isinstance(r, dict) for r in merged.results)


def _split_column_pages():
    """Split COLUMN_RESPONSE into two single-row column-oriented pages."""
    headers = COLUMN_RESPONSE["headers"]
    rows = COLUMN_RESPONSE["data"]
    return [
        {"success": True, "results": {"headers": headers, "data": [rows[0]]}, "fetched_results": {}},
        {"success": True, "results": {"headers": headers, "data": [rows[1]]}, "fetched_results": {}},
    ]


def test_find_merge_results_preserves_column_layout():
    """find_all over column pages must STAY column-oriented; data is concatenated."""
    from sbxpy import Find

    f = Find.__new__(Find)  # no real core needed for merge_results
    merged = f.merge_results(_split_column_pages())
    assert merged["success"] is True
    assert merged.get("array_type") == "column_oriented"
    assert isinstance(merged["results"], dict)
    assert merged["results"]["headers"] == COLUMN_RESPONSE["headers"]
    assert merged["results"]["data"] == COLUMN_RESPONSE["data"]  # both pages concatenated
    # caller converts explicitly when objects are wanted
    objs = column_to_objects(merged["results"])
    assert [o["_KEY"] for o in objs] == ["abc-123", "def-456"]
    assert SBXResponse(**merged).all(Variety)[1].variety_name == "Tulip"


def test_find_merge_results_object_pages_stay_list():
    """Object-array pages keep the legacy list shape."""
    from sbxpy import Find

    f = Find.__new__(Find)
    pages = [
        {"success": True, "results": [{"_KEY": "k0", "variety_name": "Iris"}], "fetched_results": {}},
        {"success": True, "results": [{"_KEY": "k1", "variety_name": "Rose"}], "fetched_results": {}},
    ]
    merged = f.merge_results(pages)
    assert "array_type" not in merged
    assert merged["results"] == [
        {"_KEY": "k0", "variety_name": "Iris"},
        {"_KEY": "k1", "variety_name": "Rose"},
    ]


def test_delete_key_extraction_works_on_column_pages():
    """The _KEY extraction used by delete() must survive column-oriented pages."""
    pages = [{"success": True, "results": COLUMN_RESPONSE}]
    keys = [row["_KEY"] for page in pages
            for row in column_to_objects(page.get("results"))]
    assert keys == ["abc-123", "def-456"]
