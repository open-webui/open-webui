#!/bin/bash
# Docker Alembic Migration Cleanup Script for mAI
# This script fixes Alembic migration issues within the Docker container

set -e

echo "🔧 mAI Docker Alembic Migration Cleanup"
echo "========================================"

# Function to run cleanup inside Docker container
run_docker_cleanup() {
    echo "🐳 Running Alembic cleanup inside Docker container..."
    
    # Create a temporary Python script inside the container
    docker exec open-webui-customization /bin/bash -c "cat > /tmp/fix_alembic.py << 'EOF'
#!/usr/bin/env python3
import sqlite3
import os
import sys
from pathlib import Path

def fix_alembic_migration():
    db_path = '/app/backend/data/webui.db'
    
    print(f'📂 Checking database at: {db_path}')
    
    if not os.path.exists(db_path):
        print('❌ Database not found')
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current alembic version
        cursor.execute('''
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='alembic_version'
        ''')
        
        if not cursor.fetchone():
            print('📋 No alembic_version table found')
            conn.close()
            return True
            
        cursor.execute('SELECT version_num FROM alembic_version')
        result = cursor.fetchone()
        
        if result:
            current_revision = result[0]
            print(f'📍 Current revision: {current_revision}')
            
            # Check if this is the problematic revision
            if current_revision == 'e41f3b2a9d75':
                print('⚠️  Found problematic revision, fixing...')
                
                # Find the latest available migration
                migrations_dir = Path('/app/backend/open_webui/migrations/versions')
                migration_files = []
                
                for file_path in migrations_dir.glob('*.py'):
                    if file_path.name != '__init__.py':
                        filename = file_path.name
                        if '_' in filename:
                            revision_id = filename.split('_', 1)[0]
                            migration_files.append((revision_id, filename))
                
                if migration_files:
                    # Sort and get the latest
                    migration_files.sort(key=lambda x: x[1])
                    latest_revision = migration_files[-1][0]
                    
                    print(f'🎯 Setting revision to: {latest_revision}')
                    
                    # Update the alembic version
                    cursor.execute('DELETE FROM alembic_version')
                    cursor.execute('INSERT INTO alembic_version (version_num) VALUES (?)', 
                                   (latest_revision,))
                    conn.commit()
                    
                    print('✅ Migration state fixed')
                else:
                    print('❌ No migration files found')
                    return False
            else:
                print('✅ No problematic revision detected')
        else:
            print('📋 No revision found in alembic_version table')
            
        conn.close()
        return True
        
    except Exception as e:
        print(f'❌ Error: {e}')
        return False

if __name__ == '__main__':
    success = fix_alembic_migration()
    sys.exit(0 if success else 1)
EOF"
    
    # Run the fix script inside the container
    docker exec open-webui-customization python3 /tmp/fix_alembic.py
    
    # Clean up the temporary script
    docker exec open-webui-customization rm -f /tmp/fix_alembic.py
    
    echo "✅ Docker cleanup completed"
}

# Function to backup database before cleanup
backup_database() {
    echo "💾 Creating database backup..."
    
    timestamp=$(date +%Y%m%d_%H%M%S)
    backup_name="webui_backup_${timestamp}.db"
    
    # Create backup using docker cp
    docker cp open-webui-customization:/app/backend/data/webui.db "./${backup_name}" 2>/dev/null || {
        echo "⚠️  Could not create backup (container might not be running)"
        return 1
    }
    
    echo "📁 Backup created: ${backup_name}"
    return 0
}

# Main execution
main() {
    # Check if container is running
    if ! docker ps | grep -q "open-webui-customization"; then
        echo "❌ Container 'open-webui-customization' is not running"
        echo "💡 Start the container first with: docker-compose -f docker-compose-customization.yaml up -d"
        exit 1
    fi
    
    echo "🔍 Container is running, proceeding with cleanup..."
    
    # Create backup
    backup_database || echo "⚠️  Continuing without backup..."
    
    # Run the cleanup
    run_docker_cleanup
    
    echo ""
    echo "🎉 Cleanup completed!"
    echo "🚀 Try restarting the container: docker-compose -f docker-compose-customization.yaml restart"
}

# Help function
show_help() {
    cat << EOF
Docker Alembic Migration Cleanup Script for mAI

This script fixes Alembic migration issues within the Docker container.
It specifically addresses the "Can't locate revision identified by 'e41f3b2a9d75'" error.

Usage:
    ./docker-alembic-fix.sh [OPTION]

Options:
    -h, --help     Show this help message
    
Prerequisites:
    - Docker container 'open-webui-customization' must be running
    - Run from the mAI project root directory

Example:
    # Start the container (if not running)
    docker-compose -f docker-compose-customization.yaml up -d
    
    # Run the fix
    ./docker-alembic-fix.sh
    
    # Restart the container
    docker-compose -f docker-compose-customization.yaml restart

EOF
}

# Parse command line arguments
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    *)
        main
        ;;
esac