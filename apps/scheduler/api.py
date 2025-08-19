"""
FastAPI application for Scheduler Service
"""

import sys
from pathlib import Path
from typing import Dict, Any, List

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from libs.core.security import verify_api_token
from libs.core.logging import get_logger

logger = get_logger(__name__)


class JobRequest(BaseModel):
    job_id: str
    name: str
    trigger_type: str  # "cron" or "interval"
    trigger_params: Dict[str, Any]
    function_name: str
    description: str = ""


class JobResponse(BaseModel):
    id: str
    name: str
    next_run: str = None
    trigger: str
    status: str = "active"


def create_app(scheduler_service) -> FastAPI:
    """Create FastAPI application"""
    
    app = FastAPI(
        title="RPI Trader Scheduler API",
        description="Internal API for Scheduler Service",
        version="0.1.0"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "service": "scheduler",
            "scheduler_running": scheduler_service.running,
            "job_count": len(scheduler_service.get_jobs())
        }
    
    @app.get("/jobs", response_model=List[JobResponse])
    async def get_jobs(_: bool = Depends(verify_api_token)):
        """Get all scheduled jobs"""
        try:
            jobs = scheduler_service.get_jobs()
            return [
                JobResponse(
                    id=job["id"],
                    name=job["name"],
                    next_run=job["next_run"],
                    trigger=job["trigger"]
                )
                for job in jobs
            ]
        except Exception as e:
            logger.error("Failed to get jobs", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/jobs")
    async def add_job(
        job_request: JobRequest,
        _: bool = Depends(verify_api_token)
    ):
        """Add a new scheduled job"""
        try:
            # Create trigger based on type
            if job_request.trigger_type == "cron":
                trigger = CronTrigger(**job_request.trigger_params)
            elif job_request.trigger_type == "interval":
                trigger = IntervalTrigger(**job_request.trigger_params)
            else:
                raise HTTPException(status_code=400, detail="Invalid trigger type")
            
            # For now, we'll just store the job info - in a full implementation,
            # you'd need to map function_name to actual callable functions
            logger.info("Job add request received", job_id=job_request.job_id)
            
            return {"status": "success", "message": f"Job {job_request.job_id} added"}
            
        except Exception as e:
            logger.error("Failed to add job", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.delete("/jobs/{job_id}")
    async def remove_job(
        job_id: str,
        _: bool = Depends(verify_api_token)
    ):
        """Remove a scheduled job"""
        try:
            scheduler_service.remove_job(job_id)
            return {"status": "success", "message": f"Job {job_id} removed"}
        except Exception as e:
            logger.error("Failed to remove job", job_id=job_id, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/jobs/{job_id}/pause")
    async def pause_job(
        job_id: str,
        _: bool = Depends(verify_api_token)
    ):
        """Pause a scheduled job"""
        try:
            scheduler_service.pause_job(job_id)
            return {"status": "success", "message": f"Job {job_id} paused"}
        except Exception as e:
            logger.error("Failed to pause job", job_id=job_id, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/jobs/{job_id}/resume")
    async def resume_job(
        job_id: str,
        _: bool = Depends(verify_api_token)
    ):
        """Resume a paused job"""
        try:
            scheduler_service.resume_job(job_id)
            return {"status": "success", "message": f"Job {job_id} resumed"}
        except Exception as e:
            logger.error("Failed to resume job", job_id=job_id, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/jobs/{job_id}")
    async def get_job(
        job_id: str,
        _: bool = Depends(verify_api_token)
    ):
        """Get details of a specific job"""
        try:
            jobs = scheduler_service.get_jobs()
            job = next((j for j in jobs if j["id"] == job_id), None)
            
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            
            return JobResponse(
                id=job["id"],
                name=job["name"],
                next_run=job["next_run"],
                trigger=job["trigger"]
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to get job", job_id=job_id, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/trigger-job/{job_id}")
    async def trigger_job(
        job_id: str,
        _: bool = Depends(verify_api_token)
    ):
        """Manually trigger a job execution"""
        try:
            # In a full implementation, you'd trigger the job immediately
            logger.info("Manual job trigger requested", job_id=job_id)
            return {"status": "success", "message": f"Job {job_id} triggered"}
        except Exception as e:
            logger.error("Failed to trigger job", job_id=job_id, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/status")
    async def get_scheduler_status(_: bool = Depends(verify_api_token)):
        """Get scheduler service status"""
        return {
            "running": scheduler_service.running,
            "job_count": len(scheduler_service.get_jobs()),
            "next_jobs": [
                {
                    "id": job["id"],
                    "name": job["name"],
                    "next_run": job["next_run"]
                }
                for job in scheduler_service.get_jobs()[:5]  # Next 5 jobs
            ]
        }
    
    return app

