---
name: jawafdehi-caseworker
description: AI assistant for Jawafdehi caseworkers to analyze corruption cases, prepare case documentation, and publish to the Jawafdehi platform
---

# Jawafdehi Caseworker Skill

CIAA/Special court case number is of format (3 digit year-case type-case number) (e.g. 081-CR-0123).

Please obtain the case number before creating a local casework folder. The case number can come from the user or be derived from Jawafdehi case details. Prompt the user only if it is not available from the Jawafdehi case details.

1. Local casework folder should be casework/<CIAA-case-number>. You MUST retrieve the case number to create the casework folder.
2. The goal is to prepare and publish a case in Jawafdehi.org. It will be something like https://jawafdehi.org/case/<case-identifier> (e.g. https://jawafdehi.org/case/209).
3. If the user provides a Jawafdehi case identifier or case URL first, use the `get_jawafdehi_case` MCP tool to load the case details and derive the CIAA/Special Court case number from `court_cases` when possible. Do not call the Jawafdehi portal API directly with `curl` for this metadata lookup.

Jawafdehi case details may include `court_cases` entries such as `special:081-CR-0060`. Treat the part before `:` as the NGM `court_identifier` and the part after `:` as the court case number. The `special` court case will be the primary case number we're looking for. You only need to ask the user for the court case number if the Jawafdehi case is unavailable or the `court_cases` does not have a special court case.

A Jawafdehi case can be in state DRAFT, IN_REVIEW, PUBLISHED, and CLOSED. While working on a case, work in either DRAFT or IN_REVIEW state.

When a case is IN_REVIEW, it is viewable in the Jawafdehi website as an unlisted URL, e.g. https://jawafdehi.org/case/209. DRAFT cases can be worked upon, but aren't visible in the website.

Jawafdehi cases should be in Nepali language whenever possible.


## Steps
1. Ask for whichever identifier is missing and required for the requested task. If the user provides a case number, ask for the Jawafdehi case identifier or case URL when needed. If the user provides a Jawafdehi case identifier or case URL, do not also ask for the court identifier unless Jawafdehi does not provide it.
2. When a user provides a Jawafdehi case identifier or case URL, load the case using the `get_jawafdehi_case` MCP tool. We will get the full sources from jawafdehi case.
3. We report some information about the case to the user.
4. We derive the NGM court identifier and court case number from the Jawafdehi case's `court_cases` field whenever possible. For example, `special:081-CR-0060` means `court_identifier=special` and `case_number=081-CR-0060`.
5. We use the `ngm_extract_case_data` tool to download the latest progress on the court case in <case folder>/review/case-progress-<court case no>.md using the derived `court_identifier` and `case_number`.
6. We then prompt the user what they would like to do.

Valid options are:
1. Improving the case.
2. Download the sources locally.
3. If and only if the jawafdehi case does not exist, we should check with user if they would like to create a new case, in which we should use the create_jawafdehi_case MCP tool.

### Improving the case
1. Improving the case requires it to be in `DRAFT` or `IN_REVIEW` status.
2. We use the `get_jawafdehi_case` to get current state and `patch_jawafdehi_case` to update using JSON patch.
3. Note that the `description` field supports HTML using TinyMCE.

#### Source Description Policy
When working with evidence sources, apply these description requirements based on evidence category:
- **Primary evidence** (CIAA charge sheets, court documents, official reports): Description is REQUIRED. Include document type and date (e.g., "CIAA Charge Sheet — Case 081-CR-0080", "Special Court Verdict — Dated Falgun 13, 2082").
- **Informative, news, and legal sources**: The source title/URL itself is often sufficient. If adding description, keep it minimal (publication name and date are enough), unless it provides important context.

### Downloading the sources locally.
We should download sources to casework folder when needed. Sources should be downloaded to casework folder/sources/raw, and their markdowns to casework folder/sources/markdown. We use `convert_to_markdown` tool to extract Markdown.

If there are newspaper sources or external links, we should also download them. Then we will use `convert_to_markdown` to convert them into markdown.

### Review handoff

This skill does not perform final case reviews. If the user asks to review a case, explain that `/jawafdehi-case-reviewer` is the dedicated review skill.

Before handing off to `/jawafdehi-case-reviewer`, make sure the local casework folder is ready:

1. The local folder must be `casework/<CIAA-case-number>/`.
2. The `sources/raw/` files must be downloaded locally.
3. The `sources/markdown/` files must be generated from the source files.
4. If the user wants review next, tell them the reviewer skill expects those local source materials to already exist.

## Default Output Format

Use this structure unless the user asks for something else:

```markdown
# केसवर्क सारांश

- CIAA केस नम्बर: <case number>
- Jawafdehi मुद्दा: <case URL or case identifier>
- हालको अवस्था: <DRAFT | IN_REVIEW | PUBLISHED | CLOSED | case_not_found>
- स्थानीय फोल्डर: `casework/<CIAA-case-number>/`
- गरिएको काम: <sources checked | case loaded | draft improved | sources downloaded | case created>

## मुख्य विवरण
- केसको छोटो परिचय
- हालको कानुनी वा प्रक्रियागत अवस्था
- उपलब्ध स्रोतहरूको स्थिति

## अर्को काम
- case improvement आवश्यक छ भने के अपडेट गर्ने
- sources डाउनलोड/convert गर्न बाँकी छ भने के गर्ने
- review चाहिएको छ भने `/jawafdehi-case-reviewer` प्रयोग गर्ने

## नोट्स
- TinyMCE `description` field HTML मा हुन्छ
- evidence/source descriptions policy लागू गरिएको छ
```

### NOTES

1. DO NOT CALL `submit_nes_change` MCP tool because that's not what we need for Jawafdehi cases. Modifies entities related with a Jawafdehi case means we update the case itself, patch the alleged entities list.

1. Whenever downloading case sources/evidences and other information from the web (e.g. newspapers), try using `curl` (or equivalent) first to preserve data integrity. `fetch` prints to stdout, polluting valuable context space, and may also tamper integrity.

1. If the user asks for review work, redirect to `/jawafdehi-case-reviewer` instead of creating review findings in this skill.
