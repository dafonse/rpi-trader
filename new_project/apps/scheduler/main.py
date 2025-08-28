"""
Main entry point for Scheduler Service
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
    setup_logging("scheduler")
    
    settings = get_settings()
    logger.info("Starting Scheduler Service", port=settings.scheduler_port)
    
    # Import and start scheduler
    from scheduler.scheduler import SchedulerService
    from scheduler.api import create_app
    
    # Create scheduler service
    scheduler_service = SchedulerService()
    
    # Create FastAPI app
    app = create_app(scheduler_service)
    
    # Start scheduler
    await scheduler_service.start()
    
    # Start FastAPI server
    import uvicorn
    
    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=settings.scheduler_port,
        log_config=None
    )
    server = uvicorn.Server(config)
    
    try:
        await server.serve()
    except KeyboardInterrupt:
        logger.info("Shutting down Scheduler Service")
    finally:
        await scheduler_service.stop()


if __name__ == "__main__":
    asyncio.run(main())

