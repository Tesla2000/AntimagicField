from __future__ import annotations


class FailedToSolveDuplicates(ValueError):
    def __init__(self, duplicate_values: frozenset[str]):
        self.duplicate_values = duplicate_values
