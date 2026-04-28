#! /usr/bin/python
#    Copyright (C) <2025>  <Author Name>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

import uvicorn
import time
import os
import re
import signal
import json
import copy
import logging
import argparse
import hashlib
import requests
import yaml
import uuid
import multiprocessing as mp
from datetime import datetime, timezone
from hashmap import hash_t 
from patterns import MaxExecTime, Recurring, WaitForEvent
from jobs import Jobs
from util import add_start_end, remove_start_end, combine_sub_trees, replace_endpoints
import xml.etree.ElementTree as ET

NS = "http://cpee.org/ns/description/1.0"
NS_PROPS = "http://cpee.org/ns/properties/2.0"
NS_RIDDL = "http://riddl.org/ns/common-patterns/notifications-producer/2.0"

ET.register_namespace('', NS)
ET.register_namespace('props', NS_PROPS)
ET.register_namespace('riddl', NS_RIDDL)
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel
from multiprocessing import Process
from reqparser import parse_requirements
from ComplianceAST import traverse
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

LOG_URL = "https://cpee.org/comp-log/receiver/"
LOG_HEADERS = {
    "Content-Type": "application/x-yaml",
    "Content-ID": "events"
}

class _LiteralStr(str):
    """String subclass that YAML will render as a literal block scalar (|)."""
    pass

def _literal_representer(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')

yaml.add_representer(_LiteralStr, _literal_representer)

def _send_description_event(instance_id, instance_uuid, description_xml):
    """Send the modified description XML as a YAML event to the compliance log."""
    change_uuid = hashlib.md5(description_xml.encode('utf-8')).hexdigest()
    timestamp = datetime.now().astimezone().isoformat()
    event = {
        'event': {
            'concept:instance': int(instance_id),
            'id:id': 'ex-ante',
            'cpee:instance': instance_uuid,
            'lifecycle:transition': 'unknown',
            'cpee:lifecycle:transition': 'description/change',
            'cpee:description': _LiteralStr(description_xml),
            'cpee:change_uuid': change_uuid,
            'time:timestamp': timestamp,
        }
    }
    yaml_data = yaml.dump(
        event,
        sort_keys=False,
        default_flow_style=False,
        explicit_start=True,
        explicit_end=True,
    )
    try:
        response = requests.post(LOG_URL, data=yaml_data.encode('utf-8'), headers=LOG_HEADERS)
        logger.info(f'Sent description event to log: status={response.status_code}')
    except Exception as e:
        logger.error(f'Failed to send description event to log: {e}')

def _fix_description_ns(xml_bytes):
    """Post-process XML bytes to use default namespace declaration instead of prefixes."""
    text = xml_bytes.decode('UTF-8')
    # For props-prefixed elements (if writing full testset)
    text = text.replace(' xmlns:props="%s"' % NS_PROPS, '')
    text = re.sub(r'<props:([\w_]+)', r'<\1', text)
    text = re.sub(r'</props:([\w_]+)', r'</\1', text)
    return text.encode('UTF-8')

class Model(BaseModel):
    cpee: str
    instance_url: str
    instance: int
    topic: str
    type: str
    name: str
    timestamp: str
    content: dict
    instance_uuid: str
    instance_name: str

app = FastAPI()
jobs_handler = Jobs()

mapping = {
    "max_exec_time" : MaxExecTime,
    "recurring" : Recurring,
    "wait_for_event" : WaitForEvent
}

@app.post("/transform")
async def transform(request: Request):
    async with request.form() as form:
        notification = json.loads(form["notification"])
        instance_id = str(notification["instance"])
        instance_uuid = notification.get("instance-uuid", str(uuid.uuid4()))
        endpoints = notification["content"]["endpoints"]
        logger.debug(f'endpoints: {endpoints}')
        try:
            req = notification["content"]["attributes"]["requirements"]
        except:
            logger.error("No requirements were passed in the notification, cannot perform transformation without requirements")
        requirements = parse_requirements(req)
        xml = ET.fromstring(notification["content"]["description"])
        xml = add_start_end(xml)
        xml= combine_sub_trees(xml)[0]
        typ3 = form["type"]
        topic = form["topic"]
        event = form["event"]
        jobs = {}
        for counter, req in enumerate(requirements):
            logger.info(f'Verifying Pattern {req}')
            modified_tree, job = traverse(req, tree=xml)
            if job is not None:
                job = replace_endpoints(job, endpoints)
                caller_id = job["CallerID"]
                if caller_id not in jobs:
                    jobs[caller_id] = []
                jobs[caller_id].append(job)
                logger.info(f'Generated job: {job}')
            xml = modified_tree
            output_tree = remove_start_end(copy.deepcopy(modified_tree))
            ET.indent(output_tree)
            xml_bytes = ET.tostring(output_tree, encoding='UTF-8', xml_declaration=True)
            xml_bytes = _fix_description_ns(xml_bytes)
            with open(f'Outputs/modified_tree_{instance_id}_{counter}.xml', 'wb') as f:
                f.write(xml_bytes)
        # Send final modified description as YAML event
        final_tree = remove_start_end(copy.deepcopy(xml))
        ET.indent(final_tree)
        final_xml_bytes = ET.tostring(final_tree, encoding='UTF-8', xml_declaration=True)
        final_xml_bytes = _fix_description_ns(final_xml_bytes)
        _send_description_event(instance_id, instance_uuid, final_xml_bytes.decode('UTF-8'))
        for caller_id, job_list in jobs.items():
            hash_key = f"{caller_id}{instance_id}"
            hash_t.insert(hash_key, job_list)
            logger.info(f'Stored jobs for hash key {hash_key}: {job_list}')
        hash_t.save_disk("Constraints.json")
    return

@app.post("/vote_syncing_before")
async def vote_syncing_before(request: Request):
    async with request.form() as form:
        notification = json.loads(form["notification"])
        instance_id = str(notification["instance"])
        caller_id = notification["content"]["activity"] 
        hash_key = f"{caller_id}{instance_id}"
        jobs = hash_t.get(hash_key)
        callback = form["callback"]
        if jobs == "No record found":
            logger.info(f'No jobs found for hash key {hash_key}, skipping voting')
            return  Response(content="true", media_type="text/plain")
        logger.info(f'Found jobs for hash key {hash_key}: {jobs}')
        return_jobs = jobs_handler.handle_jobs(jobs, phase="before", callback=callback)
        for caller_id, job_list in return_jobs.items():
            hash_key = f"{caller_id}{instance_id}"
            hash_t.insert(hash_key, job_list)
            logger.info(f'Stored jobs for hash key {hash_key}: {job_list}')
        return  Response(content="true", media_type="text/plain")

@app.post("/vote_syncing_after")
async def vote_syncing_after(request: Request):
    async with request.form() as form:
        notification = json.loads(form["notification"])
        instance_id = str(notification["instance"])
        caller_id = notification["content"]["activity"] 
        hash_key = f"{caller_id}{instance_id}"
        jobs = hash_t.get(hash_key)
        callback = form["callback"]
        if jobs == "No record found":
            logger.info(f'No jobs found for hash key {hash_key}, skipping voting')
            return  Response(content="true", media_type="text/plain")
        logger.info(f'Found jobs for hash key {hash_key}: {jobs}')
        return_jobs = jobs_handler.handle_jobs(jobs, phase="after", callback=callback)
        for caller_id, job_list in return_jobs.items():
            hash_key = f"{caller_id}{instance_id}"
            hash_t.insert(hash_key, job_list)
            logger.info(f'Stored jobs for hash key {hash_key}: {job_list}')
        return  Response(content="true", media_type="text/plain")

def _configure_logging(verbose=False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s:%(name)s:%(message)s",
        force=True,
    )


def run_server(verbose=False):
    _configure_logging(verbose)
    uvicorn.run("transformer:app", port=9322, log_level="info")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run transformer service")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug logging")
    args = parser.parse_args()
    _configure_logging(args.verbose)

    if os.path.exists('transformer.pid'):
      with open("transformer.pid","r") as f: pid =f.read() 
      logger.info('Killing ' + str(int(pid)))
      os.remove('transformer.pid')
      os.kill(int(pid),signal.SIGINT)
    else:
        mp.set_start_method("spawn", force=True)
        proc = Process(target=run_server, args=(args.verbose,), daemon=True)
        proc.start()
        logger.info('Starting ' + str(proc.pid))
        print(proc.pid, file=open('transformer.pid', 'w'))
        proc.join()
