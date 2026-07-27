# GeoTeaser visual evidence integration

`fill_geotizer` can use project maps and sections through the separately
installed `GeoMAS Geological Vision` Open WebUI tool.

## Preconditions

- The Geological Vision tool is installed with ID `geology_vision` or
  `geomas_geological_vision`, or its source contains
  `analyze_geological_materials`.
- The tool implements `output_format=evidence_json` and the private runtime
  adapter `_prepare_geotizer_visual_evidence`.
- Its `OCR_SERVICE_URL` and `OPEN_WEBUI_BASE_URL` valves are configured.
- The GeoTeaser GIS backend can resolve the requested object/project.

## User-facing call

The built-in tool accepts direct attachments and an optional exact collection
reference:

```text
fill_geotizer(
  object_name,
  project_id?,
  model_run_id?,
  vision_collection_url?
)
```

Direct attachments are passed to Geological Vision once per GeoTeaser run.
The validated analysis is cached inside the call, then mapped only against the
fields of the current bounded batch.

## Guardrails

- Visual proposals can be `calculated` or `analogue`, never `direct`.
- A proposal needs the source SHA-256, page, bbox/source region and exact
  bounded `field_key`.
- An unverified collection produces no field proposals.
- A spatial derivation additionally needs a matched project and either a
  georeferenced source or documented control-point alignment.
- A direct owner fact cannot be replaced by visual evidence.
- Conflicting equal-priority visual proposals are ignored.
- GIS calculated evidence is applied after visual evidence and therefore wins
  at the same origin tier.

The final decision remains `requires_expert_review`; this integration does not
produce conclusions about reserves, economic value or drilling.

## Offline verification

```powershell
$env:PYTHONPATH='backend'
python -m pytest backend/tests/test_geotizer_orchestration.py backend/tests/test_geotizer_vision.py -q
python -m ruff check backend/open_webui/tools/geotizer.py backend/open_webui/utils/geotizer_vision.py backend/tests/test_geotizer_vision.py
```
