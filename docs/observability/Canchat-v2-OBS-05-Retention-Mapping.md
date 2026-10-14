# OBS-05: SSC records mapping and retention clocks

Status: **Provisional answers by the project team (2026-10-14). Not approved by SSC.** | Depends on: none | Unblocks: OBS-60, OBS-61, OBS-91 | Ref: [Logging Architecture v2 §11](Canchat-v2-Logging%20Architecture-v2.md#11-retention-and-disposition-treasury-board), Gate 3

This is the decision request for Gate 3. So that work can continue, the project team answered every question from public Government of Canada sources (§1.1) and the code (§2). Each answer is marked **provisional**. SSC Information Management, Security and ATIP still need to confirm or change each answer in the **SSC confirmed** column and sign §8. Until then, OBS-60 may build with these values, but OBS-05 stays open.

## 1. What SSC is asked to decide

1. Confirm or change each retention row (§3), with its basis and disposal authority.
2. Confirm the definition of each clock trigger (§4).
3. Decide on the gaps found in the current code (§2), because some of them make the current system differ from the Terms of Use.
4. Say whether full content audit is needed (§5). This decides whether OBS-91 is built.
5. Name the owner of the records-management follow-up (§6, OBS-61).

### 1.1 Sources checked for the provisional answers (2026-10-14)

| Source | What it says | Used for |
|---|---|---|
| [TBS Event Logging Guidance](https://www.canada.ca/en/government/system/digital-government/online-security-privacy/cyber-security-guidance-policy/event-logging-guidance.html) §1.5.2 (modified 2025-12-08) | Quotes the GC cloud security control profile (AU-11) for PBMM systems: events and logs kept **at least 3 months online and at least 6 months in storage**; logs linked to a security incident kept **at least 2 years**. LAC recommends **2 years after last administrative use** for information with business value in IT or security processes. Retention for other event data is left to organizational policy. | R1, R3, R4, incident clock |
| Same guidance, §1.3 (citing SPIN 2017-01 §6.3.1) | Audit log retention follows LAC's generic valuation tool for IT and departmental requirements. | Disposal authority |
| [Privacy Regulations](https://laws-lois.justice.gc.ca/eng/regulations/SOR-83-508/page-1.html) s. 4(1) (current to 2026-09-21) | Personal information used for an administrative purpose is kept **at least 2 years after it was last used** for that purpose, unless the individual consents to disposal. If an access request was received, it is kept until the individual has been able to exercise all their rights. | R4, last administrative use, access requests |
| [TBS standard personal information banks](https://www.canada.ca/en/treasury-board-secretariat/services/access-information-privacy/access-information/info-source/standard-personal-information-banks.html) (modified 2026-07-15) | *Electronic Network Monitoring Logs* (PSU 905) and *Security Incidents and Privacy Breaches* (PSU 939) both use **RDA 98/001**. Each institution's ATIP coordinator sets the retention period. *Personnel Security Screening* (PSU 917) shows the usual pattern: 2 years after the last administrative action. | Disposal authority for R1, R4 |
| [Guide on the use of generative AI](https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai/guide-use-generative-ai.html) (modified 2026-09-24) | Using generative AI for daily tasks (drafting, brainstorming, research, translation, coding) is "more likely to yield transitory information". Under the Directive on Service and Digital, employees document activities and decisions of business value. | R5, §5 |
| [Canada.ca privacy notice](https://www.canada.ca/en/transparency/privacy.html) (modified 2025-09-05) | GC web analytics are kept for **at most 37 months**, and IP addresses are not stored in a form that identifies a person. | Precedent for R2 and R9 |
| CANChat [Terms of Use §9](../../src/routes/terms/+page.svelte) | Chat data is kept 30 days from the last activity in each chat. Usage metrics and aggregate reports may be kept longer under SSC's schedules. | R5, R11 |

**Not checked:** SSC's institution-specific retention and disposition authorities, and the retention schedule of SSC's SIEM. They are not public. The TBS policy site (`tbs-sct.canada.ca/pol`) refused automated access, so the Directive on Privacy Practices and the Directive on Service and Digital were not re-read for this answer. SSC IM should check the provisional answers against these documents.

## 2. Current state (checked in the code on 2026-10-14)

These findings affect the answers. Items 1 to 4 are differences between the code and [Terms of Use §9](../../src/routes/terms/+page.svelte) ("30 days from the last activity in each chat").

| # | Finding | Evidence | Effect |
|---|---|---|---|
| 1 | Automatic chat deletion is **off by default**. `CHAT_LIFETIME_ENABLED` defaults to `False`, and no Compose or Kubernetes manifest in the repo sets it. It is a `PersistentConfig`, so an admin may have turned it on in a deployed database. | [config.py](../../backend/open_webui/config.py#L1320-L1330) | The 30-day promise holds only where an admin enabled it. The value in each production database must be checked. |
| 2 | **Pinned chats are never deleted** by default (`CHAT_CLEANUP_PRESERVE_PINNED=True`). Archived chats are deleted (`CHAT_CLEANUP_PRESERVE_ARCHIVED=False`). | [config.py](../../backend/open_webui/config.py#L1332-L1342) | A user can keep chat content forever by pinning it. |
| 3 | The clock is `chat.updated_at`. It moves on new or edited messages, but also on rename, pin/unpin, archive/unarchive and folder moves. | [chats.py](../../backend/open_webui/models/chats.py#L160-L172), [cleanup query](../../backend/open_webui/models/chats.py#L1005-L1012) | "Last activity" today includes actions that do not add content. |
| 4 | The job runs once a day (`23 1 * * *`, America/Toronto) and deletes chats with `updated_at` older than 30 × 24 h. | [config.py](../../backend/open_webui/config.py#L1355-L1362) | A chat is actually deleted between 30 and about 31 days after its last activity, later if the job misfires or fails. |
| 5 | `message_metrics` (user ID, user email domain, chat ID, model, token counts, MCP tool) and `export_logs` (user ID, email domain, export details) have **no deletion path**. Deleting a user removes their chats but not these rows. | [message_metrics.py](../../backend/open_webui/models/message_metrics.py#L14-L29), [export_logs.py](../../backend/open_webui/models/export_logs.py#L14-L25), [users.py](../../backend/open_webui/models/users.py#L322-L339) | Personal information kept indefinitely. These tables are not in the §11 table. Under OBS-01 option (a), `message_metrics` also becomes the write point for the chat audit event. |
| 6 | The audit outbox keeps a row for 7 days after its SIEM receipt. A row without a receipt is never purged automatically. | [OBS-04 §8](Canchat-v2-OBS-04-Audit-Event-Schema.md#8-siemarchive-delivery) | Not in the §11 table. Needs confirmation as a transient copy, not a record. |
| 7 | No retention for database or object-storage backups is defined in the repo. | No backup config in `kubernetes/` | Deleted chats survive in backups for as long as backups are kept. |
| 8 | Chat deletion has no hold checks. | [Architecture §11 Implementation](Canchat-v2-Logging%20Architecture-v2.md#11-retention-and-disposition-treasury-board) | Out of scope here; goes to OBS-61. Listed so reviewers know holds are not enforced yet. |

## 3. Retention mapping

"§11 value" is what the architecture doc proposed. **Provisional answer** is the project team's answer from the sources in §1.1. It is not a claim that every number is a Treasury Board mandate. Where no GC minimum applies, the answer keeps data only as long as a stated need requires. Rows marked **new** are not in §11 today and come from §2.

| # | Store | Holds | §11 value | **Provisional answer** | Clock (§4) | Reason | Disposal authority (provisional) | SSC confirmed |
|---|---|---|---|---|---|---|---|---|
| R1 | Loki `app` | Operational and access logs, approved metadata only | 6 months | **Confirm:** 6 months (184 days), all queryable | Event time | Meets the AU-11 PBMM floor (3 months online, 6 months total). Keeping all of it queryable avoids a cold-storage tier. The logs hold user IDs and IP addresses, so they are not kept past the floor. | RDA 98/001 (as for PSU 905), to be confirmed by SSC IM | |
| R2 | Loki `frontend` | Faro errors, web vitals, page views, sessions, usage events | 6 months | **Change:** 90 days | Event time | No GC minimum applies: browser telemetry is untrusted and is not a security log ([§10](Canchat-v2-Logging%20Architecture-v2.md#10-frontend-observability-and-analytics-grafana-faro)). 90 days covers the trailing-30-day aggregation windows with margin and leaves time to investigate errors after a release. Long-term trends are kept in R9 as aggregates with no user IDs. Keeping raw records for less time reduces the amount of user-level data that can be linked back to a person. | Institution-specific, to be confirmed by SSC IM | |
| R3 | Loki `audit` | Searchable copy of metadata audit events | 2 years | **Confirm:** 2 years (731 days) | Event time | Matches the incident minimum and the LAC recommendation, so the Audit org can search the same period. It is not the authoritative record. | Same as R4 | |
| R4 | SSC SIEM / evidence archive | Authoritative audit records and evidence | ≥ 2 years, plus clocks | **Confirm:** at least 2 years from event time. A hold (R10) extends it for incidents (2 years from when the record is linked to the incident), for administrative use (2 years after last use) and for access requests. | Event time; hold clocks | AU-11 incident minimum, LAC recommendation, Privacy Regulations s. 4(1) | RDA 98/001 (as for PSU 939) or the SSC SIEM schedule, to be confirmed by SSC Security | |
| R5 | Chat DB (chats, their files and vector collections) | Chat content | 30 days | **Confirm:** 30 days after last activity, for **all** chats, including pinned chats (§4). Files and vectors are deleted with the chat. | Last chat activity | Terms §9. The generative AI guide treats daily-task use as likely transitory. A user who produces information of business value saves it in their department's repository. | Transitory information under LAC guidance; SSC IM to confirm that CANChat chats are transitory | |
| R6 | Restricted content repository | Full provider requests and responses | Same as R5 | **Not built** (§5) | n/a | Content audit is not needed (§5). | n/a | |
| R7 | Tempo | Sanitized diagnostic spans | 30 days | **Confirm:** 30 days | Event time | Diagnostic only. Spans can hold user IDs, so they are kept for a short time. Traces linked to an incident are exported to the case before they expire. | Institution-specific | |
| R8 | Operational Prometheus | Operational metrics, no user IDs | 13 months | **Confirm:** 13 months (397 days) | Sample time | Year-over-year comparison. Contains no personal information. | Institution-specific | |
| R9 | Analytics Prometheus | Approved aggregate series only | 13 months | **Confirm:** 13 months (397 days) | Sample time | Year-over-year comparison. Aggregates only. Canada.ca keeps web analytics for up to 37 months, so a longer period could be justified later if product owners need it. | Institution-specific | |
| R10 | Holds | Preserved records from any store | Until release | **Confirm** the approach. Designed in OBS-61. | Hold release | Privacy Regulations s. 4(1)(b); AU-11 incident minimum | Per case | |
| R11 **new** | `message_metrics` table | Per-message usage metadata with user ID and email domain | none | **13 months**, then delete the row. Optional before deletion: keep monthly totals by domain and model, with no user ID, on the R9 schedule. Rows are not deleted when the user is deleted; they expire on the same schedule. | Event time (`created_at`) | Usage metrics: Terms §9 allows keeping them longer than chats, and 13 months gives the same year-over-year view as R8. The table holds user IDs, so it is not kept indefinitely. Under OBS-01 (a) the authoritative chat audit record is the SIEM copy (R4), so this table does not need 2 years. | Institution-specific | |
| R12 **new** | `export_logs` table | Who exported metrics and when | none | **2 years** | Event time | Records an export of usage data that contains user IDs, which is a security-relevant administrative action. Matches R3. The `metrics.export` audit event in R4 is the authoritative copy. | Same as R4 | |
| R13 **new** | Audit outbox | Encrypted copy of an audit event until delivered | none | **Confirm:** 7 days after the SIEM receipt. A row is never purged without a receipt. | SIEM receipt time | A temporary delivery copy, not a record ([OBS-04 §8](Canchat-v2-OBS-04-Audit-Event-Schema.md#8-siemarchive-delivery)). | Transitory | |
| R14 **new** | Database and object-storage backups | Copies of R5, R11, R12 and Loki/Tempo/Prometheus objects | none | **Chat DB backups: at most 30 days**, rolling, with no long-term archive. After any restore, run the chat cleanup before users get access again. **Object storage:** old (noncurrent) versions expire after at most 7 days. | Backup time | Deleted chat content is then gone from backups no more than about 60 days after the chat's last activity. OBS-06 checks that 30 days is enough for its recovery point objective (RPO). | Follows the source store | |

**How OBS-60 will turn calendar periods into durations.** The backends only accept fixed durations. To make sure a record is never deleted before its minimum period, OBS-60 rounds up to the longest possible calendar length:

| Period | Duration used | Example Loki `retention_period` |
|---|---|---|
| 30 days | 30 days | `720h` |
| 6 months | 184 days | `4416h` |
| 13 months | 397 days | `9528h` |
| 2 years | 731 days | `17544h` |

Actual deletion then happens later, by the compactor's delete delay and run interval. If SSC sets a **maximum** retention as well as a minimum, reviewers should say so in the row, because this rounding plus the deletion delay can go a few days past the calendar period.

## 4. Clock triggers

| Clock | Definition and options | Used by | **Provisional answer** | SSC confirmed |
|---|---|---|---|---|
| **Event time** | The UTC timestamp on the record: the log record's `timestamp`, the audit event's `time` (commit time for state changes), the span start, the metric sample time, `created_at` on R11/R12. Not the ingest time. | R1–R4, R7–R9, R11, R12 | **Confirm.** | |
| **Last chat activity** | Choose one: **(A)** keep today's behaviour: any change that updates `chat.updated_at` (messages, edits, rename, pin/unpin, archive/unarchive, folder move); **(B)** only actions that add or change content (new message, regenerate, edit). Option B needs a new column and a migration. | R5, R6 | **(A).** Each of these is an action by the user, which matches "last activity" in Terms §9. It needs no migration. | |
| **Pinned and archived chats** | Choose one: **(A)** pinned chats are exempt (today's default; Terms need an update); **(B)** pinned chats follow the same 30 days (set `CHAT_CLEANUP_PRESERVE_PINNED=false`). Archived chats keep following the 30 days. | R5 | **(B).** Terms §9 covers "all chat data". Exempting pinned chats would keep content indefinitely without a stated basis. Users must be told before the change (CHANGELOG and an in-app notice). | |
| **Chat deletion enabled** | `CHAT_LIFETIME_ENABLED=true` is required in every production deployment, set in the manifests and checked at startup, so it can't be left off by accident. | R5 | **Confirm.** | |
| **Last administrative use** | The last time a record was used to make a decision that directly affects the person (Privacy Regulations s. 4(1)). Nothing in CANChat tracks this today. Proposed: the records-management design (OBS-61) defines which actions count (for example account suspension, access decision, investigation finding) and how they are recorded. Until then, R4 uses only its fixed minimum. | R4 | **Confirm.** R11 and R12 are not used for decisions about individuals, so this clock does not apply to them. If one of their records is used that way, it is preserved under a hold. | |
| **Access request** | When an ATIP request covers a record, it is kept until the requester has been able to use all their rights, even after its normal period ends (Privacy Regulations s. 4(1)(b)). Handled as a hold (R10). | All, including R5 chats | **Confirm.** Because chats are deleted 30 days after last activity, ATIP has to place the hold within that window. | |
| **Incident** | Records linked to a security incident are kept ≥ 2 years. Proposed trigger: the date the incident record links them, handled as a hold (R10), not a fixed TTL from event time. | R1–R5, R7 | **Confirm.** | |

## 5. Content audit (decides OBS-91)

The baseline in [§8](Canchat-v2-Logging%20Architecture-v2.md#8-content-audit-off-by-default) is: no content capture; authorized reviewers use an audited export of the stored chats (OBS-90).

| Option | What it means |
|---|---|
| **Not needed** | OBS-90 export is enough. OBS-91 is closed as "won't do". The stored chat may differ from the exact payload sent to the provider (system prompt, RAG context, web results are added before the call). |
| **Needed** | OBS-91 builds a restricted repository with the R6 retention, access control and receipts. SSC states which record is required (stored chat or exact provider payload) and who may access it. |

**Provisional answer: not needed.** Reasons:

- The generative AI guide treats daily-task use as likely transitory, and Terms §9 promises deletion after 30 days. A second full copy of chat content would contradict that promise.
- Every message already produces a metadata audit event (who, when, which model and features, outcome) that is kept for at least 2 years (R4). A reviewer who needs the content can export the stored chat (OBS-90) during its 30-day life, or place a hold.
- A content repository would be a new store of personal information. It would need its own privacy impact assessment and access controls.

| SSC confirmed | |
|---|---|

## 6. Records-management follow-up (OBS-61)

Only roles can be proposed here. Names have to come from SSC.

| Item | Provisional answer | SSC confirmed |
|---|---|---|
| Owner of `docs/observability/Canchat-v2-Records-Management.md` (hold model, hold-aware deletion, evidence archive, disposition evidence) | CANChat product owner (SSC), supported by the tech lead. Name to be provided. | |
| Team that owns hold creation and release | SSC ATIP office for access requests; SSC Security for incidents. CANChat operators carry out holds but do not approve them. | |
| Jira epic key | To be created when OBS-61 starts | |

## 7. Follow-up

**Can start now on the provisional answers:**

- OBS-60 builds with R1–R3 and R7–R9 as provisional values, with `frontend` at **90 days**, and keeps them configurable.
- New ticket: set `CHAT_LIFETIME_ENABLED=true` and `CHAT_CLEANUP_PRESERVE_PINNED=false` in the Compose and Kubernetes manifests, and log a startup error in production when chat deletion is off. This is user-visible: add a CHANGELOG entry and tell users before release that pinned chats will be deleted.
- New ticket: scheduled deletion for `message_metrics` (13 months) and `export_logs` (2 years), reusing the chat-cleanup scheduler and lock.
- OBS-06: chat DB backups kept at most 30 days, old object versions expire after at most 7 days, and chat cleanup runs after every restore.

**After SSC confirms:**

- Copy the confirmed values from §3 and §4 into the [§11 table](Canchat-v2-Logging%20Architecture-v2.md#11-retention-and-disposition-treasury-board), including the new rows.
- If §5 stays "not needed", close OBS-91.
- If SSC changes an answer, update the matching ticket above before it merges.

## 8. Sign-off

| Role | Name | Decision | Date |
|---|---|---|---|
| SSC Information Management | | | |
| SSC Security | | | |
| SSC ATIP | | | |
| Tech lead | | | |
