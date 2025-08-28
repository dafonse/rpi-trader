"""
Market Worker Service - End-of-day market data collection and analysis
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json

from libs.core.config import get_settings
from libs.core.logging import get_logger
from libs.data_sources import DataCollector
from libs.data.repository import MarketDataRepository, SignalRepository, AnalysisRepository
from libs.broker.bvm_mt5_client import BVMMT5Client # Import the BVM MT5 client

logger = get_logger(__name__)


class MarketService:
    """Market data collection and analysis service"""
    
    def __init__(self):
        self.settings = get_settings()
        self.is_running = False
        self.data_collector = None
        self.bvm_mt5_client = None # Initialize BVM MT5 client
        
        # Default symbols to analyze
        self.default_symbols = [
            'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA',  # Tech stocks
            'SPY', 'QQQ', 'IWM',  # ETFs
            'EURUSD=X', 'GBPUSD=X',  # Forex
            'BTC-USD', 'ETH-USD'  # Crypto
        ]
        
        # Repositories
        self.market_repo = MarketDataRepository()
        self.signal_repo = SignalRepository()
        self.analysis_repo = AnalysisRepository()
    
    async def start(self) -> None:
        """Start the market service"""
        logger.info("Starting Market Worker Service")
        self.is_running = True
        
        # Initialize data collector with API keys
        alpha_vantage_key = getattr(self.settings, 'alpha_vantage_api_key', None)
        finnhub_key = getattr(self.settings, 'finnhub_api_key', None)
        
        async with DataCollector(alpha_vantage_key, finnhub_key) as collector:
            self.data_collector = collector
            
            # Initialize BVM MT5 client if enabled
            if self.settings.bvm_mt5_enabled and not self.settings.mt5_for_execution_only:
                self.bvm_mt5_client = BVMMT5Client(
                    vm_ip=self.settings.bvm_vm_ip,
                    vm_port=self.settings.bvm_vm_port
                )
                # Connect to the BVM MT5 bridge service
                connected = await self.bvm_mt5_client.connect(
                    login=self.settings.mt5_login,
                    password=self.settings.mt5_password,
                    server=self.settings.mt5_server
                )
                if connected:
                    logger.info("BVM MT5 client initialized and connected in Market Worker")
                else:
                    logger.error("Failed to connect to BVM MT5 client in Market Worker.")

            # Main service loop
            while self.is_running:
                try:
                    await self._run_analysis_cycle()
                    
                    # Wait for next cycle (check every hour, run analysis after market close)
                    await asyncio.sleep(3600)  # 1 hour
                    
                except Exception as e:
                    logger.error("Market service cycle failed", error=str(e))
                    await asyncio.sleep(300)  # 5 minutes on error
    
    async def stop(self) -> None:
        """Stop the market service"""
        logger.info("Stopping Market Worker Service")
        self.is_running = False
        if self.bvm_mt5_client:
            await self.bvm_mt5_client.__aexit__(None, None, None)
    
    async def _run_analysis_cycle(self) -> None:
        """Run the main analysis cycle"""
        now = datetime.now()
        
        # Check if it's time for end-of-day analysis
        # Run after 4:30 PM EST (market close + 30 minutes)
        if self._should_run_eod_analysis(now):
            logger.info("Starting end-of-day analysis")
            await self._run_end_of_day_analysis()
        else:
            logger.debug("Not time for end-of-day analysis", current_time=now.strftime('%H:%M'))
    
    def _should_run_eod_analysis(self, current_time: datetime) -> bool:
        """Check if it's time to run end-of-day analysis"""
        # Convert to EST (market timezone)
        # For simplicity, assuming server is in EST or handling timezone conversion elsewhere
        
        # Run analysis after 4:30 PM EST on weekdays
        if current_time.weekday() >= 5:  # Weekend
            return False
        
        # Check if we already ran analysis today
        today = current_time.date()
        latest_analysis = self.analysis_repo.get_latest_analysis('SPY', 'end_of_day_comprehensive')
        
        if latest_analysis:
            analysis_date = datetime.fromisoformat(latest_analysis['analysis_date']).date()
            if analysis_date >= today:
                return False  # Already ran today
        
        # Run after 4:30 PM (16:30)
        return current_time.hour >= 16 and current_time.minute >= 30
    
    async def _run_end_of_day_analysis(self) -> Dict[str, Any]:
        """Run comprehensive end-of-day analysis"""
        try:
            logger.info("Running end-of-day market analysis")
            
            # Get symbols to analyze
            symbols = self._get_symbols_to_analyze()
            
            # Collect and analyze data
            results = await self.data_collector.collect_end_of_day_data(symbols)
            
            # Generate summary report
            summary = self._generate_analysis_summary(results)
            
            # Save summary
            self.analysis_repo.save_analysis(
                symbol='MARKET_SUMMARY',
                analysis_type='daily_market_summary',
                analysis_date=datetime.utcnow(),
                results=summary,
                confidence=summary.get('overall_confidence', 0.0)
            )
            
            logger.info("End-of-day analysis completed", 
                       symbols_processed=len(results),
                       successful=len([r for r in results.values() if 'error' not in r]))
            
            return results
            
        except Exception as e:
            logger.error("End-of-day analysis failed", error=str(e))
            raise
    
    def _get_symbols_to_analyze(self) -> List[str]:
        """Get list of symbols to analyze"""
        # Could be configured via settings or database
        # For now, use default symbols
        return self.default_symbols
    
    def _generate_analysis_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of analysis results"""
        try:
            summary = {
                'analysis_date': datetime.utcnow().isoformat(),
                'symbols_analyzed': len(results),
                'successful_analyses': 0,
                'failed_analyses': 0,
                'market_sentiment': 'NEUTRAL',
                'top_buy_signals': [],
                'top_sell_signals': [],
                'market_trends': {},
                'overall_confidence': 0.0,
                'key_insights': []
            }
            
            buy_signals = []
            sell_signals = []
            sentiment_scores = []
            confidence_scores = []
            
            for symbol, data in results.items():
                if 'error' in data:
                    summary['failed_analyses'] += 1
                    continue
                
                summary['successful_analyses'] += 1
                
                # Extract signals
                signals = data.get('signals', {})
                combined_signal = signals.get('combined_signal', 'HOLD')
                signal_strength = signals.get('signal_strength', 0.0)
                confidence = signals.get('confidence', 0.0)
                
                if combined_signal == 'BUY' and signal_strength > 0.3:
                    buy_signals.append({
                        'symbol': symbol,
                        'strength': signal_strength,
                        'confidence': confidence,
                        'prediction': data.get('next_day_prediction', {})
                    })
                elif combined_signal == 'SELL' and signal_strength < -0.3:
                    sell_signals.append({
                        'symbol': symbol,
                        'strength': abs(signal_strength),
                        'confidence': confidence,
                        'prediction': data.get('next_day_prediction', {})
                    })
                
                # Collect sentiment and confidence
                sentiment_scores.append(signal_strength)
                confidence_scores.append(confidence)
            
            # Sort signals by strength
            buy_signals.sort(key=lambda x: x['strength'], reverse=True)
            sell_signals.sort(key=lambda x: x['strength'], reverse=True)
            
            summary['top_buy_signals'] = buy_signals[:5]
            summary['top_sell_signals'] = sell_signals[:5]
            
            # Calculate overall market sentiment
            if sentiment_scores:
                avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
                if avg_sentiment > 0.2:
                    summary['market_sentiment'] = 'BULLISH'
                elif avg_sentiment < -0.2:
                    summary['market_sentiment'] = 'BEARISH'
                else:
                    summary['market_sentiment'] = 'NEUTRAL'
            
            # Calculate overall confidence
            if confidence_scores:
                summary['overall_confidence'] = sum(confidence_scores) / len(confidence_scores)
            
            # Generate key insights
            insights = []
            if len(buy_signals) > len(sell_signals) * 1.5:
                insights.append("Strong buying opportunities identified across multiple symbols")
            elif len(sell_signals) > len(buy_signals) * 1.5:
                insights.append("Caution advised - multiple sell signals detected")
            
            if summary['overall_confidence'] > 0.7:
                insights.append("High confidence in analysis - strong signal consensus")
            elif summary['overall_confidence'] < 0.3:
                insights.append("Low confidence - mixed signals, proceed with caution")
            
            summary['key_insights'] = insights
            
            return summary
            
        except Exception as e:
            logger.error("Failed to generate analysis summary", error=str(e))
            return {'error': str(e), 'analysis_date': datetime.utcnow().isoformat()}
    
    async def get_latest_analysis(self, symbol: str = None) -> Optional[Dict[str, Any]]:
        """Get latest analysis for a symbol or market summary"""
        try:
            if symbol:
                return self.analysis_repo.get_latest_analysis(symbol, 'end_of_day_comprehensive')
            else:
                return self.analysis_repo.get_latest_analysis('MARKET_SUMMARY', 'daily_market_summary')
        except Exception as e:
            logger.error("Failed to get latest analysis", symbol=symbol, error=str(e))
            return None
    
    async def get_signals_for_symbol(self, symbol: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get recent signals for a symbol"""
        try:
            since = datetime.utcnow() - timedelta(days=days)
            signals = self.signal_repo.get_signals_since(symbol, since)
            
            return [
                {
                    'id': signal.id,
                    'symbol': signal.symbol,
                    'signal_type': signal.signal_type,
                    'action': signal.action.value,
                    'strength': signal.strength,
                    'confidence': signal.confidence,
                    'timestamp': signal.timestamp.isoformat(),
                    'metadata': signal.metadata
                }
                for signal in signals
            ]
        except Exception as e:
            logger.error("Failed to get signals for symbol", symbol=symbol, error=str(e))
            return []
    
    async def force_analysis(self, symbols: List[str] = None) -> Dict[str, Any]:
        """Force run analysis for specific symbols (for testing/manual trigger)"""
        try:
            if not symbols:
                symbols = self.default_symbols
            
            logger.info("Force running analysis", symbols=symbols)
            
            if not self.data_collector:
                # Create temporary collector
                alpha_vantage_key = getattr(self.settings, 'alpha_vantage_api_key', None)
                finnhub_key = getattr(self.settings, 'finnhub_api_key', None)
                
                async with DataCollector(alpha_vantage_key, finnhub_key) as collector:
                    return await collector.collect_end_of_day_data(symbols)
            else:
                return await self.data_collector.collect_end_of_day_data(symbols)
                
        except Exception as e:
            logger.error("Force analysis failed", error=str(e))
            raise
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get service status information"""
        return {
            'service': 'market_worker',
            'status': 'running' if self.is_running else 'stopped',
            'default_symbols': self.default_symbols,
            'last_analysis': self.analysis_repo.get_latest_analysis('MARKET_SUMMARY', 'daily_market_summary'),
            'supported_symbols': DataCollector(None, None).get_supported_symbols() if not self.data_collector else self.data_collector.get_supported_symbols()
        }


