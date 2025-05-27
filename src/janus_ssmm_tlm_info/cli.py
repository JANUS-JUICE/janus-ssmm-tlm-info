import sys

import spiceypy
from loguru import logger as log

from janus_ssmm_tlm_info.packets import ssm_file_info

try:
    import click
except ImportError:
    log.error(
        "Click not found: if you need to use the cli tool, install janus_ssmm_tlm_info with its cli extra: pip install janus_ssmm_tlm_info[cli] or install click in your environment",
    )
    sys.exit(0)


@click.command(name="janus-ssmm-tlm-info")
@click.argument("filename", type=click.Path(exists=True, dir_okay=False), nargs=-1)
@click.option(
    "-m", "--metakernel", type=click.Path(exists=True, dir_okay=False), default=None
)
@click.option(
    "--stat/--no-stat",
    default=True,
    help="If set, print statistics at the end of the output.",
    show_default=True,
    is_flag=True,
)
def main(filename: list[click.Path], metakernel: click.Path, stat: bool) -> None:
    if metakernel:
        spiceypy.furnsh(str(metakernel))
        use_spice = True
    else:
        log.warning(
            "No metakernel provided, considering times as unix timestamps (i.e. data coming from GRM)."
        )
        use_spice = False

    allinfos = []
    for item in filename:
        info = ssm_file_info(str(item), use_spice=use_spice)
        allinfos.append(info)

    for info in allinfos:
        click.echo("------------------------------")
        for key, value in info.items():
            click.echo(f"{key}: {value}")

    if stat:
        click.echo("------------------------------")
        click.echo("stats:")
        click.echo(f"Total SSMM files: {len(allinfos)}")
        click.echo(f"Total images: {sum(info['nimages'] for info in allinfos)}")
        click.echo(f"Total packets: {sum(info['npacks'] for info in allinfos)}")
