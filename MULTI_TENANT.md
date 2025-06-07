Multi-Tenant Deployments with Provider Isolation

  Based on my analysis of the Open WebUI codebase, here's how multi-tenant deployments work with provider isolation:

  1. Multiple Provider Support Architecture

  The OAuth system supports multiple identity providers simultaneously:

  # From config.py - Multiple providers can be active at once
  OAUTH_PROVIDERS = {}

  # Each provider has independent configuration
  if GOOGLE_CLIENT_ID.value and GOOGLE_CLIENT_SECRET.value:
      OAUTH_PROVIDERS["google"] = {...}

  if MICROSOFT_CLIENT_ID.value and MICROSOFT_CLIENT_SECRET.value:
      OAUTH_PROVIDERS["microsoft"] = {...}

  if GITHUB_CLIENT_ID.value and GITHUB_CLIENT_SECRET.value:
      OAUTH_PROVIDERS["github"] = {...}

  if OAUTH_CLIENT_ID.value and OAUTH_CLIENT_SECRET.value:
      OAUTH_PROVIDERS["oidc"] = {...}

  2. Provider Isolation Mechanisms

  Separate Provider Endpoints

  Each provider has isolated login flows:
  /oauth/google/login     → Google OAuth flow
  /oauth/microsoft/login  → Microsoft OAuth flow
  /oauth/github/login     → GitHub OAuth flow
  /oauth/oidc/login       → Generic OIDC flow

  Tenant-Specific Microsoft Integration

  Microsoft specifically supports tenant isolation:
  # Microsoft tenant isolation
  MICROSOFT_CLIENT_TENANT_ID = PersistentConfig(
      "MICROSOFT_CLIENT_TENANT_ID",
      "oauth.microsoft.tenant_id",
      os.environ.get("MICROSOFT_CLIENT_TENANT_ID", ""),
  )

  # Tenant-specific discovery endpoint
  server_metadata_url = f"https://login.microsoftonline.com/{MICROSOFT_CLIENT_TENANT_ID.value}/v2.0/.well-known/openid-configuration"

  OAuth Subject Isolation

  Each user gets a provider-specific identifier:
  # From oauth.py - Provider isolation via oauth_sub
  provider_sub = f"{provider}@{sub}"  # e.g., "google@12345", "microsoft@67890"

  # Database stores provider-specific subject
  oauth_sub = Column(Text, unique=True)  # e.g., "microsoft@tenant123@user456"

  3. Multi-Tenant Deployment Patterns

  Pattern 1: Department/Division Isolation

  # Marketing team uses Google
  GOOGLE_CLIENT_ID=marketing_google_client_id
  GOOGLE_CLIENT_SECRET=marketing_google_secret

  # Engineering team uses GitHub  
  GITHUB_CLIENT_ID=engineering_github_client_id
  GITHUB_CLIENT_SECRET=engineering_github_secret

  # Executive team uses Microsoft with specific tenant
  MICROSOFT_CLIENT_ID=exec_microsoft_client_id
  MICROSOFT_CLIENT_SECRET=exec_microsoft_secret
  MICROSOFT_CLIENT_TENANT_ID=executive_tenant_id

  Pattern 2: Customer/Partner Isolation

  # Customer A uses their OIDC provider
  OAUTH_CLIENT_ID=customer_a_client_id
  OAUTH_CLIENT_SECRET=customer_a_secret
  OPENID_PROVIDER_URL=https://customer-a.auth.com/.well-known/openid-configuration

  # Customer B could use Microsoft with their tenant
  MICROSOFT_CLIENT_ID=customer_b_client_id
  MICROSOFT_CLIENT_SECRET=customer_b_secret
  MICROSOFT_CLIENT_TENANT_ID=customer_b_tenant_id

  Pattern 3: Environment-Based Isolation

  # Production environment
  OAUTH_CLIENT_ID=prod_client_id
  OPENID_PROVIDER_URL=https://prod-auth.company.com/.well-known/openid-configuration

  # Staging environment  
  OAUTH_CLIENT_ID=staging_client_id
  OPENID_PROVIDER_URL=https://staging-auth.company.com/.well-known/openid-configuration

  4. User Isolation and Mapping

  Provider-Specific User Identification

  # Each provider creates unique oauth_sub values
  google_user = "google@108234567890123456789"
  microsoft_user = "microsoft@tenant123@user-guid-456"
  github_user = "github@12345678"
  oidc_user = "oidc@custom-sub-identifier"

  Cross-Provider Email Merging (Optional)

  # Can merge accounts across providers by email if enabled
  OAUTH_MERGE_ACCOUNTS_BY_EMAIL = true

  # Same email address can authenticate via multiple providers
  user@company.com → Can login via Google, Microsoft, or OIDC

  5. Configuration Isolation

  Provider-Specific Settings

  Each provider has completely independent configuration:
  # Google-specific settings
  GOOGLE_OAUTH_SCOPE = "openid email profile"
  GOOGLE_REDIRECT_URI = "https://app.company.com/oauth/google/callback"

  # Microsoft-specific settings  
  MICROSOFT_OAUTH_SCOPE = "openid email profile"
  MICROSOFT_REDIRECT_URI = "https://app.company.com/oauth/microsoft/callback"
  MICROSOFT_CLIENT_TENANT_ID = "tenant-specific-id"

  # Custom OIDC settings
  OAUTH_SCOPES = "openid email profile groups roles"
  OPENID_REDIRECT_URI = "https://app.company.com/oauth/oidc/callback"
  OAUTH_PROVIDER_NAME = "Custom Provider Name"

  6. Runtime Provider Selection

  Dynamic Provider Loading

  # From oauth.py - Providers loaded dynamically based on configuration
  class OAuthManager:
      def __init__(self, app):
          self.oauth = OAuth()
          self.app = app
          # Only register providers that have valid configuration
          for provider_name, provider_config in OAUTH_PROVIDERS.items():
              provider_config["register"](self.oauth)

      def get_client(self, provider_name):
          return self.oauth.create_client(provider_name)

  Provider Availability Check

  # From oauth.py - Validates provider exists before processing
  async def handle_login(self, request, provider):
      if provider not in OAUTH_PROVIDERS:
          raise HTTPException(404)  # Provider not configured/available

  7. Multi-Tenant Use Cases

  Enterprise Scenarios

  1. Subsidiaries: Each subsidiary uses their own identity provider
  2. Departments: Different departments use different auth systems
  3. Customers: B2B SaaS with customer-specific identity providers
  4. Partners: External partners authenticate via their own systems
  5. Environments: Dev/staging/prod with separate auth systems

  Implementation Benefits

  - Security: Complete isolation between tenant identity sources
  - Flexibility: Support heterogeneous identity environments
  - Compliance: Meet different regulatory requirements per tenant
  - User Experience: Users authenticate with familiar identity providers
  - Migration: Gradual migration between identity providers

  8. Limitations and Considerations

  Current Limitations

  - Single instance per provider type: Can't have multiple Google or Microsoft configurations simultaneously
  - Global configuration: All providers share same role/group management settings
  - No runtime provider switching: Configuration requires restart

  Enterprise Enhancement Opportunities

  # Potential enhancements for true multi-tenancy
  OAUTH_PROVIDERS_CONFIG = {
      "tenant_a": {
          "google": {"client_id": "...", "client_secret": "..."},
          "microsoft": {"client_id": "...", "tenant_id": "..."}
      },
      "tenant_b": {
          "oidc": {"client_id": "...", "provider_url": "..."}
      }
  }

  The current implementation provides provider-level isolation which enables many multi-tenant scenarios, though true tenant-aware configuration would require
  additional development for more complex enterprise deployments.

