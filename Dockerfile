# Built from the taxes/ repo root (not tax-copilot/) so TaxData/ and
# tax-copilot/ keep the sibling layout that REPO_ROOT path resolution in
# src/build_index.py, src/agent_team.py, and api/rag/artifacts.py already
# assumes when run locally -- see tax-copilot/CLAUDE.md.
FROM python:3.12-slim

WORKDIR /app

COPY tax-copilot/requirements.txt tax-copilot/requirements.txt
# CPU-only torch first -- the default PyPI wheel bundles CUDA and balloons
# the image by several GB, which risks the Space's build timing out.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r tax-copilot/requirements.txt

COPY TaxData/ TaxData/
COPY tax-copilot/api/ tax-copilot/api/
COPY tax-copilot/src/ tax-copilot/src/
COPY tax-copilot/data/ tax-copilot/data/
COPY tax-copilot/assignment3/data/corpus_manifest.json tax-copilot/assignment3/data/corpus_manifest.json
COPY tax-copilot/assignment3/index/ tax-copilot/assignment3/index/

WORKDIR /app/tax-copilot

# Hugging Face Spaces (Docker SDK) routes traffic to this port by default.
EXPOSE 7860
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
