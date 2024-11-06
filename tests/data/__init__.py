from io import StringIO
from pathlib import Path


def get_simple_ssmm() -> Path:
    return Path(__file__).parent / "JAN1_37000010_2024.233.14.56.21.608"


def splitted_A() -> Path:
    return Path(__file__).parent / "splitted/JAN2_4700000A_2024.234.16.25.54.129"


def splitted_B() -> Path:
    return Path(__file__).parent / "splitted/JAN2_4700000B_2024.234.19.25.53.112"


def joined() -> Path:
    return Path(__file__).parent / "JAN2_4700000AB_joined"


def small_test_data() -> Path:
    return Path(__file__).parent / "test.bin"


from planetary_coverage import TourConfig


def pytest_cache_dir() -> Path:
    return Path(__file__).parent.parent.parent / ".pytest_cache"

def tour_config() -> TourConfig:
    return TourConfig(
        instrument="JUICE_JANUS",
        download_kernels=True,
        kernels_dir=pytest_cache_dir() / "spice_kernels",
        load_kernels=True,
        mk="ops",
    )
