"""IoU and element scoring utilities for layered detection."""
from __future__ import annotations

from detection.element_model import DetectedElement


def bbox_iou(a: dict, b: dict) -> float:
  """Intersection-over-union for two bboxes with x/y/w/h or width/height."""
  ax, ay = a.get("x", 0), a.get("y", 0)
  aw = a.get("w", a.get("width", 0))
  ah = a.get("h", a.get("height", 0))
  bx, by = b.get("x", 0), b.get("y", 0)
  bw = b.get("w", b.get("width", 0))
  bh = b.get("h", b.get("height", 0))
  x1 = max(ax, bx)
  y1 = max(ay, by)
  x2 = min(ax + aw, bx + bw)
  y2 = min(ay + bh, by + bh)
  if x2 <= x1 or y2 <= y1:
    return 0.0
  inter = (x2 - x1) * (y2 - y1)
  union = aw * ah + bw * bh - inter
  return inter / union if union > 0 else 0.0


def dedupe_elements(elements: list[DetectedElement], iou_threshold: float = 0.7) -> list[DetectedElement]:
  """Merge overlapping elements, keeping higher confidence."""
  if not elements:
    return []
  sorted_elems = sorted(elements, key=lambda e: e.confidence, reverse=True)
  kept: list[DetectedElement] = []
  for elem in sorted_elems:
    bbox = {"x": elem.x, "y": elem.y, "w": elem.width, "h": elem.height}
    if any(bbox_iou(bbox, {"x": k.x, "y": k.y, "w": k.width, "h": k.height}) > iou_threshold for k in kept):
      continue
    kept.append(elem)
  return kept


def score_element_match(
  elem: DetectedElement,
  *,
  name: str | None = None,
  role: str | None = None,
  automation_id: str | None = None,
  class_name: str | None = None,
) -> float:
  """Score how well an element matches query props (0..1)."""
  score = 0.0
  weight = 0.0
  if automation_id:
    weight += 0.4
    if elem.automation_id and automation_id.lower() in elem.automation_id.lower():
      score += 0.4
  if name:
    weight += 0.35
    if elem.name and name.lower() in elem.name.lower():
      score += 0.35
  if role:
    weight += 0.15
    if elem.role and role.lower() in elem.role.lower():
      score += 0.15
  if class_name:
    weight += 0.1
    if elem.class_name and class_name.lower() in elem.class_name.lower():
      score += 0.1
  if weight == 0:
    return elem.confidence
  return min(1.0, score / weight * elem.confidence)
