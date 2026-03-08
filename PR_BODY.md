### Contributor License Agreement

<!--
🚨 DO NOT DELETE THE TEXT BELOW 🚨
-->

By submitting this pull request, I confirm that I have read and fully agree to the [Contributor License Agreement (CLA)](https://github.com/open-webui/open-webui/blob/main/CONTRIBUTOR_LICENSE_AGREEMENT), and I am providing my contributions under its terms.

---

## Summary

Fixes **NameError: name 'has_access' is not defined** in `backend/open_webui/routers/tools.py` when non-admin users access the `/api/v1/tools/` endpoint.

## Problem

Non-admin users receive a 500 error when trying to access the tools endpoint. The error occurs because the `has_access` function from `open_webui.utils.access_control` is being used on line 174 but was never imported.

## Solution

Added the missing import:

```python
from open_webui.utils.access_control import has_permission, filter_allowed_access_grants, has_access
```

## Testing

- Python syntax validation passed
- This fix follows the same pattern already used in the codebase (e.g., line 182 uses `AccessGrants.has_access`)

## Related Issue

Fixes #22393
