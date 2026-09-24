"""Solvable Rulebook — docs/architecture.md §2.5-2.6.

The ruleset the Decision Engine consults before acting. Extended in two
ways only: a human Teach action (docs/context.md, Human Intelligence
Layer), or a resolved first-time-bug suggestion. Never write to this
module directly from a route handler — go through human_intelligence/.
"""

from typing import TypedDict


class Rule(TypedDict):
    topic: str
    knowledge: str


def query(topic: str) -> Rule | None:
    raise NotImplementedError


def add_rule(topic: str, knowledge: str, source: str) -> None:
    """`source` should be either 'human_teach' or 'first_time_bug_suggestion'."""
    raise NotImplementedError
