import importlib_metadata

__version__ = importlib_metadata.version("janus_ssmm_tlm_info")


from .packets import ssm_file_info

__all__ = ["ssm_file_info"]