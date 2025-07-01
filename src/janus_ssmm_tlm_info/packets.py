from enum import Enum, StrEnum
from pathlib import Path
from typing import TypedDict

import numpy as np

from janus_ssmm_tlm_info.janus_pkt import SSMM
from loguru import logger as log

class KNOWN_PEUS_VERSION(StrEnum):
    """Known PEU versions."""

    JANUS = "JANUS"
    SIS = "SIS"



PEU_VERSION_REGISTRY = {
    "0x48a": KNOWN_PEUS_VERSION.JANUS,
    "0x458": KNOWN_PEUS_VERSION.SIS,
}


class _SSMMFileInfo(TypedDict):
    """Just to highlight the content of the return type."""

    file_name: str
    nimages: int
    start_time: str
    end_time: str
    npacks: int
    apids: list[int]
    sessions: list[int]
    source: str


def ssm_file_info(file: Path | str, use_spice: bool = True) -> _SSMMFileInfo:
    """Retrieve information on the content of a SSMM file.

    Returns:
        dictionary: info on the provided ssmm file.

    Notes:
    Needs spice kernel to be already loaded to perform sc-time to utc conversion.
    It is quite slow as it reads all packages.
    """

    file = Path(file)  # ensure is a path

    ssmm = SSMM.parse_file(file)

    source = determine_peu_source(ssmm)

    if source is None:
        raise ValueError(
            f"Unknown PEU source for file {file.name}. "
            "Please check the PEU version registry."
        )
    
    if source == KNOWN_PEUS_VERSION.JANUS and not use_spice:
        log.warning(
            "Janus PEU requires SPICE for time conversion. "
            "Please set use_spice=True."
        )

    apids = np.unique(ssmm.search_all("APID")).tolist()
    sessions = ssmm.search_all("SESSION_ID")
    usessions = np.unique(sessions).tolist()

    coarse, fine = (
        ssmm.search_all("COARSE_TIME"),
        ssmm.search_all("FINE_TIME"),
    )

    im_counts = ssmm.search_all("IMG_COUNT")

    n_images = len(set(zip(sessions, im_counts, strict=False)))

    from janus_ssmm_tlm_info.time import (
        coarse_fine_to_datetime,
        coarse_fine_to_datetime_rem,
    )

    if use_spice:
        time_converter = coarse_fine_to_datetime
    else:
        time_converter = coarse_fine_to_datetime_rem

    utc = [time_converter(c, f) for c, f in zip(coarse, fine, strict=False)]

    if len(utc) > 0:
        start_time = min(utc).isoformat()
        end_time = max(utc).isoformat()
    else:
        start_time = ""
        end_time = ""

    npacks = len(ssmm.packets)

    return {
        "file_name": file.name,
        "nimages": n_images,
        "npacks": npacks,
        "apids": apids,
        "sessions": usessions,
        "start_time": start_time,
        "end_time": end_time,
        "source": str(source),
    }


def determine_peu_source(ssmm_parsed: SSMM) -> KNOWN_PEUS_VERSION | None:
    """Check if the file is a flight data file.
    Return None if it is an unknown PEU version.
    """

    version = hex(ssmm_parsed.search('H_Version'))
    return PEU_VERSION_REGISTRY.get(version, None)
