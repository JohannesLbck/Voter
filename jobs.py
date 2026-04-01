import json
import logging
import requests
from patterns import MaxExecTime, Recurring, WaitForEvent

logger = logging.getLogger(__name__)

SUBPROCESS_URL = "https://cpee.org/flow/start/xml/"


class Jobs:

    # --- vote_syncing_before jobs ---

    def open_max_exec_time(self, job, callback):
        """Open instance of a max exec time pattern."""
        logger.info(f'Open max exec time instance: {job}')
        tree = MaxExecTime(job["Time"], job["B_Endpoint"])
        response = requests.post(SUBPROCESS_URL, data={"behavior": "fork_running"}, files={"xml": ("xml", tree, "text/xml")})
        if response.status_code != 200:
            logger.error(f'Failed to open max exec time instance: {response.status_code} {response.text}')
        else:
            response_json = json.loads(response.text)
            id = response_json.get("CPEE-INSTANCE")
            abandon_job = {**job, "Phase": "after", "Pattern": "abandon_max_exec_time", "target": id}
            return abandon_job

    def open_recurring(self, job, callback):
        """Open instance of a recurring pattern."""
        logger.info(f'Open recurring instance: {job}')
        tree = Recurring(job["B_Endpoint"], job["B_Endpoint"], job["Time"])
        response = requests.post(SUBPROCESS_URL, data={"behavior": "fork_running"}, files={"xml": ("xml", tree, "text/xml")})
        if response.status_code != 200:
            logger.error(f'Failed to open recurring instance: {response.status_code} {response.text}')
        else:
            response_json = json.loads(response.text)
            target = response_json.get("CPEE-INSTANCE")
            abandon_job = {**job, "Phase": "after", "Pattern": "abandon_recurring", "target": target}
            return abandon_job

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

    # --- dispatch ---

    BEFORE_DISPATCH = {
        "maxExecTime": "open_max_exec_time",
        "recurring": "open_recurring",
    }

    AFTER_DISPATCH = {
        "abandon_max_exec_time": "abandon_max_exec_time",
        "abandon_recurring": "abandon_recurring",
    }

    def handle_jobs(self, jobs, phase, callback):
        """Dispatch a list of jobs to the appropriate handler based on phase ('before' or 'after')."""
        dispatch = self.BEFORE_DISPATCH if phase == "before" else self.AFTER_DISPATCH
        return_jobs = {}
        for job in jobs:
            if job.get("Phase") != phase:
                logger.debug(f'Skipping job with mismatched phase: expected "{phase}", got "{job.get("Phase")}"')
                continue
            pattern = job.get("Pattern")
            method_name = dispatch.get(pattern)
            if method_name is None:
                logger.warning(f'No handler for pattern "{pattern}" in phase "{phase}"')
                continue
            return_job = getattr(self, method_name)(job, callback)
            if return_job is not None:
                return_jobs[return_job["CallerID"]] = return_job
        return return_jobs
