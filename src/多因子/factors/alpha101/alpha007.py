from __future__ import annotations

import pandas as pd

from ._base import adv, delta, sign, ts_rank


def compute_alpha007(close_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    if close_df.empty or volume_df.empty:
        return close_df.copy()
    adv20 = adv(volume_df, 20)
    delta7 = delta(close_df, 7)
    signal = -ts_rank(delta7.abs(), 60) * sign(delta7)
    return signal.where(adv20 < volume_df, -1.0)
