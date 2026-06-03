"""Optional Segment Anything backend with controlled fallback behavior."""

from __future__ import annotations

from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

try:
    from models import ExtractedRegion
    from segmentation.segmenter import AdvancedSegmenter
except ImportError:  # pragma: no cover - package import path
    from ..models import ExtractedRegion
    from .segmenter import AdvancedSegmenter


class SAMUnavailableError(RuntimeError):
    """Raised when SAM dependencies are not installed in the active venv."""


class OptionalSAMSegmenter:
    """SAM wrapper that can fall back to ``AdvancedSegmenter`` without crashing."""

    def __init__(
        self,
        image: np.ndarray,
        model_name: str = "facebook/sam-vit-base",
        device: Optional[str] = None,
        fallback: bool = True,
    ):
        self.image = image
        self.model_name = model_name
        self.fallback = fallback
        self._pipeline = None
        self._processor = None
        self._model = None
        self._torch = None

        try:
            from transformers import SamModel, SamProcessor, pipeline
            import torch
        except ImportError as exc:
            if fallback:
                self.fallback_reason = "torch/transformers non installati; uso AdvancedSegmenter"
                self._fallback_segmenter = AdvancedSegmenter(image, debug=True)
                return
            raise SAMUnavailableError(
                "Installa torch e transformers per usare SAM, oppure abilita fallback=True"
            ) from exc

        self._torch = torch
        self._pipeline_factory = pipeline
        self._processor = SamProcessor.from_pretrained(model_name)
        self._model = SamModel.from_pretrained(model_name)
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        if self.device == "cuda":
            self._model = self._model.to("cuda")
        self.fallback_reason = None
        self._fallback_segmenter = None

    def segment(self, n_colors: int = 40, min_area: int = 500) -> List[ExtractedRegion]:
        """Run automatic SAM mask generation or fall back to AdvancedSegmenter."""
        if self._fallback_segmenter is not None:
            return self._fallback_segmenter.segment(n_colors=n_colors, min_area=min_area)

        generator = self._pipeline_factory(
            "mask-generation",
            model=self.model_name,
            device=0 if self.device == "cuda" else -1,
            points_per_batch=64,
        )
        image_rgb = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
        outputs = generator(Image.fromarray(image_rgb), points_per_batch=64)
        return self._outputs_to_regions(outputs, image_rgb, min_area)

    def segment_at_point(self, x: int, y: int, tolerance: int = 25) -> Optional[ExtractedRegion]:
        """Run SAM prompt segmentation from a click coordinate ``(x, y)``."""
        if self._fallback_segmenter is not None:
            return self._fallback_segmenter.segment_at_point(x, y, tolerance=tolerance)

        image_rgb = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        inputs = self._processor(pil_image, input_points=[[[x, y]]], return_tensors="pt")
        if self.device == "cuda":
            inputs = {key: value.to("cuda") for key, value in inputs.items()}

        with self._torch.no_grad():
            outputs = self._model(**inputs)

        masks = self._processor.image_processor.post_process_masks(
            outputs.pred_masks.cpu(),
            inputs["original_sizes"].cpu(),
            inputs["reshaped_input_sizes"].cpu(),
        )
        scores = outputs.iou_scores.cpu().numpy()[0]
        best_idx = int(np.argmax(scores[0]))
        mask = masks[0][0][best_idx].numpy().astype(np.uint8)
        regions = self._mask_to_regions(mask, image_rgb, min_area=100, score=float(scores[0][best_idx]))
        return max(regions, key=lambda region: region.area) if regions else None

    def _outputs_to_regions(self, outputs: dict, image_rgb: np.ndarray, min_area: int) -> List[ExtractedRegion]:
        regions = []
        masks = outputs.get("masks", [])
        scores = outputs.get("scores", [0.0] * len(masks))
        for mask, score in zip(masks, scores):
            regions.extend(self._mask_to_regions(np.array(mask).astype(np.uint8), image_rgb, min_area, float(score)))
        regions.sort(key=lambda region: region.area, reverse=True)
        return regions

    def _mask_to_regions(
        self,
        mask: np.ndarray,
        image_rgb: np.ndarray,
        min_area: int,
        score: float,
    ) -> List[ExtractedRegion]:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        regions = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area:
                continue
            moments = cv2.moments(contour)
            if moments["m00"] <= 0:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            masked_pixels = image_rgb[mask > 0]
            if len(masked_pixels):
                r, g, b = np.mean(masked_pixels, axis=0).astype(int)
                color = (int(b), int(g), int(r))
            else:
                color = (128, 128, 128)
            regions.append(
                ExtractedRegion(
                    contour=contour,
                    centroid=(float(moments["m10"] / moments["m00"]), float(moments["m01"] / moments["m00"])),
                    area=float(area),
                    bbox=(int(x), int(y), int(w), int(h)),
                    color=color,
                    score=score,
                )
            )
        return regions

