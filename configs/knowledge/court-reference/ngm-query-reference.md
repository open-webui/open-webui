# NGM Court Database Query Reference

## Overview

The NGM (Nepal Government Monitoring) database contains structured data for Nepali court cases. Queries are performed using SQL SELECT statements.

## Available Tables

### courts
| Column | Type | Description |
|--------|------|-------------|
| identifier | PK | Court identifier (e.g., `special`, `supreme`, `patanhc`) |
| court_type | VARCHAR | Type of court |
| full_name_nepali | VARCHAR | Court name in Nepali |
| full_name_english | VARCHAR | Court name in English |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Record update time |

### court_cases
| Column | Type | Description |
|--------|------|-------------|
| case_number | PK | Case number (e.g., `081-CR-0060`) |
| court_identifier | PK | Court identifier |
| registration_date_bs | VARCHAR | Registration date in BS |
| registration_date_ad | DATE | Registration date in AD |
| case_type | VARCHAR | Type of case |
| division | VARCHAR | Court division |
| category | VARCHAR | Case category |
| section | VARCHAR | Legal section |
| plaintiff | VARCHAR | Plaintiff name |
| defendant | VARCHAR | Defendant name |
| original_case_number | VARCHAR | Original case number if transferred |
| case_id | VARCHAR | Case ID |
| priority | VARCHAR | Priority level |
| registration_number | VARCHAR | Registration number |
| case_status | VARCHAR | Status (pending, decided, etc.) |
| verdict_date_bs | VARCHAR | Verdict date in BS |
| verdict_date_ad | DATE | Verdict date in AD |
| verdict_judge | VARCHAR | Judge who issued verdict |
| status | VARCHAR | Processing status |
| extra_data | JSON | Additional data |

### court_case_hearings
| Column | Type | Description |
|--------|------|-------------|
| id | PK | Hearing ID |
| case_number | FK | Case number |
| court_identifier | FK | Court identifier |
| hearing_date_bs | VARCHAR | Hearing date in BS |
| hearing_date_ad | DATE | Hearing date in AD |
| bench | VARCHAR | Bench description |
| bench_type | VARCHAR | Type of bench |
| judge_names | VARCHAR | Names of judges |
| lawyer_names | VARCHAR | Names of lawyers |
| serial_no | INT | Serial number |
| case_status | VARCHAR | Case status at hearing |
| decision_type | VARCHAR | Type of decision |
| remarks | TEXT | Remarks |
| extra_data | JSON | Additional data |

### court_case_entities
| Column | Type | Description |
|--------|------|-------------|
| id | PK | Entity ID |
| case_number | FK | Case number |
| court_identifier | FK | Court identifier |
| side | VARCHAR | Party side (plaintiff/defendant) |
| name | VARCHAR | Entity name |
| address | VARCHAR | Entity address |
| nes_id | VARCHAR | Linked NES ID |

## Common Query Patterns

### Find Cases by Court
```sql
SELECT case_number, case_status, registration_date_bs, plaintiff, defendant
FROM court_cases
WHERE court_identifier = 'special'
ORDER BY registration_date_ad DESC
LIMIT 5
```

### Find Hearings for a Case
```sql
SELECT hearing_date_bs, bench, bench_type, judge_names, decision_type, remarks
FROM court_case_hearings
WHERE court_identifier = 'special' AND case_number = '081-CR-0060'
ORDER BY hearing_date_ad ASC
```

### Find Cases by Entity
```sql
SELECT cce.case_number, cce.side, cce.name, cc.case_status
FROM court_case_entities cce
JOIN court_cases cc ON cce.case_number = cc.case_number
  AND cce.court_identifier = cc.court_identifier
WHERE cce.name LIKE '%search_term%'
LIMIT 5
```

### List Verdicts in Date Range
```sql
SELECT case_number, verdict_date_bs, verdict_judge, case_status
FROM court_cases
WHERE court_identifier = 'special'
  AND verdict_date_ad IS NOT NULL
  AND verdict_date_ad BETWEEN '2020-01-01' AND '2025-12-31'
ORDER BY verdict_date_ad DESC
LIMIT 5
```

## Notes

- All queries are read-only (SELECT only)
- Use LIMIT to control result size (default to 5)
- Court identifiers are always lowercase
- Dates come in both BS (VARCHAR) and AD (DATE) formats
- The `extra_data` field is JSON and may contain unstructured metadata
- NULL values indicate missing or unrecorded information
