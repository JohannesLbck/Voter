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
from hashmap import hash_t 
from patterns import MaxExecTime, Recurring, WaitForEvent
from util import add_start_end, combine_sub_trees, replace_endpoints
import xml.etree.ElementTree as ET
from fastapi import FastAPI,  Request
from pydantic import BaseModel
from multiprocessing import Process
from reqparser import parse_requirements
from ComplianceAST import traverse

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

mapping = {
    "max_exec_time" : MaxExecTime,
    "recurring" : Recurring,
    "wait_for_event" : WaitForEvent
}

@app.post("/transform")
async def transform(request: Request):
    async with request.form() as form:
        notification = json.loads(form["notification"])
        endpoints = notification["content"]["endpoints"]
        print(f'endpoints: {endpoints}')
        print("--------------------")
        try:
            req = notification["content"]["attributes"]["requirements"]
        except:
            return (400, "No requirements were passed in the notification, cannot perform transformation without requirements")
        requirements = parse_requirements(req)
        xml = ET.fromstring(notification["content"]["description"])
        xml = add_start_end(xml)
        xml= combine_sub_trees(xml)
        typ3 = form["type"]
        topic = form["topic"]
        event = form["event"]
        jobs = {}
        for counter, req in enumerate(requirements):
            job = traverse(req, tree=xml)
            if job is not None:
                job = replace_endpoints(job, endpoints)
                caller_id = job["CallerID"]
                if caller_id not in jobs:
                    jobs[caller_id] = []
                jobs[caller_id].append(job)
        for key,value in jobs.items():
            pass
    return


def run_server():
    pid = os.fork()
    if pid != 0:
        return
    print('Starting ' + str(os.getpid()))
    print(os.getpid(), file=open('transformer.pid', 'w'))
    uvicorn.run("transformer:app", port=9322, log_level="info")

if __name__ == "__main__":
    if os.path.exists('transformer.pid'):
      with open("transformer.pid","r") as f: pid =f.read()
      print('Killing ' + str(int(pid)))
      os.remove('transformer.pid')
      os.kill(int(pid),signal.SIGINT)
    else:
      proc = Process(target=run_server, args=(), daemon=True)
      proc.start()
      proc.join()
