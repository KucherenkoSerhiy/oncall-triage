class NotAnAlert(Exception):  # noqa: N818 - name fixed by spec
    """Raised by an adapter when the payload does not represent a firing alert."""
