#!/usr/bin/env python3
"""
Test script for real API mode demo
"""

import asyncio
import sys
import os

# Add the demo UI directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ui'))

async def test_demo_initialization():
    """Test demo initialization in real data mode"""
    try:
        from interactive_demo import InteractiveDemoSystem
        
        print("🧪 Testing demo initialization...")
        demo = InteractiveDemoSystem(use_real_data=True)
        
        print("🔌 Testing API client connections...")
        success = await demo.initialize_databases()
        
        if success:
            print("✅ Demo initialization successful!")
            print(f"Real data mode: {demo.use_real_data}")
            print(f"API client: {'✅ Connected' if demo.api_client else '❌ Not connected'}")
            print("🌐 Testing API Gateway endpoints...")
            
            if demo.api_client:
                async with demo.api_client as client:
                    health = await client.check_api_health()
                    print(f"API Gateway health: {'✅ Healthy' if health else '❌ Unhealthy'}")
        else:
            print("❌ Demo initialization failed")
            
        # Cleanup API client if needed
        if demo.api_client:
            try:
                await demo.api_client.__aexit__(None, None, None)
            except:
                pass  # Already cleaned up
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_demo_initialization())