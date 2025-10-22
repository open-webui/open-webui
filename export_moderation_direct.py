#!/usr/bin/env python3
"""
Direct Database Export Script for Moderation Data
This script connects directly to the Heroku PostgreSQL database without requiring psql
"""

import os
import sys
import subprocess
import csv
import json
from urllib.parse import urlparse

def get_database_url(app_name):
    """Get the database URL from Heroku config"""
    try:
        result = subprocess.run(
            ['heroku', 'config:get', 'DATABASE_URL', '-a', app_name],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting database URL: {e}", file=sys.stderr)
        return None

def install_psycopg2():
    """Try to install psycopg2 if not available"""
    try:
        import psycopg2
        return True
    except ImportError:
        print("Installing psycopg2-binary...")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'psycopg2-binary'], 
                         check=True, capture_output=True)
            import psycopg2
            return True
        except (subprocess.CalledProcessError, ImportError):
            print("Failed to install psycopg2-binary", file=sys.stderr)
            return False

def export_moderation_data(app_name, output_file):
    """Export moderation data to CSV"""
    
    # Get database URL
    print("🔍 Getting database connection info...")
    db_url = get_database_url(app_name)
    if not db_url:
        print("❌ Could not get database URL")
        return False
    
    print("✅ Database URL obtained")
    
    # Install psycopg2 if needed
    if not install_psycopg2():
        print("❌ Could not install required database driver")
        return False
    
    import psycopg2
    
    # Parse database URL
    parsed = urlparse(db_url)
    
    # Connect to database
    print("🔌 Connecting to database...")
    try:
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port,
            database=parsed.path[1:],  # Remove leading slash
            user=parsed.username,
            password=parsed.password,
            sslmode='require'
        )
        print("✅ Database connection established")
    except Exception as e:
        print(f"❌ Database connection failed: {e}", file=sys.stderr)
        return False
    
    try:
        # Test connection with a simple query
        print("🔍 Testing database connection...")
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM moderation_session;")
            count = cur.fetchone()[0]
            print(f"📊 Found {count} moderation session rows")
        
        if count == 0:
            print("⚠️  No moderation data found in database")
            # Create empty CSV with headers
            headers = [
                'id', 'user_id', 'child_id',
                'scenario_index', 'attempt_number', 'version_number',
                'scenario_prompt', 'original_response',
                'initial_decision', 'is_final_version',
                'strategies', 'custom_instructions', 'highlighted_texts', 'refactored_response',
                'session_metadata',
                'created_at', 'updated_at',
                'user_name', 'user_email', 'user_role',
                'child_name', 'child_age', 'child_gender', 'child_characteristics', 'parenting_style'
            ]
            
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)
            
            print(f"📁 Created empty CSV with headers: {output_file}")
            return True
        
        # Run the main query
        print("📊 Executing main query...")
        
        query = """
        SELECT 
            ms.id,
            ms.user_id,
            ms.child_id,
            ms.scenario_index,
            ms.attempt_number,
            ms.version_number,
            ms.scenario_prompt,
            ms.original_response,
            ms.initial_decision,
            ms.is_final_version,
            ms.strategies::text,
            ms.custom_instructions::text,
            ms.highlighted_texts::text,
            ms.refactored_response,
            ms.session_metadata::text,
            ms.created_at,
            ms.updated_at,
            u.name as user_name,
            u.email as user_email,
            u.role as user_role,
            cp.name as child_name,
            cp.child_age,
            cp.child_gender,
            cp.child_characteristics,
            cp.parenting_style
        FROM moderation_session ms
            LEFT JOIN "user" u ON ms.user_id = u.id
            LEFT JOIN child_profile cp ON ms.child_id = cp.id
        ORDER BY 
            ms.user_id,
            ms.child_id,
            ms.scenario_index,
            ms.attempt_number,
            ms.version_number;
        """
        
        with conn.cursor() as cur:
            cur.execute(query)
            
            # Get column names
            column_names = [desc[0] for desc in cur.description]
            
            # Write to CSV
            print("📝 Writing data to CSV...")
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(column_names)
                
                # Fetch and write data in batches
                batch_size = 1000
                total_rows = 0
                
                while True:
                    rows = cur.fetchmany(batch_size)
                    if not rows:
                        break
                    
                    writer.writerows(rows)
                    total_rows += len(rows)
                    print(f"📊 Processed {total_rows} rows...")
        
        print(f"✅ Export completed: {output_file}")
        print(f"📊 Total rows exported: {total_rows}")
        return True
        
    except Exception as e:
        print(f"❌ Error during export: {e}", file=sys.stderr)
        return False
    finally:
        conn.close()

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 export_moderation_direct.py <app_name> <output_file>")
        sys.exit(1)
    
    app_name = sys.argv[1]
    output_file = sys.argv[2]
    
    print(f"🚀 Starting direct database export for app: {app_name}")
    print(f"📁 Output file: {output_file}")
    
    # Check if Heroku CLI is available
    try:
        subprocess.run(['heroku', '--version'], capture_output=True, check=True)
        print("✅ Heroku CLI available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Heroku CLI not found. Please install it first.")
        sys.exit(1)
    
    # Check if user is logged in
    try:
        subprocess.run(['heroku', 'auth:whoami'], capture_output=True, check=True)
        print("✅ Heroku authentication confirmed")
    except subprocess.CalledProcessError:
        print("❌ Not logged into Heroku CLI. Please run: heroku login")
        sys.exit(1)
    
    # Run the export
    if export_moderation_data(app_name, output_file):
        print("🎉 Export completed successfully!")
        
        # Show file info
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            with open(output_file, 'r', encoding='utf-8') as f:
                line_count = sum(1 for line in f)
            
            print(f"📁 File: {output_file}")
            print(f"📊 Size: {file_size:,} bytes")
            print(f"📈 Records: {line_count - 1} (excluding header)")
            
            # Show preview
            print("\n📋 Preview (first 3 lines):")
            print("----------------------------------------")
            with open(output_file, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if i >= 3:
                        break
                    print(line.strip())
            print("----------------------------------------")
    else:
        print("❌ Export failed")
        sys.exit(1)

if __name__ == "__main__":
    main()

