from pathlib import Path

from janus_ssmm_tlm_info import ssm_file_info

test_data = Path(__file__).parent / "data" / "test.bin"

from planetary_coverage import TourConfig

cfg = TourConfig(
    instrument="JUICE_JANUS",
    download_kernels=True,
    kernels_dir="test-kernels",
    load_kernels=True,
    mk="ops",
)


def test_info():
    ssm_file_info(test_data)
