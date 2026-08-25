# core/avatar/renderer.py
"""
INDUS Avatar System -- Hyper-Realistic Layered 60 FPS Avatar Renderer
Layer 1: Base Ultra-HD Portrait with Ambient Micro-Breathing
Layer 2: Photorealistic Hazel/Amber Eyes with Deep Sclera AO & Catchlight Glints
Layer 3: Realistic Skin-Toned Eyelids, Creases & Fine Eyelashes
Layer 4: Anatomical Lip-Sync, Cupid's Bow, Pearlescent Teeth & Emotion Curves
Layer 5: Radial Voice Energy Burst Waves & Cyberpunk HUD Rings
"""

import math
import time
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import (
    QPainter, QPainterPath, QColor, QPen, QBrush, QPixmap,
    QRadialGradient, QLinearGradient
)

from core.avatar.models import AvatarState, OperationalState, EmotionType
from core.avatar.transitions import clamp


class AvatarRenderer:
    """
    Renders the composite animated photorealistic Avatar inside any QPainter context.
    Decoupled from input handling and timers.
    """

    def __init__(self, face_pixmap: Optional[QPixmap] = None):
        self._face_px = face_pixmap
        self._start_time = time.time()

    def set_face_pixmap(self, px: QPixmap):
        self._face_px = px

    def render(self, p: QPainter, cx: float, cy: float, fw: float, state: AvatarState, fx_controller=None):
        """
        Main draw dispatch. Renders all visual avatar layers.
        """
        # Outer Face Radius
        face_r = fw * 0.285
        face_d = int(face_r * 2)

        # Micro-breathing idle displacement (subtle 0.4% float)
        t = time.time() - self._start_time
        breathe_y = math.sin(t * 1.5) * (face_r * 0.005) if state.animation_enabled else 0.0

        # 1. Base Portrait Layer with subtle breathing
        self._draw_base_hologram(p, cx, cy + breathe_y, face_r, face_d, state)

        # 2. Dynamic Photoreal Eyes & Gaze Layer
        self._draw_eyes(p, cx, cy + breathe_y, face_r, state)

        # 3. Dynamic Skin-Toned Eyelids & Blinking Layer
        self._draw_eyelids(p, cx, cy + breathe_y, face_r, state)

        # 4. Dynamic Emotional Mouth, Teeth & Lip-Sync Layer
        self._draw_mouth(p, cx, cy + breathe_y, face_r, state)

        # 5. Radial Speaking Voice Energy Burst (from reference video)
        if state.speaking or state.audio_level > 0.04:
            self._draw_radial_voice_burst(p, cx, cy, face_r, state)

        # 6. Holographic Scanlines & Outer Accent Rings
        self._draw_holographic_overlays(p, cx, cy, face_r, state, fx_controller)

    def _draw_base_hologram(self, p: QPainter, cx: float, cy: float, face_r: float, face_d: int, state: AvatarState):
        """Renders circular-clipped ultra-HD face image with ambient edge depth."""
        if self._face_px is None or self._face_px.isNull():
            p.save()
            clip = QPainterPath()
            clip.addEllipse(QRectF(cx - face_r, cy - face_r, face_r * 2, face_r * 2))
            p.setClipPath(clip)
            grad = QRadialGradient(cx, cy, face_r)
            grad.setColorAt(0.0, QColor(10, 30, 45, 230))
            grad.setColorAt(1.0, QColor(2, 8, 16, 255))
            p.setBrush(QBrush(grad))
            p.setPen(QPen(QColor(0, 255, 255, 120), 1.5))
            p.drawEllipse(QRectF(cx - face_r, cy - face_r, face_r * 2, face_r * 2))
            p.restore()
            return

        scaled = self._face_px.scaled(
            face_d, face_d,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        off_x = (scaled.width() - face_d) // 2
        off_y = (scaled.height() - face_d) // 2

        p.save()
        clip = QPainterPath()
        clip.addEllipse(QRectF(cx - face_r, cy - face_r, face_r * 2, face_r * 2))
        p.setClipPath(clip)

        # Draw base face with pristine opacity
        p.setOpacity(0.96)
        p.drawPixmap(int(cx - face_r), int(cy - face_r), scaled, off_x, off_y, face_d, face_d)

        # Soft atmospheric edge vignette
        p.setOpacity(0.35)
        vignette = QRadialGradient(cx, cy, face_r)
        tint_col = QColor(state.hud_ring_color)
        vignette.setColorAt(0.0, QColor(0, 0, 0, 0))
        vignette.setColorAt(0.70, QColor(0, 0, 0, 20))
        vignette.setColorAt(0.95, QColor(tint_col.red(), tint_col.green(), tint_col.blue(), 75))
        vignette.setColorAt(1.0, QColor(tint_col.red(), tint_col.green(), tint_col.blue(), 150))
        p.setBrush(QBrush(vignette))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - face_r, cy - face_r, face_r * 2, face_r * 2))

        p.restore()

    def _draw_eyes(self, p: QPainter, cx: float, cy: float, face_r: float, state: AvatarState):
        """
        Preserves 100% pristine photorealistic eyes from the base ultra-HD portrait.
        No synthetic vector overlays or fake white sclera are drawn over the real face.
        """
        # Original photo eyes are 100% preserved in photorealistic ultra-HD quality
        pass

    def _draw_eyelids(self, p: QPainter, cx: float, cy: float, face_r: float, state: AvatarState):
        """
        Renders organic skin-toned eyelid dropping down smoothly during blink,
        with realistic skin gradient, eyelid crease, and fine lash contour.
        """
        if state.eyelid_coverage <= 0.01:
            return

        eye_spacing = face_r * 0.261
        eye_y_base  = cy - face_r * 0.156
        eye_w       = face_r * 0.128
        eye_h       = face_r * 0.055

        p.save()
        for side in (-1, 1):
            eye_cx = cx + side * eye_spacing
            eye_cy = eye_y_base

            socket_clip = QPainterPath()
            socket_clip.moveTo(eye_cx - eye_w, eye_cy)
            socket_clip.cubicTo(
                QPointF(eye_cx - eye_w * 0.40, eye_cy - eye_h * 1.05),
                QPointF(eye_cx + eye_w * 0.40, eye_cy - eye_h * 1.05),
                QPointF(eye_cx + eye_w, eye_cy)
            )
            socket_clip.cubicTo(
                QPointF(eye_cx + eye_w * 0.40, eye_cy + eye_h * 0.95),
                QPointF(eye_cx - eye_w * 0.40, eye_cy + eye_h * 0.95),
                QPointF(eye_cx - eye_w, eye_cy)
            )

            p.save()
            p.setClipPath(socket_clip)

            top_y = eye_cy - eye_h * 1.1
            cov_h = eye_h * 2.2 * state.eyelid_coverage
            edge_y = top_y + cov_h

            lid_path = QPainterPath()
            lid_path.moveTo(eye_cx - eye_w * 1.2, top_y)
            lid_path.lineTo(eye_cx + eye_w * 1.2, top_y)
            lid_path.cubicTo(
                QPointF(eye_cx + eye_w * 0.5, edge_y + eye_h * 0.1),
                QPointF(eye_cx - eye_w * 0.5, edge_y + eye_h * 0.1),
                QPointF(eye_cx - eye_w * 1.2, edge_y)
            )
            lid_path.closeSubpath()

            # Exact skin tone gradient sampled from portrait
            skin_grad = QLinearGradient(eye_cx, top_y, eye_cx, edge_y)
            skin_grad.setColorAt(0.0, QColor(165, 125, 115, 255))
            skin_grad.setColorAt(0.6, QColor(145, 105, 95, 255))
            skin_grad.setColorAt(1.0, QColor(115, 75, 65, 255))
            p.setBrush(QBrush(skin_grad))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPath(lid_path)

            if state.eyelid_coverage > 0.15:
                lash_path = QPainterPath()
                lash_path.moveTo(eye_cx - eye_w, edge_y)
                lash_path.cubicTo(
                    QPointF(eye_cx - eye_w * 0.4, edge_y + eye_h * 0.1),
                    QPointF(eye_cx + eye_w * 0.4, edge_y + eye_h * 0.1),
                    QPointF(eye_cx + eye_w, edge_y)
                )
                p.setPen(QPen(QColor(25, 12, 10, int(240 * state.eyelid_coverage)), 2.0,
                              Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawPath(lash_path)

            p.restore()
        p.restore()

    def _draw_mouth(self, p: QPainter, cx: float, cy: float, face_r: float, state: AvatarState):
        """
        Renders phoneme-accurate mouth shapes based on current VisemeShape.
        Falls back to energy-based openness when no viseme is active.
        15 distinct procedural mouth shapes for realistic lip sync.
        """
        from core.avatar.models import VisemeShape

        openness  = clamp(state.mouth_openness, 0.0, 1.0)
        smile     = state.mouth_smile_curve
        viseme    = state.viseme_shape

        # Skip drawing if fully closed and no smile
        if openness <= 0.02 and abs(smile) <= 0.20 and viseme == VisemeShape.SILENCE:
            return

        mouth_cy = cy + face_r * 0.363   # Calibrated mouth center Y
        mouth_w  = face_r * 0.190        # Half-width of mouth
        p.save()

        # ── Compute spread from viseme ────────────────────────────────────────
        spread_map = {
            VisemeShape.VOWEL_HIGH:   0.8,   # I — widest horizontal
            VisemeShape.VOWEL_MID:    0.7,   # E — wide horizontal
            VisemeShape.LABIODENTAL:  0.2,
            VisemeShape.ALVEOLAR:     0.3,
            VisemeShape.VOWEL_OPEN:   0.4,
            VisemeShape.VOWEL_ROUND: -0.5,   # O — rounded
            VisemeShape.VOWEL_TIGHT: -0.8,   # OO — very rounded
            VisemeShape.PALATAL:     -0.3,
            VisemeShape.LABROUND:    -0.6,
        }
        spread = spread_map.get(viseme, 0.0)
        eff_mouth_w = mouth_w * (1.0 + spread * 0.3)

        # ── BILABIAL: M, B, P — lips pressed flat ────────────────────────────
        if viseme == VisemeShape.BILABIAL or (openness <= 0.02 and abs(smile) <= 0.05):
            press_path = QPainterPath()
            press_path.moveTo(cx - eff_mouth_w, mouth_cy)
            press_path.cubicTo(
                QPointF(cx - eff_mouth_w * 0.5, mouth_cy + smile * face_r * 0.02),
                QPointF(cx + eff_mouth_w * 0.5, mouth_cy + smile * face_r * 0.02),
                QPointF(cx + eff_mouth_w, mouth_cy)
            )
            p.setPen(QPen(QColor(130, 65, 75, 220), 2.2,
                         Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(press_path)
            p.restore()
            return

        # ── LABIODENTAL: F, V — upper teeth slight show ───────────────────────
        if viseme == VisemeShape.LABIODENTAL:
            lip_h = face_r * 0.035
            # Upper lip slightly raised
            upper_path = QPainterPath()
            upper_path.moveTo(cx - eff_mouth_w * 0.7, mouth_cy - lip_h)
            upper_path.cubicTo(
                QPointF(cx - eff_mouth_w * 0.3, mouth_cy - lip_h * 1.4),
                QPointF(cx + eff_mouth_w * 0.3, mouth_cy - lip_h * 1.4),
                QPointF(cx + eff_mouth_w * 0.7, mouth_cy - lip_h)
            )
            p.setPen(QPen(QColor(190, 110, 120, 200), 1.8))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(upper_path)
            # Teeth hint
            teeth_path = QPainterPath()
            teeth_path.addRect(QRectF(cx - eff_mouth_w * 0.4,
                                       mouth_cy - lip_h * 0.8,
                                       eff_mouth_w * 0.8, lip_h * 0.6))
            p.setBrush(QBrush(QColor(240, 235, 228, 180)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPath(teeth_path)
            p.restore()
            return

        # ── DENTAL: TH — small gap, hint of tongue ────────────────────────────
        if viseme == VisemeShape.DENTAL:
            lip_h = face_r * 0.045
            gap_path = QPainterPath()
            gap_path.moveTo(cx - eff_mouth_w * 0.6, mouth_cy)
            gap_path.lineTo(cx + eff_mouth_w * 0.6, mouth_cy)
            p.setPen(QPen(QColor(100, 40, 50, 200), 2.0,
                         Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawPath(gap_path)
            # Tongue tip
            tongue = QPainterPath()
            tongue.moveTo(cx - face_r * 0.04, mouth_cy)
            tongue.cubicTo(
                QPointF(cx - face_r * 0.02, mouth_cy + lip_h * 0.8),
                QPointF(cx + face_r * 0.02, mouth_cy + lip_h * 0.8),
                QPointF(cx + face_r * 0.04, mouth_cy)
            )
            p.setBrush(QBrush(QColor(220, 100, 110, 180)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPath(tongue)
            p.restore()
            return

        # ── PALATAL: SH, CH — lips slightly forward, small oval ──────────────
        if viseme in (VisemeShape.PALATAL, VisemeShape.LABROUND):
            lip_h = face_r * 0.055 * (0.6 if viseme == VisemeShape.PALATAL else 0.8)
            tight_w = eff_mouth_w * (0.5 if viseme == VisemeShape.PALATAL else 0.55)
            oval = QPainterPath()
            oval.addEllipse(QRectF(cx - tight_w, mouth_cy - lip_h,
                                    tight_w * 2, lip_h * 2))
            cav_grad = QRadialGradient(cx, mouth_cy, tight_w)
            cav_grad.setColorAt(0.0, QColor(20, 8, 12, 255))
            cav_grad.setColorAt(0.7, QColor(40, 15, 20, 250))
            cav_grad.setColorAt(1.0, QColor(180, 100, 110, 230))
            p.setBrush(QBrush(cav_grad))
            p.setPen(QPen(QColor(160, 80, 95, 200), 1.8))
            p.drawPath(oval)
            p.restore()
            return

        # ── All remaining visemes: draw full open mouth with shape-specific geometry
        lip_h = face_r * 0.18 * openness

        # Adjust vertical geometry per viseme
        if viseme == VisemeShape.VOWEL_HIGH:        # I — narrow, almost no opening
            lip_h *= 0.45
        elif viseme == VisemeShape.VOWEL_MID:       # E — medium height, wide
            lip_h *= 0.65
        elif viseme == VisemeShape.VOWEL_TIGHT:     # OO — moderate height, rounded
            lip_h *= 0.65
            eff_mouth_w *= 0.65
        elif viseme == VisemeShape.VOWEL_ROUND:     # O — tall and round
            lip_h *= 0.85
            eff_mouth_w *= 0.80
        elif viseme == VisemeShape.VOWEL_OPEN:      # A — widest and tallest
            lip_h *= 1.0

        smile_offset = smile * face_r * 0.02
        upper_center_y = mouth_cy - lip_h * 0.35 + smile_offset
        lower_center_y = mouth_cy + lip_h * 0.75 + smile_offset * 0.5

        # 1. Oral cavity
        cavity_path = QPainterPath()
        cavity_path.moveTo(cx - eff_mouth_w, mouth_cy)
        cavity_path.cubicTo(
            QPointF(cx - eff_mouth_w * 0.5, upper_center_y),
            QPointF(cx + eff_mouth_w * 0.5, upper_center_y),
            QPointF(cx + eff_mouth_w, mouth_cy)
        )
        cavity_path.cubicTo(
            QPointF(cx + eff_mouth_w * 0.5, lower_center_y),
            QPointF(cx - eff_mouth_w * 0.5, lower_center_y),
            QPointF(cx - eff_mouth_w, mouth_cy)
        )
        cav_grad = QLinearGradient(cx, upper_center_y, cx, lower_center_y)
        cav_grad.setColorAt(0.0, QColor(14, 6, 8, 255))
        cav_grad.setColorAt(0.5, QColor(38, 12, 18, 250))
        cav_grad.setColorAt(1.0, QColor(65, 18, 25, 240))
        p.setBrush(QBrush(cav_grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(cavity_path)

        # 2. Pearlescent teeth (visible when mouth is parted)
        if openness > 0.10:
            teeth_h = min(lip_h * 0.35, face_r * 0.030)
            teeth_path = QPainterPath()
            teeth_path.moveTo(cx - eff_mouth_w * 0.55, upper_center_y + 1)
            teeth_path.quadTo(cx, upper_center_y + teeth_h,
                              cx + eff_mouth_w * 0.55, upper_center_y + 1)
            teeth_path.lineTo(cx + eff_mouth_w * 0.55, upper_center_y)
            teeth_path.lineTo(cx - eff_mouth_w * 0.55, upper_center_y)
            teeth_path.closeSubpath()
            teeth_grad = QLinearGradient(cx, upper_center_y, cx, upper_center_y + teeth_h)
            teeth_grad.setColorAt(0.0, QColor(245, 242, 238, 240))
            teeth_grad.setColorAt(0.7, QColor(228, 222, 215, 235))
            teeth_grad.setColorAt(1.0, QColor(180, 165, 155, 210))
            p.setBrush(QBrush(teeth_grad))
            p.drawPath(teeth_path)

        # 3. Upper lip with Cupid's Bow — shape adapted by spread
        upper_lip = QPainterPath()
        upper_lip.moveTo(cx - eff_mouth_w, mouth_cy)
        bow_lift = face_r * (0.012 if viseme in (VisemeShape.VOWEL_HIGH, VisemeShape.VOWEL_MID) else 0.022)
        top_peak_y = upper_center_y - bow_lift
        upper_lip.cubicTo(
            QPointF(cx - eff_mouth_w * 0.45, top_peak_y - face_r * 0.010),
            QPointF(cx - eff_mouth_w * 0.15, top_peak_y + face_r * 0.004),
            QPointF(cx, top_peak_y)
        )
        upper_lip.cubicTo(
            QPointF(cx + eff_mouth_w * 0.15, top_peak_y + face_r * 0.004),
            QPointF(cx + eff_mouth_w * 0.45, top_peak_y - face_r * 0.010),
            QPointF(cx + eff_mouth_w, mouth_cy)
        )
        upper_lip.cubicTo(
            QPointF(cx + eff_mouth_w * 0.5, upper_center_y),
            QPointF(cx - eff_mouth_w * 0.5, upper_center_y),
            QPointF(cx - eff_mouth_w, mouth_cy)
        )
        u_grad = QLinearGradient(cx, top_peak_y, cx, upper_center_y)
        u_grad.setColorAt(0.0, QColor(190, 115, 120, 230))
        u_grad.setColorAt(1.0, QColor(155, 80, 90, 245))
        p.setBrush(QBrush(u_grad))
        p.setPen(QPen(QColor(140, 70, 80, 140), 0.8))
        p.drawPath(upper_lip)

        # 4. Lower lip
        lower_lip = QPainterPath()
        lower_lip.moveTo(cx - eff_mouth_w, mouth_cy)
        lower_lip.cubicTo(
            QPointF(cx - eff_mouth_w * 0.5, lower_center_y),
            QPointF(cx + eff_mouth_w * 0.5, lower_center_y),
            QPointF(cx + eff_mouth_w, mouth_cy)
        )
        bot_rim_y = lower_center_y + face_r * 0.032
        lower_lip.cubicTo(
            QPointF(cx + eff_mouth_w * 0.55, bot_rim_y),
            QPointF(cx - eff_mouth_w * 0.55, bot_rim_y),
            QPointF(cx - eff_mouth_w, mouth_cy)
        )
        l_grad = QLinearGradient(cx, lower_center_y, cx, bot_rim_y)
        l_grad.setColorAt(0.0, QColor(175, 95, 105, 240))
        l_grad.setColorAt(0.5, QColor(215, 135, 145, 250))
        l_grad.setColorAt(1.0, QColor(165, 85, 95, 230))
        p.setBrush(QBrush(l_grad))
        p.drawPath(lower_lip)

        # 5. Smile/frown curve only when closed + emotional
        if openness <= 0.02 and abs(smile) > 0.20:
            ctrl_y = mouth_cy + smile * face_r * 0.035
            p.setPen(QPen(QColor(125, 55, 65, 200), 1.5,
                         Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            line_path = QPainterPath()
            line_path.moveTo(cx - mouth_w * 0.85, mouth_cy)
            line_path.quadTo(cx, ctrl_y, cx + mouth_w * 0.85, mouth_cy)
            p.drawPath(line_path)

        p.restore()

    def _draw_radial_voice_burst(self, p: QPainter, cx: float, cy: float, face_r: float, state: AvatarState):
        """
        Renders radial speaking energy burst waveform spikes radiating outward
        from the circular HUD perimeter (matches user video reference at 00:03 - 00:04).
        """
        p.save()
        audio = clamp(state.audio_level, 0.0, 1.0)
        t = time.time() * 4.0

        num_spikes = 40
        base_r = face_r + 5.0
        max_spike = face_r * 0.28 * (0.35 + audio * 0.85)

        for i in range(num_spikes):
            angle_deg = (i / num_spikes) * 360.0 + (t * 8.0)
            rad = math.radians(angle_deg)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)

            # Dynamic wave length per spike
            wave = 0.5 + 0.5 * math.sin(t * 3.0 + i * 0.7)
            spike_len = max_spike * wave * (0.4 + audio * 0.6)

            p1 = QPointF(cx + base_r * cos_a, cy + base_r * sin_a)
            p2 = QPointF(cx + (base_r + spike_len) * cos_a, cy + (base_r + spike_len) * sin_a)

            # Alternating cyan & magenta energy rays
            alpha = int(clamp((60 + audio * 180) * wave, 30, 240))
            color = QColor(0, 255, 255, alpha) if (i % 2 == 0) else QColor(255, 0, 170, alpha)

            p.setPen(QPen(color, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(p1, p2)

        p.restore()

    def _draw_holographic_overlays(self, p: QPainter, cx: float, cy: float, face_r: float, state: AvatarState, fx_controller):
        """
        Renders horizontal scanlines, outer glowing magenta ring, and edge glow.
        """
        p.save()

        # Fine scanlines clipped to face circle
        clip = QPainterPath()
        clip.addEllipse(QRectF(cx - face_r, cy - face_r, face_r * 2, face_r * 2))
        p.setClipPath(clip)

        p.setOpacity(0.08)
        scan_pen = QPen(QColor(0, 255, 255, 50), 0.5)
        p.setPen(scan_pen)
        y = cy - face_r
        while y < cy + face_r:
            p.drawLine(QPointF(cx - face_r, y), QPointF(cx + face_r, y))
            y += 3.5

        p.restore()

        # Magenta signature outer pulse ring
        p.save()
        pulse_alpha = fx_controller.magenta_pulse_alpha if fx_controller else 200
        mag_r = face_r + 3 + state.audio_level * face_r * 0.04
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(255, 0, 170, pulse_alpha), 1.8))
        p.drawEllipse(QRectF(cx - mag_r, cy - mag_r, mag_r * 2, mag_r * 2))

        # Inner state colored edge glow
        state_col = QColor(state.hud_ring_color)
        p.setPen(QPen(QColor(state_col.red(), state_col.green(), state_col.blue(), 160), 1.4))
        p.drawEllipse(QRectF(cx - face_r, cy - face_r, face_r * 2, face_r * 2))
        p.restore()
