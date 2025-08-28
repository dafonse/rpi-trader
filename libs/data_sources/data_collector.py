"""
Unified data collector that combines multiple data sources
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json

from .alpha_vantage import AlphaVantageClient
from .yahoo_finance import YahooFinanceClient  
from .finnhub import FinnhubClient
from ..core.logging import get_logger
from ..data.repository import MarketDataRepository, SignalRepository, AnalysisRepository
from ..data.models import MarketData, SignalData, TradeAction

logger = get_logger(__name__)


class DataCollector:
    """Unified data collector combining multiple sources"""
    
    def __init__(self, alpha_vantage_key: str = None, finnhub_key: str = None):
        self.alpha_vantage_key = alpha_vantage_key
        self.finnhub_key = finnhub_key
        
        # Initialize clients
        self.yahoo_client = YahooFinanceClient()
        self.alpha_vantage_client = None
        self.finnhub_client = None
        
        # Initialize repositories
        self.market_repo = MarketDataRepository()
        self.signal_repo = SignalRepository()
        self.analysis_repo = AnalysisRepository()
    
    async def __aenter__(self):
        """Async context manager entry"""
        if self.alpha_vantage_key:
            self.alpha_vantage_client = AlphaVantageClient(self.alpha_vantage_key)
            await self.alpha_vantage_client.__aenter__()
        
        if self.finnhub_key:
            self.finnhub_client = FinnhubClient(self.finnhub_key)
            await self.finnhub_client.__aenter__()
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.alpha_vantage_client:
            await self.alpha_vantage_client.__aexit__(exc_type, exc_val, exc_tb)
        
        if self.finnhub_client:
            await self.finnhub_client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def collect_end_of_day_data(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Collect comprehensive end-of-day data for multiple symbols
        
        Returns:
            Dict with symbol as key and comprehensive analysis as value
        """
        logger.info("Starting end-of-day data collection", symbols=symbols, count=len(symbols))
        
        results = {}
        
        for symbol in symbols:
            try:
                logger.info("Processing symbol", symbol=symbol)
                
                # Collect data from all sources
                symbol_data = {
                    'symbol': symbol,
                    'timestamp': datetime.utcnow(),
                    'price_data': {},
                    'technical_indicators': {},
                    'news_sentiment': {},
                    'analyst_recommendations': {},
                    'signals': {},
                    'next_day_prediction': {}
                }
                
                # 1. Get price data from Yahoo Finance (primary source)
                price_data = await self._get_price_data(symbol)
                symbol_data['price_data'] = price_data
                
                # 2. Get technical indicators
                technical_data = await self._get_technical_indicators(symbol)
                symbol_data['technical_indicators'] = technical_data
                
                # 3. Get news sentiment (if Finnhub available)
                if self.finnhub_client:
                    news_data = await self._get_news_sentiment(symbol)
                    symbol_data['news_sentiment'] = news_data
                
                # 4. Get analyst recommendations (if Finnhub available)
                if self.finnhub_client:
                    analyst_data = await self._get_analyst_recommendations(symbol)
                    symbol_data['analyst_recommendations'] = analyst_data
                
                # 5. Generate trading signals
                signals = await self._generate_trading_signals(symbol, symbol_data)
                symbol_data['signals'] = signals
                
                # 6. Generate next-day prediction
                prediction = await self._generate_next_day_prediction(symbol, symbol_data)
                symbol_data['next_day_prediction'] = prediction
                
                # 7. Save to database
                await self._save_analysis_to_db(symbol, symbol_data)
                
                results[symbol] = symbol_data
                logger.info("Successfully processed symbol", symbol=symbol)
                
                # Small delay between symbols to respect rate limits
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error("Failed to process symbol", symbol=symbol, error=str(e))
                results[symbol] = {
                    'symbol': symbol,
                    'error': str(e),
                    'timestamp': datetime.utcnow()
                }
        
        logger.info("Completed end-of-day data collection", processed=len(results))
        return results
    
    async def _get_price_data(self, symbol: str) -> Dict[str, Any]:
        """Get current price and recent historical data"""
        try:
            # Get current price info
            current_price = await self.yahoo_client.get_current_price(symbol)
            
            # Get recent historical data for analysis
            historical_data = await self.yahoo_client.get_historical_data(symbol, period="3mo", interval="1d")
            
            if current_price and not historical_data.empty:
                # Calculate additional metrics
                recent_high = historical_data['High'].max()
                recent_low = historical_data['Low'].min()
                avg_volume = historical_data['Volume'].mean()
                
                return {
                    'current_price': current_price['price'],
                    'open': current_price['open'],
                    'high': current_price['high'],
                    'low': current_price['low'],
                    'volume': current_price['volume'],
                    'change': current_price['change'],
                    'change_percent': current_price['change_percent'],
                    'previous_close': current_price['previous_close'],
                    '3m_high': float(recent_high),
                    '3m_low': float(recent_low),
                    'avg_volume_3m': float(avg_volume),
                    'volume_vs_avg': current_price['volume'] / avg_volume if avg_volume > 0 else 1.0,
                    'price_vs_3m_high': (current_price['price'] / recent_high - 1) * 100,
                    'price_vs_3m_low': (current_price['price'] / recent_low - 1) * 100,
                    'market_cap': current_price.get('market_cap'),
                    'pe_ratio': current_price.get('pe_ratio'),
                    'beta': current_price.get('beta')
                }
            else:
                logger.warning("No price data available", symbol=symbol)
                return {}
                
        except Exception as e:
            logger.error("Failed to get price data", symbol=symbol, error=str(e))
            return {}
    
    async def _get_technical_indicators(self, symbol: str) -> Dict[str, Any]:
        """Get technical indicators from multiple sources"""
        try:
            indicators = {}
            
            # Primary: Yahoo Finance with calculated indicators
            historical_data = await self.yahoo_client.get_historical_data(symbol, period="1y", interval="1d")
            if not historical_data.empty:
                data_with_indicators = self.yahoo_client.calculate_technical_indicators(historical_data)
                yahoo_indicators = self.yahoo_client.get_latest_indicators(data_with_indicators)
                indicators.update(yahoo_indicators)
            
            # Secondary: Alpha Vantage (if available and within limits)
            if self.alpha_vantage_client and self.alpha_vantage_client.requests_made < 20:  # Save some requests
                try:
                    # Get RSI
                    rsi_data = await self.alpha_vantage_client.get_rsi(symbol)
                    if rsi_data:
                        parsed_rsi = self.alpha_vantage_client.parse_technical_indicator(rsi_data, 'RSI')
                        if parsed_rsi:
                            indicators['av_rsi'] = parsed_rsi[0]['value']
                    
                    # Get MACD
                    macd_data = await self.alpha_vantage_client.get_macd(symbol)
                    if macd_data:
                        # MACD has multiple values, would need special parsing
                        pass
                        
                except Exception as e:
                    logger.warning("Alpha Vantage indicators failed", symbol=symbol, error=str(e))
            
            return indicators
            
        except Exception as e:
            logger.error("Failed to get technical indicators", symbol=symbol, error=str(e))
            return {}
    
    async def _get_news_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Get news sentiment analysis"""
        try:
            if not self.finnhub_client:
                return {}
            
            # Get recent news
            news_data = await self.finnhub_client.get_company_news(symbol)
            
            # Analyze sentiment
            sentiment_analysis = self.finnhub_client.analyze_news_sentiment(news_data)
            
            # Get additional sentiment data
            try:
                insider_sentiment = await self.finnhub_client.get_sentiment(symbol)
                sentiment_analysis['insider_sentiment'] = insider_sentiment
            except:
                pass
            
            return sentiment_analysis
            
        except Exception as e:
            logger.error("Failed to get news sentiment", symbol=symbol, error=str(e))
            return {}
    
    async def _get_analyst_recommendations(self, symbol: str) -> Dict[str, Any]:
        """Get analyst recommendations and price targets"""
        try:
            if not self.finnhub_client:
                return {}
            
            recommendations = {}
            
            # Get recommendation trends
            try:
                rec_data = await self.finnhub_client.get_recommendation_trends(symbol)
                rec_analysis = self.finnhub_client.analyze_recommendation_trends(rec_data)
                recommendations['trends'] = rec_analysis
            except:
                pass
            
            # Get price targets
            try:
                price_targets = await self.finnhub_client.get_price_target(symbol)
                recommendations['price_targets'] = price_targets
            except:
                pass
            
            return recommendations
            
        except Exception as e:
            logger.error("Failed to get analyst recommendations", symbol=symbol, error=str(e))
            return {}
    
    async def _generate_trading_signals(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive trading signals"""
        try:
            signals = {
                'technical_signals': {},
                'sentiment_signals': {},
                'analyst_signals': {},
                'combined_signal': 'HOLD',
                'confidence': 0.0,
                'signal_strength': 0.0
            }
            
            signal_scores = []
            
            # 1. Technical signals from Yahoo Finance indicators
            technical_indicators = data.get('technical_indicators', {})
            if technical_indicators:
                tech_signals = self.yahoo_client.generate_signals(technical_indicators)
                signals['technical_signals'] = tech_signals
                
                # Convert signal to score
                if tech_signals['overall_signal'] == 'BUY':
                    signal_scores.append(tech_signals['signal_strength'])
                elif tech_signals['overall_signal'] == 'SELL':
                    signal_scores.append(tech_signals['signal_strength'])
                else:
                    signal_scores.append(0.0)
            
            # 2. Sentiment signals
            news_sentiment = data.get('news_sentiment', {})
            if news_sentiment and 'sentiment_score' in news_sentiment:
                sentiment_score = news_sentiment['sentiment_score']
                signals['sentiment_signals'] = {
                    'signal': 'BUY' if sentiment_score > 0.2 else 'SELL' if sentiment_score < -0.2 else 'NEUTRAL',
                    'strength': abs(sentiment_score),
                    'news_count': news_sentiment.get('news_count', 0)
                }
                signal_scores.append(sentiment_score)
            
            # 3. Analyst signals
            analyst_recs = data.get('analyst_recommendations', {})
            if analyst_recs and 'trends' in analyst_recs:
                rec_score = analyst_recs['trends'].get('recommendation_score', 0.0)
                signals['analyst_signals'] = {
                    'signal': analyst_recs['trends'].get('overall_recommendation', 'HOLD'),
                    'strength': abs(rec_score),
                    'trend': analyst_recs['trends'].get('trend', 'STABLE')
                }
                signal_scores.append(rec_score)
            
            # 4. Combine all signals
            if signal_scores:
                avg_score = sum(signal_scores) / len(signal_scores)
                signals['signal_strength'] = avg_score
                signals['confidence'] = min(len(signal_scores) * 0.3, 1.0)  # More sources = higher confidence
                
                if avg_score > 0.3:
                    signals['combined_signal'] = 'BUY'
                elif avg_score < -0.3:
                    signals['combined_signal'] = 'SELL'
                else:
                    signals['combined_signal'] = 'HOLD'
            
            return signals
            
        except Exception as e:
            logger.error("Failed to generate trading signals", symbol=symbol, error=str(e))
            return {'combined_signal': 'HOLD', 'confidence': 0.0, 'signal_strength': 0.0}
    
    async def _generate_next_day_prediction(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate next trading day prediction"""
        try:
            prediction = {
                'direction': 'NEUTRAL',
                'confidence': 0.0,
                'expected_change_percent': 0.0,
                'key_factors': [],
                'risk_level': 'MEDIUM'
            }
            
            factors = []
            direction_scores = []
            
            # Factor 1: Technical momentum
            tech_indicators = data.get('technical_indicators', {})
            if tech_indicators:
                rsi = tech_indicators.get('rsi')
                macd_histogram = tech_indicators.get('macd_histogram')
                price_change_5d = tech_indicators.get('price_change_5d', 0)
                
                if rsi and rsi < 30:
                    factors.append("Oversold conditions (RSI < 30)")
                    direction_scores.append(0.6)
                elif rsi and rsi > 70:
                    factors.append("Overbought conditions (RSI > 70)")
                    direction_scores.append(-0.6)
                
                if macd_histogram and macd_histogram > 0:
                    factors.append("Positive MACD momentum")
                    direction_scores.append(0.4)
                elif macd_histogram and macd_histogram < 0:
                    factors.append("Negative MACD momentum")
                    direction_scores.append(-0.4)
                
                if abs(price_change_5d) > 0.05:  # 5% change in 5 days
                    if price_change_5d > 0:
                        factors.append("Strong upward momentum (5-day)")
                        direction_scores.append(0.3)
                    else:
                        factors.append("Strong downward momentum (5-day)")
                        direction_scores.append(-0.3)
            
            # Factor 2: News sentiment
            news_sentiment = data.get('news_sentiment', {})
            if news_sentiment and news_sentiment.get('news_count', 0) > 0:
                sentiment = news_sentiment.get('overall_sentiment')
                if sentiment == 'POSITIVE':
                    factors.append("Positive news sentiment")
                    direction_scores.append(0.4)
                elif sentiment == 'NEGATIVE':
                    factors.append("Negative news sentiment")
                    direction_scores.append(-0.4)
            
            # Factor 3: Volume analysis
            price_data = data.get('price_data', {})
            if price_data:
                volume_vs_avg = price_data.get('volume_vs_avg', 1.0)
                if volume_vs_avg > 1.5:
                    factors.append("High volume activity")
                    # High volume with positive price change is bullish
                    if price_data.get('change_percent', 0) > 0:
                        direction_scores.append(0.3)
                    else:
                        direction_scores.append(-0.3)
            
            # Calculate prediction
            if direction_scores:
                avg_score = sum(direction_scores) / len(direction_scores)
                prediction['confidence'] = min(len(direction_scores) * 0.25, 0.9)
                prediction['expected_change_percent'] = avg_score * 2  # Convert to rough percentage
                
                if avg_score > 0.2:
                    prediction['direction'] = 'UP'
                elif avg_score < -0.2:
                    prediction['direction'] = 'DOWN'
                else:
                    prediction['direction'] = 'NEUTRAL'
            
            # Risk assessment
            volatility = tech_indicators.get('volatility_20d', 0)
            if volatility > 0.03:  # 3% daily volatility
                prediction['risk_level'] = 'HIGH'
            elif volatility < 0.015:  # 1.5% daily volatility
                prediction['risk_level'] = 'LOW'
            
            prediction['key_factors'] = factors
            return prediction
            
        except Exception as e:
            logger.error("Failed to generate next day prediction", symbol=symbol, error=str(e))
            return {'direction': 'NEUTRAL', 'confidence': 0.0, 'expected_change_percent': 0.0}
    
    async def _save_analysis_to_db(self, symbol: str, data: Dict[str, Any]) -> None:
        """Save analysis results to database"""
        try:
            analysis_date = datetime.utcnow()
            
            # Save comprehensive analysis
            self.analysis_repo.save_analysis(
                symbol=symbol,
                analysis_type='end_of_day_comprehensive',
                analysis_date=analysis_date,
                results=data,
                confidence=data.get('signals', {}).get('confidence', 0.0)
            )
            
            # Save individual signal
            signals = data.get('signals', {})
            if signals.get('combined_signal'):
                signal_data = SignalData(
                    symbol=symbol,
                    signal_type='end_of_day',
                    action=TradeAction.BUY if signals['combined_signal'] == 'BUY' 
                          else TradeAction.SELL if signals['combined_signal'] == 'SELL' 
                          else TradeAction.BUY,  # Default for HOLD
                    strength=signals.get('signal_strength', 0.0),
                    confidence=signals.get('confidence', 0.0),
                    timestamp=analysis_date,
                    metadata={
                        'technical_signals': signals.get('technical_signals', {}),
                        'sentiment_signals': signals.get('sentiment_signals', {}),
                        'analyst_signals': signals.get('analyst_signals', {}),
                        'next_day_prediction': data.get('next_day_prediction', {})
                    }
                )
                
                self.signal_repo.create(signal_data)
            
            logger.info("Saved analysis to database", symbol=symbol)
            
        except Exception as e:
            logger.error("Failed to save analysis to database", symbol=symbol, error=str(e))
    
    def get_supported_symbols(self) -> Dict[str, List[str]]:
        """Get supported symbols from Yahoo Finance"""
        return self.yahoo_client.get_supported_symbols()

