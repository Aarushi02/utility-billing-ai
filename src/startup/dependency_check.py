import subprocess


def validate_dependencies():
    """
    Validate all required tariff-processing dependencies
    before the API starts serving requests.
    """

    # Ghostscript
    subprocess.run(
        ["gs", "--version"],
        check=True,
        capture_output=True,
        text=True
    )

    # Poppler
    subprocess.run(
        ["pdfinfo", "-v"],
        check=True,
        capture_output=True,
        text=True
    )

    # Camelot
    import camelot

    # OpenCV
    import cv2

    print(f"Ghostscript OK")
    print(f"Poppler OK")
    print(f"Camelot OK: {camelot.__version__}")
    print(f"OpenCV OK: {cv2.__version__}")