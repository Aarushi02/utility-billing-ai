import subprocess
import camelot
import cv2

from fastapi import APIRouter

router = APIRouter()

@router.get("/health/tariff")
def tariff_health():

    subprocess.run(
        ["gs", "--version"],
        check=True
    )

    subprocess.run(
        ["pdfinfo", "-v"],
        check=True
    )

    return {
        "status": "healthy",
        "camelot": camelot.__version__,
        "opencv": cv2.__version__
    }