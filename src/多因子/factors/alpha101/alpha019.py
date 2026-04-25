from __future__ import annotations

import pandas as pd

from ._base import delay, rank, sign, sum_ts


def compute_alpha019(close_df: pd.DataFrame) -> pd.DataFrame:
    if close_df.empty:
        return close_df.copy()
    delta7 = close_df.diff(7)
    signed_term = -sign((close_df - delay(close_df, 7)) + delta7)
    strength_term = 1 + rank(1 + sum_ts(close_df.pct_change(), 250))
    return signed_term * strength_term

