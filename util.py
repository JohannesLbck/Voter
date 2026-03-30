from utils.control_util import get_shared_ancestors, siblings, cancel_first, cancel_last, exists_by_label, get_ancestors, compare_ele, directly_follows_must, directly_follows_can
from utils.data_util import condition_finder, multi_condition_finder, activity_data_checks, data_objects, condition_impacts, extract_dobjects
from utils.resource_util import executed_by_annotated, executed_by_data
from utils.time_util import timeouts_exists, sync_exists, parse_timestamp, wait_until_exists, due_date_exists
from utils.general_util import transform_log, find_subprocess, combine_sub_trees, add_start_end
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim


def semantic_simil(value, endpoints):
    model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    value_emb = model.encode(value)
    best_match = None
    best_score = -1
    for endpoint in endpoints:
        endpoint_emb = model.encode(endpoint)
        score = cos_sim(value_emb, endpoint_emb)[0][0].item()
        if score > best_score:
            best_score = score
            best_match = endpoint
    return best_match

def replace_endpoints(job, endpoints):

    for key, value in list(job.items()):
        if not isinstance(value, str):
            continue

        # Replace endpoint placeholders used in transformer pattern jobs.
        if key.endswith("_Endpoint"):
            if value in endpoints:
                job[key] = endpoints[value]
            else:
                job[key] = semantic_simil(value, endpoints)

    return job