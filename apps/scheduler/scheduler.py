"""
Scheduler Service Implementation
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import httpx

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from libs.core.config import get_settings
from libs.core.logging import get_logger

logger = get_logger(__name__)


class SchedulerService:
    """Main scheduler service for managing automated tasks"""
    
    def __init__(self):
        self.settings = get_settings()
        self.scheduler = AsyncIOScheduler()
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.running = False
        
    async def start(self) -> None:
        """Start the scheduler service"""
        try:
            logger.info("Starting scheduler service")
            
            # Setup default scheduled jobs
            await self._setup_default_jobs()
            
            # Start the scheduler
            self.scheduler.start()
            self.running = True
            
            logger.info("Scheduler service started successfully")
            
        except Exception as e:
            logger.error("Failed to start scheduler service", error=str(e))
            raise
    
    async def stop(self) -> None:
        """Stop the scheduler service"""
        try:
            logger.info("Stopping scheduler service")
            
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
            
            await self.http_client.aclose()
            self.running = False
            
            logger.info("Scheduler service stopped")
            
        except Exception as e:
            logger.error("Error stopping scheduler service", error=str(e))
    
    async def _setup_default_jobs(self) -> None:
        """Setup default scheduled jobs"""
        
        # Daily system health report at 8:00 AM
        self.scheduler.add_job(
            self._send_daily_health_report,
            CronTrigger(hour=8, minute=0),
            id="daily_health_report",
            name="Daily Health Report",
            replace_existing=True
        )
        
        # Daily trade report at 7:00 PM
        self.scheduler.add_job(
            self._send_daily_trade_report,
            CronTrigger(hour=19, minute=0),
            id="daily_trade_report",
            name="Daily Trade Report",
            replace_existing=True
        )
        
        # System maintenance at 3:00 AM
        self.scheduler.add_job(
            self._run_system_maintenance,
            CronTrigger(hour=3, minute=0),
            id="system_maintenance",
            name="System Maintenance",
            replace_existing=True
        )
        
        # Health check every 15 minutes
        self.scheduler.add_job(
            self._run_health_check,
            IntervalTrigger(minutes=15),
            id="health_check",
            name="Health Check",
            replace_existing=True
        )
        
        # Market data cleanup daily at 2:00 AM
        self.scheduler.add_job(
            self._cleanup_old_data,
            CronTrigger(hour=2, minute=0),
            id="data_cleanup",
            name="Data Cleanup",
            replace_existing=True
        )
        
        # Reset daily trading limits at midnight
        self.scheduler.add_job(
            self._reset_daily_limits,
            CronTrigger(hour=0, minute=0),
            id="reset_daily_limits",
            name="Reset Daily Limits",
            replace_existing=True
        )
        
        logger.info("Default scheduled jobs configured")
    
    async def _send_daily_health_report(self) -> None:
        """Send daily health report via Telegram"""
        try:
            logger.info("Generating daily health report")
            
            # Collect system metrics
            health_data = await self._collect_health_metrics()
            
            # Format report message
            report = self._format_health_report(health_data)
            
            # Send via Telegram bot
            await self._send_telegram_message(report, "Markdown")
            
            logger.info("Daily health report sent successfully")
            
        except Exception as e:
            logger.error("Failed to send daily health report", error=str(e))
    
    async def _send_daily_trade_report(self) -> None:
        """Send daily trade report via Telegram"""
        try:
            logger.info("Generating daily trade report")
            
            # Get trading data from finance worker
            trade_data = await self._get_daily_trade_data()
            
            # Format report message
            report = self._format_trade_report(trade_data)
            
            # Send via Telegram bot
            await self._send_telegram_message(report, "Markdown")
            
            logger.info("Daily trade report sent successfully")
            
        except Exception as e:
            logger.error("Failed to send daily trade report", error=str(e))
    
    async def _run_system_maintenance(self) -> None:
        """Run system maintenance tasks"""
        try:
            logger.info("Running system maintenance")
            
            # Update system packages
            await self._run_system_updates()
            
            # Clean up log files
            await self._cleanup_logs()
            
            # Backup database
            await self._backup_database()
            
            # Check disk space
            await self._check_disk_space()
            
            logger.info("System maintenance completed")
            
        except Exception as e:
            logger.error("System maintenance failed", error=str(e))
    
    async def _run_health_check(self) -> None:
        """Run health check and send alerts if needed"""
        try:
            # Get health metrics
            health_data = await self._collect_health_metrics()
            
            # Check for issues and send alerts
            await self._check_health_thresholds(health_data)
            
        except Exception as e:
            logger.error("Health check failed", error=str(e))
    
    async def _cleanup_old_data(self) -> None:
        """Clean up old market data and logs"""
        try:
            logger.info("Cleaning up old data")
            
            # Call finance worker to cleanup old data
            response = await self.http_client.post(
                f"http://127.0.0.1:{self.settings.finance_worker_port}/cleanup",
                headers={"Authorization": f"Bearer {self.settings.api_token}"},
                json={"days_to_keep": 30}
            )
            
            if response.status_code == 200:
                logger.info("Old data cleanup completed")
            else:
                logger.warning("Data cleanup request failed", status_code=response.status_code)
                
        except Exception as e:
            logger.error("Data cleanup failed", error=str(e))
    
    async def _reset_daily_limits(self) -> None:
        """Reset daily trading limits"""
        try:
            logger.info("Resetting daily trading limits")
            
            # Call execution worker to reset limits
            response = await self.http_client.post(
                f"http://127.0.0.1:{self.settings.execution_worker_port}/reset_daily_limits",
                headers={"Authorization": f"Bearer {self.settings.api_token}"}
            )
            
            if response.status_code == 200:
                logger.info("Daily limits reset successfully")
            else:
                logger.warning("Failed to reset daily limits", status_code=response.status_code)
                
        except Exception as e:
            logger.error("Failed to reset daily limits", error=str(e))
    
    async def _collect_health_metrics(self) -> Dict[str, Any]:
        """Collect system health metrics"""
        health_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "services": {},
            "system": {}
        }
        
        # Check service health
        services = [
            ("bot_gateway", self.settings.bot_gateway_port),
            ("finance_worker", self.settings.finance_worker_port),
            ("market_worker", self.settings.market_worker_port),
            ("execution_worker", self.settings.execution_worker_port)
        ]
        
        for service_name, port in services:
            try:
                response = await self.http_client.get(
                    f"http://127.0.0.1:{port}/health",
                    timeout=5.0
                )
                health_data["services"][service_name] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time": response.elapsed.total_seconds()
                }
            except Exception as e:
                health_data["services"][service_name] = {
                    "status": "unreachable",
                    "error": str(e)
                }
        
        return health_data
    
    async def _get_daily_trade_data(self) -> Dict[str, Any]:
        """Get daily trading data from finance worker"""
        try:
            response = await self.http_client.get(
                f"http://127.0.0.1:{self.settings.finance_worker_port}/daily-stats",
                headers={"Authorization": f"Bearer {self.settings.api_token}"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning("Failed to get daily trade data", status_code=response.status_code)
                return {}
                
        except Exception as e:
            logger.error("Error getting daily trade data", error=str(e))
            return {}
    
    def _format_health_report(self, health_data: Dict[str, Any]) -> str:
        """Format health report message"""
        report = f"🌅 *Daily Health Report - {datetime.now().strftime('%Y-%m-%d')}*\n\n"
        
        # Service status
        report += "🔧 *Services Status:*\n"
        for service, data in health_data.get("services", {}).items():
            status_emoji = "🟢" if data["status"] == "healthy" else "🔴"
            report += f"• {service}: {status_emoji} {data['status']}\n"
        
        report += f"\n⏰ *Generated at:* {datetime.now().strftime('%H:%M:%S')}"
        
        return report
    
    def _format_trade_report(self, trade_data: Dict[str, Any]) -> str:
        """Format trade report message"""
        report = f"📊 *Daily Trade Report - {datetime.now().strftime('%Y-%m-%d')}*\n\n"
        
        if trade_data:
            total_trades = trade_data.get("total_trades", 0)
            winning_trades = trade_data.get("winning_trades", 0)
            total_pnl = trade_data.get("total_pnl", 0.0)
            
            report += f"💹 *Trading Summary:*\n"
            report += f"• Total Trades: {total_trades}\n"
            report += f"• Winning Trades: {winning_trades}\n"
            report += f"• Win Rate: {(winning_trades/total_trades*100):.1f}% " if total_trades > 0 else "• Win Rate: N/A "
            report += f"\n• Total P&L: {'🟢' if total_pnl >= 0 else '🔴'} ${total_pnl:.2f}\n"
        else:
            report += "💹 *Trading Summary:*\n• No trading data available\n"
        
        report += f"\n⏰ *Generated at:* {datetime.now().strftime('%H:%M:%S')}"
        
        return report
    
    async def _send_telegram_message(self, message: str, parse_mode: str = None) -> None:
        """Send message via Telegram bot"""
        try:
            response = await self.http_client.post(
                f"http://127.0.0.1:{self.settings.bot_gateway_port}/message",
                headers={"Authorization": f"Bearer {self.settings.api_token}"},
                json={
                    "message": message,
                    "parse_mode": parse_mode
                }
            )
            
            if response.status_code != 200:
                logger.warning("Failed to send Telegram message", status_code=response.status_code)
                
        except Exception as e:
            logger.error("Error sending Telegram message", error=str(e))
    
    async def _run_system_updates(self) -> None:
        """Run system updates"""
        # This would typically run the system-update.sh script
        logger.info("System updates would run here (placeholder)")
    
    async def _cleanup_logs(self) -> None:
        """Clean up old log files"""
        logger.info("Log cleanup would run here (placeholder)")
    
    async def _backup_database(self) -> None:
        """Backup database"""
        logger.info("Database backup would run here (placeholder)")
    
    async def _check_disk_space(self) -> None:
        """Check disk space and alert if low"""
        logger.info("Disk space check would run here (placeholder)")
    
    async def _check_health_thresholds(self, health_data: Dict[str, Any]) -> None:
        """Check health thresholds and send alerts"""
        # Check for unhealthy services
        unhealthy_services = [
            service for service, data in health_data.get("services", {}).items()
            if data["status"] != "healthy"
        ]
        
        if unhealthy_services:
            alert_message = f"🚨 *Service Alert*\n\nThe following services are unhealthy:\n"
            for service in unhealthy_services:
                alert_message += f"• {service}\n"
            
            await self._send_telegram_message(alert_message, "Markdown")
    
    # Public API methods for external job management
    
    def add_job(self, func, trigger, job_id: str, **kwargs) -> None:
        """Add a new scheduled job"""
        self.scheduler.add_job(func, trigger, id=job_id, replace_existing=True, **kwargs)
        logger.info("Job added", job_id=job_id)
    
    def remove_job(self, job_id: str) -> None:
        """Remove a scheduled job"""
        try:
            self.scheduler.remove_job(job_id)
            logger.info("Job removed", job_id=job_id)
        except Exception as e:
            logger.error("Failed to remove job", job_id=job_id, error=str(e))
    
    def get_jobs(self) -> List[Dict[str, Any]]:
        """Get list of all scheduled jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        return jobs
    
    def pause_job(self, job_id: str) -> None:
        """Pause a scheduled job"""
        try:
            self.scheduler.pause_job(job_id)
            logger.info("Job paused", job_id=job_id)
        except Exception as e:
            logger.error("Failed to pause job", job_id=job_id, error=str(e))
    
    def resume_job(self, job_id: str) -> None:
        """Resume a paused job"""
        try:
            self.scheduler.resume_job(job_id)
            logger.info("Job resumed", job_id=job_id)
        except Exception as e:
            logger.error("Failed to resume job", job_id=job_id, error=str(e))

