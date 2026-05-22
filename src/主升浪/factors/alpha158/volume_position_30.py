from __future__ import annotations

import pandas as pd

from ._base import _ts_minmax_position


def compute_volume_position_30(volume_df: pd.DataFrame) -> pd.DataFrame:
    """成交量在过去30日最小值与最大值之间的位置。"""
    if volume_df.empty:
        return volume_df.copy()
    return _ts_minmax_position(volume_df, 30)

