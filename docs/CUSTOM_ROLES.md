# Custom roles and group managers

This guide describes the backend custom-role and scoped group-manager behavior.
It is intended for administrators deploying or operating a version that includes
the custom-role migrations.

## Role semantics

- **`admin` is an exact role.** Administrative endpoints use the literal
  `admin` value. A custom role, even one with every permission leaf enabled,
  does not receive the admin bypass and cannot use the admin-only custom-role
  endpoints.
- **`user` and `pending` retain the legacy path.** Their permissions continue
  to use configured defaults and the existing most-permissive group merge.
  These roles do not provide group-manager authority.
- **Custom roles use opaque references.** A user is assigned a value such as
  `custom:<role-uuid>`, backed by the `custom_role` registry. The role's
  explicit, server-catalog permissions are normalized with omitted leaves set
  to `false`; group permissions and configured defaults are not merged into a
  custom role.
- **Invalid roles fail closed.** A malformed or unknown custom-role reference
  resolves to no permissions. Role names are normalized and unique; `admin`,
  `user`, and `pending` are reserved names. The lifecycle APIs reset assigned
  users before deactivation or deletion, so an inactive reference should only
  remain as legacy data from an interrupted or manual database change.

Custom-role assignment is deliberately manual. OAuth, LDAP, SCIM, and
trusted-header provisioning do not silently assign a custom role.

## Manual role administration

The admin-only API is rooted at `/api/v1/custom-roles`. Use an authenticated
exact-admin session; do not edit `User.role` directly.

1. Create a role with `POST /api/v1/custom-roles/create`:

   ```json
   {
     "name": "content-manager",
     "display_name": "Content manager",
     "permissions": {
       "groups": {
         "manage_members": true,
         "manage_assets": true,
         "manage_skills": true
       }
     }
   }
   ```

   Permission leaves not supplied in the request are denied. The response
   contains the immutable role UUID needed for assignment.

2. Assign an active role with `POST /api/v1/custom-roles/assign` and a body
   of `{"user_id": "<user-id>", "role_id": "<role-uuid>"}`. The target user
   must exist, and an administrator cannot assign a role to themselves through
   this endpoint. The first admin cannot be demoted.

3. Deactivate a role with
   `POST /api/v1/custom-roles/<role-uuid>/deactivate`, or update it with
   `POST /api/v1/custom-roles/<role-uuid>/update` and `{"active": false}`.
   Deactivation atomically resets every current `custom:<role-uuid>`
   assignment to the legacy `user` role before committing `active=false`. The
   operation is safe to repeat; it does not change unrelated roles. Reactivation
   is available with `{"active": true}`, but users must be assigned again.

4. Delete a role with
   `DELETE /api/v1/custom-roles/<role-uuid>`. Deletion atomically resets every
   current assignment to `user` and removes the registry row. A missing role is
   not deleted again and returns not found.

5. Remove an assignment with
   `POST /api/v1/custom-roles/<role-uuid>/unassign?user_id=<user-id>`.
   This changes the user to the legacy `pending` role; it does not restore a
   previous role automatically.

Role creation, updates, deactivation, assignment, and user-role changes emit
metadata-only lifecycle events. Review those events after any bulk operation.

## Group-manager boundary

The scoped service is additive and is rooted at
`/api/v1/group-manager/groups/<group-id>/...`. A caller is a manager for a
group only when all of these facts are true at authorization time:

The manager workspace discovers eligible groups through the separately scoped
`GET /api/v1/group-manager/groups` endpoint; it must not use legacy group APIs.

1. the caller has an active `custom:<role-uuid>` reference;
2. the role contains the exact capability required by the operation; and
3. the caller is a current member of the target group.

`groups.manage_members`, `groups.manage_assets`, and `groups.manage_skills` are
independent capabilities. For example, `manage_members` does not authorize
asset or skill changes. Membership, role, and group checks are performed in
the same transaction as each mutation, so removing membership or deactivating
the role takes effect at the boundary of a subsequent request.

Group creator IDs, resource creator IDs, and ordinary access grants do not
establish manager authority. Exact-admin and legacy users are intentionally
denied by the scoped manager service; administrators should use the existing
admin routes instead. A manager can operate only on the group in the request,
not on another group they do not currently belong to.

## Scoped resources and exclusions

The current group-owned resource allowlist is:

| Resource  | Capability             | Scoped behavior                                                                                                                                                                         |
| --------- | ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Knowledge | `groups.manage_assets` | Create, list, update, delete, and adjust the owning group's write grant. The owning group always keeps baseline read access.                                                            |
| Prompts   | `groups.manage_assets` | Create, list, update, delete, and adjust the owning group's write grant. Public, user, and other-group grants cannot be supplied or replaced.                                           |
| Skills    | `groups.manage_skills` | Create, list, read, update, and delete. IDs, `user_id`, ownership, and grants are server-controlled; the owning group receives baseline read only and has no ACL write-delta operation. |

Knowledge and prompt ownership is authoritative in `group_owned_asset`, with
one owning group per resource. Ownership cannot be inferred from an access
grant, transferred through the scoped API, or used to grant another principal.
All resource, ownership, and baseline-grant writes are committed atomically.

**Models and tools are explicitly excluded from group-manager scoped support.**
The presence of ordinary `workspace.models` or `workspace.tools` leaves in the
custom-role catalog does not create group-owned model/tool routes. Do not use a
manager role as a substitute for model administration. Tool creation/update is
server-side Python code execution and must be treated as root-equivalent trust;
it is not a contained group capability.

## Audit and redaction

- Scoped manager events are published only after a successful commit and omit
  resource content. Role events contain identifiers and role metadata, not the
  role's user content.
- When HTTP audit body capture is enabled, scoped **skill** list/create/read/
  update/delete paths are marked before request handling and both request and
  response bodies are logged as `[REDACTED]`. This also covers validation and
  authorization failures.
- The route-specific redaction does **not** cover knowledge or prompt bodies,
  nor arbitrary custom-role request bodies. For sensitive deployments, use
  `AUDIT_LOG_LEVEL=METADATA` (or configure `AUDIT_INCLUDED_PATHS` narrowly)
  rather than capturing request/response bodies. `AUDIT_LOG_LEVEL` defaults to
  `NONE`; audit files otherwise default to `<DATA_DIR>/audit.log`.

## Deployment, migration, and rollback

Before upgrading, take a consistent database backup and back up the Open WebUI
data volume. The feature schema is introduced by these revisions, in order:

- `c5a8d3e2f1b0`: `custom_role` registry;
- `fdcb6cc75284`: `group_owned_asset` and its ownership constraints;
- `a2b3c4d5e6f7`: adds `skill` to the owned-resource allowlist.

Migrations run at startup when `ENABLE_DB_MIGRATIONS=true` (the default). In a
multi-node deployment, designate one migration runner and prevent concurrent
startup migrations from multiple nodes. Confirm the startup log reaches the
repository's current Alembic head before assigning roles or creating scoped
assets. These migrations do not backfill assignments or create managers.

Rollback should normally be a restore of the pre-upgrade database/data-volume
backup together with the previous application version. Do not treat Alembic
downgrade as a routine rollback: the custom-role downgrade removes the role
registry, the ownership downgrade removes group ownership records, and
downgrading the skill allowlist can be incompatible with existing group-owned
skills. If a downgrade is unavoidable, stop application writers, take another
backup, inventory custom-role references and group-owned assets, and rehearse
the exact downgrade and restore procedure on a copy first.

## Operator validation checklist

After deployment, verify in a non-production test group and test account:

1. The migration log and database revision table show the current head, and
   `custom_role` and `group_owned_asset` exist.
2. An exact admin can create, assign, update, deactivate, reactivate, and
   unassign a role; a custom-role user cannot call the admin role API.
3. A manager with only `manage_members`, `manage_assets`, or `manage_skills`
   is limited to that capability. Remove the user from the group and confirm
   the next scoped request is denied; verify deactivation or deletion resets
   assigned users to `user` and leaves unrelated roles unchanged.
4. Knowledge, prompt, and skill create/update/delete operations stay within
   the owning group. Confirm skills have read-only group grants and that model
   and tool manager operations are rejected or unavailable.
5. With temporary audit capture enabled, exercise a skill endpoint (including
   a rejected request) and confirm request and response bodies are
   `[REDACTED]`. Do not put production content in this test.
6. Preserve the backup and record the migration head, validation results, and
   any role assignments in the deployment change record.
