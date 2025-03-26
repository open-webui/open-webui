# Keycloak

Helicopter view:

1. Create a realm
2. Create users
3. Create a client
4. Export the realm settings


## Detailed steps

### Create a realm

1. In the left navigation click the dropdown then **Create realm**
2. Enter a name
3. Click **Create**


### Configuring users

1. In the left navigaiton click **Users**
2. Click **Add user**
3. Enable **email verified**
4. Enter a username, email first and last name
5. Click **Save**
6. On the resulting page click the **Credentials** Tab
7. Click **Set password**
8. Enter the password
9. Disable **Temporary**
10. Click **Save**


### Configuring a client

1. In the left navigaiton click **Clients**
2. Click **Create client**
3. Step 1: Enter a client ID (i.e. "openwebui") and name
4. Step 2: enable **Client authentication**
5. Step 3: enter the root and home URL `http://localhost:3000` 
6. Step 3: add two **Valid redirect URIs**: `http://localhost:3000/*`, `http://localhost:8080/*`
8. Click **Save**
6. On the resulting page click the **Advanced** tab
7. In the **Proof Key for Code Exchange Code Challenge Method** dropdown select "S256"
8. Click **Save**
9. On the resulting page click the **Credentials** tab
10. Copy the **Client Secret**


## Export realm settings

### In Keycloak UI

1. In the left navigaiton click **Realm settings**
2. In the top right corner click **Action** > **Partial export**
3. Enable **Include groups and roles** and **Include clients**
4. Click **Export**
5. Save the file as `/keycloak/realm-export.json`

### In a shell of the Keycloak container

The usual way:

```
$ /opt/keycloak/bin/kc.sh export --file /opt/keycloak/data/import/realm-export.json
```

(This does not work in Keycloak 26 dev-mode due to a locked database)

Workaround:

```
$ cp cp -rp /opt/keycloak/data/h2 /tmp
$ /opt/keycloak/bin/kc.sh export  --db dev-file  --db-url 'jdbc:h2:file:/tmp/h2/keycloakdb;NON_KEYWORDS=VALUE'  --file /tmp/realm-export.json
$ cat /tmp/realm-export.json
```



## Example Open WebUI config

```
ENABLE_OAUTH_SIGNUP=true
OAUTH_CLIENT_ID=openwebui
OAUTH_PROVIDER_NAME=Keycloak
OAUTH_SCOPES=openid email
OPENID_PROVIDER_URL=http://localhost:8079/realms/openwebui/.well-known/openid-configuration
OPENID_REDIRECT_URI=http://localhost:8080/oauth/oidc/callback
OAUTH_CLIENT_SECRET=<GENERATED IN THE ADMIN CONSOLE>
```


## Troubleshooting

### On login with via Keycloak, error `Invalid parameter: redirect_uri`

#### Verification steps

1. In Keycloak check under Clients > client "openwebui" > Settings Tab the valid redirect URIs
   * It should contain `http://localhost:3000/*`
2. In the URL check the redirect URI
   * For example `redirect_uri=http%3A%2F%2Flocalhost%3A8080%2Foauth%2Foidc%2Fcallback` would be wrong as the host has to be `localhost:3000`, not `localhost:8080`
3. In OpenWebUI config check the `OPENID_REDIRECT_URI` config, it should be `OPENID_REDIRECT_URI=http://localhost:3000/oauth/oidc/callback`
   * The URL should match what was allowd in Keycloak
