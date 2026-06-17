"""
STEP date DSL builders for SBXCloud find queries.

STEP (SBX Time Expression Protocol) lets you express moving date boundaries that
the server evaluates at query time. Only values wrapped in ``${...}`` are
evaluated; plain strings are treated literally. These builders just produce those
``${...}`` strings — nothing is sent to the server unless you pass the result into
a WHERE value (e.g. ``Find.and_where_greater_or_equal_than("_META.updated", Step.last("7d"))``).

Backward compatibility: an old server that does not understand STEP will treat the
``${...}`` string as a literal value. Using STEP is therefore an explicit caller
choice; the library never injects these expressions implicitly.

See ``docs/DATES-QUERY-DSL.md`` for the full grammar.

Examples
--------
>>> Step.now()
'${now}'
>>> Step.now("-7d")
'${now-7d}'
>>> Step.last("7d")
'${last:7d}'
>>> Step.this("week")
'${this:week}'
>>> Step.start_of("day", tz="America/New_York")
'${startOf:day@America/New_York}'
>>> Step.expr("last 7 days")
'${last 7 days}'
"""


class Step:
    """Static-method builders that return STEP ``${...}`` expression strings.

    Rolling operators (``now``/``last``/``roll``) are absolute offsets from *now*
    and never take a timezone. Calendar operators (``this``/``next``/``prev``/
    ``start_of``/``end_of``) accept an optional IANA ``tz`` that is appended as
    ``@IANA`` and overrides any request-level timezone.
    """

    @staticmethod
    def now(offset=None):
        """Current server time, optionally offset, e.g. ``Step.now('-7d')``."""
        return f"${{now{offset or ''}}}"

    @staticmethod
    def last(duration):
        """Rolling lookback or calendar shortcut, e.g. ``'7d'``, ``'24:hours'``, ``'week'``."""
        return f"${{last:{duration}}}"

    @staticmethod
    def roll(duration):
        """Alias of rolling ``last``, e.g. ``Step.roll('24h')``."""
        return f"${{roll:{duration}}}"

    @staticmethod
    def this(token, tz=None):
        """Start of the containing period, e.g. ``Step.this('week')`` / ``Step.this('monday')``."""
        return Step._wrap(f"this:{token}", tz)

    @staticmethod
    def next(token, tz=None):
        """Start of the following period/weekday, e.g. ``Step.next('monday')``."""
        return Step._wrap(f"next:{token}", tz)

    @staticmethod
    def prev(token, tz=None):
        """Start of the previous period/weekday, e.g. ``Step.prev('month')``."""
        return Step._wrap(f"prev:{token}", tz)

    @staticmethod
    def start_of(token, tz=None):
        """Start (00:00:00) of the containing period, e.g. ``Step.start_of('day')``."""
        return Step._wrap(f"startOf:{token}", tz)

    @staticmethod
    def end_of(token, tz=None):
        """End (23:59:59) of the containing period, e.g. ``Step.end_of('quarter')``."""
        return Step._wrap(f"endOf:{token}", tz)

    @staticmethod
    def expr(text, tz=None):
        """Escape hatch for raw expressions / natural language, e.g. ``Step.expr('last 7 days')``."""
        return Step._wrap(text, tz)

    @staticmethod
    def _wrap(body, tz):
        return f"${{{body}{('@' + tz) if tz else ''}}}"
