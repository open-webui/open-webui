# Observability filter (discussion #5455 follow-up)

This folder holds a Python **filter function** compatible with Open WebUI’s Functions system.

It avoids custom frontend patches: timing lines use existing **`status`** events (`event_emitter`), and usage is mirrored with **`chat:completion`** where available.

## Install

1. Open **Admin → Functions → Create**.
2. Set **Type** to **Filter**.
3. Paste the contents of `observability_metrics.py` into the editor and save.
4. Enable globally or attach filters to models that should report metrics.

## Notes

- Throughput figures use streamed **`completion_tokens`** when the provider sends them; otherwise they fall back on a coarse character heuristic.
- “First text” latency is measured on the Open WebUI server while processing the stream chunks (network + model latency), **not** the browser paint time.
