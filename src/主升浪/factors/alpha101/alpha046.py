from __future__ import annotations

import pandas as pd

from ._base import delay, delta


def compute_alpha046(close_df: pd.DataFrame) -> pd.DataFrame:
    if close_df.empty:
        return close_df.copy()
    slope = (delay(close_df, 20) - delay(close_df, 10)) / 10 - (delay(close_df, 10) - close_df) / 10
    result = pd.DataFrame(-delta(close_df, 1), index=close_df.index, columns=close_df.columns)
    result = result.where(~(slope > 0.25), -1.0)
    result = result.where(~(slope < 0), 1.0)
    return result
