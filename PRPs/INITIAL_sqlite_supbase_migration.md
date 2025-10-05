## FEATURE:

[Insert your feature here]

## EXAMPLES:

[Provide and explain examples that you have in the `examples/` folder]

## DOCUMENTATION:


Previous research:

Current Database Setup (Default Docker Image)
By default, Open WebUI uses SQLite:

The database is stored as a file called webui.db located at /app/backend/data/webui.db inside the container 📦 Exporting and Importing Database | Open WebUI
All configurations are stored in this database, supporting persistent settings across instances ⭐ Features | Open WebUI
When you use the Docker volume mount -v open-webui:/app/backend/data, this SQLite database file is persisted

Accessing the Current Database:
To access or backup your current SQLite database:
bashdocker cp open-webui:/app/backend/data/webui.db ./webui.db
Yes, You CAN Migrate to PostgreSQL (including Supabase)
Open WebUI supports flexible database integration, including SQLite and Postgres, configured through environment variables ⭐ Features | Open WebUI. This means you can absolutely transition to a Supabase PostgreSQL database.
Migration Process Overview:
1. Set up your PostgreSQL/Supabase database:

Create a PostgreSQL database in Supabase
Enable the pgvector extension (required for RAG features):

sqlCREATE EXTENSION IF NOT EXISTS vector;
2. Configure Open WebUI to use PostgreSQL:
Add the DATABASE_URL environment variable to your Docker deployment:
bashDATABASE_URL=postgresql://user:password@hostname:port/dbname
For Supabase, your connection string would look like:
bashDATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
3. Initialize the schema:

Start Open WebUI with the PostgreSQL DATABASE_URL configured to create the database tables, then stop it after confirming tables are created Migrating Open WebUI SQLite Database to Postgresql | by David Shettler | Medium

4. Migrate existing data:
You have several community-developed migration tools available:

Recommended: open-webui-postgres-migration - This is an interactive, robust tool with comprehensive database integrity checking, configurable batch processing, and real-time progress visualization GitHub - taylorwilsdon/open-webui-postgres-migration: Interactive, locally hosted tool to migrate Open-WebUI SQLite databases to PostgreSQL

Installation:
bashpip install open-webui-postgres-migration
# or
uvx open-webui-postgres-migration
Important Considerations:
1. Known Migration Issue:
SQLite supports null byte content (\u0000), but PostgreSQL does not, which can cause search function failures after migration. You can fix this by executing: UPDATE chat SET chat = REPLACE(chat::TEXT, '\u0000', '')::JSONB; Conversion script SQLite to PostgreSQL · open-webui/open-webui · Discussion #8116
2. Vector Database:
If you're using RAG features, you'll also want to configure your vector database. You can set VECTOR_DB to pgvector to use PostgreSQL's vector extension How to use PostgreSQL with OpenWebUI - installvirtual, or use a separate service like Qdrant.
3. Production Considerations:
For production use, many prefer PostgreSQL over SQLite for data integrity and backup purposes OpenWebUI With Postgres And Qdrant - A Setup Guide - Hey, It Works!. With Supabase, you'd also get:

Automated backups
Point-in-time recovery
Better concurrent access handling
Easier database management and monitoring

Docker Compose Example with PostgreSQL:
yamlversion: '3'
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    ports:
      - "3000:8080"
    environment:
      - DATABASE_URL=postgresql://user:password@host:5432/dbname
      - VECTOR_DB=pgvector
    volumes:
      - open-webui:/app/backend/data

## OTHER CONSIDERATIONS:

[Any other considerations or specific requirements - great place to include gotchas that you see AI coding assistants miss with your projects a lot]
