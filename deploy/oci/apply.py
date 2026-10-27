#!/usr/bin/env python3
"""Validate the exported profile, or apply it to a local source-built container."""

import argparse
import json
import subprocess
from pathlib import Path


# Runs inside the target image using its own application models and validation.
CONTAINER_PROGRAM = r'''
import asyncio
import datetime
import json
from pathlib import Path

from sqlalchemy import select
from open_webui import config  # Initialize configuration defaults.
from open_webui.internal.db import get_async_db
from open_webui.models.config import Config
from open_webui.models.groups import Groups, GroupForm
from open_webui.models.models import Models, ModelForm
from open_webui.models.users import User

async def apply():
    async with get_async_db() as db:
        admin = (await db.execute(
            select(User).where(User.role == 'admin').order_by(User.created_at).limit(1)
        )).scalars().first()
        if admin is None:
            raise RuntimeError('Create the first local administrator account before applying the profile.')
        owner = admin.id

    backup = Path('/app/backend/data/profile-before-' +
                  datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '.json')
    backup.write_text(json.dumps(await Config.get_all(), indent=2))
    backup.chmod(0o600)

    group_ids = {}
    for spec in DOCUMENT['groups']:
        group = await Groups.get_group_by_name(spec['name'])
        if group is None:
            parent = spec.get('parent_group_id')
            group = await Groups.insert_new_group(owner, GroupForm(
                name=spec['name'], description=spec.get('description') or '',
                data=spec.get('data'), permissions=spec.get('permissions'),
                parent_group_id=group_ids.get(parent) if parent else None,
            ))
        if group is None:
            raise RuntimeError('Could not create profile group: ' + spec['name'])
        group_ids[spec['id']] = group.id

    for spec in DOCUMENT['models']:
        values = dict(spec)
        grants = []
        for grant in spec.get('access_grants', []):
            grant = dict(grant)
            if grant['principal_type'] == 'group':
                grant['principal_id'] = group_ids[grant['principal_id']]
            grants.append(grant)
        values['access_grants'] = grants
        form = ModelForm(**values)
        existing = await Models.get_model_by_id(form.id)
        if existing is None:
            model = await Models.insert_new_model(form, owner)
        else:
            model = await Models.update_model_by_id(form.id, form, user_id=owner)
        if model is None:
            raise RuntimeError('Could not import model: ' + form.id)

    settings = dict(DOCUMENT['settings'])
    original_group = settings.get('ui.default_group_id')
    if original_group:
        settings['ui.default_group_id'] = group_ids[original_group]
    await Config.upsert(settings)
    assert await Config.get('ui.default_user_role') == 'user'
    assert await Config.get('ui.enable_signup') is False
    print(json.dumps({'applied_settings': len(settings), 'groups': len(group_ids),
                      'models': len(DOCUMENT['models']), 'backup': str(backup)}))

asyncio.run(apply())
'''


def validate(document):
    if document.get('schema_version') != 1:
        raise ValueError('Unsupported profile schema.')
    settings = document['settings']
    if settings['ui.default_user_role'] != 'user' or settings['ui.enable_signup'] is not False:
        raise ValueError('Expected automatic User role and disabled password signup.')
    group_ids = {group['id'] for group in document['groups']}
    if settings.get('ui.default_group_id') not in group_ids:
        raise ValueError('Default group has no exported definition.')
    for model in document['models']:
        for grant in model.get('access_grants', []):
            if grant['principal_type'] == 'group' and grant['principal_id'] not in group_ids:
                raise ValueError('Model grant refers to an unknown group.')
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--container', default='open-webui-local')
    parser.add_argument('--apply', action='store_true', help='Write settings, groups and models to the target.')
    args = parser.parse_args()
    document = validate(json.loads(Path(__file__).with_name('runtime.json').read_text()))
    print(f"Validated {len(document['settings'])} settings, {len(document['groups'])} group(s), "
          f"and {len(document['models'])} model definitions.", flush=True)
    if not args.apply:
        print('Validation only. Use --apply after starting the local container and creating its administrator.')
        return
    program = 'DOCUMENT = ' + repr(document) + '\n' + CONTAINER_PROGRAM
    subprocess.run(['docker', 'exec', '-i', args.container, 'python', '-'], input=program, text=True, check=True)


if __name__ == '__main__':
    main()
