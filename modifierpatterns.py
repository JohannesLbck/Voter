import logging
import re
import xml.etree.ElementTree as ET
from util import * 

logger = logging.getLogger(__name__)

def max_time_between_modify(tree, a_ele, b_ele, c_ele, time):
    '''
    This function modifies the tree such that, if the max time between constraint is explicitly enforced,
    then the parallel branch that ensures the explicit enforcement is removed.
    '''
    logger.debug("Modifying tree for max_time_between constraint")
    for timeout in timeouts_exists(tree):
        if cancel_last(tree, timeout[0], b_ele) is not None:
            if not timeout[1].isdigit():
                logger.warning(f"Time value {timeout[1]} is not a digit, Assume this is the correct timeout")
                return remove_timeout(tree, timeout)
            elif int(timeout[1]) == time:
                logger.info(f"Removing timeout with id {timeout[0]} since it matches the time constraint")
                return remove_timeout(tree, timeout)
    logger.warning("No matching timeout found for the max_time_between constraint, returning original tree")
    return tree

def recurring_modify(tree, a_ele, b_ele, time):
    '''
    This function modifies the tree such that, if the modify requirement is explicitly enforced, then the parallel
    branch that contains the loop enforcing the recurring requirement is removed.
    '''
    for timeout in timeouts_exists(tree):
        if cancel_last(tree, timeout[0], b_ele) is not None:
            if not timeout[1].isdigit():
                logger.warning(f"Time value {timeout[1]} is not a digit, Assume this is the correct timeout")
                return remove_timeout(tree, timeout)
            elif int(timeout[1]) == time:
                logger.info(f"Removing timeout with id {timeout[0]} since it matches the time constraint")
                return remove_timeout(tree, timeout)
    logger.warning("No matching timeout found for the recurring constraint, returning original tree")

    return tree

def wait_for_event_modify(tree, a_ele, b_ele, time):
    return tree

def remove_timeout(tree, timeout):
    '''
    This function removes the entire parallel_branch containing the timeout from the tree.
    If this leaves only a single branch in the parallel, then the parallel is removed
    and the remaining branch's children are placed directly in the parent.
    '''
    # timeout[0] is the <timeout> element nested inside <call>/<parameters>/<arguments>.
    # Walk up the ancestor chain to find the containing parallel_branch and parallel.
    ancestors = get_ancestors(tree, timeout[0])

    parallel_branch = None
    parallel = None
    parallel_parent = None
    for i, ancestor in enumerate(ancestors):
        if ancestor.tag.endswith("parallel_branch") and parallel_branch is None:
            parallel_branch = ancestor
        elif ancestor.tag.endswith("parallel") and parallel_branch is not None and parallel is None:
            parallel = ancestor
            if i + 1 < len(ancestors):
                parallel_parent = ancestors[i + 1]
            break

    if parallel_branch is None or parallel is None:
        logger.warning("Could not find parallel_branch/parallel containing the timeout, returning original tree")
        return tree

    branches = [child for child in parallel if child.tag.endswith("parallel_branch")]

    if len(branches) == 2:
        remaining_branch = [b for b in branches if b is not parallel_branch][0]
        if parallel_parent is not None:
            idx = list(parallel_parent).index(parallel)
            parallel_parent.remove(parallel)
            for i, child in enumerate(list(remaining_branch)):
                parallel_parent.insert(idx + i, child)
            logger.info("Removed parallel gateway since only one branch was left after removing timeout branch")
        else:
            parallel.remove(parallel_branch)
            logger.info("Removed timeout branch from parallel (parallel is root element)")
    else:
        parallel.remove(parallel_branch)
        logger.info("Removed timeout branch from parallel gateway")

    return tree