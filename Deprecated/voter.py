#! /usr/bin/python
#    Copyright (C) <2025>  <Johannes Löbbecke>
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
import sys
import json
import re
import uuid
import logging
from hashmap import hash_t 
from patterns import *
import xml.etree.ElementTree as ET
from fastapi import FastAPI, File, UploadFile, Request, Form
from pydantic import BaseModel
from multiprocessing import Process
from fastapi.responses import HTMLResponse, JSONResponse

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
    "min_time_between" : min_time_between
}

@app.post("/voter")
async def Subscriber(request: Request):
    async with request.form() as form:
        #print(form)
        callback = form["callback"]
        data = json.loads(form["notification"])
        timestamp = data["timestamp"]
        instance = data["instance"]
        content = data["content"]
        activity = content["activity"]
        ## Following option would be directly connected via hashmap
        if hash_t.exists((instance)):
            rules = hash_t.get(instance)
            mapping[rules["Pattern"]](callback, timestamp, activity, instance, rules)
        #print(f'callback is {callback}')
        #print(f'notification is {data}')
        #print(f'content is {content}')
    return

def run_server():
    pid = os.fork()
    if pid != 0:
        return
    print('Starting ' + str(os.getpid()))
    print(os.getpid(), file=open('voter.pid', 'w'))
    uvicorn.run("voter:app", port=9322, log_level="info")

if __name__ == "__main__":
    if os.path.exists('voter.pid'):
      with open("voter.pid","r") as f: pid =f.read()
      print('Killing ' + str(int(pid)))
      os.remove('voter.pid')
      os.kill(int(pid),signal.SIGINT)
    else:
      proc = Process(target=run_server, args=(), daemon=True)
      proc.start()
      proc.join()

