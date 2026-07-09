def test_safecode_package_imports():
    import safecode
    import safecode.cli
    import safecode.models

    assert isinstance(safecode.__version__, str)
    assert safecode.__version__
    assert safecode.cli.app is not None
