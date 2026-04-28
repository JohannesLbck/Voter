import json
import logging
import time
import requests
from patterns import MaxExecTime, Recurring, WaitForEvent

logger = logging.getLogger(__name__)

SUBPROCESS_URL = "https://cpee.org/flow/start/xml/"
ENGINE_URL = "https://cpee.org/flow/engine"
MESSAGE_RECEIVE_URL = "https-post://cpee.org/ing/correlators/message/send/"


class Jobs:

    def _make_target(self, caller_id):
        """Generate a unique correlator target for receive-based template branches."""
        return str(hash(str(caller_id) + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())))

    def _abandon_instance(self, target, pattern_name):
        """Transition subprocess instance towards abandoned state.

        Behavior follows the Ruby snippet semantics:
        - if current state is "stopping": write "stopping"
        - if current state is "ready" or "stopped": write "abandoned"

        Additionally, if state is "running" we first request "stopping"
        so a later callback can abandon it.
        """
        if not target:
            logger.warning(f'No target instance id for {pattern_name} abandon job')
            return

        state_url = f"{ENGINE_URL}/{target}/properties/state/"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            response = requests.get(state_url)
            if response.status_code != 200:
                logger.error(f'Failed to read state for {pattern_name} instance {target}: {response.status_code} {response.text}')
                return

            state = response.text.strip()
            logger.info(f'{pattern_name} instance {target} current state: {state}')

            if state in {"running", "stopping"}:
                put_response = requests.put(state_url, headers=headers, data="value=stopping")
                if put_response.status_code >= 400:
                    logger.error(f'Failed to set stopping for {pattern_name} instance {target}: {put_response.status_code} {put_response.text}')
                else:
                    logger.info(f'Set {pattern_name} instance {target} to stopping')
                    put_respone_2 = requests.put(state_url, headers=headers, data="value=abandoned")
                    if put_respone_2.status_code >= 400:
                        logger.error(f'Failed to abandon {pattern_name} instance {target} after stopping: {put_respone_2.status_code} {put_respone_2.text}')
                    else:
                        logger.info(f'Abandoned {pattern_name} instance {target} after stopping')
            elif state in {"ready", "stopped"}:
                put_response = requests.put(state_url, headers=headers, data="value=abandoned")
                if put_response.status_code >= 400:
                    logger.error(f'Failed to abandon {pattern_name} instance {target}: {put_response.status_code} {put_response.text}')
                else:
                    logger.info(f'Abandoned {pattern_name} instance {target}')
            elif state in {"finished"}:
                put_response = requests.put(state_url, headers=headers, data="value=abandoned")
                if put_response.status_code >= 400:
                    logger.error(f'Failed to abandon {pattern_name} instance {target} in finished state: {put_response.status_code} {put_response.text}')
                else:
                    logger.info(f'Abandoned {pattern_name} instance {target} in finished state')
        except Exception as e:
            logger.error(f'Failed to abandon {pattern_name} instance {target}: {e}')

    def _send_abandon_message(self, job, pattern_name):
        """Send abandon notification message to correlator receive endpoint."""
        target = job.get("target")
        if not target:
            logger.warning(f'No target for message-based abandon of {pattern_name}: {job}')
            return

        payload = {
            "id": str(target),
            "message": f"abandon_{pattern_name}: {json.dumps(job, sort_keys=True, default=str)}",
            "ttl": "0",
        }
        try:
            response = requests.post(MESSAGE_RECEIVE_URL, data=payload)
            if response.status_code >= 400:
                logger.error(
                    f'Failed sending abandon message for {pattern_name} target={target}: '
                    f'{response.status_code} {response.text}'
                )
            else:
                logger.info(f'Sent abandon message for {pattern_name} target={target}')
        except Exception as e:
            logger.error(f'Failed sending abandon message for {pattern_name} target={target}: {e}')

    # --- vote_syncing_before jobs ---

    def open_max_exec_time(self, job, callback):
        """Open instance of a max exec time pattern."""
        logger.info(f'Open max exec time instance: {job}')
        target = hash(job["CallerID"]+time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
        tree = MaxExecTime(job["Time"], job["B_Endpoint"], target)
        response = requests.post(SUBPROCESS_URL, data={"behavior": "fork_running"}, files={"xml": ("xml", tree, "text/xml")})
        if response.status_code != 200:
            logger.error(f'Failed to open max exec time instance: {response.status_code} {response.text}')
        else:
            response_json = json.loads(response.text)
            id = response_json.get("CPEE-INSTANCE")
            abandon_job = {**job, "Phase": "after", "Pattern": "abandon_max_exec_time", "target": target,"instance_id": id}
            return abandon_job

    def open_recurring(self, job, callback):
        """Open instance of a recurring pattern."""
        logger.info(f'Open recurring instance: {job}')
        target = self._make_target(job["CallerID"])
        tree = Recurring(job["B_Endpoint"], job["B_Endpoint"], job["Time"], target)
        response = requests.post(SUBPROCESS_URL, data={"behavior": "fork_running"}, files={"xml": ("xml", tree, "text/xml")})
        if response.status_code != 200:
            logger.error(f'Failed to open recurring instance: {response.status_code} {response.text}')
        else:
            response_json = json.loads(response.text)
            instance_id = response_json.get("CPEE-INSTANCE")
            abandon_job = {**job, "Phase": "after", "Pattern": "abandon_recurring", "target": target, "instance_id": instance_id}
            return abandon_job

    def open_wait_for_event(self, job, callback):
        """Open instance of a wait for event pattern."""
        logger.info(f'Open wait for event instance: {job}')
        target = self._make_target(job["CallerID"])
        tree = WaitForEvent(job["C_Endpoint"])
        response = requests.post(SUBPROCESS_URL, data={"behavior": "fork_running"}, files={"xml": ("xml", tree, "text/xml")})
        if response.status_code != 200:
            logger.error(f'Failed to open wait for event instance: {response.status_code} {response.text}')
        else:
            response_json = json.loads(response.text)
            instance_id = response_json.get("CPEE-INSTANCE")
            abandon_job = {**job, "CallerID": job["B_ID"], "Phase": "before", "Pattern": "check_wait_for_event", "target": target, "instance_id": instance_id}
            return abandon_job

    def open_wait_for_timeout(self, job, callback):
        """Open instance of a wait for timeout pattern."""
        logger.info(f'Open wait for timeout instance: {job}')
        target = self._make_target(job["CallerID"])
        tree = MaxExecTime(job["Time"], "", target)
        response = requests.post(SUBPROCESS_URL, data={"behavior": "fork_running"}, files={"xml": ("xml", tree, "text/xml")})
        if response.status_code != 200:
            logger.error(f'Failed to open wait for timeout instance: {response.status_code} {response.text}')
        else:
            response_json = json.loads(response.text)
            instance_id = response_json.get("CPEE-INSTANCE")
            abandon_job = {**job, "CallerID": job["B_ID"], "Phase": "before", "Pattern": "check_wait_for_timeout", "target": target, "instance_id": instance_id}
            return abandon_job

    # --- vote_syncing_after jobs ---

    def abandon_max_exec_time(self, job, callback):
        """Abandon instance of a max exec time pattern."""
        logger.info(f'Abandon max exec time instance: {job}')
        self._send_abandon_message(job, "max_exec_time")

    def abandon_recurring(self, job, callback):
        """Abandon instance of a recurring pattern."""
        logger.info(f'Abandon recurring instance: {job}')
        self._send_abandon_message(job, "recurring")

    def abandon_wait_for_event(self, job, callback):
        """Abandon instance of a wait for event pattern."""
        logger.info(f'Abandon wait for event instance: {job}')
        self._abandon_instance(job.get("instance_id", job.get("target")), "wait for event")

    def abandon_wait_for_timeout(self, job, callback):
        """Abandon instance of a wait for timeout pattern."""
        logger.info(f'Abandon wait for timeout instance: {job}')
        self._abandon_instance(job.get("instance_id", job.get("target")), "wait for timeout")

    def check_wait_for_event(self, job, callback):
        """Actively wait until the wait-for-event instance is finished."""
        logger.info(f'Check wait for event instance: {job}')
        instance_id = job.get("instance_id", job.get("target"))
        state_url = f"https://cpee.org/flow/engine/{instance_id}/properties/state/"
        while True:
            try:
                response = requests.get(state_url)
                state = response.text.strip()
                logger.info(f'Wait for event instance {instance_id} state: {state}')
                if state == "finished":
                    logger.info(f'Wait for event instance {instance_id} finished successfully')
                    self._abandon_instance(instance_id, "wait for event")
                    return None
                logger.info(f'Wait for event instance {instance_id} not finished yet, checking again in 5 seconds')
            except Exception as e:
                logger.error(f'Failed to check wait for event instance {instance_id}: {e}')
                logger.info('Retrying wait-for-event check in 5 seconds')
            time.sleep(5)

    def check_wait_for_timeout(self, job, callback):
        """Actively wait until the wait-for-timeout instance is finished."""
        logger.info(f'Check wait for timeout instance: {job}')
        instance_id = job.get("instance_id", job.get("target"))
        state_url = f"https://cpee.org/flow/engine/{instance_id}/properties/state/"
        while True:
            try:
                response = requests.get(state_url)
                state = response.text.strip()
                logger.info(f'Wait for timeout instance {instance_id} state: {state}')
                if state == "finished":
                    logger.info(f'Wait for timeout instance {instance_id} finished successfully')
                    self._abandon_instance(instance_id, "wait for timeout")
                    return None
                logger.info(f'Wait for timeout instance {instance_id} not finished yet, checking again in 5 seconds')
            except Exception as e:
                logger.error(f'Failed to check wait for timeout instance {instance_id}: {e}')
                logger.info('Retrying wait-for-timeout check in 5 seconds')
            time.sleep(5)

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
        "abandon_wait_for_event": "abandon_wait_for_event",
        "abandon_wait_for_timeout": "abandon_wait_for_timeout",
    }

    def handle_jobs(self, jobs, phase, callback):
        """Dispatch a list of jobs to the appropriate handler based on phase ('before' or 'after')."""
        dispatch = self.BEFORE_DISPATCH if phase == "before" else self.AFTER_DISPATCH
        return_jobs = {}

        # Normalize persisted payload shape.
        # jobs can be: list[dict], dict, JSON string, or invalid data.
        normalized_jobs = []
        if isinstance(jobs, dict):
            normalized_jobs = [jobs]
        elif isinstance(jobs, list):
            normalized_jobs = jobs
        elif isinstance(jobs, str):
            try:
                parsed = json.loads(jobs)
                if isinstance(parsed, dict):
                    normalized_jobs = [parsed]
                elif isinstance(parsed, list):
                    normalized_jobs = parsed
                else:
                    logger.warning(f'Unsupported jobs payload type after JSON parse: {type(parsed).__name__}')
                    return {}
            except Exception:
                logger.warning(f'Unsupported jobs payload string in phase "{phase}": {jobs}')
                return {}
        else:
            logger.warning(f'Unsupported jobs payload type in phase "{phase}": {type(jobs).__name__}')
            return {}

        for job in normalized_jobs:
            if not isinstance(job, dict):
                logger.warning(f'Skipping malformed job entry of type {type(job).__name__}: {job}')
                continue
            if job.get("Phase") != phase:
                logger.debug(f'Skipping job with mismatched phase: expected "{phase}", got "{job.get("Phase")}"')
                continue
            pattern = job.get("Pattern")
            if not isinstance(pattern, str):
                logger.warning(f'Skipping job with invalid Pattern type: {pattern}')
                continue
            method_name = dispatch.get(pattern)
            if method_name is None:
                logger.warning(f'No handler for pattern "{pattern}" in phase "{phase}"')
                continue
            return_job = getattr(self, method_name)(job, callback)
            if return_job is not None:
                caller_id = return_job.get("CallerID")
                if caller_id is None:
                    logger.warning(f'Returned job missing CallerID: {return_job}')
                    continue
                if caller_id not in return_jobs:
                    return_jobs[caller_id] = []
                return_jobs[caller_id].append(return_job)
        return return_jobs
