from pathlib import Path
from typing import TypedDict

import numpy as np

from janus_ssmm_tlm_info.janus_pkt import SSMM


class _SSMMFileInfo(TypedDict):
    """Just to highlight the content of the return type."""

    file_name: str
    start_time: str
    end_time: str
    npacks: int
    apids: list[int]
    sessions: list[int]


def ssm_file_info(file: Path | str) -> _SSMMFileInfo:
    """Retrieve information on the content of a SSMM file.

    Returns:
        dictionary: info on the provided ssmm file.

    Notes:
    Needs spice kernel to be already loaded to perform sc-time to utc conversion.
    It is quite slow as it reads all packages.
    """

    file = Path(file)  # ensure is a path

    ssmm = SSMM.parse_file(file)

    apids = np.unique(ssmm.search_all("APID")).tolist()

    sessions = np.unique(ssmm.search_all("SESSION_ID")).tolist()

    coarse, fine = (
        ssmm.search_all("COARSE_TIME"),
        ssmm.search_all("FINE_TIME"),
    )

    from janus_ssmm_tlm_info.time import coarse_fine_to_datetime

    utc = [coarse_fine_to_datetime(c, f) for c, f in zip(coarse, fine, strict=False)]

    if len(utc) > 0:
        start_time = min(utc).isoformat()
        end_time = max(utc).isoformat()
    else:
        start_time = None
        end_time = None

    npacks = len(ssmm.packets)

    return {
        "file_name": file.name,
        "npacks": npacks,
        "apids": apids,
        "sessions": sessions,
        "start_time": start_time,
        "end_time": end_time,
    }
