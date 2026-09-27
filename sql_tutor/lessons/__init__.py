"""All course content, in teaching order."""

from . import basics, managing, practice, querying

LESSONS = basics.LESSONS + querying.LESSONS + managing.LESSONS + practice.LESSONS


def exercise_id(lesson, index):
    return f"{lesson.id}#{index + 1}"
