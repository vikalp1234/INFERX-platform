import sys


def test_python_is_3_12():
    assert sys.version_info[:2] == (3, 12)


def test_app_package_importable():
    import app  # noqa: F401
