"""
Main entry point for Market Worker Service
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "apps"))

from libs.core.config import get_settings
from libs.core.logging import setup_logging, get_logger

logger = get_logger(__name__)


async def main():
    """Main entry point"""
    # Setup logging
    setup_logging("market_worker")
    
    settings = get_settings()
    logger.info("Starting Market Worker Service", port=settings.market_worker_port)
    
    # Import and start market service
    from market_worker.market_service import MarketService
    from market_worker.api import create_app
    
    # Create market service
    market_service = MarketService()
    
    # Initialize market service
    await market_service.initialize()
    
    # Create FastAPI app
    app = create_app(market_service)
    
    # Start market data collection
    asyncio.create_task(market_service.start_data_collection())
    
    # Start FastAPI server
    import uvicorn
    
    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=settings.market_worker_port,
        log_config=None
    )
    server = uvicorn.Server(config)
    
    try:
        await server.serve()
    except KeyboardInterrupt:
        logger.info("Shutting down Market Worker Service")
    finally:
        await market_service.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

