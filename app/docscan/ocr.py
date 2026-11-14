"""Preprocessing + OCR engines. Engines share a tiny interface so they can be swapped/benchmarked."""
from dataclasses import dataclass
from typing import Protocol

import cv2
import numpy as np


@dataclass
class OcrResult:
    text: str
    confidence: float  # 0-100
    engine: str


class Engine(Protocol):
    name: str

    def run(self, image: np.ndarray) -> OcrResult: ...


def preprocess(image: np.ndarray) -> np.ndarray:
    """Grayscale -> denoise -> adaptive threshold. Cheap and helps on scans/photos."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    gray = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)


class TesseractEngine:
    name = "tesseract"

    def run(self, image: np.ndarray) -> OcrResult:
        import pytesseract  # imported lazily so the API image/tests don't need the binary

        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        words = [(w, float(c)) for w, c in zip(data["text"], data["conf"]) if w.strip() and float(c) >= 0]
        text = pytesseract.image_to_string(image).strip()
        conf = sum(c for _, c in words) / len(words) if words else 0.0
        return OcrResult(text=text, confidence=round(conf, 2), engine=self.name)


def load_image(path: str) -> np.ndarray:
    img = cv2.imread(path)
    if img is None:
        raise ValueError(f"cannot decode image: {path}")
    return img


def run_ocr(path: str, engine: Engine) -> OcrResult:
    return engine.run(preprocess(load_image(path)))
