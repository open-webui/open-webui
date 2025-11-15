# Security Policy

Our primary goal is to ensure the protection and confidentiality of sensitive data stored by users on open-webui.

## Supported Versions

| Version (Branch) | Supported          |
| ---------------- | ------------------ |
| main             | :white_check_mark: |
| dev              | :x:                |
| others           | :x:                |

## Zero Tolerance for External Platforms

Based on a precedent of an unacceptable degree of spamming and unsolicited communications from third-party platforms, we forcefully reaffirm our stance. **We refuse to engage with, join, or monitor any platforms outside of GitHub for vulnerability reporting.** Our reasons are not just procedural but are deep-seated in the ethos of our project, which champions transparency and direct community interaction inherent in the open-source culture. Any attempts to divert our processes to external platforms will be met with outright rejection. This policy is non-negotiable and understands no exceptions.

Any reports or solicitations arriving from sources other than our designated GitHub repository will be dismissed without consideration. We’ve seen how external engagements can dilute and compromise the integrity of community-driven projects, and we’re not here to gamble with the security and privacy of our user community.

## Reporting a Vulnerability

Reports not submitted through our designated GitHub repository will be disregarded, and we will categorically reject invitations to collaborate on external platforms. Our aggressive stance on this matter underscores our commitment to a secure, transparent, and open community where all operations are visible and contributors are accountable.

We appreciate the community's interest in identifying potential vulnerabilities. However, effective immediately, we will **not** accept low-effort vulnerability reports. Ensure that **submissions are constructive, actionable, reproducible, well documented and adhere to the following guidelines**:

1. **Report MUST be a vulnerability:** A security vulnerability is an exploitable weakness where the system behaves in an unintended way, allowing attackers to bypass security controls, gain unauthorized access, execute arbitrary code, or escalate privileges. Configuration options, missing features, and expected protocol behavior are **not vulnerabilities**.

2. **No Vague Reports**: Submissions such as "I found a vulnerability" without any details will be treated as spam and will not be accepted.

3. **In-Depth Understanding Required**: Reports must reflect a clear understanding of the codebase and provide specific details about the vulnerability, including the affected components and potential impacts.

4. **Proof of Concept (PoC) is Mandatory**: Each submission must include a well-documented proof of concept (PoC) that demonstrates the vulnerability. If confidentiality is a concern, reporters are encouraged to create a private fork of the repository and share access with the maintainers. Reports lacking valid evidence may be disregarded.

> [!NOTE]
> A PoC (Proof of Concept) is a **demonstration of exploitation of a vulnerability**. Your PoC must show:
>
> 1. What security boundary was crossed (Confidentiality, Integrity, Availability, Authenticity, Non-repudiation)
> 2. How this vulnerability was abused
> 3. What actions the attacker can now perform
>
> **Examples of valid PoCs:**
>
> - Step-by-step reproduction instructions with exact commands
> - Complete exploit code with detailed execution instructions
> - Screenshots/videos demonstrating the exploit (supplementary to written steps)
>
> **Failure to provide a reproducible PoC may lead to closure of the report**
>
> We will notify you, if we struggle to reproduce the exploit using your PoC to allow you to improve your PoC.
> However, if we repeatedly cannot reproduce the exploit using the PoC, the report may be closed.

5. **Required Patch or Actionable Remediation Plan Submission**: Along with the PoC, reporters must provide a patch or some actionable steps to remediate the identified vulnerability. This helps us evaluate and implement fixes rapidly.

6. **Streamlined Merging Process**: When vulnerability reports meet the above criteria, we can consider provided patches for immediate merging, similar to regular pull requests. Well-structured and thorough submissions will expedite the process of enhancing our security.

7. **Default Configuration Testing**: All vulnerability reports MUST be tested and reproducible using Open WebUI's out-of-the-box default configuration. Claims of vulnerabilities that only manifest with explicitly weakened security settings may be discarded, unless they are covered by the following exception:

> [!NOTE]  
> **Note**: If you believe you have found a security issue that
>
> 1. affects default configurations, **or**
> 2. represents a genuine bypass of intended security controls, **or**
> 3. works only with non-default configurations, **but the configuration in question is likely to be used by production deployments**, **then we absolutely want to hear about it.** This policy is intended to filter configuration issues and deployment problems, not to discourage legitimate security research.

8. **Threat Model Understanding Required**: Reports must demonstrate understanding of Open WebUI's self-hosted, authenticated, role-based access control architecture. Comparing Open WebUI to services with fundamentally different security models without acknowledging the architectural differences may result in report rejection.

9. **CVSS Scoring Accuracy:** If you include a CVSS score with your report, it must accurately reflect the vulnerability according to CVSS methodology. Common errors include 1) rating PR:N (None) when authentication is required, 2) scoring hypothetical attack chains instead of the actual vulnerability, or 3) inflating severity without evidence. **We will adjust inaccurate CVSS scores.** Intentionally inflated scores may result in report rejection.

> [!WARNING]
>
> **Using CVE Precedents:** If you cite other CVEs to support your report, ensure they are **genuinely comparable** in vulnerability type, threat model, and attack vector. Citing CVEs from different product categories, different vulnerability classes or different deployment models will lead us to suspect the use of AI in your report.

10. **Admin Actions Are Out of Scope:** Vulnerabilities that require an administrator to actively perform unsafe actions are **not considered valid vulnerabilities**. Admins have full system control and are expected to understand the security implications of their actions and configurations. This includes but is not limited to: adding malicious external servers (models, tools, webhooks), pasting untrusted code into Functions/Tools, or intentionally weakening security settings. **Reports requiring admin negligence or social engineering of admins may be rejected.**

> [!NOTE]
> Similar to rule "Default Configuration Testing": If you believe you have found a vulnerability that affects admins and is NOT caused by admin negligence or intentionally malicious actions,
> **then we absolutely want to hear about it.** This policy is intended to filter social engineering attacks on admins, malicious plugins being deployed by admins and similar malicious actions, not to discourage legitimate security research.

11. **AI report transparency:** Due to an extreme spike in AI-aided vulnerability reports **YOU MUST DISCLOSE if AI was used in any capacity** - whether for writing the report, generating the PoC, or identifying the vulnerability. If AI helped you in any way shape or form in the creation of the report, PoC or finding the vulnerability, you MUST disclose it.

> [!NOTE]
> AI-aided vulnerability reports **will not be rejected by us by default**. But:
>
> - If we suspect you used AI (but you did not disclose it to us), we will be asking tough follow-up questions to validate your understanding of the reported vulnerability and Open WebUI itself.
> - If we suspect you used AI (but you did not disclose it to us) **and** your report ends up being invalid/not a vulnerability/not reproducible, then you **may be banned** from reporting future vulnerabilities.
>
> This measure was necessary due to the extreme rise in clearly AI written vulnerability reports, where the vast majority of them
>
> - were not a vulnerability
> - were faulty configurations rather than a real vulnerability
> - did not provide a PoC
> - violated any of the rules outlined here
> - had a clear lack of understanding of Open WebUI
> - wrote comments with conflicting information
> - used illogical arguments

**Non-compliant submissions will be closed, and repeat extreme violators may be banned.** Our goal is to foster a constructive reporting environment where quality submissions promote better security for all users.

## Where to report the vulnerability

If you want to report a vulnerability and can meet the outlined requirements, [open a vulnerability report here](https://github.com/open-webui/open-webui/security/advisories/new).
If you feel like you are not able to follow ALL outlined requirements for vulnerability-specific reasons, still do report it, we will check every report either way.

## Product Security And For Non-Vulnerability Related Security Concerns:

If your concern does not meet the vulnerability requirements outlined above, is not a vulnerability, **but is still related to security concerns**, then use the following channels instead:

- **Documentation issues/improvement ideas:** Open an issue on our [Documentation Repository](https://github.com/open-webui/docs)
- **Feature requests:** Create a discussion in [GitHub Discussions - Ideas](https://github.com/open-webui/open-webui/discussions/) to discuss with the community if this feature request is wanted by multiple people
- **Configuration help:** Ask the community for help and guidance on our [Discord Server](https://discord.gg/5rJgQTnV4s) or on [Reddit](https://www.reddit.com/r/OpenWebUI/)
- **General issues:** Use our [Issue Tracker](https://github.com/open-webui/open-webui/issues)

**Examples of non-vulnerability, still security related concerns:**

- Suggestions for better default configuration values
- Security hardening recommendations
- Deployment best practices guidance
- Unclear configuration instructions
- Need for additional security documentation
- Feature requests for optional security enhancements (2FA, audit logging, etc.)
- General security questions about production deployment

Please use the adequate channel for your specific issue - e.g. best-practice guidance or additional documentation needs into the Documentation Repository, and feature requests into the Main Repository as an issue or discussion.

We regularly audit our internal processes and system architecture for vulnerabilities using a combination of automated and manual testing techniques. We are also planning to implement SAST and SCA scans in our project soon.

For any other immediate concerns, please create an issue in our [issue tracker](https://github.com/open-webui/open-webui/issues) or contact our team on [Discord](https://discord.gg/5rJgQTnV4s).

---

_Last updated on **2025-11-06**._
