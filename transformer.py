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
import signal
import json
import logging
import argparse
import requests
import multiprocessing as mp
from hashmap import hash_t 
from patterns import MaxExecTime, Recurring, WaitForEvent
from jobs import Jobs
from util import add_start_end, combine_sub_trees, replace_endpoints
import xml.etree.ElementTree as ET
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel
from multiprocessing import Process
from reqparser import parse_requirements
from ComplianceAST import traverse
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

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
        endpoints = notification["content"]["endpoints"]
        logger.debug(f'endpoints: {endpoints}')
        try:
            req = notification["content"]["attributes"]["requirements"]
        except:
            logger.error("No requirements were passed in the notification, cannot perform transformation without requirements")
        requirements = parse_requirements(req)
        print(notification)
        xml = ET.fromstring(notification["content"]["description"])
        xml = add_start_end(xml)
        xml= combine_sub_trees(xml)
        typ3 = form["type"]
        topic = form["topic"]
        event = form["event"]
        jobs = {}
        for counter, req in enumerate(requirements):
            logger.info(f'Verifying Pattern {req}')
            job = traverse(req, tree=xml)
            if job is not None:
                job = replace_endpoints(job, endpoints)
                caller_id = job["CallerID"]
                if caller_id not in jobs:
                    jobs[caller_id] = []
                jobs[caller_id].append(job)
                logger.info(f'Generated job: {job}')
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
        print(notification)
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
        print(form)
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
