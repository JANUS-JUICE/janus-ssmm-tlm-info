import datetime

import spiceypy


def coarse_fine_to_datetime(coarse: int, fine: int) -> datetime.datetime:
    tstring = f"{coarse}.{fine}"
    et = spiceypy.scs2e(-28, tstring)
    sc_time = spiceypy.et2datetime(et)
    return sc_time
