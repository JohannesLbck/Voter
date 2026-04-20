import os
import xml.etree.ElementTree as ET
import copy
import logging
import re
import json
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

from reqparser import parse_requirements
from ComplianceAST import traverse
from util import combine_sub_trees

NS = "http://cpee.org/ns/description/1.0"
NS_PROPS = "http://cpee.org/ns/properties/2.0"
NS_RIDDL = "http://riddl.org/ns/common-patterns/notifications-producer/2.0"

# Register namespaces so output uses clean names instead of ns0/ns1/ns2
ET.register_namespace('', NS_PROPS)
ET.register_namespace('cpee1', NS)
ET.register_namespace('riddl', NS_RIDDL)

def _fix_description_ns(xml_bytes):
    """Replace cpee1: prefixes with a default namespace redeclaration on the inner description."""
    text = xml_bytes.decode('UTF-8')
    # Remove the cpee1 namespace declaration from the root element
    text = text.replace(' xmlns:cpee1="%s"' % NS, '')
    # Replace opening inner description tag with default ns redeclaration
    text = re.sub(r'<cpee1:description(\s|>)', r'<description xmlns="%s"\1' % NS, text)
    text = text.replace('</cpee1:description>', '</description>')
    # Strip cpee1: prefix from all remaining elements
    text = text.replace('<cpee1:', '<').replace('</cpee1:', '</')
    return text.encode('UTF-8')

def add_start_end(tree):
    start = ET.Element("{%s}call" % NS, attrib={"id": "start", "endpoint": ""})
    start_params = ET.SubElement(start, "{%s}parameters" % NS)
    start_label = ET.SubElement(start_params, "{%s}label" % NS)
    start_label.text = "start_activity"

    end = ET.Element("{%s}call" % NS, attrib={"id": "end", "endpoint": ""})
    end_params = ET.SubElement(end, "{%s}parameters" % NS)
    end_label = ET.SubElement(end_params, "{%s}label" % NS)
    end_label.text = "end_activity"

    tree.insert(0, start)
    tree.append(end)
    return tree

def remove_start_end(tree):
    for elem in list(tree):
        if elem.tag == "{%s}call" % NS and elem.get("id") in ("start", "end"):
            label = elem.find("{%s}parameters/{%s}label" % (NS, NS))
            if label is not None and label.text in ("start_activity", "end_activity"):
                tree.remove(elem)
    return tree

def print_structure(elem, indent=0):
    tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
    structural_tags = ['description', 'call', 'parallel', 'parallel_branch', 'choose',
                       'alternative', 'otherwise', 'loop', 'terminate', 'start_activity',
                       'end_activity', 'stop']
    if tag not in structural_tags:
        return
    attrs = ''
    if tag == 'call':
        label_el = elem.find('{%s}parameters/{%s}label' % (NS, NS))
        endpoint = elem.get('endpoint', '')
        lbl = label_el.text if label_el is not None else ''
        attrs = f' endpoint="{endpoint}" label="{lbl}"'
    elif tag == 'parallel':
        attrs = f' wait="{elem.get("wait", "")}" cancel="{elem.get("cancel", "")}"'
    elif tag == 'loop':
        attrs = f' mode="{elem.get("mode", "")}" condition="{elem.get("condition", "")}"'
    elif tag == 'choose':
        attrs = f' mode="{elem.get("mode", "")}"'
    elif tag == 'alternative':
        attrs = f' condition="{elem.get("condition", "")}"'
    elif tag == 'stop':
        attrs = f' id="{elem.get("id", "")}"'

    print('  ' * indent + f'<{tag}{attrs}>')
    for child in elem:
        print_structure(child, indent + 1)

def process_file(process_file):
    print(f"\n{'='*60}")
    print(f"Loading process from: {process_file}")
    print(f"{'='*60}")

    full_tree = ET.parse(process_file)
    full_root = full_tree.getroot()

    # Extract requirements
    req_elem = full_root.find(".//{%s}requirements" % NS_PROPS)
    if req_elem is None or not req_elem.text:
        print("  No requirements found, skipping.")
        return
    req_text = req_elem.text
    requirements = parse_requirements(req_text)

    xml = full_root.find(".//{%s}description" % NS)
    xml, combined = combine_sub_trees(xml)

    # Save combined tree if subprocesses were actually combined
    if combined:
        combined_tree = copy.deepcopy(full_tree)
        combined_root = combined_tree.getroot()
        outer_desc = combined_root.find("{%s}description" % NS_PROPS)
        inner_desc = outer_desc.find("{%s}description" % NS)
        inner_desc.clear()
        inner_desc.tag = "{%s}description" % NS
        for attr_name, attr_val in xml.attrib.items():
            inner_desc.set(attr_name, attr_val)
        inner_desc.text = xml.text
        inner_desc.tail = xml.tail
        for child in xml:
            inner_desc.append(copy.deepcopy(child))
        ET.indent(combined_root)
        combined_bytes = ET.tostring(combined_root, encoding='UTF-8', xml_declaration=True)
        combined_bytes = _fix_description_ns(combined_bytes)
        combined_file = f"Outputs/modified_{os.path.basename(process_file)}_combined_{int(time.time())}.xml"
        with open(combined_file, 'wb') as f:
            f.write(combined_bytes)
        print(f"  Combined tree written to: {combined_file}")

    print("\n=== ORIGINAL TREE ===")
    print_structure(xml)

    jobs = {}
    for counter, req in enumerate(requirements):
        xml = add_start_end(xml)
        print(f"\n--- Processing R{counter+1}: {req} ---")
        modified_tree, job = traverse(req, tree=xml)
        if job is not None:
            caller_id = job["CallerID"]
            if caller_id not in jobs:
                jobs[caller_id] = []
            jobs[caller_id].append(job)
            print(f"  Generated job: {job}")
        else:
            print("  No transformation needed (job=None)")
        xml = modified_tree
        xml = remove_start_end(xml)

        # Write full testset: deep-copy the whole tree, replace inner description, write
        out_tree = copy.deepcopy(full_tree)
        out_root = out_tree.getroot()
        outer_desc = out_root.find("{%s}description" % NS_PROPS)
        inner_desc = outer_desc.find("{%s}description" % NS)
        # Replace inner description content with current modified tree
        inner_desc.clear()
        inner_desc.tag = "{%s}description" % NS
        for attr_name, attr_val in xml.attrib.items():
            inner_desc.set(attr_name, attr_val)
        inner_desc.text = xml.text
        inner_desc.tail = xml.tail
        for child in xml:
            inner_desc.append(copy.deepcopy(child))
        # Remove start/end from the copy
        remove_start_end(inner_desc)

        out_file = f"Outputs/modified_{os.path.basename(process_file)}_{counter}_{int(time.time())}.xml"
        ET.indent(out_root)
        xml_bytes = ET.tostring(out_root, encoding='UTF-8', xml_declaration=True)
        xml_bytes = _fix_description_ns(xml_bytes)
        with open(out_file, 'wb') as f:
            f.write(xml_bytes)
        print(f"  Written to: {out_file}")

    print("\n=== FINAL MODIFIED TREE ===")
    final = remove_start_end(copy.deepcopy(xml))
    print_structure(final)

    print("\n=== JOBS ===")
    for caller_id, job_list in jobs.items():
        print(f"  CallerID={caller_id}:")
        for j in job_list:
            print(f"    {j}")

def main():
    input_dir = "Inputs"
    xml_files = sorted(f for f in os.listdir(input_dir) if f.endswith(".xml"))
    if not xml_files:
        print(f"No XML files found in {input_dir}/")
        return
    print(f"Found {len(xml_files)} input file(s): {', '.join(xml_files)}")
    for filename in xml_files:
        process_file(os.path.join(input_dir, filename))

if __name__ == "__main__":
    main()
