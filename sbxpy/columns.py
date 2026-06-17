"""Column-oriented find-response reconstruction (shared, dependency-free).

Lives in a leaf module so both ``sbxpy.Find`` (page merging) and ``sbxpy.sbx``
(``SBXResponse``) can use one implementation without a circular import.
"""

from typing import List


def column_to_objects(results) -> List[dict]:
    """Reconstruct object-array rows from a column-oriented find response.

    ``results`` is either a legacy list (returned as-is) or the column-oriented
    ``{"headers": [...], "data": [[...], ...]}`` shape. ``_META.*`` headers are
    nested back under a ``_META`` object so the rows match the legacy layout.
    ``None`` / unexpected shapes yield an empty list.
    """
    if not isinstance(results, dict) or "headers" not in results or "data" not in results:
        return results if isinstance(results, list) else []
    headers = results["headers"]
    rows: List[dict] = []
    for row in results["data"]:
        obj: dict = {}
        for h, v in zip(headers, row):
            if h.startswith("_META."):
                obj.setdefault("_META", {})[h[len("_META."):]] = v
            else:
                obj[h] = v
        rows.append(obj)
    return rows
