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
    start = ET.Element("{%s}start_activity" % NS)
    start.text = "Inserted Start Activity"
    end = ET.Element("{%s}end_activity" % NS)
    end.text = "Inserted End Activitiy"
    tree.insert(0, start)
    tree.append(end)
    return tree

def remove_start_end(tree):
    for tag in ["start_activity", "end_activity"]:
        for elem in tree.findall("{%s}%s" % (NS, tag)):
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

def main():
    #process_file = "Inputs/RunningExamplewithTimeouts.xml"
    process_file = "Inputs/RunningExampleSimplified.xml"
    print(f"Loading process from: {process_file}")

    full_tree = ET.parse(process_file)
    full_root = full_tree.getroot()

    # Extract requirements
    req_elem = full_root.find(".//{%s}requirements" % NS_PROPS)
    req_text = req_elem.text
    requirements = parse_requirements(req_text)

    xml = full_root.find(".//{%s}description" % NS)

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

if __name__ == "__main__":
    main()
