from datetime import datetime, timedelta
from enum import Enum, StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO, TypedDict

import numpy as np
from construct.lib import Container, ListContainer
from loguru import logger as log

from janus_ssmm_tlm_info.janus_pkt import SSMM, SciPacket

if TYPE_CHECKING:
    import pandas as pd


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


_PRIMARY_HEADER_SIZE = 6  # bytes; fixed-size CCSDS packet primary header


def _packet_size_from_primary_header(header: bytes) -> int:
    """Compute a packet's total on-disk size from its 6-byte CCSDS primary header.

    The header's last 16 bits are PACKET_DATA_FIELD_LENGTH which, per CCSDS
    convention, holds (data field length in octets) - 1.
    """
    data_field_length = int.from_bytes(header[4:6], "big") + 1
    return _PRIMARY_HEADER_SIZE + data_field_length


def _scan_packet_offsets(fh: BinaryIO, file_size: int) -> list[tuple[int, int]]:
    """Walk a SciPacket stream reading only each packet's 6-byte primary header.

    Returns the ``(offset, size)`` of every packet in the file. This is far
    cheaper than a full construct parse since packet bodies -- in particular
    image payloads, the bulk of an SSMM file -- are never read.
    """
    offsets = []
    offset = 0
    while offset + _PRIMARY_HEADER_SIZE <= file_size:
        fh.seek(offset)
        size = _packet_size_from_primary_header(fh.read(_PRIMARY_HEADER_SIZE))
        if offset + size > file_size:
            log.warning(
                "Truncated trailing packet at offset {} while scanning; ignoring.",
                offset,
            )
            break
        offsets.append((offset, size))
        offset += size
    return offsets


def first_and_last_packets(file: Path) -> tuple[tuple[Container, ...], int]:
    """Fully parse only the first and last packets of an SSMM file.

    Locates packet boundaries with :func:`_scan_packet_offsets`, which reads
    just the 6-byte primary header of every packet, then parses only the
    first and last packet bodies in full. Used by the ``quick`` mode of
    :func:`ssm_file_info` to avoid materializing every packet (including all
    image data) when a fast, approximate summary is enough.

    Returns:
        A ``(packets, n_packets)`` pair, where ``packets`` is ``(first,)`` if
        the file holds a single packet, ``(first, last)`` otherwise, or
        ``()`` if the file has no packets at all; ``n_packets`` is the exact
        total packet count found while scanning.
    """
    file_size = file.stat().st_size
    with file.open("rb") as fh:
        offsets = _scan_packet_offsets(fh, file_size)
        if not offsets:
            return (), 0

        first_off, first_size = offsets[0]
        fh.seek(first_off)
        first_bytes = fh.read(first_size)

        if len(offsets) == 1:
            return (SciPacket.parse(first_bytes),), 1

        last_off, last_size = offsets[-1]
        fh.seek(last_off)
        last_bytes = fh.read(last_size)

    packets = (SciPacket.parse(first_bytes), SciPacket.parse(last_bytes))
    return packets, len(offsets)


def ssm_file_info(
    file: Path | str,
    use_spice: bool = True,
    quick: bool = False,
) -> _SSMMFileInfo:
    """Retrieve information on the content of a SSMM file.

    Args:
        file: Path to the input SSMM file.
        use_spice: Convert on-board times to UTC via SPICE (requires a metakernel
            to already be furnished). If ``False``, times are treated as raw.
        quick: If ``True``, only the file's first and last packets are parsed
            (see :func:`first_and_last_packets`) instead of every packet. This
            is much faster on large files but ``nimages``, ``apids`` and
            ``sessions`` become approximations based on just those two packets
            rather than the full file; ``npacks``, ``start_time`` and
            ``end_time`` remain exact.

    Returns:
        dictionary: info on the provided ssmm file.

    Notes:
    Needs spice kernel to be already loaded to perform sc-time to utc conversion.
    Unless ``quick`` is set, it is slow as it reads all packets.
    """

    file = Path(file)  # ensure is a path

    if quick:
        endpoint_packets, npacks = first_and_last_packets(file)
        ssmm = Container(packets=ListContainer(endpoint_packets))
    else:
        ssmm = SSMM.parse_file(file)
        npacks = len(ssmm.packets)

    source = determine_peu_source(ssmm)

    if source is None:
        if npacks == 0:
            msg = f"File {file.name} contains no packets (empty or unreadable file)."
            raise ValueError(msg)
        msg = (
            f"Unknown PEU source for file {file.name}. "
            "Please check the PEU version registry."
        )
        raise ValueError(msg)

    if source == KNOWN_PEUS_VERSION.JANUS and not use_spice:
        log.warning(
            "Janus PEU requires SPICE for time conversion. Please set use_spice=True.",
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


class _SSMMGroupSummary(TypedDict):
    """One row of a time-gap summary: files whose telemetry falls within the gap threshold."""

    n_files: int
    file_names: list[str]
    start_time: str
    end_time: str
    npacks: int
    nimages: int
    apids: list[int]
    sessions: list[int]
    source: str


def _summarize_group(group: list[_SSMMFileInfo]) -> _SSMMGroupSummary:
    starts = [info["start_time"] for info in group if info["start_time"]]
    ends = [info["end_time"] for info in group if info["end_time"]]
    apids = sorted({apid for info in group for apid in info["apids"]})
    sessions = sorted({session for info in group for session in info["sessions"]})
    sources = {info["source"] for info in group}

    return {
        "n_files": len(group),
        "file_names": [info["file_name"] for info in group],
        "start_time": min(starts) if starts else "",
        "end_time": max(ends) if ends else "",
        "npacks": sum(info["npacks"] for info in group),
        "nimages": sum(info["nimages"] for info in group),
        "apids": apids,
        "sessions": sessions,
        "source": next(iter(sources)) if len(sources) == 1 else "mixed",
    }


def summarize_infos_by_time_gap(
    infos: list[_SSMMFileInfo],
    gap_hours: float = 24.0,
) -> list[_SSMMGroupSummary]:
    """Group per-file SSMM info into contiguous blocks of telemetry.

    Files are sorted by ``start_time`` and grouped consecutively: a new group
    starts whenever the gap between the running end of the current group and
    the next file's ``start_time`` exceeds ``gap_hours``. Files with no usable
    timing info (empty ``start_time``/``end_time``) are each reported as their
    own singleton group, appended after all timed groups.

    Args:
        infos: Per-file info dicts as produced by :func:`ssm_file_info`.
        gap_hours: Minimum gap, in hours, between two files' telemetry for
            them to be considered separate blocks (default: ``24.0``).

    Returns:
        A list of group summaries, timed groups first in chronological order,
        followed by any untimed files as singleton groups.
    """
    gap = timedelta(hours=gap_hours)

    timed = [info for info in infos if info["start_time"] and info["end_time"]]
    untimed = [info for info in infos if not (info["start_time"] and info["end_time"])]

    timed.sort(key=lambda info: info["start_time"])

    groups: list[list[_SSMMFileInfo]] = []
    group_end: datetime | None = None
    for info in timed:
        start = datetime.fromisoformat(info["start_time"])
        end = datetime.fromisoformat(info["end_time"])
        if groups and group_end is not None and start - group_end <= gap:
            groups[-1].append(info)
            group_end = max(group_end, end)
        else:
            groups.append([info])
            group_end = end

    summaries = [_summarize_group(group) for group in groups]
    summaries.extend(_summarize_group([info]) for info in untimed)
    return summaries


def reduce_ssmm_file(
    file: Path | str,
    images: int | slice | list[int] = 5,
    output_suffix: str = "_reduced",
    output_file: Path | str | None = None,
) -> Path:
    """Read an SSMM file, retain a selection of images, and write to an output file.

    Args:
        file: Path to the input SSMM file.
        images: Images to retain, identified by their position in the file (0-based).
            - ``int``: keep the first *N* images (default: ``5``).
            - ``slice``: keep the images at the sliced positions, e.g. ``slice(2, 7)``.
            - ``list[int]``: keep images at the given indices, e.g. ``[0, 2, 4]``.
        output_suffix: Suffix appended to the input filename when ``output_file`` is not given
            (default: ``'_reduced'``).
        output_file: Explicit output path. If provided, ``output_suffix`` is ignored.

    Returns:
        Path to the written output file.
    """
    file = Path(file)

    if output_file is None:
        output_file = file.with_name(file.name + output_suffix)
    else:
        output_file = Path(output_file)

    ssmm = SSMM.parse_file(file)

    # Collect all unique (SESSION_ID, IMG_COUNT) pairs in order of first occurrence
    all_images: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for pkt in ssmm.packets:
        sh = pkt.science_header
        key = (sh.SESSION_ID, sh.IMG_COUNT)
        if key not in seen:
            seen.add(key)
            all_images.append(key)

    # Resolve the selection to a set of image keys
    if isinstance(images, int):
        keep = set(all_images[:images])
    elif isinstance(images, slice):
        keep = set(all_images[images])
    else:
        keep = {all_images[i] for i in images}

    # Collect packets for the selected images, preserving file order
    selected: list[object] = [
        pkt
        for pkt in ssmm.packets
        if (pkt.science_header.SESSION_ID, pkt.science_header.IMG_COUNT) in keep
    ]

    out = b"".join(SciPacket.build(pkt) for pkt in selected)
    output_file.write_bytes(out)

    log.info(
        f"Reduced {file.name}: retained {len(keep)} image(s) "
        f"({len(selected)} packets) → {output_file.name}",
    )

    return output_file


def _image_keys(file: Path) -> set[tuple[int, int]]:
    """Parse one SSMM file and return its set of (SESSION_ID, IMG_COUNT) image keys.

    Uses SSMM.parse_file + search_all, the same lightweight idiom already used
    by ssm_file_info for SESSION_ID/IMG_COUNT extraction -- deliberately avoids
    ssm_file_info() itself, which additionally does SPICE-based COARSE_TIME/
    FINE_TIME -> UTC conversion per packet, unneeded here.
    """
    ssmm = SSMM.parse_file(file)
    sessions = ssmm.search_all("SESSION_ID")
    im_counts = ssmm.search_all("IMG_COUNT")
    return set(zip(sessions, im_counts, strict=True))


def group_files_by_shared_images(files: list[Path]) -> list[list[Path]]:
    """Group SSMM files into connected components that share at least one image.

    Two files belong in the same group if they share at least one
    ``(SESSION_ID, IMG_COUNT)`` packet key -- i.e. tm2raw would need both to
    reassemble at least one image completely. Sharing is transitive: if A
    shares an image with B, and B shares a different image with C, then A, B,
    and C form a single group even though A and C may share nothing directly.
    Files that share no image with any other file form singleton groups.

    Args:
        files: SSMM files to inspect, order-independent.

    Returns:
        A list of groups (each a list of Paths); every input file appears in
        exactly one group.
    """
    file_keys = {f: _image_keys(f) for f in files}

    parent = {f: f for f in files}

    def find(f: Path) -> Path:
        while parent[f] != f:
            parent[f] = parent[parent[f]]
            f = parent[f]
        return f

    def union(a: Path, b: Path) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    # Invert to image key -> files, then union every pair of files sharing a key.
    key_to_files: dict[tuple[int, int], list[Path]] = {}
    for f in files:
        for key in file_keys[f]:
            key_to_files.setdefault(key, []).append(f)

    for group_files in key_to_files.values():
        for other in group_files[1:]:
            union(group_files[0], other)

    groups: dict[Path, list[Path]] = {}
    for f in files:
        groups.setdefault(find(f), []).append(f)

    return list(groups.values())


def _flatten_container(
    container: Container,
    parent_key: str = "",
    sep: str = ".",
) -> dict:
    """Recursively flatten a construct ``Container`` into a flat ``{key: value}`` dict.

    Nested containers are flattened with their keys joined by ``sep`` and prefixed
    by the parent key (so e.g. ``header`` + ``APID`` becomes ``header.APID``). This
    avoids collisions between identically named fields living in different sub-structs
    (e.g. ``VERSION_NUMBER`` in both ``header`` and ``data_field_header``). Construct's
    private keys (those starting with ``_``) are skipped.
    """
    items: dict = {}
    for key, value in container.items():
        if key.startswith("_"):
            continue
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        if isinstance(value, Container):
            items.update(_flatten_container(value, new_key, sep))
        else:
            items[new_key] = value
    return items


def ssmm_packets_dataframe(
    file: Path | str,
    include_image_data: bool = False,
) -> "pd.DataFrame":
    """Parse an SSMM file into a ``pandas.DataFrame`` with one row per packet.

    Every field of every packet (packet header, data field header, science header,
    nested image-info struct and science data) is flattened into its own column.
    Column names are dotted paths reflecting the nesting, e.g. ``header.APID``,
    ``science_header.IMG_INFO.Binning``.

    Args:
        file: Path to the input SSMM file.
        include_image_data: If ``False`` (default), the raw ``IMG_DATA`` byte payload
            is dropped, as it is large and rarely useful in tabular form. Set to
            ``True`` to keep it as a ``bytes`` column.

    Returns:
        A ``pandas.DataFrame`` with one row per packet.
    """
    import pandas as pd

    file = Path(file)
    ssmm = SSMM.parse_file(file)

    rows = [_flatten_container(pkt) for pkt in ssmm.packets]

    df = pd.DataFrame(rows)

    if not include_image_data:
        df = df.drop(
            columns=[c for c in df.columns if c.endswith("IMG_DATA")],
            errors="ignore",
        )

    return df


def packets_to_images_dataframe(packets: "pd.DataFrame") -> "pd.DataFrame":
    """Reduce a per-packet DataFrame to one row per image.

    An image is identified by the ``(SESSION_ID, IMG_COUNT)`` pair. Image-level
    metadata (the ``IMG_INFO`` struct) is only carried by a single packet of each
    image, so for every column the first non-null value within the group is taken;
    this collapses the sparse per-packet rows into a single, fully-populated image
    row. A ``n_packets`` column with the number of packets making up each image is
    appended.

    Args:
        packets: A per-packet DataFrame as produced by :func:`ssmm_packets_dataframe`.

    Returns:
        A ``pandas.DataFrame`` with one row per image, in order of first appearance.
    """
    key_cols = ["science_header.SESSION_ID", "science_header.IMG_COUNT"]
    missing = [c for c in key_cols if c not in packets.columns]
    if missing:
        raise KeyError(
            f"packets DataFrame is missing required column(s): {missing}. "
            "Pass a DataFrame produced by ssmm_packets_dataframe().",
        )

    grouped = packets.groupby(key_cols, sort=False)
    # .first() skips NaN, so the single packet carrying IMG_INFO wins for those columns
    images = grouped.first()
    images["n_packets"] = grouped.size()
    return images.reset_index()


def ssmm_images_dataframe(
    file: Path | str,
    include_image_data: bool = False,
) -> "pd.DataFrame":
    """Parse an SSMM file into a ``pandas.DataFrame`` with one row per image.

    Convenience wrapper that parses ``file`` into a per-packet table and reduces it
    with :func:`packets_to_images_dataframe`.

    Args:
        file: Path to the input SSMM file.
        include_image_data: Forwarded to :func:`ssmm_packets_dataframe`; kept for
            symmetry, though image data is rarely meaningful once collapsed.

    Returns:
        A ``pandas.DataFrame`` with one row per image.
    """
    packets = ssmm_packets_dataframe(file, include_image_data=include_image_data)
    return packets_to_images_dataframe(packets)


def determine_peu_source(ssmm_parsed: SSMM) -> KNOWN_PEUS_VERSION | None:
    """Check if the file is a flight data file.
    Return None if it is an unknown PEU version, or if no H_Version could be
    found at all (e.g. an empty or packet-less file).
    """

    raw_version = ssmm_parsed.search("H_Version")
    if raw_version is None:
        return None

    version = hex(raw_version)
    return PEU_VERSION_REGISTRY.get(version, None)
