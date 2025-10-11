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

We appreciate the community's interest in identifying potential vulnerabilities. However, effective immediately, we will **not** accept low-effort vulnerability reports. Ensure that **submissions are constructive, actionable, reproducible, well documented and adhere to the following guidelines**:

Reports not submitted through our designated GitHub repository will be disregarded, and we will categorically reject invitations to collaborate on external platforms. Our aggressive stance on this matter underscores our commitment to a secure, transparent, and open community where all operations are visible and contributors are accountable.

1. **No Vague Reports**: Submissions such as "I found a vulnerability" without any details will be treated as spam and will not be accepted.

2. **In-Depth Understanding Required**: Reports must reflect a clear understanding of the codebase and provide specific details about the vulnerability, including the affected components and potential impacts.

3. **Proof of Concept (PoC) is Mandatory**: Each submission must include a well-documented proof of concept (PoC) that demonstrates the vulnerability. If confidentiality is a concern, reporters are encouraged to create a private fork of the repository and share access with the maintainers. Reports lacking valid evidence may be disregarded.

4. **Required Patch or Actionable Remediation Plan Submission**: Along with the PoC, reporters must provide a patch or actionable steps to remediate the identified vulnerability. This helps us evaluate and implement fixes rapidly.

5. **Streamlined Merging Process**: When vulnerability reports meet the above criteria, we can consider them for immediate merging, similar to regular pull requests. Well-structured and thorough submissions will expedite the process of enhancing our security.

6. **Default Configuration Testing**: All vulnerability reports MUST be tested and reproducible using Open WebUI's out-of-the-box default configuration. Claims of vulnerabilities that only manifest with explicitly weakened security settings may not be considered valid vulnerability reports.

> [!NOTE]  
> **Note**: If you believe you have found a security issue that
> 1) affects default configurations **or**
> 2) represents a genuine bypass of intended security controls **or**
> 3) works only with non-default configurations **but** the configuration in question is likely to be used by production deployments
> **then we absolutely want to hear about it.** This policy is intended to filter configuration issues and deployment problems, not to discourage legitimate security research.

7. **Threat Model Understanding Required**: Reports must demonstrate understanding of Open WebUI's self-hosted, authenticated, role-based access control architecture. Comparing Open WebUI to services with fundamentally different security models without acknowledging the architectural differences may result in report rejection.

**Non-compliant submissions will be closed, and repeat extreme violators may be banned.** Our goal is to foster a constructive reporting environment where quality submissions promote better security for all users.

If you want to report a vulnerability and can meet all outlines requirements, [open a vulnerability report here](https://github.com/open-webui/open-webui/security/advisories/new).

## Product Security

We regularly audit our internal processes and system architecture for vulnerabilities using a combination of automated and manual testing techniques. We are also planning to implement SAST and SCA scans in our project soon.

For immediate concerns or detailed reports that meet our guidelines, please create an issue in our [issue tracker](/open-webui/open-webui/issues) or contact us on [Discord](https://discord.gg/5rJgQTnV4s).

---

_Last updated on **2025-10-09**._
