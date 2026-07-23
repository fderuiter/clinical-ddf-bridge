"""Pure-Python Statistical Outlier Detection Engine.

Provides algorithms for identifying statistical anomalies in clinical datasets
without using third-party scientific or data analysis libraries (such as NumPy, SciPy, or Pandas).
"""

import math
from typing import Any, Dict, List, Optional, Tuple


def calculate_mean(values: List[float]) -> float:
    """Calculate the arithmetic mean of a list of floats.

    Args:
        values (List[float]): A list of numeric values.

    Returns:
        float: The mean value. Returns 0.0 if the list is empty.
    """
    if not values:
        return 0.0
    return sum(values) / len(values)


def calculate_sample_std_dev(values: List[float], mean: float) -> float:
    """Calculate the sample standard deviation of a list of floats.

    Uses Bessel's correction (n - 1) in the denominator.

    Args:
        values (List[float]): A list of numeric values.
        mean (float): The pre-calculated mean of the values.

    Returns:
        float: The sample standard deviation. Returns 0.0 if fewer than 2 elements.
    """
    n = len(values)
    if n < 2:
        return 0.0
    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    return math.sqrt(variance)


def calculate_median(values: List[float]) -> float:
    """Calculate the median of a list of floats.

    Args:
        values (List[float]): A list of numeric values.

    Returns:
        float: The median value. Returns 0.0 if the list is empty.
    """
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 1:
        return sorted_vals[mid]
    return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0


def calculate_mad(values: List[float], median: float) -> float:
    """Calculate the Median Absolute Deviation (MAD) of a list of floats.

    Args:
        values (List[float]): A list of numeric values.
        median (float): The pre-calculated median of the values.

    Returns:
        float: The MAD value.
    """
    if not values:
        return 0.0
    deviations = [abs(x - median) for x in values]
    return calculate_median(deviations)


def calculate_percentile(values: List[float], p: float) -> float:
    """Calculate the p-th percentile of a list of floats using linear interpolation.

    Args:
        values (List[float]): A list of numeric values.
        p (float): The percentile to compute, between 0 and 100 inclusive.

    Returns:
        float: The computed percentile.
    """
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0]

    idx = (n - 1) * (p / 100.0)
    floor_idx = int(idx)
    ceil_idx = min(floor_idx + 1, n - 1)

    if floor_idx == ceil_idx:
        return sorted_vals[floor_idx]

    weight = idx - floor_idx
    return sorted_vals[floor_idx] * (1.0 - weight) + sorted_vals[ceil_idx] * weight


def detect_zscore_outliers(
    values: List[float], threshold: float = 3.0
) -> List[Dict[str, Any]]:
    """Detect outliers using the Standard Z-Score method.

    Formula: Z_i = (X_i - Mean) / StdDev. Flags if |Z_i| > threshold.

    Args:
        values (List[float]): The dataset of numeric values.
        threshold (float, optional): The standard deviation threshold. Defaults to 3.0.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries representing the detected outliers.
    """
    if len(values) < 2:
        return []

    mean = calculate_mean(values)
    std_dev = calculate_sample_std_dev(values, mean)

    # If all values are identical, there are no outliers.
    if std_dev == 0.0:
        return []

    outliers = []
    for i, val in enumerate(values):
        z_score = (val - mean) / std_dev
        if abs(z_score) > threshold:
            outliers.append(
                {
                    "index": i,
                    "value": val,
                    "score": z_score,
                    "method": "zscore",
                    "reason": f"Value {val} is {abs(z_score):.2f} standard deviations away from the mean ({mean:.2f}).",
                }
            )
    return outliers


def detect_modified_zscore_outliers(
    values: List[float], threshold: float = 3.5
) -> List[Dict[str, Any]]:
    """Detect outliers using the Robust Modified Z-Score method.

    Formula: M_i = 0.6745 * (X_i - Median) / MAD. Flags if |M_i| > threshold.

    Args:
        values (List[float]): The dataset of numeric values.
        threshold (float, optional): The MAD threshold. Defaults to 3.5.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries representing the detected outliers.
    """
    if not values:
        return []

    median = calculate_median(values)
    mad = calculate_mad(values, median)

    # If MAD is 0, we can fall back to checking if absolute deviation from median is zero.
    # To prevent division by zero, we skip scoring if MAD is 0 unless value != median.
    outliers = []
    for i, val in enumerate(values):
        if mad == 0.0:
            m_score = 0.0
        else:
            m_score = (0.6745 * (val - median)) / mad

        if abs(m_score) > threshold:
            outliers.append(
                {
                    "index": i,
                    "value": val,
                    "score": m_score,
                    "method": "modified_zscore",
                    "reason": f"Value {val} has a modified Z-score of {abs(m_score):.2f}, exceeding the threshold ({threshold}).",
                }
            )
    return outliers


def detect_tukey_outliers(
    values: List[float], k: float = 1.5
) -> List[Dict[str, Any]]:
    """Detect outliers using Tukey's Fences method.

    Formula: IQR = Q3 - Q1. Bounds: [Q1 - k * IQR, Q3 + k * IQR].

    Args:
        values (List[float]): The dataset of numeric values.
        k (float, optional): Fence multiplier (1.5 for mild, 3.0 for extreme).
            Defaults to 1.5.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries representing the detected outliers.
    """
    if len(values) < 4:
        # Tukey's fences is not robust with extremely small sample sizes
        return []

    q1 = calculate_percentile(values, 25.0)
    q3 = calculate_percentile(values, 75.0)
    iqr = q3 - q1

    lower_fence = q1 - k * iqr
    upper_fence = q3 + k * iqr

    outliers = []
    for i, val in enumerate(values):
        if val < lower_fence or val > upper_fence:
            outliers.append(
                {
                    "index": i,
                    "value": val,
                    "bounds": (lower_fence, upper_fence),
                    "method": "tukey",
                    "reason": f"Value {val} is outside Tukey's Fence boundary [{lower_fence:.2f}, {upper_fence:.2f}] with k={k}.",
                }
            )
    return outliers
