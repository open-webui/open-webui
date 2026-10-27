# Exported OCI OpenWebUI configuration

This profile was pulled from the running `open-webui` container on `openwebui`
(`https://orac-ai.com`) on 26 October 2026. The production VM was not modified.

## Files

- `runtime.json`: 22 application settings, the OpenWebUI `OCI-GenAI-Users` group,
  and 51 model definitions with group-level access rules. Includes the OCI
  endpoint, its 50 explicitly configured models, automatic `User` role, disabled
  password signup, and the default application group.
- `.env.example`: non-secret template for the container environment, including
  the existing OCI identity-domain OIDC client and callback configuration.
- `compose.yaml`: builds this checkout into a separate local container and volume.
- `apply.py`: validates the profile or imports its settings and access definitions
  using the target image's application models. It maps groups by name rather
  than reusing production database IDs. Existing group memberships are untouched.

The ignored `.deployment/` directory at the repository root contains the actual
exported credentials in `openwebui.env`, a full configuration-table snapshot in
`runtime.private.json`, and the model/group export in `model-access.private.json`.
These files have mode `0600`; the directory is excluded from Git and Docker build
contexts. The environment file uses Compose `format: raw` so credentials and
JSON values are not interpolated. A separate local session-signing key was
generated; the production session-signing key was not copied.

No users, passwords, session tokens, chats, uploaded documents, or group
memberships were copied. Individual-user model grants are excluded. The local
checkout's application code and the existing root Compose file are unchanged.

## Use with this checkout

1. Review `.deployment/openwebui.env`. It currently retains the production
   `WEBUI_URL` and `OPENID_REDIRECT_URI`. To use SSO on another address, register
   that exact callback in the OCI confidential application and update both
   environment variables. Update `webui.url` in `runtime.json` to the same site
   before applying the profile. Credentials in the private file access the real
   OCI services; substitute separate credentials when needed.
2. Build and start the separate local deployment from the repository root:

   ```sh
   docker compose -f deploy/oci/compose.yaml up -d --build
   ```

   Use `docker-compose` instead of `docker compose` if Compose is installed as a
   standalone command. The service binds to `127.0.0.1:3000` and uses its own
   persistent volume; it does not reuse the production volume.
3. Open `http://localhost:3000` and create the first local administrator account.
4. Validate and then import the settings, default group and model access:

   ```sh
   python3 deploy/oci/apply.py
   python3 deploy/oci/apply.py --apply
   ```

   The importer backs up the target settings inside its data volume before
   writing, creates missing groups, and creates or updates the exported model
   IDs. Existing accounts and memberships are not imported. Run it only against
   the intended local container; `--container` overrides `open-webui-local`.

For a new checkout, copy `deploy/oci/.env.example` to
`.deployment/openwebui.env` and supply the credentials before starting Compose.

## OCI IAM configuration is separate

Corporate Production SAML federation, first-login user provisioning, the OCI IAM
`OCI-GenAI-Users` group and application grants are managed in the `aistudio`
identity domain. They were not changed or recreated by this local export.
The OpenWebUI group with the same name is a separate application group.

## Validation performed

The saved profile and Compose configuration are validated locally. No local image
was built or started, and no new end-to-end SSO or model-inference test was run as
part of this export.
