"""Live smoke test for the additive find features.

Requires env vars: SBX_DOMAIN, SBX_APP_KEY, SBX_TOKEN, SBX_HOST.
Set MODEL (and optionally a SELECT field) for your domain, then run:

    uv run scripts/smoke_find_features.py

It exercises: baseline find(), select()+column_oriented() with to_objects()
reconstruction, a _META.updated STEP filter with sort_by(), and find_old().
"""

import asyncio
import os

from sbxpy import SbxCore, Step
from sbxpy.sbx import SBXResponse

MODEL = os.environ.get("SMOKE_MODEL", "")  # set to a real model in your domain
SELECT_FIELD = os.environ.get("SMOKE_SELECT_FIELD")  # optional single field name


def _core() -> SbxCore:
    core = SbxCore()
    core.initialize(
        os.environ["SBX_DOMAIN"], os.environ["SBX_APP_KEY"], os.environ["SBX_HOST"]
    )
    core.headers["Authorization"] = "Bearer " + os.environ["SBX_TOKEN"]
    return core


async def main():
    missing = [v for v in ("SBX_DOMAIN", "SBX_APP_KEY", "SBX_TOKEN", "SBX_HOST") if not os.environ.get(v)]
    if missing or not MODEL:
        print(f"SKIP: missing env {missing or ''} / SMOKE_MODEL not set")
        return

    core = _core()

    # 1) baseline find (no new keys) — confirms no regression
    base = await core.with_model(MODEL).set_page_size(5).find()
    print("1) find() success:", base.get("success"), "rows:", len(SBXResponse(**base).to_objects()))

    # 2) select + column_oriented single-page read, reconstructed via to_objects()
    q2 = core.with_model(MODEL).set_page_size(5).column_oriented()
    if SELECT_FIELD:
        q2 = q2.select(SELECT_FIELD)
    resp2 = await q2.find()
    objs = SBXResponse(**resp2).to_objects()
    print("2) column_oriented success:", resp2.get("success"),
          "raw results type:", type(resp2.get("results")).__name__,
          "reconstructed rows:", len(objs))

    # 3) _META.updated >= last 7 days, sorted desc by _META.updated
    resp3 = await (
        core.with_model(MODEL)
        .set_page_size(5)
        .and_where_updated_after(Step.last("7d"))
        .sort_by("_META.updated", "DESC")
        .find()
    )
    print("3) _META + STEP find() success:", resp3.get("success"),
          "rows:", len(SBXResponse(**resp3).to_objects()))

    # 4) same against legacy find/old
    resp4 = await core.with_model(MODEL).set_page_size(5).find_old()
    print("4) find_old() success:", resp4.get("success"),
          "rows:", len(SBXResponse(**resp4).to_objects()))


if __name__ == "__main__":
    asyncio.run(main())
