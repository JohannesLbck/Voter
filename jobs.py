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

    def open_wait_for_event(self, job, callback):
        """Open instance of a wait for event pattern."""
        logger.info(f'Open wait for event instance: {job}')
        tree = WaitForEvent(job["C_Endpoint"])
        response = requests.post(SUBPROCESS_URL, data={"behavior": "fork_running"}, files={"xml": ("xml", tree, "text/xml")})
        if response.status_code != 200:
            logger.error(f'Failed to open wait for event instance: {response.status_code} {response.text}')
        else:
            response_json = json.loads(response.text)
            target = response_json.get("CPEE-INSTANCE")
            abandon_job = {**job, "CallerID": job["B_ID"], "Phase": "before", "Pattern": "check_wait_for_event", "target": target}
            return abandon_job

    def open_wait_for_timeout(self, job, callback):
        """Open instance of a wait for timeout pattern."""
        logger.info(f'Open wait for timeout instance: {job}')
        tree = MaxExecTime(job["Time"], "")
        response = requests.post(SUBPROCESS_URL, data={"behavior": "fork_running"}, files={"xml": ("xml", tree, "text/xml")})
        if response.status_code != 200:
            logger.error(f'Failed to open wait for timeout instance: {response.status_code} {response.text}')
        else:
            response_json = json.loads(response.text)
            target = response_json.get("CPEE-INSTANCE")
            abandon_job = {**job, "CallerID": job["B_ID"], "Phase": "before", "Pattern": "check_wait_for_timeout", "target": target}
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

    def check_wait_for_event(self, job, callback):
        """Check if the wait for event instance is finished."""
        logger.info(f'Check wait for event instance: {job}')
        target = job.get("target")
        try:
            response = requests.get(f"https://cpee.org/flow/engine/{target}/properties/state/")
            state = response.text.strip()
            logger.info(f'Wait for event instance {target} state: {state}')
            if state == "finished":
                logger.info(f'Wait for event instance {target} finished successfully')
            else:
                logger.warning(f'Wait for event instance {target} not finished yet, state: {state}')
        except Exception as e:
            logger.error(f'Failed to check wait for event instance {target}: {e}')

    def check_wait_for_timeout(self, job, callback):
        """Check if the wait for timeout instance is finished."""
        logger.info(f'Check wait for timeout instance: {job}')
        target = job.get("target")
        try:
            response = requests.get(f"https://cpee.org/flow/engine/{target}/properties/state/")
            state = response.text.strip()
            logger.info(f'Wait for timeout instance {target} state: {state}')
            if state == "finished":
                logger.info(f'Wait for timeout instance {target} finished successfully')
            else:
                logger.warning(f'Wait for timeout instance {target} not finished yet, state: {state}')
        except Exception as e:
            logger.error(f'Failed to check wait for timeout instance {target}: {e}')

    # --- dispatch ---

    BEFORE_DISPATCH = {
        "maxExecTime": "open_max_exec_time",
        "recurring": "open_recurring",
        "wait_for_event_between": "open_wait_for_event",
        "wait_for_timeout_between": "open_wait_for_timeout",
        "check_wait_for_event": "check_wait_for_event",
        "check_wait_for_timeout": "check_wait_for_timeout",
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
