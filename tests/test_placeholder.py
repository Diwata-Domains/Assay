import assay


def test_version() -> None:
    assert isinstance(assay.__version__, str)
    assert len(assay.__version__) > 0
