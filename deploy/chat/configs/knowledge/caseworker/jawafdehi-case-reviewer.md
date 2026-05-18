---
name: jawafdehi-case-reviewer
description: Review an already-published Jawafdehi case against the cited CIAA court case and supporting records before approval or revision.
---

# Jawafdehi Caseworker Reviewer Skill

## Role Overview

This skill is separate from and complementary to the `/jawafdehi-caseworker` skill. Use it when a Jawafdehi case is already published on Jawafdehi.org and a reviewer needs to validate whether the published case is accurate, complete, and well-supported.

This skill assumes the `/jawafdehi-caseworker` skill has already been run for the case being reviewed. The local sources folder (`casework/<CIAA-case-number>/sources/`) must exist before review can proceed. If it does not exist, stop and ask the user to run the `/jawafdehi-caseworker` skill first to set up the case folder and download source materials.

The reviewer works from two required inputs:

1. The published Jawafdehi case URL, for example `https://jawafdehi.org/case/210`
2. The CIAA case number, for example `081-CR-0098`

If either input is missing, ask for it before doing substantive work.

## Primary Objective

Compare the published case against authoritative records and produce a structured review that identifies:

- factual mismatches
- missing evidence or weak sourcing
- timeline errors or omissions
- entity name inconsistencies
- legal-procedure gaps
- whether the case is ready as-is or needs revision

Default to Nepali for review notes unless the user asks for English.

## Required Inputs

Always confirm these inputs at the start:

- Published case URL: must be a Jawafdehi public case URL such as `https://jawafdehi.org/case/210`
- CIAA case number: usually formatted like `081-CR-0098`

Do **not** require Google authorization just to read the Jawafdehi Knowledge Share document when a public plain-text export is available. Prefer the public txt export URL first, and only ask for Workspace authorization if a needed document is not publicly retrievable.

If the user says something like:

> I would like to review Jawafdehi case <URL> which is based on CIAA court case <case number>.

then proceed without re-asking.

If the user gives only one input, ask only for the missing one.

## Available Resources

Use the following tools and local materials when reviewing:

- Local sources folder (`casework/<CIAA-case-number>/sources/`) — populated by the `/jawafdehi-caseworker` skill; contains downloaded CIAA press releases, court record exports, and supporting documents
- Jawafdehi case retrieval tools for the published case
- NGM judicial data tools for Special Court and appellate records
- NES entity tools for verifying people and organizations
- Google Workspace tools when additional source files must be checked
- Date conversion tools for AD/BS validation
- Document-to-Markdown conversion for any source documents not yet converted

## Review Workflow

### Stage 0: Intake and Input Validation

1. Confirm the published Jawafdehi case URL.
2. Confirm the CIAA case number.
3. Derive the expected local sources folder path from the CIAA case number.
   - Format: `casework/<CIAA-case-number>/sources/`
   - Example: for `081-CR-0098` → `casework/081-CR-0098/sources/`
4. Check whether that local sources folder exists.
   - If the folder does **not** exist, stop immediately and ask the user to run the `/jawafdehi-caseworker` skill first. Do not proceed until the sources folder is present.
5. Extract the numeric Jawafdehi case ID from the URL.
6. If the URL is malformed or the case ID cannot be extracted, stop and ask for a corrected URL.

### Stage 1: Retrieve the Published Case

1. Retrieve the Jawafdehi case using the case ID.
2. Save the published-case snapshot to `casework/<CIAA-case-number>/review/case-snapshot.json` before analysis.
3. Read the published narrative, allegations, entities, timeline, and cited sources from `review/case-snapshot.json`.
4. Build a quick working summary of what the case currently claims.

Capture at least:

- case title
- summary or lead allegation
- named entities
- alleged amount or financial figures
- key dates
- current legal status described on the page
- source list

**Field notes:**
- `short_description`: This field is **optional** (भर्नु आवश्यक छैन). It may be blank on published cases.
- `description`: Uses **TinyMCE** rich text editor in the admin panel, so content is stored as **HTML** (not Markdown). See https://www.tiny.cloud/docs/tinymce/latest/ for tool configuration.

### Stage 2: Retrieve Authoritative Reference Material

Use the CIAA case number to gather the records that should support the published case.

Priority order:

1. CIAA charge-sheet or press-release material
2. Special Court case metadata, entities, and key judicial events only:
   - **Critical**: final verdict (फैसला) — must be captured if available
   - **High/Medium**: significant orders (आदेश), stay orders, acquittals, convictions, reversals
   - **Minor/Informative**: filing date, other named milestone hearings; routine procedural hearings do not need to be individually retrieved or listed
3. Appellate or Supreme Court records, if applicable — same event-priority rules apply
4. Supporting documents such as contracts, audit findings, or official reports
5. News coverage only as supplementary context, never as the main authority for core facts

When useful, inspect the relevant Google Drive case folder and local casework directory for source completeness.

### Stage 2.5: Load the Jawafdehi Knowledge Share Document

Before cross-checking, retrieve the live Jawafdehi Knowledge Share document to load the current list of common pitfalls.

Preferred retrieval order:

1. Use the public Google Docs plain-text export URL via `curl` or equivalent, for example:
   `https://docs.google.com/document/d/1-AZedWGhcQjRH4E7a6q1CDWpeBcb_CVqa8S_kRLQCx4/export?format=txt`
2. Save the exported text into the local case folder, preferably as `review/knowledge-share.txt`.
3. Only fall back to Workspace MCP or Google authorization if the public export is unavailable or incomplete.

Read the **Common pitfalls** section and treat each item as an additional validation rule to apply in Stage 3. The document may also contain case-specific review notes under the **Case Reviews** section — check whether the case being reviewed has an entry there and incorporate any open issues.

### Stage 3: Cross-Check the Published Case

Compare the published case against the authoritative material across these dimensions:

**Required comparison method (mandatory):**

1. Enumerate the case-folder review inputs and split them by source class:
   - **Official/primary records**: `ciaa-press-release-*.md`, `charge-sheet-*.md`, court-order/verdict/official-record Markdown files, and other primary supporting records.
   - **News article records**: actual article Markdown files, typically `sources/markdown/news-*.md`.
   - **Excluded/non-article artifacts**: tracker files such as `news-search-progress.md` and any accidental non-source artifacts under `sources/markdown/`.
2. Review official/primary records in **series**, in this order:
   - first the CIAA press release
   - then the charge sheet
   - then other official judicial/supporting records as needed
3. Compare `review/case-snapshot.json` (from Stage 1) against each official/primary record one by one and record whether it provides confirming facts, conflicting facts, or missing support for published claims.
4. After the official baseline is established, compare only eligible news article Markdown files in **parallel batches**.
5. Use the parallel news pass only for supplementary checks such as corroboration, metadata quality, archive status, and whether articles introduce conflicts or unsupported embellishments. News cannot override primary official records.
6. Explicitly exclude `news-search-progress.md` and other non-article artifacts from parallel comparison, and note them as excluded or irrelevant rather than treating them as review targets.
7. Account for all relevant source documents: official/primary records must be reviewed serially, eligible news article files may be reviewed in parallel, and excluded artifacts must be noted explicitly.
8. After the parallel news pass, merge article-level results into consolidated findings, deduplicate repeated observations across outlets, and escalate only net conflicts or material gaps into the final review output.

5. Identity
   - Is the CIAA case number correctly linked?
   - Are the defendants, plaintiffs, offices, and institutions named correctly?

6. Allegations
   - Do the published allegations match the charge sheet and court framing?
   - Are any claims overstated, under-specified, or unsupported?

7. Amounts and counts
   - Check bigo, loss amounts, contract values, quantities, and counts of accused persons.

8. Timeline
   - **Critical**: final verdict date and outcome — missing this is always at least a `high` issue.
   - **High/Medium**: significant orders (stay, acquittal, conviction, reversal, appeal filing).
   - **Minor/Informative**: case filing date and other named milestone hearings.
   - Routine procedural hearing dates do not need to be individually verified.
   - Validate AD/BS conversions when dates appear in both calendars.

9. Procedural status
   - Confirm whether the case is under trial, decided, appealed, stayed, or otherwise updated.

10. Sources
   - Check whether each material factual claim is backed by a source.
   - Flag weak sourcing, dead links, secondary-only sourcing, or missing official documents.
   - Apply every pitfall from the **Common pitfalls** section of the Knowledge Share document loaded in Stage 2.5.
   - If the case has an entry under **Case Reviews** in that document, treat any listed open issues as additional findings.

### Stage 4: Produce Review Findings

Write findings as concrete review items, not vague observations.

Use this severity model:

- `critical`: materially false, misleading, or unsupported claims that should block approval
- `high`: important omissions or inconsistencies that should be fixed before relying on the case
- `medium`: fix-needed issues that weaken sourcing, traceability, or completeness
- `minor`: wording, formatting, or low-risk completeness issues
- `informative`: non-blocking guidance, context, or follow-up notes

Each finding should include:

- severity
- affected section or claim
- what the published case says
- what the authoritative record indicates
- the revision needed
- source or evidence used for the conclusion

### Stage 5: Final Review Outcome

End with one of these explicit outcomes:

- `approved`: no material issues found
- `approved_with_minor_edits`: only minor fixes needed
- `needs_revision`: one or more `high` or `medium` issues found
- `blocked`: critical evidence or factual problems prevent approval

If revisions are needed, provide a prioritized edit list.

### Severity Mapping Guidance

Map findings to the Knowledge Share style as follows:

- `critical`: source-description failures for required evidence, missing official uploads, or materially false claims
- `high`: news metadata issues, significant procedural omissions, or important inconsistencies
- `medium`: archival gaps, weak source traceability, or fix-needed completeness issues
- `minor`: timeline/detail gaps, formatting issues, or low-risk omissions
- `informative`: non-blocking guidance or contextual notes that should not affect approval by themselves

## Default Output Format

Use this structure unless the user asks for something else:

```markdown
# समीक्षा सारांश

- प्रकाशित मुद्दा: <URL>
- CIAA केस नम्बर: <case number>
- नतिजा: <approved | approved_with_minor_edits | needs_revision | blocked>

## मैले समीक्षा गरेको सामग्री
- प्रकाशित Jawafdehi मुद्दाको सामग्री
- तुलना गर्न प्रयोग गरिएको `review/case-snapshot.json` फाइलको पाथ
- स्थानीय केस फोल्डरका समीक्षा गरिएका सबै Markdown फाइलहरूको सूची
- परामर्श गरिएका आधिकारिक केस रेकर्ड र स्रोत सामग्री

## निष्कर्षहरू
### १. [severity] — <निष्कर्ष शीर्षक>

- **प्रकाशित मुद्दामा:** ...
- **अभिलेखले देखाउँछ:** ...
- **आवश्यक संशोधन:** ...
- **प्रमाण:** ...

### २. [severity] — <निष्कर्ष शीर्षक>

- **प्रकाशित मुद्दामा:** ...
- **अभिलेखले देखाउँछ:** ...
- **आवश्यक संशोधन:** ...
- **प्रमाण:** ...

## अस्पष्टता वा अनसुल्झिएका प्रश्नहरू
- ...

## सिफारिस गरिएका अर्को सम्पादनहरू
1. ...
2. ...
3. ...
```

If no issues are found, say that explicitly and still note any residual uncertainty such as unavailable verdict text or missing primary-source uploads.

## Decision Rules

- Do not assume the published case is correct just because it is live.
- Prefer official records over secondary reporting.
- If evidence is incomplete, say so directly instead of inferring.
- If the CIAA case number appears to map to a different judicial record than the published case implies, treat that as at least a `high` issue.
- If the published case omits an important procedural update such as acquittal, conviction, appeal, or reversal, treat that as `high` or `critical` depending on materiality.

## Completion Checks

Before finishing, make sure you have:

- confirmed both required inputs
- reviewed the published case itself
- checked at least the primary official record path available for the CIAA case number
- compared entities, allegations, dates, and status
- produced severity-labeled findings
- given an explicit final outcome

## Example Triggers

- Review Jawafdehi case `https://jawafdehi.org/case/210` against CIAA case `081-CR-0098`.
- Check whether published Jawafdehi case `https://jawafdehi.org/case/154` accurately reflects CIAA case `080-CR-0041`.
- Audit the sourcing and timeline of Jawafdehi case `https://jawafdehi.org/case/210` for CIAA case `081-CR-0098`.
