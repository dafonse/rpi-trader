"""
Main entry point for Execution Worker Service
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
    setup_logging("execution_worker")
    
    settings = get_settings()
    logger.info("Starting Execution Worker Service", port=settings.execution_worker_port)
    
    # Import and start execution service
    from apps.execution_worker.execution_service import ExecutionService
    from apps.execution_worker.api import create_app
    
    # Create execution service
    execution_service = ExecutionService()
    
    # Initialize execution service
    await execution_service.initialize()
    
    # Create FastAPI app
    app = create_app(execution_service)
    
    # Start FastAPI server
    import uvicorn
    
    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=settings.execution_worker_port,
        log_config=None
    )
    server = uvicorn.Server(config)
    
    try:
        await server.serve()
    except KeyboardInterrupt:
        logger.info("Shutting down Execution Worker Service")
    finally:
        await execution_service.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

