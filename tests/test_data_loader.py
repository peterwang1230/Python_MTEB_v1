import unittest
import pandas as pd
from src.mteb_v1.data_loader import DataLoader

class TestDataLoader(unittest.TestCase):

    def test_resample_to_timeframe(self):
        # Create sample hourly data
        dates = pd.date_range('2023-01-01', periods=100, freq='h')
        df = pd.DataFrame({
            'Open': [100 + i for i in range(100)],
            'High': [105 + i for i in range(100)],
            'Low': [95 + i for i in range(100)],
            'Close': [102 + i for i in range(100)],
            'Volume': [1000 for _ in range(100)]
        }, index=dates)

        # Resample to daily
        daily = DataLoader.resample_to_timeframe(df, '1D')
        self.assertIsInstance(daily, pd.DataFrame)
        self.assertIn('Open', daily.columns)

    def test_yahoo_symbol_candidates_prefers_tw_suffix_for_numeric_tickers(self):
        self.assertEqual(
            DataLoader.yahoo_symbol_candidates('2330'),
            ['2330.TW', '2330.TWO', '2330'],
        )

    def test_yahoo_symbol_candidates_keeps_explicit_suffix(self):
        self.assertEqual(DataLoader.yahoo_symbol_candidates('2330.TW'), ['2330.TW'])

    def test_resample_to_timeframe_accepts_legacy_uppercase_hour_alias(self):
        dates = pd.date_range('2023-01-01', periods=4, freq='30min')
        df = pd.DataFrame({
            'Open': [100, 101, 102, 103],
            'High': [101, 102, 103, 104],
            'Low': [99, 100, 101, 102],
            'Close': [100, 101, 102, 103],
            'Volume': [1000, 1000, 1000, 1000]
        }, index=dates)

        hourly = DataLoader.resample_to_timeframe(df, '1H')

        self.assertEqual(len(hourly), 2)
        self.assertEqual(hourly.iloc[0]['Volume'], 2000)

    def test_resample_to_timeframe_accepts_yfinance_minute_alias(self):
        dates = pd.date_range('2023-01-01', periods=4, freq='15min')
        df = pd.DataFrame({
            'Open': [100, 101, 102, 103],
            'High': [101, 102, 103, 104],
            'Low': [99, 100, 101, 102],
            'Close': [100, 101, 102, 103],
            'Volume': [1000, 1000, 1000, 1000]
        }, index=dates)

        fifteen_minute = DataLoader.resample_to_timeframe(df, '15m')

        self.assertEqual(len(fifteen_minute), 4)
        self.assertEqual(fifteen_minute.iloc[-1]['Close'], 103)

if __name__ == '__main__':
    unittest.main()
