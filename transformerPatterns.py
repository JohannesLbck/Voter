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
import xml.etree.ElementTree as ET
from util import * 
from modifierpatterns import recurring_modify, max_time_between_modify, wait_for_event_modify, max_exec_time_modify, wait_for_timeout_modify

## Check util which is an interface to all other methods if you want all method names


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
        b_endpoint_key = b_endpoint_key if b_endpoint_key != "" else b
        loops = tree.findall(".//ns0:loop", namespace)
        modified_tree = recurring_modify(tree, a_ele, b_ele, t) # Creates the modified tree here
        return modified_tree, {"CallerID" : a_ele.get("id"),
                    "Phase": "before",
                    "Pattern" : "recurring",
                    "Time" : t,
                    "B_Endpoint" : b_endpoint_key}
    
    else:
        logger.info(f'Activity "{a}" is missing in the process, so the recurring requirement is trivially false')
        return tree, None

# maxExecTime: If a takes longer than time, b needs to be executed, mapped from timed_alternative
def maxExecTime(tree, a, b, time):
    a_ele = exists_by_label(tree, a)
    if a_ele is not None:
        a_id = a_ele.get("id")
        b_ele = exists_by_label(tree, b)
        b_endpoint_key = b_ele.get("endpoint") if b_ele is not None else b
        b_endpoint_key = b_endpoint_key if b_endpoint_key != "" else b
        modified_tree = max_exec_time_modify(tree, a_ele, b_ele, time) # Creates the modified tree here
        return modified_tree, {"CallerID" : a_id,
                    "Phase": "before",
                    "Pattern" : "maxExecTime",
                    "Time" : time,
                    "B_Endpoint" : b_endpoint_key}
    else:
        logger.info(f'Activity "{a}" is missing so the maximal execution time is by definition not exceeded, since the activity is never executed')
        return tree, None

## There are technically many ways to implement this and accordingly many ways this could be checked, we enforcce here a very visually pleasing way of enforcing this, which is a event based gateway with a timeout. If said timeout finishes first it would mean that the max time between has passed. This is just one of many ways such as adding syncs before and after a and b, but this would be much less checkable and also have several ways of implementing
def max_time_between(tree, a, b, time, c = None):
    apath = exists_by_label(tree, a)
    bpath = exists_by_label(tree, b)
    if apath is not None:
        if bpath is not None:
            c_path = exists_by_label(tree, c)
            c_endpoint_key = c_path.get("endpoint") if c_path is not None else c
            c_endpoint_key = c_endpoint_key if c_endpoint_key != "" else c
            modified_tree = max_time_between_modify(tree, apath, bpath, c_path, time) # Creates the modified tree here
            return modified_tree, {"CallerID" : apath.get("id"),
                    "Phase": "before",
                    "Pattern" : "max_time_between",
                    "Time" : time,
                    "C_Endpoint" : c_endpoint_key}
        else:
            logger.info(f'Activity "{b}" is missing in the process')
            return tree, None
    else:
        logger.info(f'Activity "{a}" is missing in the process')
        return tree, None

## Min Time between two activities, enforced via Voting
def wait_for_event_between(tree, a, b, event):
    a_sync = None
    if leads_to_helper(tree, a, b):
        apath = exists_by_label(tree, a)
        bpath = exists_by_label(tree, b)
        if apath is not None and bpath is not None:
            if type(event) == int:
                ## Event is a timeout with time event
                modified_tree = wait_for_timeout_modify(tree, apath, bpath, event) # Creates the modified tree here
                return modified_tree, {"CallerID" : apath.get("id"),
                    "Phase": "before",
                    "Pattern" : "wait_for_timeout_between",
                    "B_ID" : bpath.get("id"),
                    "Time" : event}
            else:
                c_path = exists_by_label(tree, event)
                c_endpoint_key = c_path.get("endpoint") if c_path is not None else event
                c_endpoint_key = c_endpoint_key if c_endpoint_key != "" else event
                modified_tree = wait_for_event_modify(tree, apath, bpath, c_path) # Creates the modified tree here
                return modified_tree, {"CallerID" : apath.get("id"),
                    "Phase": "before",
                    "Pattern" : "wait_for_event_between",
                    "B_ID" : bpath.get("id"),
                    "Event" : event,
                    "C_Endpoint" : c_endpoint_key}
        return tree, None
    else:
        logger.info(f'Activities "{a}" and "{b}" are not in a leads_to relationship, so the wait for event between requirement is False')
        return tree, None
    
    

## By Due Date: Decide how to handle due dates later
## This simply reads the annotation whether the due date is set correctly in the annotation, it does not check actual implementation, could be extended with voting later then it would even work during execution
def by_due_date_annotated(tree, a, timestamp):
    return tree, None
## By Due Date: checks if the due date requirement is explicitly defined through sync check 
def by_due_date_explicit(tree, a, timestamp):
    return tree, None

## checks both annotated and explicit, returns true if either
def by_due_date(tree, a, timestamp, c = None):
    return tree, None



def leads_to_helper(tree, a, b):
    apath = exists_by_label(tree, a)
    bpath = exists_by_label(tree, b)
    if apath is not None:
        if bpath is not None:
            compare = compare_ele(tree, apath, bpath)
            if compare == 0:
                logger.info(f'Activity "{a}" and Activity "{b}" are on different exclusive branches')
                return False
            elif compare == -1:
                logger.info(f'Activity "{a}" and Activity "{b}" are in parrallel')
                return False
            elif compare == 1:
                logger.info(f'Activity "{a}" is before Activity "{b}, checking if {b} is on a different exclusive branch"')
                ancestors_a, ancestors_b, shared = get_shared_ancestors(tree, apath, bpath)
                if any(elem.tag.endswith("choose") for elem in ancestors_b):
                    MCA = shared[-1].tag
                    if MCA.endswith("alternative") or MCA.endswith("otherwise") or MCA.endswith("parallel_branch"):
                        logger.info(f'Activity "{a}" and Activity "{b}" are on the same branch in the correct order')
                        return True
                    logger.info(f'Activity "{a} was found before "{b}, but it is in a different exclusive branch, so leads_to can not be guaranteed in every trace')
                    return False
                logger.info(f'Activity "{a}" is before Activity "{b}" and they do not share any exclusive branches, so leads_to is guaranteed')
                return True
            elif compare == 2:
                logger.info(f'Activity "{b}" is before Activity "{a}"')
                return False
        else:
            logger.info(f'Activity "{b}" is not found in the tree')
            return False 
    else:
        logger.info(f'Activity "{a}" is not found in the tree')
        return True




def executed_by(tree, a, resource):
    return tree, None

# These are just left empty to keep compatability with the full ASTs
def exists(tree, a):#
    return tree, None
def absence(tree, a):
    return tree, None
def loop(tree, a):
    return tree, None
def directly_follows(tree, a, b):
    return tree, None
def exclusive(tree, a, b):
    return tree, None
def leads_to(tree, a, b):
    return tree, None
def precedence(tree, a, b):
    return tree, None
def leads_to_absence(tree, a, b):
    return tree, None
def parallel(tree, a, b):
    return tree, None
# Resource
def executed_by_identify(tree, resource):
    return tree, None
def executed_by_return(tree, a):
    return tree, None
## Data
def send_exist(tree, data, complete = False):
    return tree, None
def receive_exist(tree, data, complete = False):
    return tree, None
def activity_sends(tree, a, data):
    return tree, None
def activity_receives(tree, a, data):
    return tree, None
def condition(tree, condition):
    return tree, None
def condition_directly_follows(tree, condition , a):
    return tree, None
def failure_eventually_follows(tree, a, b):
    return tree, None

def failure_directly_follows(tree, a, b):
    return tree, None
def condition_eventually_follows(tree, condition, a, scope = "branch"):
    return tree, None
def data_leads_to_absence(tree, condition, a):
    return tree, None
