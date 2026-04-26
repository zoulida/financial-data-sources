from __future__ import annotations

import pandas as pd

from ._base import adv, decay_linear, delta, rank, returns, ts_rank


def compute_alpha039(close_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    if close_df.empty or volume_df.empty:
        return close_df.copy()
    return -rank(delta(close_df, 7) * (1 - rank(decay_linear(volume_df / adv(volume_df, 20), 9)))) * (1 + rank(ts_rank(returns(close_df), 250)))
