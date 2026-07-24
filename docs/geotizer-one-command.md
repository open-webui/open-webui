# GeoTeaser one-command orchestration

`MainAgent_yulong` exposes one built-in operation, `fill_geotizer`, when its
model metadata contains the existing `mainagent_tool_yulong` tool ID.
Specialist models do not receive this operation and therefore cannot start
nested GeoTeaser runs.

## User contract

The complete workflow starts from one ordinary chat message:

```text
Заполни Геотизер для Верхне-Колпинской площади.
В конце сделай Excel-таблицу и пришли ссылку для скачивания.
```

The parent model calls `fill_geotizer(object_name=...)` once. The function
returns a short completeness summary and an authenticated XLSX download link
under the Open WebUI origin.

An interrupted run can be continued by the same function with its `run_id`.

## Responsibility split

- `gis_service` owns GIS project resolution, DataCube handoff, the canonical
  108-row/351-field state, owner validation, final audit and XLSX rendering.
- Open WebUI owns specialist sub-chat execution and the orchestration loop.
- `MainAgent_tool_yulong` remains the existing KB/WEB/GIS delegation runtime.
- The existing `Sub Agent` runs the final `SkilledAgent` owner batch without
  external tools.

The Open WebUI controller does not write workbook cells directly.

## Deterministic loop

For each `next_batch` returned by `geotizer_fill`:

1. ignore evidence routes already satisfied by `start.datacube`;
2. run independent `contributor_call` routes concurrently;
3. call the exact owner producer with only the bounded field catalog,
   DataCube handoff and contributor evidence;
4. require one JSON patch for every owner field and no foreign fields;
5. preflight statuses, values, source inventory, source references and
   locators;
6. submit the atomic owner batch to `gis_service`;
7. repair a rejected owner response at most three times;
8. finalize only after `next_batch` becomes empty.

The controller is capped at 12 batches. The current policy has eight.

## Download boundary

The private GIS artifact route is not exposed as an agent tool. Open WebUI
provides an authenticated proxy:

```text
GET /api/v1/geotizer/files/{run_id}/geotizer.xlsx
```

The proxy reuses the configured `mcpgis` connection and never places its bearer
token in the user-visible URL.

## Validation

Focused tests cover:

- contributor-before-owner ordering;
- `start.datacube` route suppression;
- unsupported producer rejection;
- JSON and fenced-JSON extraction;
- exact field partition validation;
- provenance on negative decisions;
- the full start/submit/finalize state sequence;
- bounded repair before the first state mutation.

Run locally:

```powershell
$env:PYTHONPATH = "backend"
python -m pytest backend/tests/test_geotizer_orchestration.py -q
```
