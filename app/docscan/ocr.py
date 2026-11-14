"""Preprocessing + OCR engines. Engines share a tiny interface so they can be swapped/benchmarked."""
from dataclasses import dataclass
from typing import Protocol

import cv2
import numpy as np

cv2.setNumThreads(1)  # one worker = one core; parallelism comes from replicas, not threads


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

        # single Tesseract pass: derive both text and confidence from image_to_data
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        lines: dict[tuple, list[str]] = {}
        confs: list[float] = []
        for i, word in enumerate(data["text"]):
            conf = float(data["conf"][i])
            if not word.strip() or conf < 0:
                continue
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            lines.setdefault(key, []).append(word)
            confs.append(conf)
        text = "\n".join(" ".join(ws) for _, ws in sorted(lines.items()))
        conf = sum(confs) / len(confs) if confs else 0.0
        return OcrResult(text=text, confidence=round(conf, 2), engine=self.name)


def load_image(path: str) -> np.ndarray:
    img = cv2.imread(path)
    if img is None:
        raise ValueError(f"cannot decode image: {path}")
    return img


def run_ocr(path: str, engine: Engine) -> OcrResult:
    return engine.run(preprocess(load_image(path)))
