from backtesting.evaluator import evaluate_trend
import pandas as pd


def test_evaluate_trend():
    df = pd.DataFrame({"date": [1, 2], "downside_prob": [0.2, 0.4]})
    out = evaluate_trend(df)
    assert out["change"] == 0.2
