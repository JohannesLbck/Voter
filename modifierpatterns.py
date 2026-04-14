import logging
import re
import xml.etree.ElementTree as ET
from util import * 

logger = logging.getLogger(__name__)


def _find_timeout_call(tree, timeout_element):
    '''Find the <call> element that contains a <timeout> element.'''
    for ancestor in get_ancestors(tree, timeout_element):
        if ancestor.tag.endswith("call"):
            return ancestor
    return None

def _in_separate_branches(tree, ele1, ele2):
    '''Check if ele1 and ele2 are in different branches of the same parallel.
    Returns the parallel element if found, None otherwise.
    Unlike cancel_last/cancel_first, this does not restrict on wait/cancel attributes.'''
    _, _, shared = get_shared_ancestors(tree, ele1, ele2)
    shared_branch = 0
    parallel_count = 0
    for ancestor in shared:
        if ancestor.tag.endswith("parallel_branch"):
            shared_branch += 1
        elif ancestor.tag.endswith("parallel"):
            if shared_branch <= parallel_count:
                return ancestor
            parallel_count += 1
    return None


## Currently the following 3 methods all do the exact same thing, keep them as 3 for now, in case I find a reason to separate them later
## Also makes testing easier

def max_exec_time_modify(tree, a_ele, b_ele, time):
    '''
    This function modifies the tree such that, if the max execution time constraint is explicitly enforced, then the parallel
    branch that contains the timeout enforcing the max execution time constraint is removed.
    The timeout and b_ele are in the same branch (timeout fires, then b executes), while a_ele is in a different branch.
    '''
    for timeout in timeouts_exists(tree):
        timeout_call = _find_timeout_call(tree, timeout[0])
        if timeout_call is None:
            continue
        if _in_separate_branches(tree, timeout_call, a_ele) is not None:
            print(f'Found timeout call with id {timeout_call.get("id", "unknown")} in separate branch from a_ele with id {a_ele.get("id", "unknown")}')
            if not timeout[1].isdigit():
                logger.warning(f"Time value {timeout[1]} is not a digit, Assume this is the correct timeout")
                return remove_timeout(tree, timeout)
            elif int(timeout[1]) == time:
                logger.info(f"Removing timeout with id {timeout_call.get('id', 'unknown')} since it matches the time constraint")
                return remove_timeout(tree, timeout)
    logger.warning("No matching timeout found for the maxExecTime constraint, returning original tree")
    return tree

def max_time_between_modify(tree, a_ele, b_ele, c_ele, time):
    '''
    This function modifies the tree such that, if the max time between constraint is explicitly enforced,
    then the parallel branch that ensures the explicit enforcement is removed.
    The timeout races against b_ele (in different branches): if time elapses before b, c executes.
    '''
    logger.debug("Modifying tree for max_time_between constraint")
    for timeout in timeouts_exists(tree):
        timeout_call = _find_timeout_call(tree, timeout[0])
        if timeout_call is None:
            continue
        if _in_separate_branches(tree, timeout_call, b_ele) is not None:
            if not timeout[1].isdigit():
                logger.warning(f"Time value {timeout[1]} is not a digit, Assume this is the correct timeout")
                return remove_timeout(tree, timeout)
            elif int(timeout[1]) == time:
                logger.info(f"Removing timeout with id {timeout_call.get('id', 'unknown')} since it matches the time constraint")
                return remove_timeout(tree, timeout)
    logger.warning("No matching timeout found for the max_time_between constraint, returning original tree")
    return tree

def recurring_modify(tree, a_ele, b_ele, time):
    '''
    This function modifies the tree such that, if the modify requirement is explicitly enforced, then the parallel
    branch that contains the loop enforcing the recurring requirement is removed.
    The timeout and b_ele are in the same branch (inside a loop), while a_ele is in a different branch.
    '''
    for timeout in timeouts_exists(tree):
        timeout_call = _find_timeout_call(tree, timeout[0])
        if timeout_call is None:
            continue
        if _in_separate_branches(tree, timeout_call, a_ele) is not None:
            if not timeout[1].isdigit():
                logger.warning(f"Time value {timeout[1]} is not a digit, Assume this is the correct timeout")
                return remove_timeout(tree, timeout)
            elif int(timeout[1]) == time:
                logger.info(f"Removing timeout with id {timeout_call.get('id', 'unknown')} since it matches the time constraint")
                return remove_timeout(tree, timeout)
    logger.warning("No matching timeout found for the recurring constraint, returning original tree")

    return tree

def _is_between(tree, a_ele, b_ele, target):
    '''Check if target is inside a parallel that appears between a_ele and b_ele in the tree.
    a_ele appears before the parallel, b_ele appears after it.'''
    ancestors = get_ancestors(tree, target)
    # Find the parallel_branch and parallel containing the target
    for ancestor in ancestors:
        if ancestor.tag.endswith("parallel") and not ancestor.tag.endswith("parallel_branch"):
            # Check that a_ele and b_ele are NOT inside this parallel (they are before/after it)
            a_ancestors = get_ancestors(tree, a_ele)
            b_ancestors = get_ancestors(tree, b_ele)
            if ancestor not in a_ancestors and ancestor not in b_ancestors:
                return True
    return False

def wait_for_event_modify(tree, a_ele, b_ele, c_ele):
    '''
    This function modifies the tree such that, if the wait for event constraint is explicitly enforced,
    then the parallel branch that contains the event call (c_ele) is removed.
    a_ele and b_ele are before/after the parallel; c_ele is inside a parallel branch.
    '''
    if c_ele is None:
        logger.warning("c_ele is None, cannot find event call to remove")
        return tree
    if _is_between(tree, a_ele, b_ele, c_ele):
        logger.info(f"Removing event call branch with id {c_ele.get('id', 'unknown')} from parallel between a_ele and b_ele")
        return _remove_branch_containing(tree, c_ele)
    logger.warning("No matching event call found in a parallel between a_ele and b_ele for the wait_for_event constraint, returning original tree")
    return tree

def wait_for_timeout_modify(tree, a_ele, b_ele, time):
    '''
    This function modifies the tree such that, if the wait for timeout constraint is explicitly enforced,
    then the parallel branch that contains the timeout is removed.
    a_ele and b_ele are before/after the parallel; the timeout is inside a parallel branch.
    '''
    for timeout in timeouts_exists(tree):
        timeout_call = _find_timeout_call(tree, timeout[0])
        if timeout_call is None:
            continue
        if _is_between(tree, a_ele, b_ele, timeout_call):
            if not timeout[1].isdigit():
                logger.warning(f"Time value {timeout[1]} is not a digit, Assume this is the correct timeout")
                return remove_timeout(tree, timeout)
            elif int(timeout[1]) == time:
                logger.info(f"Removing timeout with id {timeout_call.get('id', 'unknown')} since it matches the time constraint")
                return remove_timeout(tree, timeout)
    logger.warning("No matching timeout found for the wait_for_timeout constraint, returning original tree")
    return tree

def _remove_branch_containing(tree, element):
    '''
    Removes the parallel_branch containing `element` from the tree.
    If this leaves only a single branch in the parallel, the parallel is unwrapped
    and the remaining branch's children are placed directly in the parent.
    '''
    ancestors = get_ancestors(tree, element)

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
        logger.warning("Could not find parallel_branch/parallel containing the element, returning original tree")
        return tree

    branches = [child for child in parallel if child.tag.endswith("parallel_branch")]

    if len(branches) == 2:
        remaining_branch = [b for b in branches if b is not parallel_branch][0]
        if parallel_parent is not None:
            idx = list(parallel_parent).index(parallel)
            parallel_parent.remove(parallel)
            for i, child in enumerate(list(remaining_branch)):
                parallel_parent.insert(idx + i, child)
            logger.info("Removed parallel gateway since only one branch was left after removing branch")
        else:
            parallel.remove(parallel_branch)
            logger.info("Removed branch from parallel (parallel is root element)")
    else:
        parallel.remove(parallel_branch)
        logger.info("Removed branch from parallel gateway")

    return tree

def remove_timeout(tree, timeout):
    '''Remove the parallel_branch containing the timeout from the tree.'''
    return _remove_branch_containing(tree, timeout[0])