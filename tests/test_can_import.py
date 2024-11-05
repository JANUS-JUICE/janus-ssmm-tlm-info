def test_import_package():
    """Verify we can import the main package"""
    import janus_ssmm_tlm_info

def test_has_version():
    """Check that the package has an accesible __version__"""
    import janus_ssmm_tlm_info
    version = janus_ssmm_tlm_info.__version__