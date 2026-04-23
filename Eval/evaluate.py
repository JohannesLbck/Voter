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
import re
import shutil
import subprocess
from collections import Counter, defaultdict, deque

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

SEQUENCE_WRAPPER_TAGS = {"description", "parallel_branch", "alternative", "otherwise"}
ACTIVITY_TAGS = {"call", "terminate", "stop"}
CONNECTOR_TYPES = {"AND", "XOR", "OR"}


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


def _choose_type(elem):
    """Map CPEE choose mode to EPC-style connector type."""
    mode = (elem.attrib.get("mode") or "").strip().lower()
    if mode in {"inclusive", "or"}:
        return "OR"
    # Default to XOR for exclusive or unspecified choose nodes.
    return "XOR"


def _max_nesting_depth(elem):
    """Maximum nesting depth of structured blocks (parallel/choose/loop)."""
    tag = _strip_ns(elem.tag)
    child_depths = [_max_nesting_depth(c) for c in _structural_children(elem)]
    best_child = max(child_depths) if child_depths else 0
    if tag in CONNECTOR_TAGS:
        return 1 + best_child
    return best_child


def _build_flow_graph(tree):
    """Build a directed flow graph from the structured CPEE tree.

    Returns a dict with nodes/edges and connector metadata. Connector metadata
    uses EPC-style AND/XOR/OR types with explicit split/join roles.
    """
    next_id = [0]
    nodes = set()
    edges = set()
    node_meta = {}
    connector_roles = {}

    def add_node(kind, connector_type=None, role=None):
        next_id[0] += 1
        nid = f"n{next_id[0]}"
        nodes.add(nid)
        node_meta[nid] = {
            "kind": kind,
            "connector_type": connector_type,
            "role": role,
        }
        if connector_type in CONNECTOR_TYPES and role in {"split", "join"}:
            connector_roles[nid] = (connector_type, role)
        return nid

    def add_edge(src, dst):
        if src is not None and dst is not None:
            edges.add((src, dst))

    def connect_all(from_nodes, to_nodes):
        for src in from_nodes:
            for dst in to_nodes:
                add_edge(src, dst)

    def build_sequence(elements):
        entries = set()
        prev_exits = None
        for child in elements:
            tag = _strip_ns(child.tag)
            if tag not in STRUCTURAL_TAGS:
                continue
            child_entries, child_exits = build_elem(child)
            if not child_entries and not child_exits:
                continue
            if not entries:
                entries = set(child_entries)
            if prev_exits is not None:
                connect_all(prev_exits, child_entries)
            prev_exits = set(child_exits)
        if not entries:
            return set(), set()
        return entries, (prev_exits if prev_exits is not None else set())

    def branch_content(branch_elem):
        return [c for c in branch_elem if _strip_ns(c.tag) in STRUCTURAL_TAGS]

    def build_elem(elem):
        tag = _strip_ns(elem.tag)

        if tag in ACTIVITY_TAGS:
            nid = add_node("activity")
            return {nid}, {nid}

        if tag in SEQUENCE_WRAPPER_TAGS:
            return build_sequence(branch_content(elem))

        if tag == "parallel":
            split = add_node("connector", connector_type="AND", role="split")
            join = add_node("connector", connector_type="AND", role="join")

            branches = [c for c in elem if _strip_ns(c.tag) == "parallel_branch"]
            if not branches:
                add_edge(split, join)
                return {split}, {join}

            for br in branches:
                b_entries, b_exits = build_sequence(branch_content(br))
                if b_entries:
                    connect_all({split}, b_entries)
                    connect_all(b_exits, {join})
                else:
                    add_edge(split, join)

            return {split}, {join}

        if tag == "choose":
            ctype = _choose_type(elem)
            split = add_node("connector", connector_type=ctype, role="split")
            join = add_node("connector", connector_type=ctype, role="join")

            branches = [
                c for c in elem
                if _strip_ns(c.tag) in {"alternative", "otherwise"}
            ]
            if not branches:
                add_edge(split, join)
                return {split}, {join}

            for br in branches:
                b_entries, b_exits = build_sequence(branch_content(br))
                if b_entries:
                    connect_all({split}, b_entries)
                    connect_all(b_exits, {join})
                else:
                    add_edge(split, join)

            return {split}, {join}

        if tag == "loop":
            # Model loop semantics as decision + explicit back-edge.
            decision = add_node("loop_decision")
            after_loop = add_node("loop_exit")
            add_edge(decision, after_loop)  # condition false path

            body_entries, body_exits = build_sequence(branch_content(elem))
            if body_entries:
                connect_all({decision}, body_entries)
                connect_all(body_exits, {decision})

            return {decision}, {after_loop}

        return set(), set()

    root_children = [c for c in tree if _strip_ns(c.tag) in STRUCTURAL_TAGS]
    build_sequence(root_children)

    out_adj = defaultdict(set)
    in_adj = defaultdict(set)
    for src, dst in edges:
        out_adj[src].add(dst)
        in_adj[dst].add(src)

    # Ensure every node appears in adjacency maps.
    for nid in nodes:
        out_adj[nid]
        in_adj[nid]

    connector_data = []
    connector_nodes = set()
    for nid, (ctype, role) in connector_roles.items():
        degree = len(out_adj[nid]) if role == "split" else len(in_adj[nid])
        connector_data.append(
            {
                "id": nid,
                "type": ctype,
                "role": role,
                "degree": degree,
            }
        )
        connector_nodes.add(nid)

    return {
        "nodes": nodes,
        "edges": edges,
        "out_adj": out_adj,
        "in_adj": in_adj,
        "node_meta": node_meta,
        "connector_data": connector_data,
        "connector_nodes": connector_nodes,
        "non_connector_nodes": nodes - connector_nodes,
    }


def _count_cut_vertices(graph):
    """Count articulation points on the undirected projection of the graph."""
    nodes = list(graph["nodes"])
    if len(nodes) < 3:
        return 0

    undirected = defaultdict(set)
    for src, dst in graph["edges"]:
        undirected[src].add(dst)
        undirected[dst].add(src)
    for nid in graph["nodes"]:
        undirected[nid]

    def reachable_without(removed):
        remaining = set(graph["nodes"]) - {removed}
        if not remaining:
            return set()
        start = next(iter(remaining))
        seen = {start}
        q = deque([start])
        while q:
            cur = q.popleft()
            for nxt in undirected[cur]:
                if nxt == removed or nxt in seen:
                    continue
                seen.add(nxt)
                q.append(nxt)
        return seen

    cut_count = 0
    full_nodes = set(graph["nodes"])
    for nid in nodes:
        remaining = full_nodes - {nid}
        if len(remaining) < 2:
            continue
        if reachable_without(nid) != remaining:
            cut_count += 1
    return cut_count


def _nodes_on_directed_cycles(graph):
    """Return set of nodes that belong to at least one directed cycle."""
    out_adj = graph["out_adj"]
    in_adj = graph["in_adj"]
    all_nodes = set(graph["nodes"])

    visited = set()
    order = []

    def dfs1(start):
        stack = [(start, False)]
        while stack:
            node, expanded = stack.pop()
            if expanded:
                order.append(node)
                continue
            if node in visited:
                continue
            visited.add(node)
            stack.append((node, True))
            for nxt in out_adj[node]:
                if nxt not in visited:
                    stack.append((nxt, False))

    for nid in all_nodes:
        if nid not in visited:
            dfs1(nid)

    visited.clear()
    cycle_nodes = set()

    for nid in reversed(order):
        if nid in visited:
            continue
        comp = set()
        stack = [nid]
        visited.add(nid)
        while stack:
            cur = stack.pop()
            comp.add(cur)
            for prev in in_adj[cur]:
                if prev not in visited:
                    visited.add(prev)
                    stack.append(prev)

        if len(comp) > 1:
            cycle_nodes.update(comp)
        else:
            only = next(iter(comp))
            if only in out_adj[only]:
                cycle_nodes.add(only)

    return cycle_nodes


def _longest_simple_path_length(graph):
    """Return length (in edges) of the longest simple directed path.

    Notes:
    - A model with cycles can have infinitely long non-simple paths.
    - This metric therefore uses simple paths (no node repeats), which
      is finite and aligns with a practical notion of longest possible path.
    """
    out_adj = graph["out_adj"]
    nodes = list(graph["nodes"])
    best = 0

    def dfs(node, visited, length):
        nonlocal best
        if length > best:
            best = length
        for nxt in out_adj[node]:
            if nxt in visited:
                continue
            visited.add(nxt)
            dfs(nxt, visited, length + 1)
            visited.remove(nxt)

    for start in nodes:
        dfs(start, {start}, 0)

    return best


# ── Metrics aligned to formal definitions ──────────────────────────────

def size(analysis):
    """|N|: number of graph nodes (activities + connector instances)."""
    return len(analysis["nodes"])


def diameter(analysis):
    """Diameter: longest possible simple directed path (edge count)."""
    return _longest_simple_path_length(analysis)


def avg_connector_degree(analysis):
    """dC: average connector degree over AND/XOR/OR connector instances."""
    connectors = analysis["connector_data"]
    if not connectors:
        return 0.0
    return sum(c["degree"] for c in connectors) / len(connectors)


def max_connector_degree(analysis):
    """d^C: maximum connector degree over AND/XOR/OR connector instances."""
    connectors = analysis["connector_data"]
    if not connectors:
        return 0
    return max(c["degree"] for c in connectors)


def separability(analysis):
    """Π(G) = |cut-vertices| / (|N| - 2)."""
    n = len(analysis["nodes"])
    if n <= 2:
        return 0.0
    cut_vertices = _count_cut_vertices(analysis)
    return cut_vertices / (n - 2)


def sequentiality(analysis):
    """Ξ(G): share of arcs between non-connector nodes."""
    edges = analysis["edges"]
    if not edges:
        return 0.0
    non_connectors = analysis["non_connector_nodes"]
    seq_arcs = sum(1 for src, dst in edges if src in non_connectors and dst in non_connectors)
    return seq_arcs / len(edges)


def depth(tree):
    """Λ: maximum nesting depth of structured blocks."""
    return _max_nesting_depth(tree)


def mismatch(analysis):
    """MM(G): type-wise split/join degree mismatch summed over AND/XOR/OR."""
    by_type = {
        "AND": {"split": 0, "join": 0},
        "XOR": {"split": 0, "join": 0},
        "OR": {"split": 0, "join": 0},
    }
    for c in analysis["connector_data"]:
        by_type[c["type"]][c["role"]] += c["degree"]
    return sum(abs(v["split"] - v["join"]) for v in by_type.values())


def heterogeneity(analysis):
    """CH(G): entropy over AND/XOR/OR connectors using log base 3."""
    counts = Counter(c["type"] for c in analysis["connector_data"])
    total = sum(counts.values())
    if total == 0:
        return 0.0

    entropy = 0.0
    log3 = math.log(3)
    for c in counts.values():
        p = c / total
        if p > 0:
            entropy -= p * (math.log(p) / log3)
    return entropy


def cyclicity(analysis):
    """CYCN(G): fraction of nodes that belong to directed cycles."""
    n = len(analysis["nodes"])
    if n == 0:
        return 0.0
    cycle_nodes = _nodes_on_directed_cycles(analysis)
    return len(cycle_nodes) / n


def token_splits(analysis):
    """TS(G): extra tokens introduced by AND/OR split connectors."""
    total = 0
    for c in analysis["connector_data"]:
        if c["role"] == "split" and c["type"] in {"AND", "OR"}:
            total += max(c["degree"] - 1, 0)
    return total


def control_flow_complexity(analysis):
    """CFC(G) according to split connector weighting."""
    total = 0
    for c in analysis["connector_data"]:
        if c["role"] != "split":
            continue
        d = c["degree"]
        if c["type"] == "AND":
            total += 1
        elif c["type"] == "XOR":
            total += d
        elif c["type"] == "OR":
            total += (2 ** d) - 1
    return total


def join_complexity(analysis):
    """JC(G) according to join connector weighting."""
    total = 0
    for c in analysis["connector_data"]:
        if c["role"] != "join":
            continue
        d = c["degree"]
        if c["type"] == "AND":
            total += 1
        elif c["type"] == "XOR":
            total += d
        elif c["type"] == "OR":
            total += (2 ** d) - 1
    return total




# ── All metrics in one pass ────────────────────────────────────────────

FULLMETRICS = [
    ("Size |N|",                 size),
    ("Diameter (Longest Path)",  diameter),
    ("Avg. Connector Degree dC", avg_connector_degree),
    ("Max. Connector Degree d^C", max_connector_degree),
    ("Separability Pi",          separability),
    ("Sequentiality Xi",         sequentiality),
    ("Depth Lambda",             depth),
    ("Mismatch MM",              mismatch),
    ("Heterogeneity CH",         heterogeneity),
    ("Cyclicity CYCN",           cyclicity),
    ("Token Splits TS",          token_splits),
    ("Control Flow Complexity CFC", control_flow_complexity),
    ("Join Complexity JC",       join_complexity),
]

METRICS = [
    ("Size |N|",                 size),
    ("Diameter (Longest Path)",  diameter),
    ("Separability Pi",          separability),
    ("Sequentiality Xi",         sequentiality),
    ("Heterogeneity CH",         heterogeneity),
    ("Cyclicity CYCN",           cyclicity),
    ("Control Flow Complexity CFC", control_flow_complexity),
    ("Join Complexity JC",       join_complexity),
]


def compute_metrics(tree):
    """Return an ordered dict of metric-name → value for *tree*."""
    analysis = _build_flow_graph(tree)
    return {
        name: (fn(tree) if name == "Depth Lambda" else fn(analysis))
        for name, fn in METRICS
    }


def _safe_slug(text):
    """Convert arbitrary text to a filesystem-safe slug."""
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", text.strip())
    return slug.strip("_") or "graph"


def export_flow_graph(tree, label, output_dir):
    """Export directed flow graph visualization as DOT and optional PNG.

    DOT is always written. If Graphviz 'dot' is available on PATH,
    a PNG is rendered next to the DOT file.
    """
    analysis = _build_flow_graph(tree)
    node_meta = analysis["node_meta"]
    edges = sorted(analysis["edges"])

    os.makedirs(output_dir, exist_ok=True)
    base_name = _safe_slug(label)
    dot_path = os.path.join(output_dir, f"{base_name}.dot")
    png_path = os.path.join(output_dir, f"{base_name}.png")

    def _dot_node_attrs(nid):
        meta = node_meta.get(nid, {})
        kind = meta.get("kind")
        ctype = meta.get("connector_type")
        role = meta.get("role")

        if kind == "activity":
            return 'shape=box, style="rounded,filled", fillcolor="#e6f2ff", label="ACT"'
        if kind == "loop_decision":
            return 'shape=diamond, style="filled", fillcolor="#fff4cc", label="LOOP?"'
        if kind == "loop_exit":
            return 'shape=circle, style="filled", fillcolor="#f2f2f2", label="EXIT"'
        if kind == "connector":
            txt = ctype if ctype else "CONN"
            if role:
                txt = f"{txt}\\n{role}"
            return f'shape=diamond, style="filled", fillcolor="#fce5cd", label="{txt}"'
        return 'shape=ellipse, label="NODE"'

    lines = []
    lines.append("digraph FlowGraph {")
    lines.append('  rankdir=LR;')
    lines.append('  graph [fontsize=10, fontname="Helvetica"];')
    lines.append('  node [fontsize=10, fontname="Helvetica"];')
    lines.append('  edge [fontsize=9, fontname="Helvetica"];')

    for nid in sorted(analysis["nodes"]):
        lines.append(f'  "{nid}" [{_dot_node_attrs(nid)}];')

    for src, dst in edges:
        lines.append(f'  "{src}" -> "{dst}";')

    lines.append("}")

    with open(dot_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    rendered_png = False
    if shutil.which("dot"):
        try:
            subprocess.run(
                ["dot", "-Tpng", dot_path, "-o", png_path],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            rendered_png = True
        except Exception:
            rendered_png = False

    return dot_path, (png_path if rendered_png else None)


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
    vis_dir = os.path.join(base_dir, "Eval", "flow_graphs")

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
        dot_path, png_path = export_flow_graph(
            input_tree,
            f"{input_basename}__ORIGINAL",
            vis_dir,
        )
        print(f"  [GRAPH] {dot_path}")
        if png_path:
            print(f"  [GRAPH] {png_path}")

        output_files = find_output_files(input_basename, outputs_dir)
        if not output_files:
            print("  No corresponding output files found.")
        for out_path in output_files:
            out_name = os.path.basename(out_path)
            try:
                out_tree = get_process_tree(out_path)
                rows.append((out_name, compute_metrics(out_tree)))
                dot_path, png_path = export_flow_graph(
                    out_tree,
                    f"{input_basename}__{out_name}",
                    vis_dir,
                )
                print(f"  [GRAPH] {dot_path}")
                if png_path:
                    print(f"  [GRAPH] {png_path}")
            except Exception as e:
                print(f"  [ERROR] {out_name}: {e}")

        print()
        print_metrics_table(rows)


if __name__ == "__main__":
    main()
