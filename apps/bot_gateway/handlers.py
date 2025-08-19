"""
Telegram bot command handlers
"""

import asyncio
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta

import psutil
import httpx
from telegram import Update
from telegram.ext import ContextTypes

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from libs.core.config import get_settings
from libs.core.logging import get_logger

logger = get_logger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_instance) -> None:
    """Handle /start command"""
    welcome_message = """
🤖 *Welcome to RPI Trader Bot!*

I'm your trading assistant running on Raspberry Pi. Here's what I can do:

📊 *Trading Commands:*
• /positions - Show current positions
• /trades - Show recent trades  
• /balance - Show account balance
• /stop_trading - Emergency stop all trading
• /start_trading - Resume trading

🔧 *System Commands:*
• /status - System status overview
• /health - Detailed health metrics
• /system - System information
• /logs - Recent system logs
• /reboot - Reboot the system

Use /help anytime to see this message again.

*Status:* Online ✅
*Trading:* {'Enabled' if bot_instance.is_trading_enabled() else 'Disabled'} {'🟢' if bot_instance.is_trading_enabled() else '🔴'}
"""
    
    await update.message.reply_text(welcome_message, parse_mode="Markdown")


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_instance) -> None:
    """Handle /help command"""
    help_message = """
🆘 *RPI Trader Bot Commands*

*Trading Commands:*
/positions - Show current open positions
/trades - Show recent trade history
/balance - Show account balance and equity
/stop_trading - Emergency stop (kill switch)
/start_trading - Resume trading operations

*System Commands:*
/status - Quick system status
/health - Detailed health metrics
/system - System information (CPU, RAM, etc.)
/logs - Show recent application logs
/reboot - Reboot the Raspberry Pi

*Emergency:*
In case of emergency, use /stop_trading to immediately halt all trading operations.

*Support:*
All commands are logged for security and debugging purposes.
"""
    
    await update.message.reply_text(help_message, parse_mode="Markdown")


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_instance) -> None:
    """Handle /status command"""
    try:
        settings = get_settings()
        
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Check service status
        services_status = await _check_services_status()
        
        # Get uptime
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        
        status_message = f"""
📊 *System Status Report*

🖥️ *System:*
• CPU Usage: {cpu_percent:.1f}%
• Memory: {memory.percent:.1f}% ({memory.used // (1024**3):.1f}GB / {memory.total // (1024**3):.1f}GB)
• Disk: {disk.percent:.1f}% ({disk.used // (1024**3):.1f}GB / {disk.total // (1024**3):.1f}GB)
• Uptime: {uptime.days}d {uptime.seconds//3600}h {(uptime.seconds//60)%60}m

🔧 *Services:*
{services_status}

💹 *Trading:*
• Status: {'Enabled' if bot_instance.is_trading_enabled() else 'Disabled'} {'🟢' if bot_instance.is_trading_enabled() else '🔴'}
• Mode: {'Live Trading' if not settings.dry_run_mode else 'Dry Run'} {'💰' if not settings.dry_run_mode else '🧪'}

⏰ *Last Updated:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        await update.message.reply_text(status_message, parse_mode="Markdown")
        
    except Exception as e:
        logger.error("Error in status handler", error=str(e))
        await update.message.reply_text(f"❌ Error getting status: {str(e)}")


async def health_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_instance) -> None:
    """Handle /health command"""
    try:
        # Get detailed system health
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Get temperature (Raspberry Pi specific)
        temp = await _get_cpu_temperature()
        
        # Get network status
        network_stats = psutil.net_io_counters()
        
        # Get load average
        load_avg = psutil.getloadavg()
        
        health_message = f"""
🏥 *Detailed Health Report*

🖥️ *CPU:*
• Cores: {cpu_count}
• Frequency: {cpu_freq.current:.0f}MHz (Max: {cpu_freq.max:.0f}MHz)
• Load Average: {load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}
• Temperature: {temp}°C {'🔥' if temp > 70 else '❄️' if temp < 40 else '🌡️'}

💾 *Memory:*
• RAM: {memory.percent:.1f}% ({memory.available // (1024**3):.1f}GB available)
• Swap: {swap.percent:.1f}% ({swap.used // (1024**2):.0f}MB used)

🌐 *Network:*
• Bytes Sent: {network_stats.bytes_sent // (1024**2):.0f}MB
• Bytes Received: {network_stats.bytes_recv // (1024**2):.0f}MB

🔋 *Status:*
• Overall Health: {'🟢 Good' if temp < 70 and memory.percent < 80 and cpu_count > 0 else '🟡 Warning' if temp < 80 and memory.percent < 90 else '🔴 Critical'}

⏰ *Timestamp:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        await update.message.reply_text(health_message, parse_mode="Markdown")
        
    except Exception as e:
        logger.error("Error in health handler", error=str(e))
        await update.message.reply_text(f"❌ Error getting health info: {str(e)}")


async def positions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_instance) -> None:
    """Handle /positions command"""
    try:
        settings = get_settings()
        
        # Call finance worker to get positions
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://127.0.0.1:{settings.finance_worker_port}/positions")
            
            if response.status_code == 200:
                positions = response.json()
                
                if not positions:
                    await update.message.reply_text("📊 No open positions currently.")
                    return
                
                positions_text = "📊 *Current Positions:*\n\n"
                total_unrealized_pnl = 0
                
                for pos in positions:
                    pnl_emoji = "🟢" if pos.get('unrealized_pnl', 0) >= 0 else "🔴"
                    positions_text += f"*{pos['symbol']}*\n"
                    positions_text += f"• Quantity: {pos['quantity']}\n"
                    positions_text += f"• Avg Price: ${pos['average_price']:.4f}\n"
                    positions_text += f"• Current: ${pos.get('current_price', 0):.4f}\n"
                    positions_text += f"• P&L: {pnl_emoji} ${pos.get('unrealized_pnl', 0):.2f}\n\n"
                    
                    total_unrealized_pnl += pos.get('unrealized_pnl', 0)
                
                positions_text += f"*Total Unrealized P&L:* {'🟢' if total_unrealized_pnl >= 0 else '🔴'} ${total_unrealized_pnl:.2f}"
                
                await update.message.reply_text(positions_text, parse_mode="Markdown")
            else:
                await update.message.reply_text("❌ Unable to fetch positions. Finance worker may be offline.")
                
    except Exception as e:
        logger.error("Error in positions handler", error=str(e))
        await update.message.reply_text(f"❌ Error getting positions: {str(e)}")


async def trades_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_instance) -> None:
    """Handle /trades command"""
    try:
        settings = get_settings()
        
        # Get limit from command args (default 10)
        limit = 10
        if context.args and len(context.args) > 0:
            try:
                limit = min(int(context.args[0]), 50)  # Max 50 trades
            except ValueError:
                pass
        
        # Call finance worker to get trades
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://127.0.0.1:{settings.finance_worker_port}/trades?limit={limit}")
            
            if response.status_code == 200:
                trades = response.json()
                
                if not trades:
                    await update.message.reply_text("📈 No recent trades found.")
                    return
                
                trades_text = f"📈 *Recent Trades (Last {len(trades)}):*\n\n"
                
                for trade in trades:
                    status_emoji = {"FILLED": "✅", "PENDING": "⏳", "CANCELLED": "❌", "REJECTED": "🚫"}.get(trade['status'], "❓")
                    action_emoji = "🟢" if trade['action'] == 'BUY' else "🔴"
                    
                    trades_text += f"{status_emoji} *{trade['symbol']}* {action_emoji}\n"
                    trades_text += f"• Action: {trade['action']} {trade['quantity']}\n"
                    trades_text += f"• Price: ${trade.get('price', 0):.4f}\n"
                    trades_text += f"• Status: {trade['status']}\n"
                    trades_text += f"• Time: {trade['created_at'][:19]}\n"
                    
                    if trade.get('pnl'):
                        pnl_emoji = "🟢" if float(trade['pnl']) >= 0 else "🔴"
                        trades_text += f"• P&L: {pnl_emoji} ${trade['pnl']}\n"
                    
                    trades_text += "\n"
                
                await update.message.reply_text(trades_text, parse_mode="Markdown")
            else:
                await update.message.reply_text("❌ Unable to fetch trades. Finance worker may be offline.")
                
    except Exception as e:
        logger.error("Error in trades handler", error=str(e))
        await update.message.reply_text(f"❌ Error getting trades: {str(e)}")


async def balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_instance) -> None:
    """Handle /balance command"""
    try:
        settings = get_settings()
        
        # Call finance worker to get account info
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://127.0.0.1:{settings.finance_worker_port}/account")
            
            if response.status_code == 200:
                account = response.json()
                
                balance_text = f"""
💰 *Account Balance*

💵 *Balance:* ${account.get('balance', 0):.2f}
📊 *Equity:* ${account.get('equity', 0):.2f}
📈 *Free Margin:* ${account.get('free_margin', 0):.2f}
⚖️ *Used Margin:* ${account.get('margin', 0):.2f}
🏦 *Currency:* {account.get('currency', 'USD')}
📊 *Leverage:* 1:{account.get('leverage', 1)}

*Account:* {account.get('login', 'N/A')}
*Server:* {account.get('server', 'N/A')}

⏰ *Updated:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
                
                await update.message.reply_text(balance_text, parse_mode="Markdown")
            else:
                await update.message.reply_text("❌ Unable to fetch account balance. Finance worker may be offline.")
                
    except Exception as e:
        logger.error("Error in balance handler", error=str(e))
        await update.message.reply_text(f"❌ Error getting balance: {str(e)}")


async def system_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_instance) -> None:
    """Handle /system command"""
    try:
        # Get system information
        uname = psutil.uname()
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        
        system_text = f"""
🖥️ *System Information*

*Hardware:*
• System: {uname.system}
• Machine: {uname.machine}
• Processor: {uname.processor}

*Software:*
• OS: {uname.system} {uname.release}
• Version: {uname.version}
• Python: {sys.version.split()[0]}

*Runtime:*
• Boot Time: {boot_time.strftime('%Y-%m-%d %H:%M:%S')}
• Timezone: {datetime.now().astimezone().tzinfo}

*Network:*
• Hostname: {uname.node}
"""
        
        await update.message.reply_text(system_text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error("Error in system info handler", error=str(e))
        await update.message.reply_text(f"❌ Error getting system info: {str(e)}")


async def logs_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_instance) -> None:
    """Handle /logs command"""
    try:
        # Get recent logs using journalctl
        lines = 20
        if context.args and len(context.args) > 0:
            try:
                lines = min(int(context.args[0]), 100)  # Max 100 lines
            except ValueError:
                pass
        
        # Get logs from systemd journal
        result = subprocess.run(
            ["journalctl", "-u", "rpi-trader-*", "-n", str(lines), "--no-pager"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout:
            logs_text = f"📋 *Recent Logs (Last {lines} lines):*\n\n```\n{result.stdout[-3000:]}\n```"  # Limit to 3000 chars
        else:
            logs_text = "📋 No recent logs found or unable to access system logs."
        
        await update.message.reply_text(logs_text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error("Error in logs handler", error=str(e))
        await update.message.reply_text(f"❌ Error getting logs: {str(e)}")


async def reboot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_instance) -> None:
    """Handle /reboot command"""
    try:
        await update.message.reply_text("🔄 *System Reboot Initiated*\n\nThe system will reboot in 10 seconds. I'll be back online shortly!", parse_mode="Markdown")
        
        # Schedule reboot
        asyncio.create_task(_delayed_reboot())
        
    except Exception as e:
        logger.error("Error in reboot handler", error=str(e))
        await update.message.reply_text(f"❌ Error initiating reboot: {str(e)}")


async def stop_trading_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_instance) -> None:
    """Handle /stop_trading command (emergency stop)"""
    try:
        bot_instance.set_trading_enabled(False)
        
        # Notify all workers to stop trading
        settings = get_settings()
        async with httpx.AsyncClient() as client:
            await client.post(f"http://127.0.0.1:{settings.execution_worker_port}/emergency_stop")
        
        await update.message.reply_text("🛑 *EMERGENCY STOP ACTIVATED*\n\nAll trading operations have been halted immediately!", parse_mode="Markdown")
        
        logger.warning("Emergency stop activated via Telegram")
        
    except Exception as e:
        logger.error("Error in stop trading handler", error=str(e))
        await update.message.reply_text(f"❌ Error stopping trading: {str(e)}")


async def start_trading_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_instance) -> None:
    """Handle /start_trading command"""
    try:
        bot_instance.set_trading_enabled(True)
        
        # Notify execution worker to resume trading
        settings = get_settings()
        async with httpx.AsyncClient() as client:
            await client.post(f"http://127.0.0.1:{settings.execution_worker_port}/resume_trading")
        
        await update.message.reply_text("✅ *Trading Resumed*\n\nTrading operations have been re-enabled.", parse_mode="Markdown")
        
        logger.info("Trading resumed via Telegram")
        
    except Exception as e:
        logger.error("Error in start trading handler", error=str(e))
        await update.message.reply_text(f"❌ Error starting trading: {str(e)}")


# Helper functions

async def _check_services_status() -> str:
    """Check status of RPI Trader services"""
    services = [
        "rpi-trader-bot-gateway",
        "rpi-trader-scheduler", 
        "rpi-trader-finance-worker",
        "rpi-trader-market-worker",
        "rpi-trader-execution-worker"
    ]
    
    status_text = ""
    for service in services:
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip() == "active":
                status_text += f"• {service.replace('rpi-trader-', '')}: 🟢 Active\n"
            else:
                status_text += f"• {service.replace('rpi-trader-', '')}: 🔴 Inactive\n"
        except Exception:
            status_text += f"• {service.replace('rpi-trader-', '')}: ❓ Unknown\n"
    
    return status_text


async def _get_cpu_temperature() -> float:
    """Get CPU temperature (Raspberry Pi specific)"""
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = float(f.read().strip()) / 1000.0
            return temp
    except Exception:
        return 0.0


async def _delayed_reboot():
    """Delayed system reboot"""
    await asyncio.sleep(10)
    subprocess.run(["sudo", "reboot"], check=False)

