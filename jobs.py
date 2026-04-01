import logging
import requests
from patterns import MaxExecTime, Recurring, WaitForEvent

logger = logging.getLogger(__name__)

SUBPROCESS_URL = "https://cpee.org/flow/start/xml/"


class Jobs:

    # --- vote_syncing_before jobs ---

    def wait_for_event_callback(self, job, callback):
        """Wait for callback of a wait for event pattern."""
        logger.info(f'Wait for event callback: {job}')
        # TODO: implement wait for event callback logic
        pass

    def open_max_exec_time(self, job, callback):
        """Open instance of a max exec time pattern."""
        logger.info(f'Open max exec time instance: {job}')
        tree = MaxExecTime(job["Time"], job["B_Endpoint"])
        response = requests.post(SUBPROCESS_URL, data={"behavior": "fork_running"}, files={"xml": ("xml", tree, "text/xml")})
        print(f'open_max_exec_time response: {response.status_code} {response.text}')
        # TODO: add the checking job to the hashmap
        pass

    def open_recurring(self, job, callback):
        """Open instance of a recurring pattern."""
        logger.info(f'Open recurring instance: {job}')
        tree = Recurring(job["B_Endpoint"], job["B_Endpoint"], job["Time"])
        response = requests.post(SUBPROCESS_URL, data={"behavior": "fork_running"}, files={"xml": ("xml", tree, "text/xml")})
        print(f'open_recurring response: {response.status_code} {response.text}')
        # TODO: add the checking job to the hashmap
        pass

    # --- vote_syncing_after jobs ---

    def abandon_max_exec_time(self, job, callback):
        """Abandon instance of a max exec time pattern."""
        logger.info(f'Abandon max exec time instance: {job}')
        # TODO: implement abandon max exec time instance
        pass

    def abandon_recurring(self, job, callback):
        """Abandon instance of a recurring pattern."""
        logger.info(f'Abandon recurring instance: {job}')
        # TODO: implement abandon recurring instance
        pass

    def open_wait_for_event(self, job, callback):
        """Open instance of a wait for event pattern."""
        logger.info(f'Open wait for event instance: {job}')
        tree = WaitForEvent(job["B_Endpoint"])
        response = requests.post(SUBPROCESS_URL, data={"behavior": "fork_running"}, files={"xml": ("xml", tree, "text/xml")})
        print(f'open_wait_for_event response: {response.status_code} {response.text}')
        # TODO: add the checking job to the hashmap
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

    def handle_jobs(self, jobs, phase, callback):
        """Dispatch a list of jobs to the appropriate handler based on phase ('before' or 'after')."""
        dispatch = self.BEFORE_DISPATCH if phase == "before" else self.AFTER_DISPATCH
        for job in jobs:
            pattern = job.get("Pattern")
            method_name = dispatch.get(pattern)
            if method_name is None:
                logger.warning(f'No handler for pattern "{pattern}" in phase "{phase}"')
                continue
            getattr(self, method_name)(job, callback)
