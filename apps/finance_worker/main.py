"""
Main entry point for Finance Worker Service
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from libs.core.config import get_settings
from libs.core.logging import setup_logging, get_logger

logger = get_logger(__name__)


async def main():
    """Main entry point"""
    # Setup logging
    setup_logging("finance_worker")
    
    settings = get_settings()
    logger.info("Starting Finance Worker Service", port=settings.finance_worker_port)
    
    # Import and start finance service
    from apps.finance_worker.finance_service import FinanceService
    from apps.finance_worker.api import create_app
    
    # Create finance service
    finance_service = FinanceService()
    
    # Initialize database
    await finance_service.initialize()
    
    # Create FastAPI app
    app = create_app(finance_service)
    
    # Start FastAPI server
    import uvicorn
    
    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=settings.finance_worker_port,
        log_config=None
    )
    server = uvicorn.Server(config)
    
    try:
        await server.serve()
    except KeyboardInterrupt:
        logger.info("Shutting down Finance Worker Service")
    finally:
        await finance_service.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

