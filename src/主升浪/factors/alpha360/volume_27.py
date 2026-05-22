from __future__ import annotations

import pandas as pd

from ._base import volume_lag_ratio


def compute_volume_27(volume_df: pd.DataFrame) -> pd.DataFrame:
    return volume_lag_ratio(volume_df, 27)
