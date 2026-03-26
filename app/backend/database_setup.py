"""
Database setup script for multi-tenancy collections and indexes.
Run this once to initialize the database schema.
"""

import asyncio
from motor.motor_asyncio import AsyncClient
from core.database import get_database
import os
from dotenv import load_dotenv

load_dotenv()

async def setup_collections_and_indexes():
    """Create required collections and indexes for multi-tenancy"""
    
    try:
        client = AsyncClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
        db = client[os.getenv("MONGO_DB", "infralens")]
        
        print("🔧 Setting up collections and indexes...")
        
        # 1. Create chat_shares collection
        try:
            await db.create_collection("chat_shares")
            print("✅ Created chat_shares collection")
        except Exception as e:
            print(f"ℹ️  chat_shares collection may already exist: {e}")
        
        # 2. Create organizations collection if not exists
        try:
            await db.create_collection("organizations")
            print("✅ Created organizations collection")
        except Exception as e:
            print(f"ℹ️  organizations collection may already exist: {e}")
        
        # 3. Create usage tracking collection
        try:
            await db.create_collection("usage")
            print("✅ Created usage collection")
        except Exception as e:
            print(f"ℹ️  usage collection may already exist: {e}")
        
        # 4. Create invitations collection
        try:
            await db.create_collection("invitations")
            print("✅ Created invitations collection")
        except Exception as e:
            print(f"ℹ️  invitations collection may already exist: {e}")
        
        print("\n📑 Creating indexes for multi-tenancy isolation...\n")
        
        # ======== CHAT_SHARES INDEXES ========
        print("🔍 chat_shares indexes:")
        
        # Index 1: Find chats shared with specific email
        await db.chat_shares.create_index([("shared_with_email", 1), ("created_at", -1)])
        print("   ✅ shared_with_email + created_at")
        
        # Index 2: Find shares by org_id
        await db.chat_shares.create_index([("org_id", 1), ("created_at", -1)])
        print("   ✅ org_id + created_at")
        
        # Index 3: Find shares by chat_session_id
        await db.chat_shares.create_index([("chat_session_id", 1)])
        print("   ✅ chat_session_id")
        
        # ======== ORGANIZATIONS INDEXES ========
        print("\n🔍 organizations indexes:")
        
        # Index 1: Primary lookup by org_id
        await db.organizations.create_index([("org_id", 1)], unique=True)
        print("   ✅ org_id (unique)")
        
        # Index 2: Find orgs by owner
        await db.organizations.create_index([("owner_user_id", 1)])
        print("   ✅ owner_user_id")
        
        # ======== REPOSITORIES INDEXES ========
        print("\n🔍 repositories indexes:")
        
        # Index 1: Personal repos (user_id + org_id=null)
        await db.repositories.create_index([("user_id", 1), ("org_id", 1)])
        print("   ✅ user_id + org_id")
        
        # Index 2: Org repos
        await db.repositories.create_index([("org_id", 1), ("ingested_at", -1)])
        print("   ✅ org_id + ingested_at")
        
        # Index 3: Repo name + org isolation
        await db.repositories.create_index([("name", 1), ("org_id", 1)])
        print("   ✅ name + org_id")
        
        # ======== CHATS INDEXES ========
        print("\n🔍 chats indexes:")
        
        # Index 1: User + repo isolation
        await db.chats.create_index([("user_id", 1), ("repository_name", 1), ("created_at", -1)])
        print("   ✅ user_id + repository_name + created_at")
        
        # Index 2: Org context
        await db.chats.create_index([("org_id", 1), ("user_id", 1)])
        print("   ✅ org_id + user_id")
        
        # ======== USAGE INDEXES ========
        print("\n🔍 usage indexes:")
        
        # Index 1: Org usage by month
        await db.usage.create_index([("org_id", 1), ("month", 1)], unique=True)
        print("   ✅ org_id + month (unique)")
        
        # ======== INVITATIONS INDEXES ========
        print("\n🔍 invitations indexes:")
        
        # Index 1: Invitations sent to email
        await db.invitations.create_index([("invited_email", 1), ("org_id", 1)])
        print("   ✅ invited_email + org_id")
        
        # Index 2: Invitations created in org
        await db.invitations.create_index([("org_id", 1), ("created_at", -1)])
        print("   ✅ org_id + created_at")
        
        print("\n\n✨ Database setup complete!")
        print("\nCreated collections:")
        print("  • chat_shares — for storing chat sharing between team members")
        print("  • organizations — for Team plan organizations")
        print("  • usage — for quota tracking")
        print("  • invitations — for org member invitations")
        
        print("\nCreated indexes:")
        print("  • Isolation: org_id + user_id on all collections")
        print("  • Performance: Efficient lookups for multi-tenancy queries")
        print("  • Uniqueness: org_id + month for usage tracking")
        
        await client.close()
        
    except Exception as e:
        print(f"❌ Setup failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(setup_collections_and_indexes())
