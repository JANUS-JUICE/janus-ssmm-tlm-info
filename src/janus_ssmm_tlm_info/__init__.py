import sys

from loguru import logger as log

import importlib.metadata as metadata



__version__ = metadata.version("janus_ssmm_tlm_info")

log.disable("janus_ssmm_tlm_info")

def log_enable(
    level: str = "INFO", mod: str = "janus_ssmm_tlm_info", remove_handlers: bool = True
) -> None:
    """Enable logging for a given module at specific level, by default it operates on the whole module."""
    if remove_handlers:
        log.remove()
    log.enable(mod)
    log.add(sys.stderr, level=level)


def log_enable_debug() -> None:
    """Enable debug logging for a given module, by default it operates on the whole module."""
    log_enable(level="DEBUG")


def log_disable(mod: str = "janus_ssmm_tlm_info") -> None:
    """Totally disable logging from this module, by default it operates on the whole module."""
    log.disable(mod)

from .packets import ssm_file_info

__all__ = ["ssm_file_info"]