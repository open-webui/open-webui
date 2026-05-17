# Caseworker Guide: Case Classification

## Case Types on Jawafdehi

### CORRUPTION
Corruption cases involving abuse of public office, bribery, illicit enrichment, and related offenses.

**Sub-categories:**
- **Bribery**: Direct payment or benefit to influence official action
- **Abuse of Authority**: Using official position for personal gain or to cause government loss
- **Illicit Enrichment**: Assets disproportionate to known income sources
- **Procurement Fraud**: Manipulation of public procurement processes
- **Revenue Leakage**: Causing loss of government revenue
- **Public Property**: Misuse or misappropriation of public land or property
- **Nepotism/Favoritism**: Appointing unqualified relatives or associates

### PROMISES
Cases tracking public commitments, election promises, and government pledges.

**Sub-categories:**
- **Election Manifesto**: Promises made during election campaigns
- **Government Pledge**: Official government announcements and commitments
- **Infrastructure Project**: Tracked public infrastructure projects
- **Policy Announcement**: Policy commitments and implementation tracking

## Key Classification Principles

### Case Type Determination
- If the case involves alleged criminal corruption → CORRUPTION
- If the case tracks political/administrative promises → PROMISES
- A case cannot be both types simultaneously

### Court Case Association
- Each Jawafdehi case can reference multiple `court_cases`
- The primary court case is typically the Special Court case
- Format: `court_identifier:case_number` (e.g., `special:081-CR-0060`)

### Entity Classification
- **Alleged**: Persons or organizations accused in the case
- **Related**: Persons or organizations connected to but not directly accused
- **Victim**: Persons or organizations harmed by the alleged corruption
- **Witness**: Persons providing testimony or evidence

## Tagging Guidelines

### Required Tags
- Court identifier (e.g., `special`, `supreme`, `patanhc`)
- Case status context (e.g., `charge-sheet-filed`, `sub-judice`, `verdict-issued`)

### Recommended Tags
- Sector (e.g., `education`, `health`, `infrastructure`, `land`)
- Ministry/Department involved
- Geographic location
- Estimated amount involved (if known)

### Example Tag Set
For a case about land grabbing in Bhaktapur:
```
special, land, local-government, bhaktapur, public-property, charge-sheet-filed
```

## Status Tracking

### DRAFT
- Initial creation, case details being compiled
- Not visible on public website
- Can be freely edited

### IN_REVIEW
- Case content is complete, pending editorial review
- Visible via unlisted URL on jawafdehi.org
- Ready for review by editorial team

### PUBLISHED
- Case is publicly available on jawafdehi.org
- Searchable and indexable
- Changes require versioning consideration

### CLOSED
- Case is archived
- No longer active or maintained
- Still accessible via direct URL
