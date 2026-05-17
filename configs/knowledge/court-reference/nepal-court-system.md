# Nepal Court System Reference

## Court Hierarchy

### Supreme Court (सर्वोच्च अदालत)
- **Court Identifier**: `supreme`
- **Location**: Kathmandu
- **Jurisdiction**: Nationwide, final appellate authority
- **Bench Types**: Single, Division (2 judges), Full (3+ judges), Constitutional
- **Role**: Final appeal for Special Court decisions; constitutional interpretation
- **Website**: supremecourt.gov.np

### High Courts (उच्च अदालत)
- **Jurisdiction**: Regional, appellate from District Courts
- **Number of High Courts**: 7 (and 10 Benches)

High Court identifiers for NGM queries:

| Court | Identifier | Location |
|-------|-----------|----------|
| High Court Biratnagar | `biratnagarhc` | Biratnagar |
| High Court Ilam Bench | `illamhc` | Ilam |
| High Court Dhankuta Bench | `dhankutahc` | Dhankuta |
| High Court Okhaldhunga Bench | `okhaldhungahc` | Okhaldhunga |
| High Court Janakpur | `janakpurhc` | Janakpur |
| High Court Rajbiraj Bench | `rajbirajhc` | Rajbiraj |
| High Court Birganj | `birganjhc` | Birganj |
| High Court Patan | `patanhc` | Lalitpur |
| High Court Hetauda | `hetaudahc` | Hetauda |
| High Court Pokhara | `pokharahc` | Pokhara |
| High Court Baglung | `baglunghc` | Baglung |
| High Court Tulsipur | `tulsipurhc` | Tulsipur |
| High Court Butwal | `butwalhc` | Butwal |
| High Court Nepalgunj | `nepalgunjhc` | Nepalgunj |
| High Court Surkhet | `surkhethc` | Surkhet |
| High Court Jumla Bench | `jumlahc` | Jumla |
| High Court Dipayal | `dipayalhc` | Dipayal |
| High Court Mahendranagar | `mahendranagarhc` | Mahendranagar |

### District Courts (जिल्ला अदालत)
- **Jurisdiction**: District-level, original jurisdiction for most cases
- **Number**: 77 (one per district)
- **Role**: First instance for civil and most criminal cases

District Court identifiers follow the pattern `<district>dc`:
- Examples: `achhamdc`, `argakhanchidc`, `bhaktapurdc`, `kathmandudc`, `lalitpurdc`, `kaskidc`

### Special Court (विशेष अदालत)
- **Court Identifier**: `special`
- **Location**: Kathmandu
- **Jurisdiction**: Exclusive jurisdiction over corruption cases
- **Composition**: Chairperson + 2 Members
- **Appeal**: To Supreme Court

## Case Number Formats

### CIAA/Special Court
Format: `YYY-CR-NNNN`
- YYY: Nepali year (e.g., 081 for 2081 BS)
- CR: Case type code
- NNNN: Sequential case number
- Example: `081-CR-0060`

### Supreme Court
Format: Varies by case type
- Writ numbers: `NN-NN-NNNN`
- Appeal numbers: Varies

### District/High Courts
Format: Varies by court and case type

## Key Court Procedures

### Filing Process
1. CIAA investigates and prepares charge sheet
2. Charge sheet filed at Special Court
3. Accused appears and responds
4. Evidence examination
5. Final arguments
6. Judgment

### Hearings
- Cases may have multiple hearing dates
- Bench composition varies by case
- Hearing decisions include: orders, interim orders, final judgments
- Hearing types: regular, mention, stay order, etc.

### Verdicts
- Conviction: Guilty with specified sentence (imprisonment + fine)
- Acquittal: Not guilty, charges dismissed
- Partial: Some charges proven, some dismissed
- Verdict date recorded in both BS and AD

## NGM Database Queries

The NGM (Nepal Government Monitoring) database provides structured court data.

### Key Tables
- `courts`: Court master data (identifier, name, type)
- `court_cases`: Case records (number, court, dates, status, verdict)
- `court_case_hearings`: Hearing records (date, bench, judges, lawyers, decision)
- `court_case_entities`: Parties involved (plaintiff, defendant, side)
