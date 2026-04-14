"""
Evaluation script for comparing input and output CPEE process trees.

Reads an input tree from the Inputs/ directory and the corresponding
output trees from the Outputs/ directory, then computes structural
metrics on each tree for comparison.
"""

import os
import sys
import glob
import xml.etree.ElementTree as ET
import math
from collections import Counter

# ── Namespaces ──────────────────────────────────────────────────────────
NS = "http://cpee.org/ns/description/1.0"
NS_PROPS = "http://cpee.org/ns/properties/2.0"

# Tags that constitute "structural" nodes in the process tree
STRUCTURAL_TAGS = {
    "description", "call", "parallel", "parallel_branch",
    "choose", "alternative", "otherwise",
    "loop", "terminate", "stop",
}

# Tags that are control-flow connectors (gateways / routing constructs)
CONNECTOR_TAGS = {"parallel", "choose", "loop"}


# ── Helper: extract the inner process-tree element ──────────────────────
def get_process_tree(xml_path):
    """Parse *xml_path* and return the inner <description> element that
    holds the CPEE process tree."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    desc = root.find(".//{%s}description" % NS)
    if desc is None:
        raise ValueError(f"No inner <description> element found in {xml_path}")
    return desc


def _strip_ns(tag):
    """Return local tag name without namespace URI."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _structural_children(elem):
    """Yield child elements whose tag is a structural process-tree tag."""
    for child in elem:
        if _strip_ns(child.tag) in STRUCTURAL_TAGS:
            yield child


# ── Metric placeholders ────────────────────────────────────────────────

def size(tree):
    """M1 – Size: total number of structural nodes in the tree."""
    count = 0
    stack = [tree]
    while stack:
        node = stack.pop()
        if _strip_ns(node.tag) in STRUCTURAL_TAGS or _strip_ns(node.tag) in CONNECTOR_TAGS:
            count += 1
            stack.extend(_structural_children(node))
    return count


def diameter(tree):
    """M2 – Diameter: length of the longest root-to-leaf path
    (counted in edges between structural nodes)."""

    def _longest(node, depth):
        children = list(_structural_children(node))
        if not children:
            return depth
        return max(_longest(c, depth + 1) for c in children)

    return _longest(tree, 0)


def separability(tree):
    """M3 – Separability: number of cut-vertices / Size.

    A cut-vertex is a structural node whose removal would disconnect the
    tree into two or more components.

    TODO: implement cut-vertex detection; returning placeholder 0.0.
    """
    n = size(tree)
    if n == 0:
        return 0.0
    cut_vertices = 0  # TODO: compute actual cut-vertices
    return cut_vertices / n


def concurrency(tree):
    """M4 – Concurrency (token-split-sum): sum over every parallel
    gateway of (number_of_branches − 1), which equals the extra tokens
    introduced at that split.

    TODO: verify semantics; currently counts parallel_branch children of
    each <parallel> element.
    """
    total = 0
    stack = [tree]
    while stack:
        node = stack.pop()
        tag = _strip_ns(node.tag)
        if tag == "parallel":
            branches = [c for c in node if _strip_ns(c.tag) == "parallel_branch"]
            if branches:
                total += len(branches) - 1
        if tag in STRUCTURAL_TAGS:
            stack.extend(_structural_children(node))
    return total


def cyclicity(tree):
    """M5 – Cyclicity: number of <loop> elements in the tree."""
    count = 0
    stack = [tree]
    while stack:
        node = stack.pop()
        if _strip_ns(node.tag) == "loop":
            count += 1
        if _strip_ns(node.tag) in STRUCTURAL_TAGS:
            stack.extend(_structural_children(node))
    return count


def heterogeneity(tree):
    """M6 – Heterogeneity: Shannon entropy of connector-type
    distribution (parallel, choose, loop).

    Entropy H = − Σ p_i · log2(p_i) over the connector types.
    """
    counts = Counter()
    stack = [tree]
    while stack:
        node = stack.pop()
        tag = _strip_ns(node.tag)
        if tag in CONNECTOR_TAGS:
            counts[tag] += 1
        if tag in STRUCTURAL_TAGS:
            stack.extend(_structural_children(node))

    total = sum(counts.values())
    if total == 0:
        return 0.0

    entropy = 0.0
    for c in counts.values():
        p = c / total
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy


# ── All metrics in one pass ────────────────────────────────────────────

METRICS = [
    ("Size (#Nodes)",            size),
    ("Diameter (Longest Path)",  diameter),
    ("Separability",             separability),
    ("Concurrency (Token Split)",concurrency),
    ("Cyclicity (#Loops)",       cyclicity),
    ("Heterogeneity (Entropy)",  heterogeneity),
]


def compute_metrics(tree):
    """Return an ordered dict of metric-name → value for *tree*."""
    return {name: fn(tree) for name, fn in METRICS}


# ── Matching outputs to an input ───────────────────────────────────────

def find_output_files(input_basename, outputs_dir):
    """Return sorted list of output files that correspond to the given
    input file name.  Output naming convention produced by the
    transformer:  modified_<input_basename>_<counter>_<timestamp>.xml
    """
    pattern = os.path.join(outputs_dir, f"modified_{input_basename}_*")
    return sorted(glob.glob(pattern))


# ── Pretty-print ───────────────────────────────────────────────────────

def print_metrics_table(rows):
    """Print a comparison table.  *rows* is a list of (label, metrics_dict)."""
    if not rows:
        return

    metric_names = [name for name, _ in METRICS]
    col_width = max(len(n) for n in metric_names) + 2
    label_width = max(len(label) for label, _ in rows) + 2

    # Header
    header = "".ljust(label_width) + "".join(n.ljust(col_width) for n in metric_names)
    print(header)
    print("-" * len(header))

    for label, metrics in rows:
        vals = "".join(f"{metrics[n]:<{col_width}.4f}" if isinstance(metrics[n], float)
                       else f"{metrics[n]:<{col_width}}"
                       for n in metric_names)
        print(f"{label:<{label_width}}{vals}")


# ── CLI entry point ────────────────────────────────────────────────────

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    inputs_dir = os.path.join(base_dir, "Inputs")
    outputs_dir = os.path.join(base_dir, "Outputs")

    # If a specific input file is given as argument, use it; otherwise
    # evaluate all files in Inputs/
    if len(sys.argv) > 1:
        input_files = [os.path.join(inputs_dir, f) for f in sys.argv[1:]]
    else:
        input_files = sorted(glob.glob(os.path.join(inputs_dir, "*.xml")))

    if not input_files:
        print("No input files found.")
        return

    for input_path in input_files:
        input_basename = os.path.basename(input_path)
        print(f"\n{'=' * 70}")
        print(f"Input: {input_basename}")
        print(f"{'=' * 70}")

        try:
            input_tree = get_process_tree(input_path)
        except Exception as e:
            print(f"  [ERROR] Could not parse input: {e}")
            continue

        rows = []
        rows.append(("ORIGINAL", compute_metrics(input_tree)))

        output_files = find_output_files(input_basename, outputs_dir)
        if not output_files:
            print("  No corresponding output files found.")
        for out_path in output_files:
            out_name = os.path.basename(out_path)
            try:
                out_tree = get_process_tree(out_path)
                rows.append((out_name, compute_metrics(out_tree)))
            except Exception as e:
                print(f"  [ERROR] {out_name}: {e}")

        print()
        print_metrics_table(rows)


if __name__ == "__main__":
    main()
