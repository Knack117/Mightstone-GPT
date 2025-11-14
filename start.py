#!/usr/bin/env python3
"""
Startup script for Mightstone GPT Webservice
"""

import asyncio
import sys
import uvicorn

from app.main import app


async def main():
    """Main startup function."""
    print("🚀 Starting Mightstone GPT Webservice v2.0")
    print("📡 API will be available at http://localhost:8080")
    print("📚 Documentation at http://localhost:8080/docs")
    print("=" * 50)
    
    try:
        # Run with uvicorn
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=8080,
            log_level="info",
            access_log=True
        )
        server = uvicorn.Server(config)
        await server.serve()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Mightstone GPT Webservice")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())