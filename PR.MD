# Pull Request Checklist

### Note to first-time contributors
If required, a Discussion was opened to describe the bug/fix and gather feedback before submitting this PR.

**Before submitting, make sure you've checked the following:**

- [x] **Target branch:** This pull request targets the `dev` branch.
- [x] **Description:** Provided below.
- [x] **Changelog:** Added below (Keep a Changelog format).
- [ ] **Documentation:** N/A (no new environment variables or docs changes required).
- [x] **Dependencies:** No new dependencies.
- [x] **Testing:** Manual tests performed (steps listed below).
- [x] **Agentic AI Code:** Parts were created with AI assistance; I performed additional human review and manual testing.
- [x] **Code review:** Performed a self-review; aligned with existing coding patterns.
- [x] **Title Prefix:** Uses `fix:`.

---

## Description

Fix server-side image generation/edit flow so the LLM reliably knows an image operation happened (even for text-only models), and harden the handler against missing `chat_id` and missing websocket emitter in error paths.

Related issue: [open-webui/open-webui#19702](https://github.com/open-webui/open-webui/issues/19702#issuecomment-3605279895)

---

# Changelog Entry

### Description

Improve `chat_image_generation_handler` robustness and make the final prompt used for image generation/edit visible to the LLM via system context injection.

### Fixed

- Prevent `AttributeError` when `chat_id` is missing (avoid `chat_id.startswith(...)` on `None`).
- Guard websocket event emission (including error paths) when no emitter exists.
- Prevent `"None"` from being sent as an image generation prompt when `prompt` is `None`.
- Inject the final image generation/edit prompt used into system `<context>` so text-only models can acknowledge image operations consistently.

---

### Additional Information

- Scope limited to: `backend/open_webui/utils/middleware.py` (`chat_image_generation_handler`).

### Testing (Manual)

- Enabled **Settings → Tools → Image generation**.
- Requested an image (e.g., “Draw a cat”).
- Verified:
  - Image is generated and shown in the chat UI.
  - Model response acknowledges the image operation and does not contradict it (e.g., no “I can’t generate images” after generation).
- Tested error paths:
  - Triggered an image generation failure and confirmed no crash when `chat_id` is missing (no websocket emitter available).

### Screenshots or Videos

- (Optional) Add screenshots of: generated/edited image + model response acknowledging the operation.

### Contributor License Agreement

By submitting this pull request, I confirm that I have read and fully agree to the [Contributor License Agreement (CLA)](https://github.com/open-webui/open-webui/blob/main/CONTRIBUTOR_LICENSE_AGREEMENT), and I am providing my contributions under its terms.

> [!NOTE]
> Deleting the CLA section will lead to immediate closure of your PR and it will not be merged in.
