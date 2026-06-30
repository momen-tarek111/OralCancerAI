"""
core/test_runner.py
────────────────────
Wraps the AI pipeline from test_script.py in a QThread-safe worker.

Model weight paths — edit the four MODEL_* constants below to point
to your local .pth files before running the application.

Result dict emitted by `finished` signal:
    status            : "Negative" | "PreCancer" | "Positive"
    stage             : "Stage 1" | "Stage 2" | "Stage 3" | ""
    label             : raw model label (normal/osmf/wdoscc/mdoscc/pdoscc)
    original_path     : str — copy of the input image saved to a tmp file
    segmentation_path : str — B&W mask saved to a tmp file
    heatmap_path      : str — Grad-CAM XAI heatmap saved to a tmp file
    classified_path   : str — coloured disease overlay saved to a tmp file
    error             : str — non-empty only on failure
"""

import os
import tempfile
import shutil

from PySide6.QtCore import QObject, Signal, QThread

from core.utils import resource_path

# ── ▶  UPDATE THESE PATHS TO YOUR LOCAL MODEL FILES  ◀ ───────
MODEL_SEG_PATH  = resource_path("models/weights/unet_weights2.pth")
MODEL_4_PATH    = resource_path("models/weights/best_convnext_4.pth")
MODEL_2_PATH    = resource_path("models/weights/best_efficientnet_2.pth")
MODEL_5_PATH    = resource_path("models/weights/best_convnext_5.pth")

# ─────────────────────────────────────────────────────────────

# Label → (UI status, UI stage)
_LABEL_MAP = {
    "normal": ("Negative",  ""),
    "osmf":   ("PreCancer", ""),
    "pdoscc": ("Positive",  "Stage 1"),
    "mdoscc": ("Positive",  "Stage 2"),
    "wdoscc": ("Positive",  "Stage 3"),
}


def _tmp_png() -> str:
    fd, path = tempfile.mkstemp(suffix=".png", prefix="htc_exam_")
    os.close(fd)
    return path


def _save_np_as_png(arr, path: str):
    """Save a numpy RGB array as a PNG using PIL (no matplotlib window)."""
    from PIL import Image as PILImage
    import numpy as np
    if arr.dtype != "uint8":
        arr = (arr * 255).clip(0, 255).astype("uint8")
    PILImage.fromarray(arr).save(path)


# ─────────────────────────────────────────────────────────────
#  WORKER  — runs on a background QThread
# ─────────────────────────────────────────────────────────────
class ModelWorker(QObject):
    finished = Signal(dict)
    progress = Signal(int)   # 0-100

    def __init__(self, image_path: str):
        super().__init__()
        self._image_path = image_path

    def run(self):
        result = {
            "status":            "",
            "stage":             "",
            "label":             "",
            "original_path":     "",
            "segmentation_path": "",
            "heatmap_path":      "",
            "classified_path":   "",
            "patch_labels":      [],   # list[16] — raw model label per patch
            "error":             "",
        }

        try:
            import cv2
            import torch
            import torch.nn as nn
            import numpy as np
            from PIL import Image
            from torchvision.models import (
                convnext_tiny, efficientnet_b4, ConvNeXt_Tiny_Weights)
            from torchvision import transforms
            from pytorch_grad_cam import GradCAM
            from pytorch_grad_cam.utils.image import show_cam_on_image

            device  = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            softmax = nn.Softmax(dim=1)

            # ── Save a copy of the original image ────────────
            orig_tmp = _tmp_png()
            shutil.copy2(self._image_path, orig_tmp)
            result["original_path"] = orig_tmp

            # ── Read image ───────────────────────────────────
            self.progress.emit(5)
            img_bgr = cv2.imread(self._image_path)
            if img_bgr is None:
                raise ValueError(f"Cannot read image: {self._image_path}")
            img = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

            # ════════════════════════════════════════════════
            #  STEP 1 — Segmentation (UNet)
            # ════════════════════════════════════════════════
            self.progress.emit(10)

            class DoubleConv(nn.Module):
                def __init__(self, in_ch, out_ch):
                    super().__init__()
                    self.conv = nn.Sequential(
                        nn.Conv2d(in_ch, out_ch, 3, padding=1, bias=False),
                        nn.BatchNorm2d(out_ch), nn.ReLU(inplace=True),
                        nn.Conv2d(out_ch, out_ch, 3, padding=1, bias=False),
                        nn.BatchNorm2d(out_ch), nn.ReLU(inplace=True),
                    )
                def forward(self, x): return self.conv(x)

            class UNet(nn.Module):
                def __init__(self):
                    super().__init__()
                    self.enc1 = DoubleConv(3, 64);   self.enc2 = DoubleConv(64, 128)
                    self.enc3 = DoubleConv(128, 256); self.enc4 = DoubleConv(256, 512)
                    self.pool = nn.MaxPool2d(2)
                    self.bottleneck = DoubleConv(512, 1024)
                    self.up4  = nn.ConvTranspose2d(1024, 512, 2, 2)
                    self.dec4 = DoubleConv(1024, 512)
                    self.up3  = nn.ConvTranspose2d(512, 256, 2, 2)
                    self.dec3 = DoubleConv(512, 256)
                    self.up2  = nn.ConvTranspose2d(256, 128, 2, 2)
                    self.dec2 = DoubleConv(256, 128)
                    self.up1  = nn.ConvTranspose2d(128, 64, 2, 2)
                    self.dec1 = DoubleConv(128, 64)
                    self.out  = nn.Conv2d(64, 1, 1)

                def forward(self, x):
                    e1 = self.enc1(x);  e2 = self.enc2(self.pool(e1))
                    e3 = self.enc3(self.pool(e2)); e4 = self.enc4(self.pool(e3))
                    b  = self.bottleneck(self.pool(e4))
                    d4 = self.dec4(torch.cat([self.up4(b),  e4], dim=1))
                    d3 = self.dec3(torch.cat([self.up3(d4), e3], dim=1))
                    d2 = self.dec2(torch.cat([self.up2(d3), e2], dim=1))
                    d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))
                    return self.out(d1)

            seg_model = UNet()
            seg_model.load_state_dict(
                torch.load(MODEL_SEG_PATH, map_location=device))
            seg_model.to(device).eval()

            # Run segmentation
            img_resized = cv2.resize(img, (256, 256)) / 255.0
            img_t = torch.tensor(img_resized).permute(2, 0, 1).float().unsqueeze(0)
            with torch.no_grad():
                pred = seg_model(img_t.to(device))
                pred = torch.sigmoid(pred)
            mask = pred[0, 0].cpu().numpy()
            mask = (mask > 0.5).astype(np.uint8)
            mask = cv2.resize(mask, (img.shape[1], img.shape[0]),
                              interpolation=cv2.INTER_NEAREST)

            # Save B&W mask as PNG
            seg_tmp = _tmp_png()
            _save_np_as_png((mask * 255).astype(np.uint8), seg_tmp)
            result["segmentation_path"] = seg_tmp
            del seg_model
            self.progress.emit(30)

            # ════════════════════════════════════════════════
            #  STEP 2 — Load classification models
            # ════════════════════════════════════════════════
            transform_4 = transforms.Compose([
                transforms.Resize((224, 224)), transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406],
                                     [0.229, 0.224, 0.225]),
            ])
            transform_2 = transforms.Compose([
                transforms.Resize((380, 380)), transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406],
                                     [0.229, 0.224, 0.225]),
            ])
            transform_5 = ConvNeXt_Tiny_Weights.DEFAULT.transforms()

            model_4 = convnext_tiny(weights=None)
            model_4.classifier[2] = nn.Linear(
                model_4.classifier[2].in_features, 4)
            model_4.load_state_dict(
                torch.load(MODEL_4_PATH, map_location=device))
            model_4.to(device).eval()

            model_2 = efficientnet_b4(weights=None)
            model_2.classifier[1] = nn.Linear(
                model_2.classifier[1].in_features, 2)
            model_2.load_state_dict(
                torch.load(MODEL_2_PATH, map_location=device))
            model_2.to(device).eval()

            model_5 = convnext_tiny(weights=None)
            model_5.classifier[2] = nn.Linear(
                model_5.classifier[2].in_features, 5)
            model_5.load_state_dict(
                torch.load(MODEL_5_PATH, map_location=device))
            model_5.to(device).eval()

            self.progress.emit(50)

            # ════════════════════════════════════════════════
            #  STEP 3 — Classify full image
            # ════════════════════════════════════════════════
            img_pil = Image.fromarray(img)

            with torch.no_grad():
                probs4 = softmax(model_4(
                    transform_4(img_pil).unsqueeze(0).to(device))
                )[0].cpu().numpy()

                probs2 = softmax(model_2(
                    transform_2(img_pil).unsqueeze(0).to(device))
                )[0].cpu().numpy()

                probs5 = softmax(model_5(
                    transform_5(img_pil).unsqueeze(0).to(device))
                )[0].cpu().numpy()

            fp = {"normal": 0, "osmf": 0, "pdoscc": 0,
                  "mdoscc": 0, "wdoscc": 0}
            
            fp["normal"]  += probs4[0]
            fp["osmf"]    += probs4[1]
            fp["pdoscc"]  += probs4[2]
            oscc = probs4[3]
            fp["mdoscc"]  += oscc * probs2[0]
            fp["wdoscc"]  += oscc * probs2[1]
            fp["mdoscc"]  += probs5[0]
            fp["normal"]  += probs5[1]
            fp["osmf"]    += probs5[2]
            fp["pdoscc"]  += probs5[3]
            fp["wdoscc"]  += probs5[4]


            label         = max(fp, key=fp.get)
            status, stage = _LABEL_MAP.get(label, ("Negative", ""))
            result["label"]  = label
            result["status"] = status
            result["stage"]  = stage
            self.progress.emit(65)

            # ════════════════════════════════════════════════
            #  STEP 4 — Patch-level classification + heatmap
            # ════════════════════════════════════════════════
            def classify_patch(patch_np):
                p_pil = Image.fromarray(patch_np)
                with torch.no_grad():
                    pf4 = softmax(model_4(
                        transform_4(p_pil).unsqueeze(0).to(device))
                    )[0].cpu().numpy()
                    pf2 = softmax(model_2(
                        transform_2(p_pil).unsqueeze(0).to(device))
                    )[0].cpu().numpy()
                    pf5 = softmax(model_5(
                        transform_5(p_pil).unsqueeze(0).to(device))
                    )[0].cpu().numpy()
                pp = {"normal": 0, "osmf": 0, "pdoscc": 0,
                      "mdoscc": 0, "wdoscc": 0}
                pp["normal"]  += pf4[0]; pp["osmf"]   += pf4[1]
                pp["pdoscc"]  += pf4[2]
                osc = pf4[3]
                pp["mdoscc"]  += osc * pf2[0]; pp["wdoscc"] += osc * pf2[1]
                pp["mdoscc"]  += pf5[0]; pp["normal"]  += pf5[1]
                pp["osmf"]    += pf5[2]; pp["pdoscc"]  += pf5[3]
                pp["wdoscc"]  += pf5[4]
                return max(pp, key=pp.get)

            h, w, _ = img.shape
            grid    = 4
            ph, pw  = h // grid, w // grid
            heatmap = np.zeros((h, w, 3), dtype=np.uint8)

            _COLOR = {
                "osmf":   np.array([173, 216, 230]),
                "pdoscc": np.array([255, 255, 0]),
                "mdoscc": np.array([255, 165, 0]),
                "wdoscc": np.array([255, 0,   0]),
            }

            patch_labels = []
            for i in range(grid):
                for j in range(grid):
                    y1, y2 = i * ph, (i + 1) * ph
                    x1, x2 = j * pw, (j + 1) * pw
                    patch_cls = classify_patch(img[y1:y2, x1:x2])
                    patch_labels.append(patch_cls)        # ← NEW: store label
                    if patch_cls in _COLOR:
                        patch_mask = mask[y1:y2, x1:x2]
                        heatmap[y1:y2, x1:x2][patch_mask == 1] = \
                            _COLOR[patch_cls]
                        print(patch_cls)
            result["patch_labels"] = patch_labels

            overlay   = cv2.addWeighted(img, 0.7, heatmap, 0.6, 0)
            heat_tmp  = _tmp_png()
            _save_np_as_png(overlay, heat_tmp)
            result["classified_path"] = heat_tmp
            self.progress.emit(80)

            # ════════════════════════════════════════════════
            #  STEP 5 — Grad-CAM XAI map
            # ════════════════════════════════════════════════
            input_tensor = transform_4(img_pil).unsqueeze(0).to(device)
            img_small    = cv2.resize(img, (224, 224))
            img_float    = img_small.astype(np.float32) / 255.0

            cam = GradCAM(model=model_4,
                          target_layers=[model_4.features[-1]])
            grayscale_cam = cam(input_tensor=input_tensor)[0]
            cam_image     = show_cam_on_image(
                img_float, grayscale_cam, use_rgb=True)
            cam_image     = cv2.resize(
                cam_image, (img.shape[1], img.shape[0]))

            cls_tmp = _tmp_png()
            _save_np_as_png(cam_image, cls_tmp)
            result["heatmap_path"] = cls_tmp
            self.progress.emit(100)

        except Exception as e:
            import traceback
            result["error"] = traceback.format_exc()
            print(f"[ModelWorker] error: {e}")

        self.finished.emit(result)


# ─────────────────────────────────────────────────────────────
#  ModelRunner — public convenience wrapper
# ─────────────────────────────────────────────────────────────
class ModelRunner:
    """
    Usage:
        runner = ModelRunner(image_path)
        runner.finished.connect(my_callback)   # callback(result_dict)
        runner.progress.connect(my_pct_cb)     # callback(int 0-100)
        runner.start()
    """

    def __init__(self, image_path: str):
        self._thread = QThread()
        self._worker = ModelWorker(image_path)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self.finished = self._worker.finished
        self.progress = self._worker.progress

    def start(self):
        self._thread.start()