"""RAG feature layer, split by cost so the boundary is structural.

    artifacts.py   -- reads finished assignment-3 result files. Zero LLM calls.
    retrieval.py   -- indexing, retrieval, chunk browsing, hit-rate. Zero LLM calls.
    generation.py  -- grounded answers and the four judges. Costs calls.

Two thirds of the feature is therefore testable with no API key and no network,
and a call cannot accidentally leak into a route documented as free.

Every module here imports from tax-copilot/src/, which is a namespace package
whose modules import each other flatly (`from build_index import ...`). That
only resolves with src/ on sys.path -- done once, here.
"""

import os
import sys

SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
