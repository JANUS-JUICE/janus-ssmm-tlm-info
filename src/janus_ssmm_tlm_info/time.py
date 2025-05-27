import datetime


import spiceypy


def coarse_fine_to_datetime(coarse: int, fine: int) -> datetime.datetime:
    tstring = f"{coarse}.{fine}"
    et = spiceypy.scs2e(-28, tstring)
    sc_time = spiceypy.et2datetime(et)
    return sc_time


# def unix_ticks_to_datetime(ticks: int) -> datetime.datetime:
#             if "/" in time:
#             time = time.split("/")[1]
#         parts = time.split(":")
#         ticks = int(parts[0]) + int(parts[1]) / 65536


#         tt = Timestamp(datetime.fromtimestamp(ticks, pytz.utc))
def coarse_fine_to_datetime_rem(coarse: int, fine: int) -> datetime.datetime:
    ticks = coarse + fine / 65536

    return datetime.datetime.fromtimestamp(ticks)
