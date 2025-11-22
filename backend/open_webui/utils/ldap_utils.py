import re
from ldap3.utils.dn import parse_dn

def parse_memberof_groups_from_filter(ldap_filter: str) -> list[str]:
    if not ldap_filter:
        return []

    pattern = r'(?i)(?<![a-z0-9_])memberOf\s*=\s*([^()]+)'
    matches = re.findall(pattern, ldap_filter)

    group_cns: list[str] = []

    for dn in matches:
        dn = dn.strip()
        try:
            rdns = parse_dn(dn, escape=True, strip=True)
        except Exception:
            continue

        if isinstance(rdns, list) and len(rdns) > 0 and isinstance(rdns[0], tuple):
            cns = [part[1] for part in rdns if len(part) >= 2 and part[0].lower() == "cn"]
            group_cns.extend(cns)
            continue

    return group_cns