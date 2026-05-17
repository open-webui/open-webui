# Caseworker Guide: Using Jawafdehi Tools

## Available Tools

### Case Search and Retrieval

#### search_cases
Search for corruption cases by keywords, tags, or entities.
- Query by case title, description, or involved entities
- Filter by case type (CORRUPTION, PROMISES)
- Results include case slug for detailed lookups

#### get_case
Retrieve complete case details including allegations, evidence, timeline, and audit history.
- Use the case slug from search results
- Optionally fetch detailed source information with `fetch_sources=true`

### Court Data

#### extract_court_data
Download complete judicial case information from Nepal's court system (NGM database).
- Requires `court_identifier` (e.g., `special`, `supreme`, `patanhc`)
- Requires exact `case_number` (e.g., `081-CR-0060`)
- Returns metadata, hearings, and entities (plaintiffs/defendants)

#### query_judicial
Run SQL queries against NGM court database tables.
- Tables: `courts`, `court_cases`, `court_case_hearings`, `court_case_entities`
- Use for advanced searches when specific case numbers are unknown

### Entity Management

#### search_entities
Search Nepal Entity Service (NES) for persons and organizations.
- Filter by entity type (person, organization, location)
- Search by name or tags
- Returns NES IDs for entity profiles

#### get_entity
Retrieve complete entity profile with associated cases.
- Use the Jawafdehi entity ID or NES ID

#### get_nes_entities
Bulk retrieve NES entity profiles by NES ID.
- Returns full profiles with metadata

### Date Conversion

#### convert_date
Convert dates between AD (Gregorian) and BS (Bikram Sambat).
- Mode: `ad_to_bs` or `bs_to_ad`
- Input dates in `YYYY-MM-DD` format
- Always use this tool for accurate conversions — never convert manually

### Document Processing

#### convert_to_markdown
Convert documents (PDF, DOCX, web pages, etc.) to Markdown.
- Supports local files, web URLs, and data URIs
- Use `output_path` to save converted Markdown to a file
- The `likhit` plugin provides Nepal-specific PDF handling

## Common Workflows

### Starting a New Case
1. Obtain CIAA/Special Court case number
2. Use `extract_court_data` to get court progress
3. Research involved entities with `search_entities`
4. Search for related cases with `search_cases`
5. Create case draft with `create_jawafdehi_case`

### Updating an Existing Case
1. Load case with `get_jawafdehi_case`
2. Download updated court data with `extract_court_data`
3. Convert new sources to Markdown with `convert_to_markdown`
4. Update case with `patch_jawafdehi_case` using JSON Patch operations

### Researching an Entity
1. Search with `search_entities` (query by name)
2. Get full profile with `get_nes_entities`
3. Find associated cases with `search_cases`
4. Cross-reference with court records using `query_judicial`

## Tool Tips

- Always convert dates using `convert_date` — manual conversion is unreliable
- The `special` court identifier refers to the Special Court, Kathmandu
- Court identifiers are lowercase: `supreme`, `special`, `patanhc`, etc.
- Case slugs are URL-safe identifiers; use them for all API lookups
- JSON Patch uses RFC 6902 format for `patch_jawafdehi_case`
