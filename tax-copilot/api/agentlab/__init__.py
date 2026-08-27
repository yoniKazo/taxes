"""שכבת מטלה 4 (Agent Lab), נפרדת מ-`api/agents/` הקיים (קונפיגורציות LLM-writer
של מטלה 2 -- listAgents/RunForm ב-TestLabPage). אין קשר בין השניים; ראו
plans/assignment4-plan.md, "התנגשות שם אמיתית".

כמו api/rag/__init__.py: מודולים כאן מייבאים מ-tax-copilot/src/ בייבוא עירום
(`from tools import ...`), שדורש את src/ על sys.path -- נעשה פעם אחת, כאן.
"""

import os
import sys

SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
