from backtesting.historical_cases import HISTORICAL_CASES
from backtesting.runner import run_backtest

if __name__ == "__main__":
    for key, case in HISTORICAL_CASES.items():
        results = run_backtest(case)
        print(key, len(results))
