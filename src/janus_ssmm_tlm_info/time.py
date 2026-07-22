import datetime

import spiceypy
from quick_spice_manager import QuickSpiceManager

_ops_kernels_manager: QuickSpiceManager | None = None


def ensure_ops_kernels_loaded() -> None:
    """Load the standard 'ops' metakernel via QuickSpiceManager, once per process.

    No-op on subsequent calls: kernel loading is expensive, and once the
    'ops' kernels are furnished they cover any time in the mission for which
    on-board time conversion is needed.
    """
    global _ops_kernels_manager  # noqa: PLW0603 - lazy process-wide singleton
    if _ops_kernels_manager is None:
        _ops_kernels_manager = QuickSpiceManager(mk="ops")
        _ops_kernels_manager.load_kernels()


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
