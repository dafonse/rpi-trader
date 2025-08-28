"""
Finnhub API client for market news and sentiment analysis
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json

from ..core.logging import get_logger

logger = get_logger(__name__)


class FinnhubClient:
    """Client for Finnhub API - Market news and sentiment"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://finnhub.io/api/v1"
        self.session = None
        
        # Rate limiting: 60 calls per minute for free tier
        self.requests_made = 0
        self.minute_limit = 60
        self.last_minute_reset = datetime.now()
        self.min_request_interval = 1  # second between requests
        self.last_request_time = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def _reset_rate_limit_if_needed(self):
        """Reset rate limit counter if a minute has passed"""
        now = datetime.now()
        if (now - self.last_minute_reset).total_seconds() >= 60:
            self.requests_made = 0
            self.last_minute_reset = now
    
    async def _make_request(self, endpoint: str, params: Dict[str, str] = None) -> Dict[str, Any]:
        """Make API request with rate limiting"""
        self._reset_rate_limit_if_needed()
        
        if self.requests_made >= self.minute_limit:
            logger.warning("Finnhub rate limit reached", limit=self.minute_limit)
            # Wait until next minute
            wait_time = 60 - (datetime.now() - self.last_minute_reset).total_seconds()
            if wait_time > 0:
                logger.info("Waiting for rate limit reset", wait_seconds=wait_time)
                await asyncio.sleep(wait_time)
                self._reset_rate_limit_if_needed()
        
        # Basic rate limiting between requests
        if self.last_request_time:
            time_since_last = (datetime.now() - self.last_request_time).total_seconds()
            if time_since_last < self.min_request_interval:
                wait_time = self.min_request_interval - time_since_last
                await asyncio.sleep(wait_time)
        
        if params is None:
            params = {}
        params['token'] = self.api_key
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            async with self.session.get(url, params=params) as response:
                self.requests_made += 1
                self.last_request_time = datetime.now()
                
                if response.status == 200:
                    data = await response.json()
                    return data
                elif response.status == 429:
                    logger.warning("Finnhub rate limit exceeded")
                    raise Exception("Rate limit exceeded")
                else:
                    logger.error("Finnhub HTTP error", status=response.status)
                    raise Exception(f"HTTP Error: {response.status}")
                    
        except Exception as e:
            logger.error("Finnhub request failed", endpoint=endpoint, error=str(e))
            raise
    
    async def get_company_news(self, symbol: str, from_date: str = None, to_date: str = None) -> List[Dict[str, Any]]:
        """
        Get company news
        
        Args:
            symbol: Stock symbol
            from_date: From date in YYYY-MM-DD format (default: 30 days ago)
            to_date: To date in YYYY-MM-DD format (default: today)
        """
        if not from_date:
            from_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not to_date:
            to_date = datetime.now().strftime('%Y-%m-%d')
        
        params = {
            'symbol': symbol,
            'from': from_date,
            'to': to_date
        }
        
        logger.info("Fetching company news from Finnhub", symbol=symbol, from_date=from_date, to_date=to_date)
        return await self._make_request('company-news', params)
    
    async def get_market_news(self, category: str = "general") -> List[Dict[str, Any]]:
        """
        Get market news by category
        
        Args:
            category: News category (general, forex, crypto, merger)
        """
        params = {'category': category}
        
        logger.info("Fetching market news from Finnhub", category=category)
        return await self._make_request('news', params)
    
    async def get_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Get sentiment data for a symbol"""
        params = {'symbol': symbol}
        
        logger.info("Fetching sentiment from Finnhub", symbol=symbol)
        return await self._make_request('stock/insider-sentiment', params)
    
    async def get_recommendation_trends(self, symbol: str) -> List[Dict[str, Any]]:
        """Get analyst recommendation trends"""
        params = {'symbol': symbol}
        
        logger.info("Fetching recommendation trends from Finnhub", symbol=symbol)
        return await self._make_request('stock/recommendation', params)
    
    async def get_price_target(self, symbol: str) -> Dict[str, Any]:
        """Get analyst price targets"""
        params = {'symbol': symbol}
        
        logger.info("Fetching price targets from Finnhub", symbol=symbol)
        return await self._make_request('stock/price-target', params)
    
    async def get_earnings_calendar(self, from_date: str = None, to_date: str = None) -> Dict[str, Any]:
        """Get earnings calendar"""
        if not from_date:
            from_date = datetime.now().strftime('%Y-%m-%d')
        if not to_date:
            to_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        params = {
            'from': from_date,
            'to': to_date
        }
        
        logger.info("Fetching earnings calendar from Finnhub", from_date=from_date, to_date=to_date)
        return await self._make_request('calendar/earnings', params)
    
    async def get_economic_calendar(self) -> List[Dict[str, Any]]:
        """Get economic calendar"""
        logger.info("Fetching economic calendar from Finnhub")
        return await self._make_request('calendar/economic')
    
    async def get_covid19_data(self) -> List[Dict[str, Any]]:
        """Get COVID-19 statistics"""
        logger.info("Fetching COVID-19 data from Finnhub")
        return await self._make_request('covid19/us')
    
    def analyze_news_sentiment(self, news_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze sentiment from news data"""
        try:
            if not news_data:
                return {
                    'overall_sentiment': 'NEUTRAL',
                    'sentiment_score': 0.0,
                    'news_count': 0,
                    'positive_count': 0,
                    'negative_count': 0,
                    'neutral_count': 0
                }
            
            # Simple sentiment analysis based on headline keywords
            positive_keywords = [
                'up', 'rise', 'gain', 'bull', 'positive', 'growth', 'increase',
                'profit', 'beat', 'strong', 'good', 'excellent', 'success',
                'breakthrough', 'upgrade', 'buy', 'outperform'
            ]
            
            negative_keywords = [
                'down', 'fall', 'drop', 'bear', 'negative', 'decline', 'decrease',
                'loss', 'miss', 'weak', 'bad', 'poor', 'failure',
                'downgrade', 'sell', 'underperform', 'crash', 'plunge'
            ]
            
            sentiment_scores = []
            positive_count = 0
            negative_count = 0
            neutral_count = 0
            
            for article in news_data:
                headline = article.get('headline', '').lower()
                summary = article.get('summary', '').lower()
                text = f"{headline} {summary}"
                
                positive_score = sum(1 for keyword in positive_keywords if keyword in text)
                negative_score = sum(1 for keyword in negative_keywords if keyword in text)
                
                if positive_score > negative_score:
                    sentiment_scores.append(1.0)
                    positive_count += 1
                elif negative_score > positive_score:
                    sentiment_scores.append(-1.0)
                    negative_count += 1
                else:
                    sentiment_scores.append(0.0)
                    neutral_count += 1
            
            overall_score = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
            
            if overall_score > 0.2:
                overall_sentiment = 'POSITIVE'
            elif overall_score < -0.2:
                overall_sentiment = 'NEGATIVE'
            else:
                overall_sentiment = 'NEUTRAL'
            
            return {
                'overall_sentiment': overall_sentiment,
                'sentiment_score': overall_score,
                'news_count': len(news_data),
                'positive_count': positive_count,
                'negative_count': negative_count,
                'neutral_count': neutral_count,
                'sentiment_distribution': {
                    'positive_ratio': positive_count / len(news_data),
                    'negative_ratio': negative_count / len(news_data),
                    'neutral_ratio': neutral_count / len(news_data)
                }
            }
            
        except Exception as e:
            logger.error("Failed to analyze news sentiment", error=str(e))
            return {
                'overall_sentiment': 'NEUTRAL',
                'sentiment_score': 0.0,
                'news_count': 0,
                'error': str(e)
            }
    
    def analyze_recommendation_trends(self, recommendation_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze analyst recommendation trends"""
        try:
            if not recommendation_data:
                return {
                    'overall_recommendation': 'HOLD',
                    'recommendation_score': 0.0,
                    'trend': 'STABLE'
                }
            
            # Get the most recent recommendation
            latest = recommendation_data[0]  # Assuming sorted by date desc
            
            buy = latest.get('buy', 0)
            hold = latest.get('hold', 0)
            sell = latest.get('sell', 0)
            strong_buy = latest.get('strongBuy', 0)
            strong_sell = latest.get('strongSell', 0)
            
            total = buy + hold + sell + strong_buy + strong_sell
            
            if total == 0:
                return {
                    'overall_recommendation': 'HOLD',
                    'recommendation_score': 0.0,
                    'trend': 'STABLE'
                }
            
            # Calculate weighted score
            score = (strong_buy * 2 + buy * 1 + hold * 0 + sell * -1 + strong_sell * -2) / total
            
            if score > 0.5:
                overall_rec = 'STRONG_BUY'
            elif score > 0.1:
                overall_rec = 'BUY'
            elif score > -0.1:
                overall_rec = 'HOLD'
            elif score > -0.5:
                overall_rec = 'SELL'
            else:
                overall_rec = 'STRONG_SELL'
            
            # Analyze trend if we have multiple data points
            trend = 'STABLE'
            if len(recommendation_data) > 1:
                previous = recommendation_data[1]
                prev_total = sum([previous.get(k, 0) for k in ['buy', 'hold', 'sell', 'strongBuy', 'strongSell']])
                if prev_total > 0:
                    prev_score = (previous.get('strongBuy', 0) * 2 + previous.get('buy', 0) * 1 + 
                                previous.get('hold', 0) * 0 + previous.get('sell', 0) * -1 + 
                                previous.get('strongSell', 0) * -2) / prev_total
                    
                    if score > prev_score + 0.1:
                        trend = 'IMPROVING'
                    elif score < prev_score - 0.1:
                        trend = 'DECLINING'
            
            return {
                'overall_recommendation': overall_rec,
                'recommendation_score': score,
                'trend': trend,
                'breakdown': {
                    'strong_buy': strong_buy,
                    'buy': buy,
                    'hold': hold,
                    'sell': sell,
                    'strong_sell': strong_sell,
                    'total': total
                }
            }
            
        except Exception as e:
            logger.error("Failed to analyze recommendation trends", error=str(e))
            return {
                'overall_recommendation': 'HOLD',
                'recommendation_score': 0.0,
                'trend': 'STABLE',
                'error': str(e)
            }

