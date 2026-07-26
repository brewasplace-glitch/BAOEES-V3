"""Workday calendar utilities for BB24."""

from __future__ import annotations

from datetime import date, timedelta


class WorkdayCalendar:
    """Monday-Friday calendar with optional project holidays."""

    def __init__(self, holidays: set[date] | None = None) -> None:
        self.holidays = set(holidays or set())

    def is_workday(self, value: date) -> bool:
        return value.weekday() < 5 and value not in self.holidays

    def normalize_start(self, value: date) -> date:
        current = value
        while not self.is_workday(current):
            current += timedelta(days=1)
        return current

    def add_workdays(self, start: date, offset: int) -> date:
        if offset < 0:
            raise ValueError("Workday offset must not be negative.")
        current = self.normalize_start(start)
        if offset == 0:
            return current
        count = 0
        while count < offset:
            current += timedelta(days=1)
            if self.is_workday(current):
                count += 1
        return current

    def workdays_between(self, start: date, finish: date) -> list[date]:
        """Return inclusive project workdays between two dates."""
        if finish < start:
            return []
        current = self.normalize_start(start)
        result: list[date] = []
        while current <= finish:
            if self.is_workday(current):
                result.append(current)
            current += timedelta(days=1)
        return result
