"""
Yahoo Finance client for historical market data
"""

import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd

from ..core.logging import get_logger

logger = get_logger(__name__)


class YahooFinanceClient:
    """Client for Yahoo Finance data"""
    
    def __init__(self):
        self.session = None
    
    async def get_historical_data(self, symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """
        Get historical data from Yahoo Finance
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'EURUSD=X')
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
        """
        try:
            logger.info("Fetching historical data from Yahoo Finance", symbol=symbol, period=period)
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            
            if data.empty:
                logger.warning("No data returned from Yahoo Finance", symbol=symbol)
                return pd.DataFrame()
            
            logger.info("Successfully fetched data", symbol=symbol, records=len(data))
            return data
            
        except Exception as e:
            logger.error("Failed to fetch Yahoo Finance data", symbol=symbol, error=str(e))
            return pd.DataFrame()
    
    async def get_current_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current price and basic info"""
        try:
            logger.info("Fetching current price from Yahoo Finance", symbol=symbol)
            
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if not info:
                logger.warning("No info returned from Yahoo Finance", symbol=symbol)
                return None
            
            # Get recent price data
            hist = ticker.history(period="2d", interval="1d")
            if hist.empty:
                logger.warning("No recent price data", symbol=symbol)
                return None
            
            latest = hist.iloc[-1]
            previous = hist.iloc[-2] if len(hist) > 1 else latest
            
            current_price = {
                'symbol': symbol,
                'price': float(latest['Close']),
                'open': float(latest['Open']),
                'high': float(latest['High']),
                'low': float(latest['Low']),
                'volume': int(latest['Volume']),
                'previous_close': float(previous['Close']),
                'change': float(latest['Close'] - previous['Close']),
                'change_percent': float(((latest['Close'] - previous['Close']) / previous['Close']) * 100),
                'timestamp': latest.name.to_pydatetime(),
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'dividend_yield': info.get('dividendYield'),
                'beta': info.get('beta'),
                '52_week_high': info.get('fiftyTwoWeekHigh'),
                '52_week_low': info.get('fiftyTwoWeekLow')
            }
            
            logger.info("Successfully fetched current price", symbol=symbol, price=current_price['price'])
            return current_price
            
        except Exception as e:
            logger.error("Failed to fetch current price", symbol=symbol, error=str(e))
            return None
    
    async def get_multiple_symbols(self, symbols: List[str], period: str = "1y") -> Dict[str, pd.DataFrame]:
        """Get historical data for multiple symbols"""
        try:
            logger.info("Fetching data for multiple symbols", symbols=symbols, count=len(symbols))
            
            # Use yfinance download for multiple symbols
            data = yf.download(symbols, period=period, group_by='ticker', auto_adjust=True, prepost=True)
            
            result = {}
            
            if len(symbols) == 1:
                # Single symbol returns different structure
                result[symbols[0]] = data
            else:
                # Multiple symbols
                for symbol in symbols:
                    if symbol in data.columns.levels[0]:
                        result[symbol] = data[symbol]
                    else:
                        logger.warning("No data for symbol", symbol=symbol)
                        result[symbol] = pd.DataFrame()
            
            logger.info("Successfully fetched multiple symbols", count=len(result))
            return result
            
        except Exception as e:
            logger.error("Failed to fetch multiple symbols", error=str(e))
            return {}
    
    async def get_forex_pair(self, base: str, quote: str, period: str = "1y") -> pd.DataFrame:
        """Get forex pair data (e.g., EUR/USD)"""
        # Yahoo Finance forex format: EURUSD=X
        symbol = f"{base}{quote}=X"
        return await self.get_historical_data(symbol, period)
    
    async def get_crypto_data(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        """Get cryptocurrency data"""
        # Yahoo Finance crypto format: BTC-USD
        if not symbol.endswith('-USD'):
            symbol = f"{symbol}-USD"
        return await self.get_historical_data(symbol, period)
    
    def calculate_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate basic technical indicators"""
        try:
            if data.empty:
                return data
            
            df = data.copy()
            
            # Simple Moving Averages
            df['SMA_20'] = df['Close'].rolling(window=20).mean()
            df['SMA_50'] = df['Close'].rolling(window=50).mean()
            df['SMA_200'] = df['Close'].rolling(window=200).mean()
            
            # Exponential Moving Averages
            df['EMA_12'] = df['Close'].ewm(span=12).mean()
            df['EMA_26'] = df['Close'].ewm(span=26).mean()
            
            # MACD
            df['MACD'] = df['EMA_12'] - df['EMA_26']
            df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
            df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
            
            # RSI
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            # Bollinger Bands
            df['BB_Middle'] = df['Close'].rolling(window=20).mean()
            bb_std = df['Close'].rolling(window=20).std()
            df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
            df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
            df['BB_Width'] = df['BB_Upper'] - df['BB_Lower']
            df['BB_Position'] = (df['Close'] - df['BB_Lower']) / df['BB_Width']
            
            # Volume indicators
            df['Volume_SMA'] = df['Volume'].rolling(window=20).mean()
            df['Volume_Ratio'] = df['Volume'] / df['Volume_SMA']
            
            # Price momentum
            df['Price_Change_1d'] = df['Close'].pct_change(1)
            df['Price_Change_5d'] = df['Close'].pct_change(5)
            df['Price_Change_20d'] = df['Close'].pct_change(20)
            
            # Volatility
            df['Volatility_20d'] = df['Close'].rolling(window=20).std()
            
            logger.info("Technical indicators calculated successfully", indicators_count=12)
            return df
            
        except Exception as e:
            logger.error("Failed to calculate technical indicators", error=str(e))
            return data
    
    def get_latest_indicators(self, data_with_indicators: pd.DataFrame) -> Dict[str, Any]:
        """Extract latest technical indicator values"""
        try:
            if data_with_indicators.empty:
                return {}
            
            latest = data_with_indicators.iloc[-1]
            
            indicators = {
                'price': float(latest['Close']),
                'sma_20': float(latest['SMA_20']) if pd.notna(latest['SMA_20']) else None,
                'sma_50': float(latest['SMA_50']) if pd.notna(latest['SMA_50']) else None,
                'sma_200': float(latest['SMA_200']) if pd.notna(latest['SMA_200']) else None,
                'ema_12': float(latest['EMA_12']) if pd.notna(latest['EMA_12']) else None,
                'ema_26': float(latest['EMA_26']) if pd.notna(latest['EMA_26']) else None,
                'macd': float(latest['MACD']) if pd.notna(latest['MACD']) else None,
                'macd_signal': float(latest['MACD_Signal']) if pd.notna(latest['MACD_Signal']) else None,
                'macd_histogram': float(latest['MACD_Histogram']) if pd.notna(latest['MACD_Histogram']) else None,
                'rsi': float(latest['RSI']) if pd.notna(latest['RSI']) else None,
                'bb_upper': float(latest['BB_Upper']) if pd.notna(latest['BB_Upper']) else None,
                'bb_middle': float(latest['BB_Middle']) if pd.notna(latest['BB_Middle']) else None,
                'bb_lower': float(latest['BB_Lower']) if pd.notna(latest['BB_Lower']) else None,
                'bb_position': float(latest['BB_Position']) if pd.notna(latest['BB_Position']) else None,
                'volume_ratio': float(latest['Volume_Ratio']) if pd.notna(latest['Volume_Ratio']) else None,
                'volatility_20d': float(latest['Volatility_20d']) if pd.notna(latest['Volatility_20d']) else None,
                'price_change_1d': float(latest['Price_Change_1d']) if pd.notna(latest['Price_Change_1d']) else None,
                'price_change_5d': float(latest['Price_Change_5d']) if pd.notna(latest['Price_Change_5d']) else None,
                'price_change_20d': float(latest['Price_Change_20d']) if pd.notna(latest['Price_Change_20d']) else None,
                'timestamp': latest.name.to_pydatetime()
            }
            
            return indicators
            
        except Exception as e:
            logger.error("Failed to extract latest indicators", error=str(e))
            return {}
    
    def generate_signals(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Generate basic trading signals from indicators"""
        try:
            signals = {
                'overall_signal': 'HOLD',
                'signal_strength': 0.0,
                'signals': {},
                'timestamp': datetime.utcnow()
            }
            
            signal_scores = []
            
            # RSI signals
            if indicators.get('rsi'):
                rsi = indicators['rsi']
                if rsi < 30:
                    signals['signals']['rsi'] = 'BUY'
                    signal_scores.append(0.7)
                elif rsi > 70:
                    signals['signals']['rsi'] = 'SELL'
                    signal_scores.append(-0.7)
                else:
                    signals['signals']['rsi'] = 'NEUTRAL'
                    signal_scores.append(0.0)
            
            # MACD signals
            if indicators.get('macd') and indicators.get('macd_signal'):
                macd = indicators['macd']
                macd_signal = indicators['macd_signal']
                if macd > macd_signal:
                    signals['signals']['macd'] = 'BUY'
                    signal_scores.append(0.6)
                else:
                    signals['signals']['macd'] = 'SELL'
                    signal_scores.append(-0.6)
            
            # Moving Average signals
            if indicators.get('sma_20') and indicators.get('sma_50'):
                sma_20 = indicators['sma_20']
                sma_50 = indicators['sma_50']
                price = indicators['price']
                
                if price > sma_20 > sma_50:
                    signals['signals']['ma_trend'] = 'BUY'
                    signal_scores.append(0.8)
                elif price < sma_20 < sma_50:
                    signals['signals']['ma_trend'] = 'SELL'
                    signal_scores.append(-0.8)
                else:
                    signals['signals']['ma_trend'] = 'NEUTRAL'
                    signal_scores.append(0.0)
            
            # Bollinger Bands signals
            if indicators.get('bb_position'):
                bb_pos = indicators['bb_position']
                if bb_pos < 0.1:  # Near lower band
                    signals['signals']['bollinger'] = 'BUY'
                    signal_scores.append(0.5)
                elif bb_pos > 0.9:  # Near upper band
                    signals['signals']['bollinger'] = 'SELL'
                    signal_scores.append(-0.5)
                else:
                    signals['signals']['bollinger'] = 'NEUTRAL'
                    signal_scores.append(0.0)
            
            # Calculate overall signal
            if signal_scores:
                avg_score = sum(signal_scores) / len(signal_scores)
                signals['signal_strength'] = avg_score
                
                if avg_score > 0.3:
                    signals['overall_signal'] = 'BUY'
                elif avg_score < -0.3:
                    signals['overall_signal'] = 'SELL'
                else:
                    signals['overall_signal'] = 'HOLD'
            
            return signals
            
        except Exception as e:
            logger.error("Failed to generate signals", error=str(e))
            return {'overall_signal': 'HOLD', 'signal_strength': 0.0, 'signals': {}}
    
    def get_supported_symbols(self) -> Dict[str, List[str]]:
        """Get list of commonly supported symbols by category"""
        return {
            'stocks': [
                'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX',
                'SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'VOO'
            ],
            'forex': [
                'EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X', 'USDCAD=X',
                'USDCHF=X', 'NZDUSD=X', 'EURGBP=X', 'EURJPY=X', 'GBPJPY=X'
            ],
            'crypto': [
                'BTC-USD', 'ETH-USD', 'ADA-USD', 'DOT-USD', 'LTC-USD',
                'XRP-USD', 'LINK-USD', 'BCH-USD', 'XLM-USD', 'ETC-USD'
            ],
            'commodities': [
                'GC=F',  # Gold
                'SI=F',  # Silver
                'CL=F',  # Crude Oil
                'NG=F',  # Natural Gas
                'HG=F',  # Copper
            ]
        }

