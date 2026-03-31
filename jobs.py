import logging

logger = logging.getLogger(__name__)


class Jobs:

    # --- vote_syncing_before jobs ---

    def wait_for_event_callback(self, job):
        """Wait for callback of a wait for event pattern."""
        logger.info(f'Wait for event callback: {job}')
        # TODO: implement wait for event callback logic
        pass

    def open_max_exec_time(self, job):
        """Open instance of a max exec time pattern."""
        logger.info(f'Open max exec time instance: {job}')
        # TODO: implement open max exec time instance
        pass

    def open_recurring(self, job):
        """Open instance of a recurring pattern."""
        logger.info(f'Open recurring instance: {job}')
        # TODO: implement open recurring instance
        pass

    # --- vote_syncing_after jobs ---

    def abandon_max_exec_time(self, job):
        """Abandon instance of a max exec time pattern."""
        logger.info(f'Abandon max exec time instance: {job}')
        # TODO: implement abandon max exec time instance
        pass

    def abandon_recurring(self, job):
        """Abandon instance of a recurring pattern."""
        logger.info(f'Abandon recurring instance: {job}')
        # TODO: implement abandon recurring instance
        pass

    def open_wait_for_event(self, job):
        """Open instance of a wait for event pattern."""
        logger.info(f'Open wait for event instance: {job}')
        # TODO: implement open wait for event instance
        pass

    # --- dispatch ---

    BEFORE_DISPATCH = {
        "wait_for_event": "wait_for_event_callback",
        "maxExecTime": "open_max_exec_time",
        "recurring": "open_recurring",
    }

    AFTER_DISPATCH = {
        "maxExecTime": "abandon_max_exec_time",
        "recurring": "abandon_recurring",
        "wait_for_event": "open_wait_for_event",
    }

    def handle_jobs(self, jobs, phase):
        """Dispatch a list of jobs to the appropriate handler based on phase ('before' or 'after')."""
        dispatch = self.BEFORE_DISPATCH if phase == "before" else self.AFTER_DISPATCH
        for job in jobs:
            pattern = job.get("Pattern")
            method_name = dispatch.get(pattern)
            if method_name is None:
                logger.warning(f'No handler for pattern "{pattern}" in phase "{phase}"')
                continue
            getattr(self, method_name)(job)
