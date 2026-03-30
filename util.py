from utils.control_util import get_shared_ancestors, siblings, cancel_first, cancel_last, exists_by_label, get_ancestors, compare_ele, directly_follows_must, directly_follows_can
from utils.data_util import condition_finder, multi_condition_finder, activity_data_checks, data_objects, condition_impacts, extract_dobjects
from utils.resource_util import executed_by_annotated, executed_by_data
from utils.time_util import timeouts_exists, sync_exists, parse_timestamp, wait_until_exists, due_date_exists
from utils.general_util import transform_log, find_subprocess, combine_sub_trees, add_start_end
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim

_SEMANTIC_MODEL = None


def _get_semantic_model():
    global _SEMANTIC_MODEL
    if _SEMANTIC_MODEL is None:
        _SEMANTIC_MODEL = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    return _SEMANTIC_MODEL


def semantic_simil(value, endpoint_keys, endpoint_embeddings=None):
    model = _get_semantic_model()
    value_emb = model.encode(value)
    if endpoint_embeddings is None:
        endpoint_embeddings = model.encode(endpoint_keys)

    best_match = None
    best_score = -1
    for idx, endpoint in enumerate(endpoint_keys):
        endpoint_emb = endpoint_embeddings[idx]
        score = cos_sim(value_emb, endpoint_emb)[0][0].item()
        if score > best_score:
            best_score = score
            best_match = endpoint
    return best_match

def replace_endpoints(job, endpoints):
    if not isinstance(job, dict) or not isinstance(endpoints, dict) or len(endpoints) == 0:
        return job

    model = _get_semantic_model()
    endpoint_keys = list(endpoints.keys())
    endpoint_embeddings = model.encode(endpoint_keys)

    for key, value in list(job.items()):
        if not isinstance(value, str):
            continue

        # Replace endpoint placeholders used in transformer pattern jobs.
        if key.endswith("_Endpoint"):
            if value in endpoints:
                job[key] = endpoints[value]
            else:
                matched_key = semantic_simil(value, endpoint_keys, endpoint_embeddings)
                if matched_key is not None:
                    job[key] = endpoints[matched_key]

    return job