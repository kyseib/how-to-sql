"""Data types that describe course content."""

from dataclasses import dataclass, field


@dataclass
class Exercise:
    """A task the learner solves by writing SQL.

    The learner's SQL and `solution` are each run against a fresh copy of the
    sample database (after `setup`). The outcomes are compared:

    - If `check` is None, the last result set each produced is compared.
    - Otherwise each `probes` statement is run (recording success/failure),
      then `check` is run and its result sets are compared. Use this for
      INSERT/UPDATE/DELETE/CREATE exercises where the end state matters.
    """
    prompt: str
    solution: str
    hints: list = field(default_factory=list)
    ordered: bool = False       # row order matters (the task asks for ORDER BY)
    check_names: bool = False   # column names must match (the task asks for aliases)
    setup: str = ""
    check: str = ""
    probes: list = field(default_factory=list)
    explanation: str = ""       # shown after a correct answer


@dataclass
class Quiz:
    question: str
    options: list
    answer: int                 # index into options
    explanation: str = ""


@dataclass
class Lesson:
    id: str
    title: str
    summary: str
    pages: list
    exercises: list = field(default_factory=list)
