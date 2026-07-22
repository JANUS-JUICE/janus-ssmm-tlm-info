import json
import sys
from datetime import datetime

import spiceypy
from loguru import logger as log

from janus_ssmm_tlm_info import log_enable
from janus_ssmm_tlm_info.packets import ssm_file_info, summarize_infos_by_time_gap

try:
    import click
except ImportError:
    log.error(
        "Click not found: if you need to use the cli tool, install janus_ssmm_tlm_info with its cli extra: pip install janus_ssmm_tlm_info[cli] or install click in your environment",
    )
    sys.exit(0)

from rich.console import Console
from rich.table import Table


def _format_duration(start_time: str, end_time: str) -> str:
    if not start_time or not end_time:
        return ""
    total_seconds = int(
        (
            datetime.fromisoformat(end_time) - datetime.fromisoformat(start_time)
        ).total_seconds(),
    )
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts = [f"{days}d"] if days else []
    parts += [f"{hours}h"] if hours or days else []
    parts.append(f"{minutes}m")
    return " ".join(parts)


def _files_table(infos: list) -> Table:
    table = Table(title="SSMM files")
    table.add_column("file")
    table.add_column("source")
    table.add_column("start_time")
    table.add_column("end_time")
    table.add_column("npacks", justify="right")
    table.add_column("nimages", justify="right")
    table.add_column("apids")
    table.add_column("sessions")
    for info in infos:
        table.add_row(
            info["file_name"],
            info["source"],
            info["start_time"],
            info["end_time"],
            str(info["npacks"]),
            str(info["nimages"]),
            ", ".join(str(a) for a in info["apids"]),
            ", ".join(str(s) for s in info["sessions"]),
        )
    return table


def _groups_table(groups: list, gap_hours: float) -> Table:
    table = Table(title=f"SSMM telemetry blocks (new block after a gap > {gap_hours}h)")
    table.add_column("#", justify="right")
    table.add_column("files", justify="right")
    table.add_column("start_time")
    table.add_column("end_time")
    table.add_column("duration")
    table.add_column("npacks", justify="right")
    table.add_column("nimages", justify="right")
    table.add_column("source")
    table.add_column("apids")
    table.add_column("sessions")
    for i, group in enumerate(groups, start=1):
        table.add_row(
            str(i),
            str(group["n_files"]),
            group["start_time"],
            group["end_time"],
            _format_duration(group["start_time"], group["end_time"]),
            str(group["npacks"]),
            str(group["nimages"]),
            group["source"],
            ", ".join(str(a) for a in group["apids"]),
            ", ".join(str(s) for s in group["sessions"]),
        )
    return table


def _stats_table(infos: list) -> Table:
    table = Table(title="stats", show_header=False)
    table.add_column("metric")
    table.add_column("value", justify="right")
    table.add_row("Total SSMM files", str(len(infos)))
    table.add_row("Total images", str(sum(info["nimages"] for info in infos)))
    table.add_row("Total packets", str(sum(info["npacks"] for info in infos)))
    return table


@click.command(name="janus-ssmm-tlm-info")
@click.argument("filename", type=click.Path(exists=True, dir_okay=False), nargs=-1)
@click.option(
    "-m",
    "--metakernel",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
)
@click.option(
    "--stat/--no-stat",
    default=True,
    help="If set, print statistics at the end of the output.",
    show_default=True,
    is_flag=True,
)
@click.option(
    "--quick/--no-quick",
    default=False,
    help=(
        "If set, only parse each file's first and last packet instead of every "
        "packet. Much faster on large files, but nimages/apids/sessions become "
        "approximations based on just those two packets."
    ),
    show_default=True,
    is_flag=True,
)
@click.option(
    "--raw/--no-raw",
    default=False,
    help="Output JSON instead of a formatted table.",
    show_default=True,
    is_flag=True,
)
@click.option(
    "--summary/--no-summary",
    default=False,
    help=(
        "Summarize files into contiguous blocks of telemetry, splitting on gaps "
        "larger than --gap-hours, instead of listing every file."
    ),
    show_default=True,
    is_flag=True,
)
@click.option(
    "--gap-hours",
    type=float,
    default=24.0,
    help="Gap, in hours, between files' telemetry that starts a new block in --summary mode.",
    show_default=True,
)
def main(
    filename: list[click.Path],
    metakernel: click.Path,
    stat: bool,
    quick: bool,
    raw: bool,
    summary: bool,
    gap_hours: float,
) -> None:
    log_enable()

    if metakernel:
        spiceypy.furnsh(str(metakernel))
        use_spice = True
    else:
        log.info(
            "No metakernel provided: SPICE kernels will be auto-loaded via "
            "QuickSpiceManager(mk='ops') only if a file requires them "
            "(e.g. JANUS PEU); other sources fall back to raw timestamps.",
        )
        use_spice = None

    allinfos = []
    for item in filename:
        try:
            info = ssm_file_info(str(item), use_spice=use_spice, quick=quick)
        except Exception as exc:
            log.error(f"Skipping {item}: {exc}")
            continue
        allinfos.append(info)

    rows = (
        summarize_infos_by_time_gap(allinfos, gap_hours=gap_hours)
        if summary
        else allinfos
    )

    if raw:
        payload = {"groups" if summary else "files": rows}
        if stat:
            payload["stats"] = {
                "total_files": len(allinfos),
                "total_images": sum(info["nimages"] for info in allinfos),
                "total_packets": sum(info["npacks"] for info in allinfos),
            }
        click.echo(json.dumps(payload, indent=2))
        return

    console = Console()
    console.print(_groups_table(rows, gap_hours) if summary else _files_table(rows))

    if stat:
        console.print(_stats_table(allinfos))
