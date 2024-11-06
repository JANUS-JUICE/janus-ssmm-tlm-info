from click.testing import CliRunner

from janus_ssmm_tlm_info.cli import main
from tests.data import small_test_data, tour_config

tc = tour_config()
meta = tc.kernels[0]

ssmm = small_test_data()





def test_hello_world() -> None:
  runner = CliRunner()
  with meta as m:
    result = runner.invoke(main, [str(ssmm), '--metakernel', f"{m}"])
  assert result.exit_code == 0
#   assert result.output == 'Hello Peter!\n'
