import importlib.metadata

__version__ = importlib.metadata.version("janus_ssmm_tlm_info")


from .packets import ssm_file_info

__all__ = ["ssm_file_info"]