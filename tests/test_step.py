"""Offline tests for the STEP date-DSL builders."""

from sbxpy import Step
from sbxpy.timedsl import Step as StepDirect


def test_step_is_reexported_from_package():
    assert Step is StepDirect


def test_now():
    assert Step.now() == "${now}"
    assert Step.now("-7d") == "${now-7d}"
    assert Step.now("+2h") == "${now+2h}"


def test_last_and_roll():
    assert Step.last("7d") == "${last:7d}"
    assert Step.last("24:hours") == "${last:24:hours}"
    assert Step.last("week") == "${last:week}"
    assert Step.roll("24h") == "${roll:24h}"


def test_calendar_operators():
    assert Step.this("week") == "${this:week}"
    assert Step.next("monday") == "${next:monday}"
    assert Step.prev("month") == "${prev:month}"
    assert Step.start_of("day") == "${startOf:day}"
    assert Step.end_of("quarter") == "${endOf:quarter}"


def test_timezone_suffix():
    assert Step.start_of("day", tz="America/New_York") == "${startOf:day@America/New_York}"
    assert Step.this("week", tz="UTC") == "${this:week@UTC}"


def test_expr_escape_hatch():
    assert Step.expr("last 7 days") == "${last 7 days}"
    assert Step.expr("startOf:day", tz="Europe/London") == "${startOf:day@Europe/London}"
