import unittest
import pandas as pd
from src.mteb_v1.indicators import Indicators

class TestIndicators(unittest.TestCase):

    def setUp(self):
        # Create sample data
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        self.df = pd.DataFrame({
            'High': [100 + i + (i % 10) for i in range(100)],
            'Low': [90 + i - (i % 10) for i in range(100)],
            'Close': [95 + i for i in range(100)],
            'Volume': [1000 + i * 10 for i in range(100)]
        }, index=dates)

    def test_pivot_points(self):
        pivot_high, pivot_low = Indicators.pivot_points(self.df, 5)
        self.assertIsInstance(pivot_high, pd.Series)
        self.assertIsInstance(pivot_low, pd.Series)
        self.assertFalse(pivot_high.isna().any())
        self.assertFalse(pivot_low.isna().any())
        self.assertEqual(pivot_high.dtype, bool)
        self.assertEqual(pivot_low.dtype, bool)

    def test_pivot_points_does_not_mark_every_bar_as_a_pivot(self):
        df = pd.DataFrame({
            'High': [1, 2, 5, 2, 1, 2, 3],
            'Low': [1, 0, 1, 2, 1, 0, 1],
            'Close': [1, 1, 4, 2, 1, 1, 2],
            'Volume': [100 for _ in range(7)]
        }, index=pd.date_range('2023-01-01', periods=7, freq='D'))

        pivot_high, pivot_low = Indicators.pivot_points(df, 1)

        self.assertEqual(pivot_high.tolist(), [False, False, True, False, False, False, False])
        self.assertEqual(pivot_low.tolist(), [False, True, False, False, False, True, False])

    def test_ema(self):
        ema = Indicators.ema(self.df['Close'], 20)
        self.assertEqual(len(ema), len(self.df))
        self.assertTrue(ema.iloc[-1] > 0)

if __name__ == '__main__':
    unittest.main()
