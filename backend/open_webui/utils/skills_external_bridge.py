import hashlib
import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from open_webui.models.skills import SkillForm, Skills
from open_webui.models.users import Users


log = logging.getLogger(__name__)


EXTERNAL_SKILLS_MANAGER = "claude-external-skills-bridge"


@dataclass
class ExternalSkillEntry:
    source_group: str
    source_relpath: str
    source_file: str
    skill_id: str
    name: str
    description: str
    content: str
    scripts: list[str]


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name, "true" if default else "false")
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _env_csv(name: str, default: str = "") -> list[str]:
    raw = os.environ.get(name, default)
    return [item.strip() for item in str(raw).split(",") if item.strip()]


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text.strip()

    end_index = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_index = idx
            break

    if end_index is None:
        return {}, text.strip()

    frontmatter = {}
    for line in lines[1:end_index]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip().strip('"').strip("'")
        if key:
            frontmatter[key] = value

    body = "\n".join(lines[end_index + 1 :]).strip()
    return frontmatter, body


def _safe_read_text(path: Path, max_bytes: int) -> str:
    if not path.exists() or not path.is_file():
        return ""
    if path.stat().st_size > max_bytes:
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _stable_skill_id(source_group: str, source_relpath: str) -> str:
    digest = hashlib.sha1(
        f"{source_group}:{source_relpath}".encode("utf-8", errors="replace")
    ).hexdigest()[:16]
    return f"extskill_{digest}"


def _discover_skill_files(
    base_root: Path, scan_path: str, max_files: int
) -> list[Path]:
    scan_root = base_root / scan_path
    if not scan_root.exists() or not scan_root.is_dir():
        return []

    skill_files = []
    for file_path in scan_root.rglob("SKILL.md"):
        if len(skill_files) >= max_files:
            break
        if file_path.is_file():
            skill_files.append(file_path)

    return sorted(skill_files)


def _collect_scripts(skill_dir: Path) -> list[str]:
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.exists() or not scripts_dir.is_dir():
        return []

    items = []
    for script in scripts_dir.rglob("*"):
        if script.is_file():
            items.append(str(script.relative_to(skill_dir)).replace("\\", "/"))

    return sorted(items)


def _normalize_name(raw_name: str, fallback: str) -> str:
    name = (raw_name or "").strip()
    if name:
        return name

    cleaned = re.sub(r"[-_]+", " ", fallback).strip()
    return cleaned or "External Skill"


def _build_default_activation(mode: str, hint: str) -> dict:
    normalized_mode = (mode or "manual").strip().lower()
    if normalized_mode not in {"manual", "auto", "always", "semantic"}:
        normalized_mode = "manual"

    activation = {"mode": normalized_mode}
    if normalized_mode == "semantic" and hint:
        activation["semantic_hint"] = hint

    return activation


def discover_external_skills_from_env() -> dict:
    enabled = _env_bool("EXTERNAL_SKILLS_SYNC_ENABLED", False)
    root_path = Path(
        os.environ.get("EXTERNAL_SKILLS_ROOT", "/external/.claude")
    ).expanduser()
    scan_paths = _env_csv(
        "EXTERNAL_SKILLS_SCAN_PATHS",
        "skills,plugins/marketplaces",
    )
    max_files = int(os.environ.get("EXTERNAL_SKILLS_MAX_FILES", "1500"))
    max_bytes = int(os.environ.get("EXTERNAL_SKILLS_MAX_FILE_BYTES", "500000"))

    result = {
        "enabled": enabled,
        "root": str(root_path),
        "scan_paths": scan_paths,
        "entries": [],
        "errors": [],
    }

    if not enabled:
        return result

    if not root_path.exists() or not root_path.is_dir():
        result["errors"].append(f"External skills root not found: {root_path}")
        return result

    entries: list[ExternalSkillEntry] = []
    for scan_path in scan_paths:
        for skill_file in _discover_skill_files(root_path, scan_path, max_files):
            source_relpath = str(skill_file.relative_to(root_path)).replace("\\", "/")
            source_group = scan_path
            skill_id = _stable_skill_id(source_group, source_relpath)

            raw_text = _safe_read_text(skill_file, max_bytes)
            if not raw_text:
                continue

            frontmatter, body = _parse_frontmatter(raw_text)
            description = str(frontmatter.get("description", "")).strip()
            name = _normalize_name(
                str(frontmatter.get("name", "")),
                skill_file.parent.name,
            )

            content = body if body else raw_text
            scripts = _collect_scripts(skill_file.parent)

            entries.append(
                ExternalSkillEntry(
                    source_group=source_group,
                    source_relpath=source_relpath,
                    source_file=str(skill_file),
                    skill_id=skill_id,
                    name=name,
                    description=description,
                    content=content,
                    scripts=scripts,
                )
            )

    result["entries"] = entries
    return result


def _resolve_owner_user_id(
    initiator_user_id: Optional[str] = None,
    db: Optional[Session] = None,
) -> Optional[str]:
    if initiator_user_id:
        user = Users.get_user_by_id(initiator_user_id, db=db)
        if user:
            return user.id

    admin_user = Users.get_super_admin_user(db=db)
    if admin_user:
        return admin_user.id

    first_user = Users.get_first_user(db=db)
    if first_user:
        return first_user.id

    return None


def sync_external_skills_from_env(
    initiator_user_id: Optional[str] = None,
    db: Optional[Session] = None,
) -> dict:
    discovered = discover_external_skills_from_env()
    public_discovery = {
        key: value for key, value in discovered.items() if key != "entries"
    }

    if not discovered.get("enabled", False):
        return {
            **public_discovery,
            "discovered": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
        }

    owner_user_id = _resolve_owner_user_id(initiator_user_id=initiator_user_id, db=db)
    if not owner_user_id:
        return {
            **public_discovery,
            "discovered": len(discovered.get("entries", [])),
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": [
                *discovered.get("errors", []),
                "No valid owner user found for external skill import.",
            ],
        }

    default_priority = int(os.environ.get("EXTERNAL_SKILLS_DEFAULT_PRIORITY", "40"))
    default_activation_mode = os.environ.get(
        "EXTERNAL_SKILLS_DEFAULT_ACTIVATION",
        "semantic",
    )

    created = 0
    updated = 0
    skipped = 0
    errors = list(discovered.get("errors", []))

    for entry in discovered.get("entries", []):
        try:
            existing = Skills.get_skill_by_id(entry.skill_id, db=db)

            bridge_meta = {
                "managed": True,
                "manager": EXTERNAL_SKILLS_MANAGER,
                "source_group": entry.source_group,
                "source_relpath": entry.source_relpath,
                "source_file": entry.source_file,
                "scripts": entry.scripts,
                "has_python_scripts": any(
                    script.lower().endswith(".py") for script in entry.scripts
                ),
                "has_shell_scripts": any(
                    script.lower().endswith(".sh") for script in entry.scripts
                ),
                "synced_at": int(time.time()),
            }

            if existing:
                next_meta = existing.meta if isinstance(existing.meta, dict) else {}
                next_meta = {
                    **next_meta,
                    "description": entry.description
                    or next_meta.get("description", ""),
                    "external_bridge": bridge_meta,
                }

                updates = {
                    "name": entry.name,
                    "content": entry.content,
                    "meta": next_meta,
                }

                if not isinstance(existing.activation, dict) or not existing.activation:
                    updates["activation"] = _build_default_activation(
                        default_activation_mode,
                        entry.description or entry.name,
                    )

                if existing.priority is None:
                    updates["priority"] = default_priority

                if Skills.update_skill_by_id(entry.skill_id, updates, db=db):
                    updated += 1
                else:
                    skipped += 1
                continue

            form_data = SkillForm(
                id=entry.skill_id,
                name=entry.name,
                content=entry.content,
                meta={
                    "description": entry.description,
                    "external_bridge": bridge_meta,
                },
                activation=_build_default_activation(
                    default_activation_mode,
                    entry.description or entry.name,
                ),
                effects={},
                is_active=True,
                priority=default_priority,
                access_control=None,
            )

            created_skill = Skills.insert_new_skill(owner_user_id, form_data, db=db)
            if created_skill:
                created += 1
            else:
                skipped += 1
        except Exception as e:
            errors.append(f"{entry.source_file}: {e}")
            continue

    summary = {
        **public_discovery,
        "owner_user_id": owner_user_id,
        "discovered": len(discovered.get("entries", [])),
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
    }

    log.info(
        f"External skills sync completed: discovered={summary['discovered']} created={created} updated={updated} skipped={skipped} errors={len(errors)}"
    )

    return summary
