from xtquant import xtdata
import time
from datetime import datetime

tick = xtdata.get_full_tick(['SH', 'SZ'])
print(tick)
