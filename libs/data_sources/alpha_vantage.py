"""
Alpha Vantage API client for market data and technical indicators
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal
import json

from ..core.logging import get_logger

logger = get_logger(__name__)


class AlphaVantageClient:
    """Client for Alpha Vantage API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.session = None
        
        # Rate limiting: 25 requests per day for free tier
        self.requests_made = 0
        self.daily_limit = 25
        self.last_request_time = None
        self.min_request_interval = 12  # seconds between requests
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _make_request(self, params: Dict[str, str]) -> Dict[str, Any]:
        """Make API request with rate limiting"""
        if self.requests_made >= self.daily_limit:
            logger.warning("Alpha Vantage daily limit reached", limit=self.daily_limit)
            raise Exception("Daily API limit reached")
        
        # Rate limiting
        if self.last_request_time:
            time_since_last = (datetime.now() - self.last_request_time).total_seconds()
            if time_since_last < self.min_request_interval:
                wait_time = self.min_request_interval - time_since_last
                logger.info("Rate limiting: waiting", wait_seconds=wait_time)
                await asyncio.sleep(wait_time)
        
        params['apikey'] = self.api_key
        
        try:
            async with self.session.get(self.base_url, params=params) as response:
                self.requests_made += 1
                self.last_request_time = datetime.now()
                
                if response.status == 200:
                    data = await response.json()
                    
                    # Check for API errors
                    if "Error Message" in data:
                        logger.error("Alpha Vantage API error", error=data["Error Message"])
                        raise Exception(f"API Error: {data['Error Message']}")
                    
                    if "Note" in data:
                        logger.warning("Alpha Vantage rate limit note", note=data["Note"])
                        raise Exception("API rate limit exceeded")
                    
                    return data
                else:
                    logger.error("Alpha Vantage HTTP error", status=response.status)
                    raise Exception(f"HTTP Error: {response.status}")
                    
        except Exception as e:
            logger.error("Alpha Vantage request failed", error=str(e))
            raise
    
    async def get_daily_data(self, symbol: str, outputsize: str = "compact") -> Dict[str, Any]:
        """Get daily time series data"""
        params = {
            'function': 'TIME_SERIES_DAILY',
            'symbol': symbol,
            'outputsize': outputsize  # compact (100 days) or full (20+ years)
        }
        
        logger.info("Fetching daily data from Alpha Vantage", symbol=symbol)
        return await self._make_request(params)
    
    async def get_intraday_data(self, symbol: str, interval: str = "5min") -> Dict[str, Any]:
        """Get intraday time series data"""
        params = {
            'function': 'TIME_SERIES_INTRADAY',
            'symbol': symbol,
            'interval': interval  # 1min, 5min, 15min, 30min, 60min
        }
        
        logger.info("Fetching intraday data from Alpha Vantage", symbol=symbol, interval=interval)
        return await self._make_request(params)
    
    async def get_sma(self, symbol: str, interval: str = "daily", time_period: int = 20) -> Dict[str, Any]:
        """Get Simple Moving Average"""
        params = {
            'function': 'SMA',
            'symbol': symbol,
            'interval': interval,
            'time_period': str(time_period),
            'series_type': 'close'
        }
        
        logger.info("Fetching SMA from Alpha Vantage", symbol=symbol, period=time_period)
        return await self._make_request(params)
    
    async def get_ema(self, symbol: str, interval: str = "daily", time_period: int = 20) -> Dict[str, Any]:
        """Get Exponential Moving Average"""
        params = {
            'function': 'EMA',
            'symbol': symbol,
            'interval': interval,
            'time_period': str(time_period),
            'series_type': 'close'
        }
        
        logger.info("Fetching EMA from Alpha Vantage", symbol=symbol, period=time_period)
        return await self._make_request(params)
    
    async def get_rsi(self, symbol: str, interval: str = "daily", time_period: int = 14) -> Dict[str, Any]:
        """Get Relative Strength Index"""
        params = {
            'function': 'RSI',
            'symbol': symbol,
            'interval': interval,
            'time_period': str(time_period),
            'series_type': 'close'
        }
        
        logger.info("Fetching RSI from Alpha Vantage", symbol=symbol, period=time_period)
        return await self._make_request(params)
    
    async def get_macd(self, symbol: str, interval: str = "daily") -> Dict[str, Any]:
        """Get MACD (Moving Average Convergence Divergence)"""
        params = {
            'function': 'MACD',
            'symbol': symbol,
            'interval': interval,
            'series_type': 'close'
        }
        
        logger.info("Fetching MACD from Alpha Vantage", symbol=symbol)
        return await self._make_request(params)
    
    async def get_bollinger_bands(self, symbol: str, interval: str = "daily", time_period: int = 20) -> Dict[str, Any]:
        """Get Bollinger Bands"""
        params = {
            'function': 'BBANDS',
            'symbol': symbol,
            'interval': interval,
            'time_period': str(time_period),
            'series_type': 'close'
        }
        
        logger.info("Fetching Bollinger Bands from Alpha Vantage", symbol=symbol, period=time_period)
        return await self._make_request(params)
    
    async def get_forex_daily(self, from_symbol: str, to_symbol: str) -> Dict[str, Any]:
        """Get daily forex data"""
        params = {
            'function': 'FX_DAILY',
            'from_symbol': from_symbol,
            'to_symbol': to_symbol
        }
        
        logger.info("Fetching forex data from Alpha Vantage", pair=f"{from_symbol}/{to_symbol}")
        return await self._make_request(params)
    
    async def get_crypto_daily(self, symbol: str, market: str = "USD") -> Dict[str, Any]:
        """Get daily cryptocurrency data"""
        params = {
            'function': 'DIGITAL_CURRENCY_DAILY',
            'symbol': symbol,
            'market': market
        }
        
        logger.info("Fetching crypto data from Alpha Vantage", symbol=symbol, market=market)
        return await self._make_request(params)
    
    def parse_daily_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse daily time series data into standardized format"""
        try:
            time_series_key = "Time Series (Daily)"
            if time_series_key not in data:
                logger.error("Invalid daily data format", keys=list(data.keys()))
                return []
            
            time_series = data[time_series_key]
            parsed_data = []
            
            for date_str, values in time_series.items():
                parsed_data.append({
                    'date': datetime.strptime(date_str, '%Y-%m-%d'),
                    'open': float(values['1. open']),
                    'high': float(values['2. high']),
                    'low': float(values['3. low']),
                    'close': float(values['4. close']),
                    'volume': int(values['5. volume'])
                })
            
            # Sort by date (newest first)
            parsed_data.sort(key=lambda x: x['date'], reverse=True)
            return parsed_data
            
        except Exception as e:
            logger.error("Failed to parse daily data", error=str(e))
            return []
    
    def parse_technical_indicator(self, data: Dict[str, Any], indicator_name: str) -> List[Dict[str, Any]]:
        """Parse technical indicator data into standardized format"""
        try:
            # Find the technical analysis key
            tech_key = None
            for key in data.keys():
                if "Technical Analysis" in key:
                    tech_key = key
                    break
            
            if not tech_key:
                logger.error("Invalid technical indicator format", keys=list(data.keys()))
                return []
            
            tech_data = data[tech_key]
            parsed_data = []
            
            for date_str, values in tech_data.items():
                # Different indicators have different value keys
                value_key = list(values.keys())[0]  # Usually the first (and only) key
                
                parsed_data.append({
                    'date': datetime.strptime(date_str, '%Y-%m-%d'),
                    'value': float(values[value_key])
                })
            
            # Sort by date (newest first)
            parsed_data.sort(key=lambda x: x['date'], reverse=True)
            return parsed_data
            
        except Exception as e:
            logger.error("Failed to parse technical indicator", indicator=indicator_name, error=str(e))
            return []
    
    def get_latest_price(self, daily_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Get the latest price from daily data"""
        if not daily_data:
            return None
        
        latest = daily_data[0]  # Already sorted by date desc
        return {
            'symbol': 'N/A',  # Will be set by caller
            'price': latest['close'],
            'open': latest['open'],
            'high': latest['high'],
            'low': latest['low'],
            'volume': latest['volume'],
            'date': latest['date'],
            'change': latest['close'] - latest['open'],
            'change_percent': ((latest['close'] - latest['open']) / latest['open']) * 100
        }

