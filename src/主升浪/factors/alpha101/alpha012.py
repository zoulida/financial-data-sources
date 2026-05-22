from __future__ import annotations

import pandas as pd

from ._base import sign


def compute_alpha012(volume_df: pd.DataFrame, close_df: pd.DataFrame) -> pd.DataFrame:
    if volume_df.empty or close_df.empty:
        return close_df.copy()
    return sign(volume_df.diff(1)) * (-close_df.diff(1))

