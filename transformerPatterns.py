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

import logging
import re
#from hashmap import constraints_t # Future Work :) 
import xml.etree.ElementTree as ET
from util import * 
## Check util which is an interface to all other methods if you want all method names

## Load the Hashmap for run time voting


## This contains the verification using explicit, annotated verification, meaning the activities are identified by labels and resources
## are explicity annotated

namespace = {"ns0": "http://cpee.org/ns/description/1.0"}
data_decision_tags= [ ".//ns0:loop", ".//ns0:alternative"]
logger = logging.getLogger(__name__)

## Temporal Patterns, adapted from PTV, ==> Part of the contribution

# Recurring: While A is happening, b needs to be recurring every t time.
def recurring(tree, a, b, t):
    a_ele = exists_by_label(tree, a)
    if a_ele is not None:
        b_ele = exists_by_label(tree, b)
        b_endpoint_key = b_ele.get("endpoint") if b_ele is not None else b
        b_endpoint_key = b_endpoint_key if b_endpoint_key is not "" else b
        return {"CallerID" : a_ele.get("id"),
                    "Phase": "before",
                    "Pattern" : "recurring",
                    "Time" : t,
                    "B_Endpoint" : b_endpoint_key}
    
    else:
        logger.info(f'Activity "{a}" is missing in the process, so the recurring requirement is trivially false')

# maxExecTime: If a takes longer than time, b needs to be executed, mapped from timed_alternative
def maxExecTime(tree, a, b, time):
    a_ele = exists_by_label(tree, a)
    if a_ele is not None:
        a_id = a_ele.get("id")
        b_ele = exists_by_label(tree, b)
        b_endpoint_key = b_ele.get("endpoint") if b_ele is not None else b
        b_endpoint_key = b_endpoint_key if b_endpoint_key is not "" else b
        return {"CallerID" : a_id,
                    "Phase": "before",
                    "Pattern" : "maxExecTime",
                    "Time" : time,
                    "B_Endpoint" : b_endpoint_key}
    else:
        logger.info(f'Activity "{a}" is missing so the maximal execution time is by definition not exceeded, since the activity is never executed')
        return None

## There are technically many ways to implement this and accordingly many ways this could be checked, we enforcce here a very visually pleasing way of enforcing this, which is a event based gateway with a timeout. If said timeout finishes first it would mean that the max time between has passed. This is just one of many ways such as adding syncs before and after a and b, but this would be much less checkable and also have several ways of implementing
def max_time_between(tree, a, b, time, c = None):
    apath = exists_by_label(tree, a)
    bpath = exists_by_label(tree, b)
    if apath is not None:
        if bpath is not None:
            c_path = exists_by_label(tree, c)
            c_endpoint_key = c_path.get("endpoint") if c_path is not None else c
            c_endpoint_key = c_endpoint_key if c_endpoint_key is not "" else c
            return {"CallerID" : apath.get("id"),
                    "Phase": "before",
                    "Pattern" : "max_time_between",
                    "Time" : time,
                    "C_Endpoint" : c_endpoint_key}
        else:
            logger.info(f'Activity "{b}" is missing in the process')
            return None
    else:
        logger.info(f'Activity "{a}" is missing in the process')
        return None

## Min Time between two activities, enforced via Voting
def min_time_between(tree, a, b, time, c = None):
    a_sync = False
    if leads_to(tree, a, b):
        apath = exists_by_label(tree, a)
        bpath = exists_by_label(tree, b)
        ## Original Method had errors, but this pattern never appears in practice, so fix this later
        return True
    else:
        logger.info(f'Activities "{a}" and "{b}" are not in a leads_to relationship, so the min_time_between requirement is False')
        return False 
    
    

## By Due Date: Decide how to handle due dates later
## This simply reads the annotation whether the due date is set correctly in the annotation, it does not check actual implementation, could be extended with voting later then it would even work during execution
def by_due_date_annotated(tree, a, timestamp):
    return None
## By Due Date: checks if the due date requirement is explicitly defined through sync check 
def by_due_date_explicit(tree, a, timestamp):
    return None

## checks both annotated and explicit, returns true if either
def by_due_date(tree, a, timestamp, c = None):
    return None






def executed_by(args):
    return None

# These are just left empty to keep compatability with the full ASTs
def exists(tree, a):#
    return None
def absence(tree, a):
    return None
def loop(tree, a):
    return None
def directly_follows(tree, a, b):
    return None
def exclusive(tree, a, b):
    return None
def leads_to(tree, a, b):
    return None
def precedence(tree, a, b):
    return None
def leads_to_absence(tree, a, b):
    return None
def parallel(tree, a, b):
    return None
# Resource
def executed_by_identify(tree, resource):
    return None
def executed_by_return(tree, a):
    return None
## Data
def send_exist(tree, data, complete = False):
    return None
def receive_exist(tree, data, complete = False):
    return None
def activity_sends(tree, a, data):
    return None
def activity_receives(tree, a, data):
    return None   
def condition(tree, condition):
    return None
def condition_directly_follows(tree, condition , a):
    return None
def failure_eventually_follows(tree, a, b):
    return None

def failure_directly_follows(tree, a, b):
    return None
def condition_eventually_follows(tree, condition, a, scope = "branch"):
    return None
def data_leads_to_absence(tree, condition, a):
    return None
