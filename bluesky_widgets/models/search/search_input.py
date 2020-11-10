from datetime import datetime, timedelta

import dateutil.tz

from .queries import TimeRange, InvertedRange
from ...utils.event import EmitterGroup, Event

LOCAL_TIMEZONE = dateutil.tz.tzlocal()
_epoch = datetime(1970, 1, 1, 0, 0, tzinfo=LOCAL_TIMEZONE)


def secs_since_epoch(datetime):
    return (datetime - _epoch) / timedelta(seconds=1)


def ensure_abs(*abs_or_rel_times):
    """
    If datetime, pass through. If timedelta, interpret as relative to now.
    """
    now = datetime.now()
    results = []
    for item in abs_or_rel_times:
        if isinstance(item, timedelta):
            results.append(now + item)
        else:
            results.append(item)
    return results


class SearchInput:
    def __init__(self):
        self._since = None
        self._until = None
        self._query = {}
        self.events = EmitterGroup(
            source=self,
            auto_connect=True,
            query=Event,
            since=Event,
            until=Event,
            reload=Event,
        )
        self._time_validator = None

    @property
    def time_validator(self):
        return self._time_validator

    @time_validator.setter
    def time_validator(self, validator):
        self._time_validator = validator

    def __repr__(self):
        return f"<SearchInput {self._query!r}>"

    @property
    def query(self):
        """
        MongoDB query
        """
        return self._query

    @query.setter
    def query(self, query):
        if query == self.query:
            return
        self._query = query

    @property
    def since(self):
        """
        Lower bound on time range
        """
        return self._since

    @since.setter
    def since(self, since):
        if self.time_validator is not None:
            self.time_validator(since=since, until=self.until)
        if isinstance(since, (int, float)):
            since = datetime.fromtimestamp(since)
        if isinstance(since, datetime):
            if since == self.since:
                return
            if since.tzinfo is None:
                since = since.replace(tzinfo=LOCAL_TIMEZONE)
        self._since = since
        self.events.since(date=since)

    @property
    def until(self):
        """
        Upper bound on time range
        """
        return self._until

    @until.setter
    def until(self, until):
        if self.time_validator is not None:
            self.time_validator(since=self.since, until=until)
        if isinstance(until, (int, float)):
            until = datetime.fromtimestamp(until)
        if isinstance(until, datetime):
            if until == self.until:
                return
            if until.tzinfo is None:
                until = until.replace(tzinfo=LOCAL_TIMEZONE)
        self._until = until
        self.events.until(date=until)

    def on_since(self, event):
        try:
            since, until = ensure_abs(event.date, self._until)
            tr = TimeRange(since=since, until=until)
        except InvertedRange:
            # Move 'until' as well to create a valid (though empty) interval.
            self.until = event.date
            return
        if tr:
            self._query.update(tr)
        else:
            self._query.pop("time", None)
        self.events.query(query=self._query)

    def on_until(self, event):
        try:
            since, until = ensure_abs(self._since, event.date)
            tr = TimeRange(since=since, until=until)
        except InvertedRange:
            # Move 'since' as well to create a valid (though empty) interval.
            self.since = event.date
            return
        if tr:
            self._query.update(tr)
        else:
            self._query.pop("time", None)
        self.events.query(query=self._query)

    def request_reload(self):
        # If time range was given in relative terms, re-evaluate them relative
        # to the current time.
        changed = False
        if isinstance(self._since, timedelta):
            self.since = self._since
            changed = True
        if isinstance(self._until, timedelta):
            self.until = self._until
            changed = True
        # If the times were re-evaluated, the query Event will have been
        # emitted, so it would be redundant to reload.
        if not changed:
            self.events.reload()