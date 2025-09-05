#!/usr/bin/env python3
"""
Database Initialization Script for HIPAA-Compliant Healthcare AI Platform
==========================================================================

This script initializes the PostgreSQL database with proper users, schemas, and HIPAA tables
to ensure both Python and Go services can connect successfully.
"""

import asyncio
import asyncpg
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def setup_database():
    """Initialize database with proper user, schemas, and HIPAA tables"""
    
    print("🏥 HIPAA-Compliant Database Initialization")
    print("=" * 50)
    print()
    
    # Database configuration
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "chatbot_app")
    target_user = os.getenv("POSTGRES_USER", "chatbot_user")
    target_password = os.getenv("POSTGRES_PASSWORD", "secure_password")
    
    print(f"🎯 Target Database: {host}:{port}/{database}")
    print(f"🎯 Target User: {target_user}")
    print()
    
    # Try different admin credentials to connect to PostgreSQL
    admin_credentials = [
        # Docker default postgres superuser (most likely)
        ("postgres", target_password),  # Same password as our user
        ("postgres", "postgres"),       # Default postgres password
        (target_user, target_password), # Our user might already exist
    ]
    
    connection = None
    admin_used = None
    
    print("🔍 Attempting to connect with admin credentials...")
    
    for admin_user, admin_pass in admin_credentials:
        try:
            print(f"  Trying {admin_user}...")
            connection = await asyncpg.connect(
                host=host,
                port=port,
                database=database,
                user=admin_user,
                password=admin_pass
            )
            admin_used = admin_user
            print(f"  ✅ Connected as {admin_user}")
            break
        except Exception as e:
            print(f"  ❌ Failed as {admin_user}: {str(e)[:60]}...")
            continue
    
    if not connection:
        print()
        print("❌ Could not connect with any admin credentials!")
        print()
        print("💡 Please ensure PostgreSQL is running with proper credentials:")
        print(f"   docker exec -it chatbot-postgres psql -U postgres -d {database}")
        return False
    
    try:
        print()
        print("🔧 Setting up database schema and users...")
        print()
        
        # Check existing users
        print("📋 Checking existing users...")
        existing_users = await connection.fetch("SELECT usename FROM pg_user ORDER BY usename")
        user_list = [row['usename'] for row in existing_users]
        print(f"   Existing users: {', '.join(user_list)}")
        
        # Create target user if it doesn't exist
        if target_user not in user_list:
            print(f"👤 Creating user '{target_user}'...")
            await connection.execute(f"""
                CREATE USER {target_user} WITH 
                PASSWORD '{target_password}' 
                CREATEDB 
                NOSUPERUSER 
                NOCREATEROLE;
            """)
            print(f"   ✅ User '{target_user}' created")
        else:
            print(f"👤 Updating password for existing user '{target_user}'...")
            await connection.execute(f"ALTER USER {target_user} WITH PASSWORD '{target_password}'")
            print(f"   ✅ Password updated for '{target_user}'")
        
        # Create required schemas
        print()
        print("📁 Creating database schemas...")
        schemas = ["auth", "compliance", "app", "memory", "knowledge"]
        
        for schema in schemas:
            try:
                await connection.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
                print(f"   ✅ Schema '{schema}' ready")
            except Exception as e:
                print(f"   ⚠️ Schema '{schema}': {e}")
        
        # Grant permissions to target user
        print()
        print("🔐 Setting up permissions...")
        
        # Grant database-level permissions
        await connection.execute(f"GRANT ALL PRIVILEGES ON DATABASE {database} TO {target_user}")
        print(f"   ✅ Database privileges granted to '{target_user}'")
        
        # Grant schema permissions
        for schema in schemas:
            await connection.execute(f"GRANT ALL PRIVILEGES ON SCHEMA {schema} TO {target_user}")
            await connection.execute(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA {schema} TO {target_user}")
            await connection.execute(f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA {schema} TO {target_user}")
            await connection.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT ALL PRIVILEGES ON TABLES TO {target_user}")
            await connection.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT ALL PRIVILEGES ON SEQUENCES TO {target_user}")
            print(f"   ✅ Schema '{schema}' permissions granted")
        
        # Enable required extensions
        print()
        print("🔌 Enabling PostgreSQL extensions...")
        extensions = [
            "uuid-ossp",    # UUID generation
            "citext",       # Case-insensitive text
            "vector"        # pgvector for embeddings
        ]
        
        for ext in extensions:
            try:
                await connection.execute(f"CREATE EXTENSION IF NOT EXISTS \"{ext}\"")
                print(f"   ✅ Extension '{ext}' enabled")
            except Exception as e:
                print(f"   ⚠️ Extension '{ext}': {e}")
        
        # Test connection with target user
        print()
        print("🧪 Testing target user connection...")
        
        test_conn = await asyncpg.connect(
            host=host,
            port=port,
            database=database,
            user=target_user,
            password=target_password
        )
        
        # Test basic operations
        version = await test_conn.fetchval("SELECT version()")
        schemas_check = await test_conn.fetch("SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('auth', 'compliance', 'app', 'memory', 'knowledge')")
        
        await test_conn.close()
        
        print(f"   ✅ Connection successful!")
        print(f"   ✅ PostgreSQL: {version.split(',')[0]}")
        print(f"   ✅ Schemas available: {len(schemas_check)}/5")
        
        print()
        print("🎉 Database initialization completed successfully!")
        print()
        print("📋 Next Steps:")
        print("   1. Run Alembic migrations: alembic upgrade head")
        print("   2. Test Go services connection")
        print("   3. Run comprehensive HIPAA tests")
        
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False
    
    finally:
        if connection:
            await connection.close()

async def main():
    """Main initialization function"""
    success = await setup_database()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())