# Benchmark workspace image for runanchor live measurement.
# Corpus seed tests run under pytest; the base slim image ships without it.
# Rebuild: contree build --tag runanchor-bench eval/runanchor-bench-image
FROM python:3.12-slim
RUN pip install --no-cache-dir pytest==8.*
WORKDIR /work
