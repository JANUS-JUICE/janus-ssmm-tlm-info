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
@click.argument("filename", type=click.Path(exists=True, dir_okay=False))
@click.option("-m", "--metakernel", type=click.Path(exists=True, dir_okay=False))
def main(filename: click.Path, metakernel: click.Path) -> None:


    spiceypy.furnsh(str(metakernel))

    info = ssm_file_info(str(filename))
    for key, value in info.items():
        click.echo(f"{key}: {value}")
