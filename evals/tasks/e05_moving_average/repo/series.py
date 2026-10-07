"""Simple time-series helpers."""


def moving_average(values: list[float], window: int) -> list[float]:
    """Average of each run of `window` consecutive values.

    moving_average([1, 2, 3, 4], 2) -> [1.5, 2.5, 3.5]
    """
    if window < 1:
        raise ValueError("window must be at least 1")
    if window > len(values):
        return []
    return [sum(values[i : i + window]) / window for i in range(len(values) - window)]


def percent_change(old: float, new: float) -> float:
    if old == 0:
        raise ZeroDivisionError("percent change from zero is undefined")
    return (new - old) / old * 100
