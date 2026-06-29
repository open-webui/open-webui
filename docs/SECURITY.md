# Security Policy

Our goal is to protect Open WebUI's users and their data, and to handle security reports with a clear, consistent, and publicly documented process.
We want to operate a transparent security process, in which accepted vulnerabilities are published openly as advisories so anyone can see what was found, how it was resolved and most importantly, which version contains a patch for it.
Our stance: a visible advisory history is evidence of active scrutiny and a disclosure process that works, not a measure of how fragile the software is.

## Supported Versions

| Version (Branch) | Supported          |
| ---------------- | ------------------ |
| main             | :white_check_mark: |
| dev              | :x:                |
| others           | :x:                |

**If an issue is already fixed, or already being fixed in the open, at the time you file, the report will not be accepted** — it did not contribute to discovering or remediating the issue, and we will not publish an advisory for it.

A fix counts as already-existing regardless of which branch it lives on — including `dev` — and regardless of whether it was silently resolved in an earlier version. Branch support status (see table above) governs where a vulnerability must be _reproducible_, not whether a fix already exists: a bug live in a supported branch but already fixed in `dev` is still an already-fixed issue under this rule.

Two specific patterns this covers, both of which we reject:

- Filing a report for a bug found in an **older version** that was already resolved by the time of the current supported version.
- **Monitoring our public commits or pull requests** and filing a report for an issue they already address or fix. We have observed automated monitoring of our public commits and PRs that produced reports against fixes others had already authored; this rule exists to reject that pattern.

We need not decide whether you discovered the issue independently — we cannot, and it makes no difference. On the provable facts your report duplicates work that is already public and already fixed or being fixed; you filed strictly last, and there is no way to distinguish independent discovery from scraping. Credit for the issue belongs to whoever found or fixed it — who in turn forfeits their own claim to it by disclosing publicly instead of reporting it to us confidentially first. A publicly-disclosed fix therefore earns no advisory, and no credit for anyone.

> [!TIP]
> **Before reporting, check whether your finding still reproduces on the `dev` branch** (and any other active development branch).
> We develop in the open, and a fix may already be committed there ahead of a release. Confirming this first saves you the effort of writing up a report we'd have to close as already-fixed.

## Good-faith reports that aren't vulnerabilities

If you've found something that you know is **not strictly a vulnerability under our policy** — but where public disclosure would still be irresponsible (e.g. an urgent dependency bump needed because of a downstream vuln, or similar) — you may **still report it privately** via [GitHub Security Advisories](https://github.com/open-webui/open-webui/security/advisories/new). We will handle it responsibly.

In line with the CVE rules, we will **not** publish an advisory or mint a CVE for these — but we **will** act on them (e.g. ship the bump) and keep the report confidential until handled.
<ins>**Where a fix lands as a result of your report and you'd like credit, we'll try to acknowledge you (e.g. as a co-author on the change).**</ins>

Thank you for your report!

## What a Valid Report Gets You

If your report describes a real vulnerability under this policy, here's what you can expect from us:

- **Credit on the advisory.** You're named as the reporter on the published advisory. Where multiple reporters each demonstrated a distinct vector, every one of you is credited (see [Report Handling](#report-handling)).
- **Coordinated disclosure.** We won't publish out from under you while you're still working the issue with us. Status moves visibly on the advisory itself — including the CVE request — and GitHub notifies you of those updates, so you can follow it through to publication.
- **A real fix, handled responsibly.** For findings with broad or severe real-world impact, we may hold publication for up to ~2 weeks after the patched release so administrators can update before details are public.

We're a small volunteer team, so what we _can't_ offer is a bounty or a guaranteed turnaround. What you get is a serious fix, honest credit, and a process that treats your work as the contribution it is.

## Alignment with the CVE Program

The **CVE Program rules** (and CNA operational rules) are the **baseline** for all CVE handling here, and this policy operates within them. Under those rules, the determination of whether a report constitutes a security vulnerability in Open WebUI is the vendor's to make; this policy documents the criteria by which we exercise that determination. Where the rules are silent, they still apply; where this policy specifies how we apply them to Open WebUI, it does so as the vendor's published disposition criteria, not as a replacement for or exception to the program rules.

## Reporting Channel

We accept vulnerability reports **only** through [GitHub Security Advisories](https://github.com/open-webui/open-webui/security/advisories/new). Reports submitted through **any** other platform — including but not limited to third-party vulnerability reporting platforms, vulnerability brokers, social media, email, Discord, or Reddit — will not be processed.

This is not a procedural preference. As a volunteer- and community-driven project, our security process is built around the same transparency and direct community interaction as the rest of our work, and GitHub Security Advisories is where that process lives. We do not and cannot monitor or engage with external reporting platforms, and reports arriving through them will be closed without review.

A report filed on another platform has no standing here: it confers no priority, establishes no filing date, and creates no obligation for us to triage, publish, or otherwise consider it. Only the GitHub Security Advisory record exists for the purposes of this policy — including determining who filed first.

## Foreign CNAs and Vendor Disposition

[Based on multiple precedents of foreign CNAs minting CVEs without communicating the report to us prior to publication and/or minting CVEs that do not withstand any scrutiny](https://docs.openwebui.com/security/vendor-dispositions/), this rule was established.
When a report is filed via GitHub Security Advisories and the maintainers close it as out-of-scope per this policy, that closure is the **vendor's disposition** of the issue. A CVE Numbering Authority (CNA) that mints a CVE for such an issue without reflecting that vendor disposition in the resulting record is acting against vendor disposition.

We respond to such records by:

1. Filing a **REJECT** request with the CVE Program (with **DISPUTED** as fallback);
2. Cataloging the record publicly, naming the issuing CNA;
3. Refusing to provide vendor statements, version mappings, fix references, or any other coordination that would lend authority to the record;
4. Escalating repeated patterns from a single CNA to the CVE Program Root.

**Channel compliance does not entitle a CNA to override vendor disposition.** Reporters who escalate a closed-as-out-of-scope/not-a-vulnerability GHSA report to a third-party CNA after vendor disposition has been issued are likewise considered to have acted against vendor disposition, and **may be barred from future GHSA submissions.**

## Rules for Reporting a Vulnerability

We appreciate the community's interest in identifying potential vulnerabilities!
If you want to report something that does not fulfill our rules and guidelines laid out here, you can still report it and we will handle it, [see our good faith reporting section for more information](#good-faith-reports-that-arent-vulnerabilities).

However, effective immediately, we will **not** accept low-effort vulnerability reports. Ensure that **submissions are constructive, actionable, reproducible, well documented and adhere to the following guidelines**:

**Security boundaries:** Throughout this policy, "the security boundaries" means the five we recognize: Confidentiality, Integrity, Availability, Authenticity, and Non-repudiation. We interpret these broadly — equivalent concepts from other security frameworks fall within them. A valid vulnerability must cross at least one of them against a party other than the reporter.

1. **Report MUST be a vulnerability:** A security vulnerability is an exploitable weakness where the system behaves in an unintended way, allowing attackers to bypass security controls, gain unauthorized access, execute arbitrary code, or escalate privileges. Configuration options, missing features, and expected protocol behavior are not vulnerabilities. A vulnerability must cross at least one of the security boundaries (defined above).

2. **No Vague Reports**: Submissions such as "I found a vulnerability" without any details will be treated as spam and will not be accepted.

3. **In-Depth Understanding**: Reports must reflect a clear understanding of the codebase, how Open WebUI is used and provide specific details about the vulnerability, including the affected components and potential impacts.

4. **Proof of Concept (PoC) is Mandatory**: Each submission must include a well-documented proof of concept (PoC) that demonstrates the vulnerability. If confidentiality is a concern, reporters are encouraged to create a private fork of the repository and share access with the maintainers. Reports lacking valid evidence may be disregarded.

> [!NOTE]
> A PoC (Proof of Concept) is a **demonstration of exploitation of a vulnerability**. Your PoC must show:
>
> 1. Exactly which security boundary was crossed
> 2. How this vulnerability is triggered/abused (inputs, endpoints, UI actions, etc.)
> 3. What actions the attacker can now perform
> 4. Exact steps and commands to reproduce (copy/paste runnable where possible), expected result vs. actual result

5. **Remediation is required**:

Along with the PoC, you must provide **either**:

1. **a remediation plan** (i.e. "actionable steps" that a maintainer can apply), **or**
2. **a patch/PR**

Your remediation guidance can include, for example:

- The **likely root cause** (what's wrong and where)
- The **location(s)** to change (file/module/function names if known)
- The **recommended fix approach** (validation/sanitization rules, auth checks, safe defaults, etc.)
- Any **security tradeoffs** or potential regressions to watch for

6. **Default Configuration Testing**: Vulnerability reports must be tested and reproducible using Open WebUI's out-of-the-box default configuration. Claims of vulnerabilities that only manifest with explicitly weakened security settings may be discarded, unless they are covered by the following exception:

> [!NOTE]  
> **Note**: If you believe you have found a security issue that
>
> 1. affects default configurations, **or**
> 2. represents a genuine bypass of intended security controls, **or**
> 3. works only with non-default configurations, **but the configuration in question is likely to be used by production deployments**, **then we absolutely want to hear about it.** This policy is intended to filter configuration issues and deployment problems, not to discourage legitimate security research.

7. **Threat Model Understanding Required**: Reports must demonstrate understanding of Open WebUI's self-hosted, single-tenant, authenticated, extensible, role-based access control architecture. Comparing Open WebUI to services with fundamentally different security models without acknowledging the architectural differences may result in report rejection.

8. **CVSS Scoring Accuracy:** You do not have to include a CVSS score in your report. If you leave the CVSS section empty, we will fill it out for you prior to publishing. If you include a CVSS score with your report, it must accurately reflect the vulnerability according to CVSS methodology. In case of inaccurate CVSS, we will adjust the CVSS score of your report. If you cite other CVEs to support your report, ensure they are **genuinely comparable** in vulnerability type, threat model, and attack vector.

9. **Admin Actions Are Out of Scope:** Vulnerabilities that require an administrator to actively perform unsafe actions are **not considered valid vulnerabilities**. **Admins have full system control and are expected to understand the security implications of their actions and configurations**. This includes but is not limited to: adding malicious external servers (models, tools, webhooks, functions), pasting untrusted code into Functions/Tools, or intentionally weakening security settings. **Reports requiring admin negligence or social engineering of admins may be rejected.**

> [!NOTE]
> Similar to rule "Default Configuration Testing": If you believe you have found a vulnerability that affects admins and is NOT caused by admin negligence or intentionally malicious actions,
> **then we absolutely want to hear about it.** This policy is intended to filter social engineering attacks on admins, malicious plugins being deployed by admins and similar malicious actions, not to discourage legitimate security research.

10. **Tools & Functions Code Execution Is Intended Behavior:** Open WebUI's Tools and Functions feature is **designed** to execute user-provided Python code on the server. This is core, intentional functionality — not a vulnerability (see also 'Threat Model Understanding'). Function creation is **restricted to administrators only**. Tool creation is controlled by the `workspace.tools` permission, which is **disabled by default** for non-admin users and should only be granted to fully trusted users who are equivalent to system administrators in terms of trust. <ins>**Granting a user the ability to create Tools is equivalent to giving them shell access to the server**</ins>. If an administrator grants this permission to untrusted users, this constitutes intentional misconfiguration and is additionally covered by 'Admin Actions Are Out of Scope'. More generally, **reports describing ANY attack chain that involves Tools or Functions — including but not limited to code execution, file access, network requests, or environment variable access — will be closed as not a vulnerability / intended behavior.** This applies to both direct code execution and frontmatter-based package installation (`pip install`).

> [!IMPORTANT]
> **For administrators:** Treat the `workspace.tools` permission as **root-equivalent access**. Only grant it to users you would trust with direct access to your server. If you enable this permission for untrusted users, you are accepting the risk of arbitrary code execution on your host. For more details, see our [Plugin Security documentation](https://docs.openwebui.com/features/extensibility/plugin/).

11. **Legacy Code Paths Are Out of Scope:** Open WebUI maintains some code paths that are explicitly marked as legacy in the official documentation, which is authoritative as to what is legacy. Legacy paths remain available — sometimes still the default — purely for backwards-compatibility reasons, not because they are the supported or maintained surface. The supported replacement is the migration target, and security and functional work happens on the replacement, not the legacy path. Reports describing a security boundary issue on a legacy code path that does not also reproduce on the supported replacement are usually out of scope under this rule.

> [!NOTE]
> If you find a security issue that:
>
> 1. exists on a legacy code path **and also on the supported modern replacement**, OR
> 2. exists on a legacy code path **and the legacy path is the only documented way to achieve a given function** (no migration target exists yet)
>
> we still want to hear about it. This rule is intended to filter reports that target deprecated paths with a documented modern alternative, not to discourage finding real bugs in paths users are still on.

12. **AI report transparency:** Due to a spike in vulnerability reports **you must disclose if AI was used in any capacity** - whether for writing the report, generating the PoC, or identifying the vulnerability. If AI helped you in any way shape or form in the creation of the report, PoC or finding the vulnerability, you must disclose it. Note that AI-aided vulnerability reports **will not be rejected by us by default** but reports not declaring AI use, yet appear AI-aided will undergo severely more scrutiny.

13. **Self-Affecting Issues Are Not Vulnerabilities:** A vulnerability requires crossing a security boundary that affects **a party other than the reporter**. Crossing one of the security boundaries only against the reporter's own data, account, session, or environment is **not a vulnerability** - it is a bug, and belongs in the [Issue Tracker](https://github.com/open-webui/open-webui/issues), not in a security report.

> [!NOTE]
> This rule is about **who is harmed**, not about severity. A user modifying or deleting their own data, impairing their own session, observing their own configuration, or disabling security controls on their own account is out of scope under this rule, regardless of impact.
>
> If the same action also affects another user, the operator, the host system, or shared resources, identify that second party clearly in the PoC, and we want to hear about it.

**Non-compliant submissions may be closed, and repeat or extreme violators may be banned from submitting reports.** Our goal is to foster a constructive reporting environment where quality submissions promote better security for all users.
If you want to report something that does not fulfill our rules and guidelines laid out here, you can still report it and we will handle it, [see our good faith reporting section for more information](#good-faith-reports-that-arent-vulnerabilities).

## Expected Timeframe

We aim to triage new reports, ship fixes, and publish advisories promptly. However, due to the very high volume of incoming vulnerability reports, issues, discussions, pull requests, and general project maintenance — lately compounded by a high number of (AI-generated) reports — our capacity to respond is limited. Open WebUI is a community-driven project maintained by a small team, and security reports are handled alongside all other project responsibilities.

**Please expect several weeks** for your report to be triaged, investigated, fixed, and published. While we aim to respond to every report as quickly as possible, it is normal to experience periods of silence lasting up to several weeks. **This does not mean your report has been ignored** — it means we have not yet had the capacity to address it. Feel free to post a follow-up comment on your advisory for visibility if you feel your report may have been lost; we'll get to you as soon as our capacity allows. The entire process can realistically take multiple weeks from initial submission to final publication. We appreciate your patience and understanding.

**We do not accept reporter-imposed publishing deadlines.** We coordinate disclosure on our own schedule, and we will triage, fix, and publish as fast as we reasonably can. Externally-imposed hard timelines do not speed this up — they do the opposite: they pull our limited time away from actually fixing issues and toward managing a clock, **at the expense of every other report (even ones that might be more serious)** in the queue and the project as a whole. A deadline attached to your report will not change when or how fast it is handled.

For findings we judge to have **broad or severe real-world impact** — regardless of CVSS score — we may hold off on publishing for a couple of days, max ~2 weeks after the patched version is released, to give administrators time to update their instances.

## Report Handling

When multiple independent reporters describe the same vulnerability class **but** each demonstrates a **distinct and separate exploitation vector** — for example, the same missing authorization check reached through different endpoints — we will consolidate them into the earliest filing **and credit every reporter who demonstrated a distinct path on the consolidated advisory**. Only one CVE will be issued for the consolidated advisory.

The other case: If you report a valid vulnerability that somebody else reported before you (identical vulnerability, identical exploitation vector), we will close your report as a duplicate. The earliest filing is the one we will handle going forward, and we will not publish multiple advisories for the same vulnerability.

### Why duplicate reports don't receive credit

We credit only the earliest filer of a given vulnerability:

1. **The first report did the work.** By the time a later report arrives, triage and fix are already in motion. Later reports don't change the outcome or timeline; crediting them would misrepresent what moved the fix.
2. **Credit-for-duplicates incentivizes flooding.** If similar-but-later filings earn credit, the rational play is to skim open advisories and file variations. We already see this pressure — the first-filer rule is what limits it.
3. **Co-discovery is different from duplication.** Multiple reporters **are credited** on one advisory **when each contributes a _distinct_ finding** — different vector, different affected component, different sub-path the earlier filing does not cover. That is the consolidation rule above. Filing a duplicate of an existing report is not co-discovery.

## Responsible Disclosure

Vulnerability reports submitted through GitHub Security Advisories are **private and confidential**. Generally: Public disclosure of **ANY** details is **STRICTLY PROHIBITED** until an advisory for the vulnerability has been **fully published** — not merely when a CVE ID has been assigned, but when an advisory itself is publicly visible.

This prohibition applies to **all channels**, including but not limited to comments on pull requests, issues, or discussions (on GitHub or elsewhere), social media (Discord, Reddit or any other platform), blogs, forums, or any other website or service.

This confidential, responsible disclosure process exists to give us time to fix bugs, publish fixes and alert users once a fix is ready. The entire premise of responsible disclosure is to **protect users from vulnerabilities**. Therefore, premature disclosure undermines the security of all Open WebUI users and **violates the trust** inherent in the responsible disclosure process. **Reporters who prematurely publicly disclose vulnerability details before official publication <ins>WILL BE PERMANENTLY BANNED from future reporting.</ins>**

## For Non-Vulnerability Related Questions or Security Concerns:

You can use the following channels:

- **Documentation issues/improvement ideas:** Open an issue on our [Documentation Repository](https://github.com/open-webui/docs)
- **Feature requests:** Create a discussion in [GitHub Discussions - Ideas](https://github.com/open-webui/open-webui/discussions/) to discuss with the community if this feature request is wanted by multiple people
- **Configuration help:** Ask the community for help and guidance on our [Discord Server](https://discord.gg/5rJgQTnV4s) or on [Reddit](https://www.reddit.com/r/OpenWebUI/)
- **General issues:** Use our [Issue Tracker](https://github.com/open-webui/open-webui/issues)
- **Bugs:** Report bugs to our [Issue Tracker](https://github.com/open-webui/open-webui/issues)
- **Best-practice guidance:** Help expand the [Documentation](https://github.com/open-webui/docs).

We regularly audit our internal processes and system architecture for vulnerabilities using a combination of automated and manual testing techniques. We are also planning to implement SAST and SCA scans in our project soon.

For any other immediate concerns and questions, please create an issue in our [issue tracker](https://github.com/open-webui/open-webui/issues) or contact our team on [Discord](https://discord.gg/5rJgQTnV4s).

---

_Last updated on **2026-06-13**._
