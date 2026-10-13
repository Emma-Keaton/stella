"""evals - the Stella agent eval suite.

Run it before and after changing anything in `agent/`. Without a measured
baseline, "it got smarter" is a guess.
"""

from evals.tasks import Task, default_suite, suite_manifest

__all__ = ["Task", "default_suite", "suite_manifest"]