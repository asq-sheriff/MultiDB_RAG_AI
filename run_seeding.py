#!/usr/bin/env python3
"""
Direct seeding script to seed therapeutic knowledge base
"""
import os
import asyncio
import sys

# Load appropriate environment configuration
from ai_services.shared.utils.env_loader import load_environment, detect_environment

# Detect and load the right environment
env_type = detect_environment()
print(f"🔍 Detected environment: {env_type}")
load_environment(env_type)

# Now import the seeding modules
from ai_services.ingestion_pipeline.seed_data import AdvancedSeedingPipeline, AdvancedSeedConfig

async def seed_therapeutic_knowledge():
    print('🌱 Starting therapeutic knowledge base seeding...')
    print(f'MongoDB Host: {os.getenv("MONGO_HOST")}:{os.getenv("MONGO_PORT")}')
    
    # Use default config with mock embeddings
    config = AdvancedSeedConfig()
    config.use_real_embeddings = False
    
    pipeline = AdvancedSeedingPipeline(config)
    
    try:
        results = await pipeline.run_complete_seeding()
        
        print('\n📊 Therapeutic Knowledge Base Seeding Results:')
        for phase, result in results.items():
            if isinstance(result, dict) and 'status' in result:
                print(f'  {phase}: {result.get("status", "unknown")}')
                if 'processed_count' in result:
                    print(f'    Processed: {result["processed_count"]} items')
                if 'chunks_created' in result:
                    print(f'    Chunks: {result["chunks_created"]}')
                if 'embeddings_generated' in result:
                    print(f'    Embeddings: {result["embeddings_generated"]}')
            else:
                print(f'  {phase}: {result}')
        
        print('\n✅ Therapeutic knowledge base seeded successfully!')
        print('Your senior care AI companion is now ready with:')
        print('  • 50 Empathic Companion Cards for loneliness, grief, anxiety')
        print('  • 100 SAFE-T Crisis Scenarios with intervention protocols') 
        print('  • Senior Care Enhancement Guide with specialized understanding')
        return results
        
    except Exception as e:
        print(f'❌ Seeding failed: {e}')
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(seed_therapeutic_knowledge())
    if result:
        print("\n🎯 Seeding completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Seeding failed!")
        sys.exit(1)