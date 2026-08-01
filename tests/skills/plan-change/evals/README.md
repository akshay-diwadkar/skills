# Plan-change machine-pipeline benchmark

`tools/benchmark_sealing.py` measures equivalent tiny, standard, and high-risk
fixtures through the removed v5 prepare/validate/finalize phases and v6 sealing
with one in-process timing boundary. It excludes agent exploration, drafting,
model calls, judge scoring, tool-call accounting, and token accounting.

The v6 results are sealing-only microbenchmarks. This repository contains no
live provider/model comparison or end-to-end agent parity claim.
