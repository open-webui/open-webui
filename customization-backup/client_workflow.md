# Client workflow - production ready

⏺ mAI Production Deployment Workflow for Hetzner Cloud

1. Server Preparation
- Fresh Ubuntu server on Hetzner Cloud
- Install Docker and Docker Compose
- Clone mAI repository from customization branch
1. Client Configuration & Database Setup

Run generate_client_env.py --production which performs ALL necessary setup:

- Prompts for:
    - OpenRouter Provisioning API key
    - Organization name (e.g., "ABC Company Sp. z o.o.")
    - Spending limit (unlimited or specific amount)
- Automatically:
    - Creates new API key via OpenRouter Provisioning API
    - Tests API key and captures external_user mapping
    - Generates .env file with all configuration
    - Creates SQLite database tables if missing
    - Inserts client organization record with 1.3x markup rate
    - Sets up environment for automatic initialization on container startup
1. Docker Deployment
- Use docker-compose-customization.yaml with env_file: .env
- Container starts and automatically:
    - Reads environment variables
    - Runs usage_tracking_init.py (idempotent initialization)
    - Ensures client organization exists
    - All users automatically belong to this organization
1. Admin User Setup
- First user to register becomes admin
- Admin manages users through Settings → Admin → Users interface
- Admin can create additional users (up to 19 total)
1. Automatic Usage Tracking

When users make queries:

- Each user gets unique external_user_id mapping
- OpenRouter responses captured by openrouter_client_manager
- Usage data saved to database with 1.3x markup
- Subscription billing calculated based on user count and creation dates
1. Multi-Client Isolation

For multiple clients on same Hetzner server:

- Each client gets separate Docker container (different ports)
- Each has own .env file and database volume
- Complete data isolation between clients
- No cross-client data access

The entire process is streamlined with a single command (generate_client_env.py --production), ensuring production-ready deployment with proper billing and usage monitoring configured automatically.
