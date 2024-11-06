from pathlib import Path

from janus_ssmm_tlm_info import ssm_file_info

from tests.data import small_test_data


from tests.data import tour_config

tc = tour_config()



def test_info():
    ssm_file_info(small_test_data())
