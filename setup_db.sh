#!/bin/bash

# Create required tables and initialize data
echo "Creating required tables..."
PGPASSWORD=BJmM1FSHt5aWRhbn psql -h aws-0-eu-west-3.pooler.supabase.com -U postgres.ddoimsqiehmrjoepwugw -d postgres -c "CREATE TABLE IF NOT EXISTS owui_config (id SERIAL PRIMARY KEY, data JSONB NOT NULL, version INTEGER NOT NULL, created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(), updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW());"

echo "Inserting default config..."
PGPASSWORD=BJmM1FSHt5aWRhbn psql -h aws-0-eu-west-3.pooler.supabase.com -U postgres.ddoimsqiehmrjoepwugw -d postgres -c "INSERT INTO owui_config (data, version) SELECT '{\"version\":\"1.0.0\",\"settings\":{\"ui\":{\"theme\":\"system\"}}}', 1 WHERE NOT EXISTS (SELECT 1 FROM owui_config LIMIT 1);"

echo "Creating alembic version table..."
PGPASSWORD=BJmM1FSHt5aWRhbn psql -h aws-0-eu-west-3.pooler.supabase.com -U postgres.ddoimsqiehmrjoepwugw -d postgres -c "CREATE TABLE IF NOT EXISTS owui_alembic_version (version_num VARCHAR(32) NOT NULL, PRIMARY KEY (version_num));"

echo "Setting up alembic version..."
PGPASSWORD=BJmM1FSHt5aWRhbn psql -h aws-0-eu-west-3.pooler.supabase.com -U postgres.ddoimsqiehmrjoepwugw -d postgres -c "DELETE FROM owui_alembic_version;"
PGPASSWORD=BJmM1FSHt5aWRhbn psql -h aws-0-eu-west-3.pooler.supabase.com -U postgres.ddoimsqiehmrjoepwugw -d postgres -c "INSERT INTO owui_alembic_version (version_num) VALUES ('sync_activities_schema');"

echo "Database setup completed." 