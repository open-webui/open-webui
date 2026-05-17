# Caseworker Guide: Case Analysis Workflow

## Overview

This guide describes the standard workflow for analyzing corruption cases on the Jawafdehi platform. The workflow ensures consistent, thorough, and legally sound case documentation.

## Step 1: Case Identification

When starting work on a case, identify:
- The CIAA or Special Court case number (format: `YYY-CR-NNNN`)
- The Jawafdehi case slug (used in URLs: `jawafdehi.org/case/<slug>`)
- The case status: DRAFT, IN_REVIEW, PUBLISHED, or CLOSED

## Step 2: Load Case Data

### From Jawafdehi Platform
- Use the `get_jawafdehi_case` tool with the case slug to retrieve case details
- This provides allegations, evidence, entities, and court case references

### From NGM Court System
- Derive the `court_identifier` and `case_number` from the Jawafdehi case's `court_cases` field
- Example: `special:081-CR-0060` means `court_identifier=special`, `case_number=081-CR-0060`
- Use `ngm_extract_case_data` to download court progress data

## Step 3: Source Material Collection

### Primary Sources (Required)
- CIAA charge sheets
- Court verdicts and orders
- Official government reports

### Secondary Sources
- News articles (print and online media)
- Investigative reports
- Public complaints and documentation

### Source Storage
- Store raw sources in `casework/<case-number>/sources/raw/`
- Convert documents to Markdown using `convert_to_markdown`
- Store converted files in `casework/<case-number>/sources/markdown/`

## Step 4: Case Documentation

### Required Fields
- Title (concise, descriptive)
- Case type (CORRUPTION or PROMISES)
- Description (Markdown, with detailed allegations and evidence)
- Short description (1-2 line summary)
- Alleged entities (persons and organizations involved)
- Evidence sources (with proper descriptions and URLs)

### Description Structure
Use this Markdown structure:
```markdown
## मुद्दाको पृष्ठभूमि
[Background of the case in Nepali]

## आरोप र विवरण
[Allegations in detail, in Nepali]

## प्रमाण र स्रोतहरू
[Evidence list with source references]

## कानुनी अवस्था
[Current legal status and court progress]

## स्रोतहरू
[Full list of sources with links]
```

## Step 5: Source Description Policy

### Primary Evidence (CIAA documents, court orders, official reports)
- Description is REQUIRED
- Include document type and date
- Example: "CIAA Charge Sheet — Case 081-CR-0080"
- Example: "Special Court Verdict — Dated Falgun 13, 2082"

### News and Media Sources
- Title and URL are often sufficient
- If adding description, keep it minimal (publication name and date)

## Step 6: Case Publishing

- Cases start in DRAFT status
- Move to IN_REVIEW when ready for editorial review
- PUBLISHED cases are publicly visible on jawafdehi.org
- CLOSED cases are archived and no longer active

## Important Principles

1. **Presumption of Innocence**: Always state that accused persons are presumed innocent until proven guilty
2. **Factual Accuracy**: Only present verified facts with proper source citations
3. **Nepali Language**: Use Nepali language whenever possible for case content
4. **No Legal Advice**: Present facts and records, not legal opinions
5. **Source Attribution**: Always cite sources for every claim
