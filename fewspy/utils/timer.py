"""Timer for fewsbokeh."""

import time


class Timer(object):
    """Record function efficiency."""

    def __init__(self, logger):
        self.start = time.time()
        self.milestone = self.start
        self.logger = logger

    def start(self):
        """Start the timer."""
        self.start = time.time()

    def report(self, message=""):
        """Set milestone and report."""
        self.logger.debug(f"{message} in {(time.time() - self.milestone):.3f} sec")
        self.milestone = time.time()

    def reset(self, message=None):
        """Report task-efficiency and reset."""
        if message:
            self.logger.debug(f"{message} in {(time.time() - self.start):.3f} sec")
        self.start = time.time()
        self.milestone = self.start
