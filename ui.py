from __future__ import annotations

import json
import math
import os
import platform
import random
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil

from PyQt6.QtCore import (
    QEasingCurve, QMimeData, QObject, QPointF, QRectF, QSize, Qt,
    QTimer, QUrl, pyqtSignal, pyqtSlot,
)
from PyQt6.QtGui import (
    QBrush, QColor, QDragEnterEvent, QDropEvent, QFont, QFontDatabase,
    QKeySequence, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
    QRadialGradient, QShortcut, QConicalGradient,
)
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QScrollArea, QSizePolicy, QTextEdit,
    QVBoxLayout, QWidget, QProgressBar, QStackedWidget, QComboBox, QSlider,
)

from core.info_card.manager import InfoCardManager
from core.weather_card.manager import WeatherCardManager
from core.image_card.manager import ImageCardManager


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR   = _base_dir()
CONFIG_DIR = BASE_DIR / "config"
API_FILE   = CONFIG_DIR / "api_keys.json"

_DEFAULT_W, _DEFAULT_H = 1120, 760
_MIN_W,     _MIN_H     = 940,  660
_LEFT_W  = 248
_RIGHT_W = 248
_OS = platform.system()

# Font stack -- Consolas first for clean Windows rendering
_FONT_MONO = "Consolas"
_FONT_UI   = "Segoe UI"

_EQ_BARS    = 32
_PARTICLE_N = 22


# --- Colour Palette -- Military HUD Theme -------------------------------------
class C:
    BG          = "#000000"    # Pure black -- pitch dark cockpit
    PANEL       = "#030810"    # Near-black panel
    PANEL2      = "#060F1C"    # Slightly lighter panel
    PANEL3      = "#050D18"    # Alternate panel
    BORDER      = "#0F2A4A"    # Sharp dark-blue border
    BORDER_B    = "#1A4A7A"    # Bright border / focus

    PRI         = "#00FFFF"    # Electric cyan -- primary accent
    PRI_DIM     = "#008A8A"    # Dimmed cyan
    PRI_GHO     = "#001A1A"    # Cyan ghost (hover background)
    CYAN        = "#00BFFF"    # Deep sky blue
    MAGENTA     = "#FF00AA"    # Magenta -- HUD ring accent
    AMBER       = "#FFB300"    # Warning amber
    RED         = "#FF2244"    # Alert red

    TEXT        = "#4ADDE8"    # Readable cyan text
    TEXT_BRIGHT = "#FFFFFF"    # Pure white labels
    TEXT_DIM    = "#1C5060"    # Muted label color
    TEXT_MUTED  = "#102030"    # Very dim

    # State colours -- sharper, more vivid
    COL_LISTEN  = "#00FFFF"    # Cyan when listening
    COL_SPEAK   = "#00BFFF"    # Blue when speaking
    COL_THINK   = "#FFB300"    # Amber when thinking
    COL_MUTED   = "#FF2244"    # Red when muted


def qcol(h: str, a: int = 255) -> QColor:
    c = QColor(h); c.setAlpha(a); return c


# --- System Metrics (background thread) -------------------------------------
class _SysMetrics:
    def __init__(self):
        self.cpu = 0.0
        self.cpu_freq     = ""
        self.mem_pct      = 0.0
        self.mem_used_gb  = 0.0
        self.mem_total_gb = 16.0
        self.net_sent     = 0.0
        self.net_recv     = 0.0
        self.net_str      = "^0K v0K"
        self.disk_pct     = 0.0
        self.disk_free_gb = 0.0
        self.latency_ms   = 45.0
        self.gpu          = -1.0
        self.tmp          = -1.0
        self._lock        = threading.Lock()
        self._last_net    = psutil.net_io_counters()
        self._last_net_t  = time.time()
        self._last_ping_t = 0.0
        self._running     = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while self._running:
            try:
                self._update()
            except Exception:
                pass
            time.sleep(1.5)

    def _update(self):
        cpu = psutil.cpu_percent(interval=None)
        freq_str = ""
        try:
            freq = psutil.cpu_freq()
            if freq and freq.current:
                freq_str = f"{freq.current / 1000:.1f}GHz"
        except Exception:
            pass

        vmem = psutil.virtual_memory()
        mem_pct      = vmem.percent
        mem_used_gb  = vmem.used / (1024 ** 3)
        mem_total_gb = vmem.total / (1024 ** 3)

        nc  = psutil.net_io_counters()
        now = time.time()
        dt  = now - self._last_net_t
        if dt > 0:
            up_kb = ((nc.bytes_sent - self._last_net.bytes_sent) / dt) / 1024.0
            dn_kb = ((nc.bytes_recv - self._last_net.bytes_recv) / dt) / 1024.0
            up_s  = f"^{up_kb/1024:.1f}M" if up_kb >= 1024 else f"^{up_kb:.0f}K"
            dn_s  = f"v{dn_kb/1024:.1f}M" if dn_kb >= 1024 else f"v{dn_kb:.0f}K"
            net_str = f"{up_s} {dn_s}"
        else:
            up_kb = dn_kb = 0.0
            net_str = "^0K v0K"
        self._last_net   = nc
        self._last_net_t = now

        try:
            d = psutil.disk_usage("C:" if _OS == "Windows" else "/")
            disk_pct, disk_free_gb = d.percent, d.free / (1024 ** 3)
        except Exception:
            disk_pct = disk_free_gb = 0.0

        if now - self._last_ping_t >= 3.0:
            try:
                t0 = time.time()
                s  = socket.create_connection(("8.8.8.8", 53), timeout=1.0)
                self.latency_ms = max(1.0, (time.time() - t0) * 1000.0)
                s.close()
            except Exception:
                pass
            self._last_ping_t = now

        gpu = self._get_gpu()
        tmp = self._get_temp()

        with self._lock:
            self.cpu          = cpu
            self.cpu_freq     = freq_str
            self.mem_pct      = mem_pct
            self.mem_used_gb  = mem_used_gb
            self.mem_total_gb = mem_total_gb
            self.net_sent     = up_kb
            self.net_recv     = dn_kb
            self.net_str      = net_str
            self.disk_pct     = disk_pct
            self.disk_free_gb = disk_free_gb
            self.gpu          = gpu
            self.tmp          = tmp

    def _get_gpu(self) -> float:
        try:
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=2
            )
            if r.returncode == 0:
                vals = [float(v.strip()) for v in r.stdout.strip().split("\n") if v.strip()]
                if vals:
                    return sum(vals) / len(vals)
        except Exception:
            pass
        return -1.0

    def _get_temp(self) -> float:
        try:
            temps = psutil.sensors_temperatures()
            for name in ["coretemp", "k10temp", "cpu_thermal", "acpitz"]:
                if name in temps and temps[name]:
                    return temps[name][0].current
        except Exception:
            pass
        return -1.0

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "cpu":          self.cpu,
                "cpu_freq":     self.cpu_freq,
                "mem":          self.mem_pct,
                "mem_used_gb":  self.mem_used_gb,
                "mem_total_gb": self.mem_total_gb,
                "net_str":      self.net_str,
                "net_sent":     self.net_sent,
                "net_recv":     self.net_recv,
                "disk_pct":     self.disk_pct,
                "disk_free_gb": self.disk_free_gb,
                "latency_ms":   self.latency_ms,
                "gpu":          self.gpu,
                "tmp":          self.tmp,
            }


_metrics = _SysMetrics()


# --- Arc Reactor HUD Canvas -------------------------------------------------
class HudCanvas(QWidget):
    """Iron Man Mark-50 Arc-Reactor HUD: 32-bar radial EQ, 3-ring mechanical
    arcs, dual sine waveforms, particle orb glow, state-driven colours."""

    def __init__(self, face_path: str, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setMinimumSize(300, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.muted         = False
        self.speaking      = False
        self.state         = "LISTENING"
        self._audio_level  = 0.0
        self._target_audio = 0.0

        # Load face image for holographic rendering (resolve robustly)
        self._face_px: QPixmap | None = None
        candidates = []
        if face_path:
            p = Path(face_path)
            candidates.append(p)
            if not p.is_absolute():
                candidates.append(BASE_DIR / face_path)
        candidates.append(BASE_DIR / "face.png")
        for c in candidates:
            if c.exists():
                px = QPixmap(str(c))
                if not px.isNull():
                    self._face_px = px
                    break

        # Initialize Avatar Controller & Renderer
        from core.avatar import AvatarController, AvatarRenderer
        self.avatar_controller = AvatarController()
        self.avatar_renderer = AvatarRenderer(self._face_px)
        self.setMouseTracking(True)

        # 3 mechanical ring angles
        self._rings      = [0.0, 120.0, 240.0]
        self._scan       = 0.0
        self._scan2      = 180.0
        self._wave_phase = 0.0
        self._wave2      = math.pi
        self._tick       = 0

        # 32-bar EQ smoothed heights
        self._eq_tgt = [0.0] * _EQ_BARS
        self._eq_cur = [0.0] * _EQ_BARS

        # Particles
        self._particles = [
            {
                "ang": random.uniform(0, 360),
                "spd": random.uniform(0.4, 1.2),
                "r":   random.uniform(0.13, 0.24),
                "sz":  random.uniform(1.5, 3.5),
                "a":   random.randint(70, 190),
            }
            for _ in range(_PARTICLE_N)
        ]

        # Breathing pulse
        self._pulse     = 0.0
        self._pulse_dir = 1

        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._tmr.start(16)   # 60 fps

    def mouseMoveEvent(self, event):
        pos = event.position()
        self.avatar_controller.follow_cursor(pos.x(), pos.y(), self.width(), self.height())
        super().mouseMoveEvent(event)

    def set_audio_level(self, level: float):
        self._target_audio = max(self._target_audio, max(0.0, min(1.0, float(level))))

    def _state_col(self) -> str:
        if self.muted:
            return C.COL_MUTED
        return {
            "SPEAKING": C.COL_SPEAK,
            "THINKING": C.COL_THINK,
            "EXECUTING": C.COL_THINK,
            "MUTED": C.COL_MUTED,
            "STANDBY": C.COL_LISTEN,    # Vibrant Cyan in STANDBY (Image 3)
            "IDLE": C.COL_LISTEN,       # Vibrant Cyan
            "ACTIVATING": C.COL_LISTEN,
            "CANCELLING": C.COL_MUTED,
            "CANCELLED": C.COL_MUTED,
        }.get(self.state, C.COL_LISTEN)


    def _step(self):
        self._tick += 1
        al = self._audio_level

        # Audio envelope
        self._audio_level  += (self._target_audio - self._audio_level) * 0.30
        self._target_audio *= 0.86

        # Breathing pulse
        self._pulse += 0.04 * self._pulse_dir
        if self._pulse >= 1.0:
            self._pulse_dir = -1
        elif self._pulse <= 0.0:
            self._pulse_dir = 1

        # Ring rotations (alternating directions)
        boost = 1.0 + al * 2.5
        spd   = (2.2 if self.speaking else 0.7) * boost
        for i in range(3):
            d = 1 if i % 2 == 0 else -1
            self._rings[i] = (self._rings[i] + d * spd * (i * 0.4 + 0.6)) % 360

        # Scan sweeps
        self._scan  = (self._scan  + (3.0 if self.speaking else 1.0) * boost) % 360
        self._scan2 = (self._scan2 - (2.2 if self.speaking else 0.6) * boost) % 360

        # Waveform phases
        dyn = 0.04 + al * 0.15 if not self.muted else 0.0
        self._wave_phase += dyn
        self._wave2      += dyn * 0.73

        # EQ targets
        for i in range(_EQ_BARS):
            if al > 0.01:
                base  = al * (0.5 + 0.45 * math.sin(self._tick * 0.11 + i * 0.45))
                noise = random.uniform(-0.08, 0.08)
                self._eq_tgt[i] = max(0.0, min(1.0, base + noise))
            else:
                idle = 0.04 + 0.03 * math.sin(self._tick * 0.05 + i * 0.35)
                self._eq_tgt[i] = idle if not self.muted else 0.0
            self._eq_cur[i] += (self._eq_tgt[i] - self._eq_cur[i]) * 0.25

        # Step Avatar physics & real-time lip-sync/gaze
        # IMPORTANT: Do NOT override avatar_controller.state.audio_level here —
        # it is already correctly set by process_audio_chunk() from live PCM data.
        # Only sync operational state and speaking flag.
        state_lower = self.state.lower() if isinstance(self.state, str) else self.state
        self.avatar_controller.set_state(state_lower)
        self.avatar_controller.state.speaking = self.speaking
        # Only use HUD audio level as a fallback when avatar has no live audio data
        if self.avatar_controller.state.audio_level < 0.01:
            self.avatar_controller.state.audio_level = self._audio_level
        self.avatar_controller.update()

        self.update()

    # -- Paint ----------------------------------------------------------------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)        # Crisp text
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)   # Crisp images
        p.fillRect(self.rect(), qcol(C.BG))

        W, H  = self.width(), self.height()
        cx, cy = W / 2, H / 2
        fw    = min(W, H) * 0.90
        sc    = self._state_col()

        self._draw_corner_brackets(p, cx, cy, fw)
        self._draw_compass_ring(p, cx, cy, fw, sc)
        self._draw_mechanical_rings(p, cx, cy, fw, sc)
        self._draw_eq_bars(p, cx, cy, fw, sc)
        self._draw_scan_arcs(p, cx, cy, fw, sc)
        self._draw_crosshairs(p, cx, cy, fw)
        self._draw_particles(p, cx, cy, fw, sc)
        self._draw_core_orb(p, cx, cy, fw, sc)
        self._draw_face_holographic(p, cx, cy, fw, sc)   # holographic face overlay
        self._draw_waveforms(p, cx, cy, fw, sc)
        self._draw_orb_text(p, cx, cy, fw, sc)

    # -- Holographic Face ------------------------------------------------------
    def _draw_face_holographic(self, p: QPainter, cx: float, cy: float,
                                fw: float, sc: str) -> None:
        """Render the animated AI avatar in the HUD center using layered rendering."""
        self.avatar_renderer.render(p, cx, cy, fw, self.avatar_controller.state, self.avatar_controller.fx)

    def _draw_corner_brackets(self, p, cx, cy, fw):
        bl, half = 30, fw / 2
        p.setPen(QPen(qcol(C.PRI_DIM, 150), 1.6))
        for bx, by, dx, dy in [
            (cx - half, cy - half,  1,  1), (cx + half, cy - half, -1,  1),
            (cx - half, cy + half,  1, -1), (cx + half, cy + half, -1, -1),
        ]:
            p.drawLine(QPointF(bx, by), QPointF(bx + dx * bl, by))
            p.drawLine(QPointF(bx, by), QPointF(bx, by + dy * bl))

    def _draw_compass_ring(self, p, cx, cy, fw, sc):
        r_out = fw * 0.49
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(qcol(sc, 45), 1))
        p.drawEllipse(QRectF(cx - r_out, cy - r_out, r_out * 2, r_out * 2))

        for deg in range(0, 360, 5):
            rad = math.radians(deg)
            cos_r, sin_r = math.cos(rad), math.sin(rad)
            if deg % 45 == 0:
                r_in, pw, alpha = r_out - 12, 1.5, 210
            elif deg % 15 == 0:
                r_in, pw, alpha = r_out - 8,  1.2, 140
            else:
                r_in, pw, alpha = r_out - 4,  0.8,  70
            p.setPen(QPen(qcol(sc, alpha), pw))
            p.drawLine(
                QPointF(cx + r_out * cos_r, cy - r_out * sin_r),
                QPointF(cx + r_in  * cos_r, cy - r_in  * sin_r),
            )

        # Cardinal labels
        p.setFont(QFont(_FONT_MONO, 6, QFont.Weight.Bold))
        p.setPen(QPen(qcol(sc, 180), 1))
        for deg, lbl in [(0, "E"), (90, "N"), (180, "W"), (270, "S")]:
            rad = math.radians(deg)
            lx  = cx + (r_out + 10) * math.cos(rad) - 6
            ly  = cy - (r_out + 10) * math.sin(rad) - 5
            p.drawText(QRectF(lx, ly, 14, 10), Qt.AlignmentFlag.AlignCenter, lbl)

    def _draw_mechanical_rings(self, p, cx, cy, fw, sc):
        configs = [(0.40, 2.2, 88, 32), (0.31, 1.6, 65, 45), (0.22, 1.2, 48, 38)]
        for idx, (r_frac, pw, arc_span, gap) in enumerate(configs):
            r    = fw * r_frac
            base = self._rings[idx]
            p.setPen(QPen(qcol(sc, 190 - idx * 35), pw))
            p.setBrush(Qt.BrushStyle.NoBrush)
            rect = QRectF(cx - r, cy - r, r * 2, r * 2)
            ang  = base
            while ang < base + 360:
                p.drawArc(rect, int(ang * 16), int(arc_span * 16))
                ang += arc_span + gap

    def _draw_eq_bars(self, p, cx, cy, fw, sc):
        r_inner = fw * 0.16
        r_max   = fw * 0.20
        for i in range(_EQ_BARS):
            ang_rad = math.radians((360 / _EQ_BARS) * i - 90)
            cos_a   = math.cos(ang_rad)
            sin_a   = math.sin(ang_rad)
            frac    = self._eq_cur[i]
            r_end   = r_inner + r_max * frac

            # Colour gradient: Cyan -> Blue -> Magenta (Military HUD)
            if frac < 0.5:
                t   = frac * 2
                col = QColor(int(0 + 0 * t), int(255 + (191 - 255) * t), int(255 + (255 - 255) * t))
            else:
                t   = (frac - 0.5) * 2
                col = QColor(int(0 + 255 * t), int(191 + (0 - 191) * t), int(255 + (170 - 255) * t))
            col.setAlpha(180 + int(60 * frac))

            pen = QPen(col, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawLine(
                QPointF(cx + r_inner * cos_a, cy + r_inner * sin_a),
                QPointF(cx + r_end   * cos_a, cy + r_end   * sin_a),
            )

    def _draw_scan_arcs(self, p, cx, cy, fw, sc):
        for r_frac, span, alpha, pw in [(0.44, 28, 230, 2.0), (0.34, 20, 140, 1.5)]:
            r    = fw * r_frac
            rect = QRectF(cx - r, cy - r, r * 2, r * 2)
            ang  = self._scan if r_frac > 0.40 else self._scan2
            p.setPen(QPen(qcol(sc, alpha), pw))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(rect, int(ang * 16), int(span * 16))

    def _draw_crosshairs(self, p, cx, cy, fw):
        ch_r  = fw * 0.46
        gap_h = fw * 0.14
        p.setPen(QPen(qcol(C.BORDER_B, 110), 1))
        p.drawLine(QPointF(cx - ch_r, cy), QPointF(cx - gap_h, cy))
        p.drawLine(QPointF(cx + gap_h, cy), QPointF(cx + ch_r, cy))
        p.drawLine(QPointF(cx, cy - ch_r), QPointF(cx, cy - gap_h))
        p.drawLine(QPointF(cx, cy + gap_h), QPointF(cx, cy + ch_r))

    def _draw_particles(self, p, cx, cy, fw, sc):
        orb_r = fw * 0.10 + self._audio_level * fw * 0.03
        for pt in self._particles:
            r_dist = fw * pt["r"] + orb_r
            rad    = math.radians(pt["ang"])
            px     = cx + r_dist * math.cos(rad)
            py     = cy + r_dist * math.sin(rad)
            alpha  = int(pt["a"] * (0.5 + 0.5 * self._pulse))
            sz     = pt["sz"] * (0.8 + 0.4 * self._pulse)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(qcol(sc, alpha)))
            p.drawEllipse(QRectF(px - sz / 2, py - sz / 2, sz, sz))

    def _draw_core_orb(self, p, cx, cy, fw, sc):
        if self._face_px is not None:
            # When holographic face is active, draw large ambient backdrop glow behind the face
            face_r = fw * 0.285
            for glow_r, alpha in [(face_r * 1.5, 14), (face_r * 1.25, 28), (face_r * 1.05, 45)]:
                g = QRadialGradient(cx, cy, glow_r)
                gc = QColor(sc); gc.setAlpha(alpha)
                gz = QColor(sc); gz.setAlpha(0)
                g.setColorAt(0, gc); g.setColorAt(1, gz)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(g))
                p.drawEllipse(QRectF(cx - glow_r, cy - glow_r, glow_r * 2, glow_r * 2))
            return

        orb_r = fw * 0.10 + self._audio_level * fw * 0.025
        # Outer glow layers
        for glow_r, alpha in [(orb_r * 2.4, 12), (orb_r * 1.8, 25), (orb_r * 1.3, 48)]:
            g = QRadialGradient(cx, cy, glow_r)
            gc = QColor(sc); gc.setAlpha(alpha)
            gz = QColor(sc); gz.setAlpha(0)
            g.setColorAt(0, gc); g.setColorAt(1, gz)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(g))
            p.drawEllipse(QRectF(cx - glow_r, cy - glow_r, glow_r * 2, glow_r * 2))
        # Core fill
        g2 = QRadialGradient(cx, cy, orb_r)
        ic = QColor(sc); ic.setAlpha(85)
        oc = QColor(sc); oc.setAlpha(18)
        g2.setColorAt(0.0, ic); g2.setColorAt(1.0, oc)
        p.setBrush(QBrush(g2))
        p.setPen(QPen(qcol(sc, 220), 1.5))
        p.drawEllipse(QRectF(cx - orb_r, cy - orb_r, orb_r * 2, orb_r * 2))

    def _draw_waveforms(self, p, cx, cy, fw, sc):
        if self._face_px is not None:
            # Draw soundwave ring arcs orbiting the face
            face_r = fw * 0.285
            amp1 = (2 if not self.muted else 0) + (8 if self.speaking else 0) + self._audio_level * 16
            for idx, (phase, arc_r, alpha, col_name) in enumerate([
                (self._wave_phase, face_r + 8, 220, C.PRI),
                (self._wave2,      face_r + 14, 160, C.MAGENTA),
            ]):
                path = QPainterPath()
                pts = 48
                for i in range(pts + 1):
                    rad = math.radians((360 / pts) * i)
                    wave = math.sin(phase + i * 0.45) * amp1
                    r_curr = arc_r + wave
                    x = cx + r_curr * math.cos(rad)
                    y = cy + r_curr * math.sin(rad)
                    if i == 0:
                        path.moveTo(x, y)
                    else:
                        path.lineTo(x, y)
                path.closeSubpath()
                p.setPen(QPen(qcol(col_name, alpha), 1.2))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawPath(path)
            return

        orb_r = fw * 0.10 + self._audio_level * fw * 0.025
        amp1  = (0 if self.muted else 3) + (10 if self.speaking else 0) + self._audio_level * 18
        for phase, amp, alpha in [(self._wave_phase, amp1, 240), (self._wave2, amp1 * 0.6, 140)]:
            path = QPainterPath()
            pts  = 36
            step = (orb_r * 1.8) / pts
            sx   = cx - orb_r * 0.9
            path.moveTo(sx, cy)
            for i in range(1, pts + 1):
                x   = sx + i * step
                env = math.sin(i / pts * math.pi)
                y   = cy + math.sin(phase + i * 0.30) * amp * env
                path.lineTo(x, y)
            p.setPen(QPen(qcol(sc, alpha), 1.4))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)

    def _draw_orb_text(self, p, cx, cy, fw, sc):
        if self._face_px is not None:
            # Draw 'INDUS' in bold glowing cyan directly below the holographic face (Image 3)
            face_r = fw * 0.285
            text_y = cy + face_r + 8
            lbl = "INDUS"

            # Glow backing for text
            p.setFont(QFont(_FONT_MONO, 13, QFont.Weight.Bold))
            p.setPen(QPen(qcol(C.PRI, 90), 3))
            p.drawText(QRectF(cx - 80, text_y, 160, 20), Qt.AlignmentFlag.AlignCenter, lbl)

            # Main text
            p.setPen(QPen(qcol(C.TEXT_BRIGHT), 1))
            p.drawText(QRectF(cx - 80, text_y, 160, 20), Qt.AlignmentFlag.AlignCenter, lbl)

            # State text below
            sub = "MUTED" if self.muted else ("SPEAKING" if self.speaking else ("THINKING" if self.state == "THINKING" else "ONLINE"))
            p.setFont(QFont(_FONT_MONO, 7, QFont.Weight.Bold))
            p.setPen(QPen(qcol(sc, 220), 1))
            p.drawText(QRectF(cx - 80, text_y + 18, 160, 12), Qt.AlignmentFlag.AlignCenter, f"? {sub}")
            return

        orb_r = fw * 0.10
        lbl   = "MUTED" if self.muted else ("SPEAKING" if self.speaking else "INDUS")
        sub   = "OFFLINE" if self.muted else "ONLINE"
        p.setFont(QFont(_FONT_MONO, 8, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.TEXT_BRIGHT), 1))
        p.drawText(QRectF(cx - orb_r, cy - 13, orb_r * 2, 12), Qt.AlignmentFlag.AlignCenter, lbl)
        p.setFont(QFont(_FONT_MONO, 6))
        p.setPen(QPen(qcol(sc, 160), 1))
        p.drawText(QRectF(cx - orb_r, cy + 3, orb_r * 2, 10), Qt.AlignmentFlag.AlignCenter, sub)


# --- Metric Bar --------------------------------------------------------------
class MetricBar(QWidget):
    """Animated gradient progress bar with smooth interpolation."""

    def __init__(self, label: str, val_text: str = "--", color: str = C.PRI, parent=None):
        super().__init__(parent)
        self._label = label
        self._color = color
        self._value = 0.0
        self._text  = val_text
        self._anim  = 0.0
        self.setFixedHeight(50)
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(28)

    def _tick(self):
        if abs(self._anim - self._value) > 0.4:
            self._anim += (self._value - self._anim) * 0.18
            self.update()

    def set_value(self, pct: float, text: str):
        self._value = max(0.0, min(100.0, pct))
        self._text  = text
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        # Label -- white, sharp
        p.setFont(QFont(_FONT_MONO, 7, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.TEXT_DIM), 1))
        p.drawText(QRectF(0, 0, W - 78, 16),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._label)

        # Value -- electric cyan, right-aligned
        p.setFont(QFont(_FONT_MONO, 8, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.PRI), 1))
        p.drawText(QRectF(W - 78, 0, 78, 16),
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self._text)

        # Bar track -- dark, sharp edges (no rounded)
        bar_y = 22
        bar_h = 6
        p.setBrush(QBrush(qcol("#050F1A")))
        p.setPen(QPen(qcol(C.BORDER, 160), 1))
        p.drawRect(QRectF(0, bar_y, W, bar_h))

        # Bar fill with gradient
        fill_w = max(0, int(W * self._anim / 100))
        if fill_w > 0:
            stop_col = C.RED if self._value > 85 else (C.AMBER if self._value > 65 else C.PRI)
            grad = QLinearGradient(0, 0, fill_w, 0)
            grad.setColorAt(0.0, qcol(C.PRI_DIM, 180))
            grad.setColorAt(0.5, qcol(stop_col, 220))
            grad.setColorAt(1.0, qcol(stop_col, 255))
            p.setBrush(QBrush(grad))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(QRectF(1, bar_y + 1, fill_w - 1, bar_h - 2))

        # End tick marks -- military style
        p.setPen(QPen(qcol(C.PRI_DIM, 100), 1))
        p.drawLine(QPointF(0, bar_y - 2),    QPointF(0, bar_y + bar_h + 2))
        p.drawLine(QPointF(W - 1, bar_y - 2), QPointF(W - 1, bar_y + bar_h + 2))



# --- Log Widget --------------------------------------------------------------
class LogWidget(QTextEdit):
    _sig = pyqtSignal(str)

    _COL = {"sys": "#FFB300", "you": "#FFFFFF", "ai": "#00FFFF", "err": "#FF2244", "file": "#00BFFF"}
    _PFX = {"sys": "* SYS: ", "ai": "< INDUS  ", "you": "> YOU: ", "file": "  FILE: "}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont(_FONT_MONO, 9))
        self.setStyleSheet(f"""
            QTextEdit {{
                background: {C.BG};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                padding: 10px 12px;
            }}
            QScrollBar:vertical {{
                background: {C.BG};
                width: 5px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {C.PRI_DIM};
                border-radius: 0px;
                min-height: 12px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        self._queue:  list[str] = []
        self._typing  = False
        self._text    = ""
        self._pos     = 0
        self._tag     = "sys"
        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._sig.connect(self._enqueue)

    def append_log(self, text: str):
        self._sig.emit(text)

    def _enqueue(self, text: str):
        self._queue.append(text)
        if not self._typing:
            self._next()

    def _next(self):
        if not self._queue:
            self._typing = False
            return
        self._typing = True
        raw = self._queue.pop(0).strip()
        self._pos = 0
        tl = raw.lower()
        if tl.startswith("you:"):
            self._tag, self._text = "you", raw[4:].strip()
        elif tl.startswith("jarvis:"):
            self._tag, self._text = "ai", raw[7:].strip()
        elif tl.startswith("indus:"):
            self._tag, self._text = "ai", raw[6:].strip()
        elif tl.startswith("sys:"):
            self._tag, self._text = "sys", raw[4:].strip()
        elif tl.startswith("file:"):
            self._tag, self._text = "file", raw[5:].strip()
        elif "err" in tl:
            self._tag, self._text = "err", raw
        else:
            self._tag, self._text = "sys", raw
        self._text = self._text.replace("JARVIS", "INDUS").replace("Jarvis", "INDUS")
        self._tmr.start(3)

    def _step(self):
        if self._pos < len(self._text):
            ch  = self._text[self._pos]
            cur = self.textCursor()
            fmt = cur.charFormat()
            col = qcol(self._COL.get(self._tag, C.TEXT))
            fmt.setForeground(QBrush(col))
            fmt.setFont(QFont(_FONT_MONO, 9))
            cur.movePosition(cur.MoveOperation.End)
            if self._pos == 0:
                pfx_col = self._COL.get(self._tag, C.TEXT)
                pfx_lbl = self._PFX.get(self._tag, "  ")
                pf = cur.charFormat()
                pf.setForeground(QBrush(qcol(pfx_col, 200)))
                pf.setFont(QFont(_FONT_MONO, 8, QFont.Weight.Bold))
                cur.insertText(pfx_lbl, pf)
            cur.insertText(ch, fmt)
            self.setTextCursor(cur)
            self.ensureCursorVisible()
            self._pos += 1
        else:
            self._tmr.stop()
            cur = self.textCursor()
            cur.movePosition(cur.MoveOperation.End)
            cur.insertText("\n")
            self.setTextCursor(cur)
            self.ensureCursorVisible()
            QTimer.singleShot(12, self._next)


# --- File Drop Zone ----------------------------------------------------------
class FileDropZone(QWidget):
    file_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(95)
        self._current_file: str | None = None
        self._hovering  = False
        self._drag_over = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self._canvas = _DropCanvas(self)
        lay.addWidget(self._canvas)

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._drag_over = True; self._canvas.update()

    def dragLeaveEvent(self, e):
        self._drag_over = False; self._canvas.update()

    def dropEvent(self, e: QDropEvent):
        self._drag_over = False
        urls = e.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if Path(path).is_file():
                self._set_file(path)
        self._canvas.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._browse()

    def enterEvent(self, e):
        self._hovering = True; self._canvas.update()

    def leaveEvent(self, e):
        self._hovering = False; self._canvas.update()

    def current_file(self) -> str | None:
        return self._current_file

    def clear_file(self):
        self._current_file = None; self._canvas.update()

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select File for INDUS", str(Path.home()), "All Files (*.*)"
        )
        if path:
            self._set_file(path)

    def _set_file(self, path: str):
        self._current_file = path
        self._canvas.update()
        self.file_selected.emit(path)


class _DropCanvas(QWidget):
    def __init__(self, zone: FileDropZone):
        super().__init__(zone)
        self._z = zone

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        z  = self._z
        W, H = self.width(), self.height()
        rect = QRectF(1, 1, W - 2, H - 2)

        bg = qcol("#071d28" if z._drag_over else C.PANEL)
        p.setBrush(QBrush(bg)); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(rect, 5, 5)

        bc = qcol(C.PRI if (z._drag_over or z._hovering or z._current_file) else C.BORDER)
        p.setPen(QPen(bc, 1, Qt.PenStyle.DashLine)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, 5, 5)

        # Corner brackets
        bl = 10; m = 3
        p.setPen(QPen(qcol(C.PRI_DIM, 150), 1.2))
        for bx, by, dx, dy in [(m, m, 1, 1), (W-m, m, -1, 1), (m, H-m, 1, -1), (W-m, H-m, -1, -1)]:
            p.drawLine(QPointF(bx, by), QPointF(bx + dx * bl, by))
            p.drawLine(QPointF(bx, by), QPointF(bx, by + dy * bl))

        cx_d, cy_d = W / 2, H / 2
        if z._current_file:
            path = Path(z._current_file)
            p.setFont(QFont(_FONT_MONO, 8, QFont.Weight.Bold))
            p.setPen(QPen(qcol(C.TEXT_BRIGHT), 1))
            nm = path.name if len(path.name) <= 26 else path.name[:23] + "..."
            p.drawText(QRectF(0, cy_d - 12, W, 16), Qt.AlignmentFlag.AlignCenter, f"[FILE] {nm}")
            p.setFont(QFont(_FONT_MONO, 7))
            p.setPen(QPen(qcol(C.PRI), 1))
            p.drawText(QRectF(0, cy_d + 6, W, 14), Qt.AlignmentFlag.AlignCenter, "Click to change")
        else:
            p.setFont(QFont(_FONT_MONO, 9))
            p.setPen(QPen(qcol(C.TEXT_MUTED), 1))
            p.drawText(QRectF(0, cy_d - 18, W, 16), Qt.AlignmentFlag.AlignCenter, "[ + ]")
            p.setFont(QFont(_FONT_MONO, 7))
            p.setPen(QPen(qcol(C.TEXT_MUTED if not z._hovering else C.TEXT_BRIGHT), 1))
            p.drawText(QRectF(0, cy_d + 2, W, 14), Qt.AlignmentFlag.AlignCenter, "Drop a file here")
            p.setFont(QFont(_FONT_MONO, 7))
            p.setPen(QPen(qcol(C.TEXT_DIM), 1))
            p.drawText(QRectF(0, cy_d + 16, W, 12), Qt.AlignmentFlag.AlignCenter, "or click to browse")


# --- Glass Panel -------------------------------------------------------------
class GlassPanel(QFrame):
    """Military HUD panel with sharp edges, neon border, and corner brackets."""

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self._title = title
        self.setStyleSheet("GlassPanel { background: transparent; border: none; }")

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        rect = QRectF(0.5, 0.5, W - 1, H - 1)

        # Pure black fill -- no gradient softening
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(qcol(C.PANEL, 245)))
        p.drawRect(rect)

        # Sharp outer border -- electric cyan tint
        p.setPen(QPen(qcol(C.BORDER_B, 180), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(rect)

        # Corner brackets -- brighter, thicker (military HUD signature)
        bl, m = 16, 2
        p.setPen(QPen(qcol(C.PRI, 200), 1.5))
        for bx, by, dx, dy in [
            (m, m, 1, 1), (W-m, m, -1, 1), (m, H-m, 1, -1), (W-m, H-m, -1, -1)
        ]:
            p.drawLine(QPointF(bx, by), QPointF(bx + dx * bl, by))
            p.drawLine(QPointF(bx, by), QPointF(bx, by + dy * bl))

        # Title -- electric cyan, uppercase, sharp
        if self._title:
            p.setFont(QFont(_FONT_MONO, 7, QFont.Weight.Bold))
            p.setPen(QPen(qcol(C.PRI, 220), 1))
            p.drawText(QRectF(14, 7, W - 28, 14), Qt.AlignmentFlag.AlignLeft, self._title)


# --- Setup Overlay -----------------------------------------------------------
class SetupOverlay(QWidget):
    done = pyqtSignal(str, str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            SetupOverlay {{
                background: rgba(3, 13, 16, 248);
                border: 1px solid {C.PRI_DIM};
                border-radius: 8px;
            }}
        """)
        detected = {"darwin": "mac", "windows": "windows"}.get(_OS.lower(), "linux")
        self._sel_os = detected
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 24, 32, 24)
        lay.setSpacing(8)

        def _lbl(txt, fs=9, bold=False, color=C.PRI, align=Qt.AlignmentFlag.AlignCenter):
            w = QLabel(txt)
            w.setAlignment(align)
            w.setFont(QFont(_FONT_MONO, fs, QFont.Weight.Bold if bold else QFont.Weight.Normal))
            w.setStyleSheet(f"color: {color}; background: transparent;")
            return w

        lay.addWidget(_lbl("[ INITIALISING INDUS CORE ]", 12, True))
        lay.addWidget(_lbl("Configure API credentials before system launch.", 8, color=C.TEXT_MUTED))
        lay.addSpacing(8)

        def _inp(label, ph):
            lay.addWidget(_lbl(label, 8, color=C.TEXT_DIM, align=Qt.AlignmentFlag.AlignLeft))
            i = QLineEdit()
            i.setEchoMode(QLineEdit.EchoMode.Password)
            i.setPlaceholderText(ph)
            i.setFont(QFont(_FONT_MONO, 9))
            i.setFixedHeight(32)
            i.setStyleSheet(f"""
                QLineEdit {{ background: {C.PANEL}; color: {C.TEXT_BRIGHT};
                    border: 1px solid {C.BORDER}; border-radius: 4px; padding: 4px 10px; }}
                QLineEdit:focus {{ border: 1px solid {C.PRI}; }}
            """)
            lay.addWidget(i)
            return i

        self._key_input = _inp("GEMINI API KEY", "AIza...")
        self._or_input  = _inp("OPENROUTER API KEY", "sk-or-...")
        self._nv_input  = _inp("NVIDIA API KEY (OPTIONAL FALLBACK)", "nvapi-...")

        lay.addSpacing(10)
        btn = QPushButton("[ INITIALISE SYSTEM ]")
        btn.setFont(QFont(_FONT_MONO, 9, QFont.Weight.Bold))
        btn.setFixedHeight(36)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ background: {C.PANEL2}; color: {C.PRI};
                border: 1px solid {C.PRI_DIM}; border-radius: 4px; }}
            QPushButton:hover {{ background: {C.PRI_GHO}; border: 1px solid {C.PRI}; }}
        """)
        btn.clicked.connect(self._submit)
        lay.addWidget(btn)

    def _submit(self):
        key    = self._key_input.text().strip()
        or_key = self._or_input.text().strip()
        nv_key = self._nv_input.text().strip()
        if key and (or_key or nv_key):
            self.done.emit(key, or_key, nv_key, self._sel_os)


# --- Settings Overlay --------------------------------------------------------
class SettingsOverlay(QWidget):
    saved  = pyqtSignal(dict)
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            SettingsOverlay {{
                background: rgba(4, 17, 26, 252);
                border: 1px solid {C.PRI};
                border-radius: 10px;
            }}
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(8)

        hdr = QHBoxLayout()
        self._title_lbl = QLabel("[ SETTINGS ]")
        self._title_lbl.setFont(QFont(_FONT_MONO, 11, QFont.Weight.Bold))
        self._title_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        close_btn = QPushButton("x")
        close_btn.setFixedSize(24, 24)
        close_btn.setFont(QFont(_FONT_MONO, 10, QFont.Weight.Bold))
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {C.TEXT_MUTED}; border: none; }}
            QPushButton:hover {{ color: {C.RED}; }}
        """)
        close_btn.clicked.connect(self._close)
        hdr.addWidget(self._title_lbl); hdr.addStretch(); hdr.addWidget(close_btn)
        root.addLayout(hdr)

        self._breadcrumb = QLabel("SETTING")
        self._breadcrumb.setFont(QFont(_FONT_MONO, 7))
        self._breadcrumb.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        root.addWidget(self._breadcrumb)
        root.addSpacing(2)

        self._stack = QStackedWidget(self)
        root.addWidget(self._stack, stretch=1)

        pages = [
            self._build_page_settings(),
            self._build_page_api_keys(),
            self._build_page_keys(),
            self._build_page_audio(),
            self._build_page_theme(),
            self._build_page_memory(),
        ]
        for pg in pages:
            self._stack.addWidget(pg)

        self._goto_settings()

    def _nav(self, idx, title, crumb):
        self._stack.setCurrentIndex(idx)
        self._title_lbl.setText(title)
        self._breadcrumb.setText(crumb)

    def _goto_settings(self):  self._nav(0, "[ SETTINGS ]", "SETTING")
    def _goto_api_keys(self):  self._nav(1, "[ SETTINGS > API KEYS ]", "SETTING > API KEYS")
    def _goto_keys(self):      self._nav(2, "[ SETTINGS > API KEYS > EDIT ]", "SETTING > API KEYS > EDIT")

    def _goto_audio(self):
        self._nav(3, "[ SETTINGS > AUDIO ]", "SETTING > AUDIO")
        self._refresh_mics_ui()

    def _goto_theme(self):
        self._nav(4, "[ SETTINGS > THEME ]", "SETTING > THEME")
        self._refresh_theme_ui()

    def _goto_memory(self):
        self._nav(5, "[ SETTINGS > MEMORY ]", "SETTING > MEMORY")
        self._refresh_memory_ui()

    # -- Page builders ---------------------------------------------------------
    def _btn_style(self, color=None):
        c = color or C.PRI
        return f"""
            QPushButton {{ background: {C.BG}; color: {C.TEXT};
                border: 1px solid {C.BORDER}; border-radius: 4px; text-align:left; padding-left:10px; }}
            QPushButton:hover {{ color: {C.TEXT_BRIGHT}; border: 1px solid {c}; background: {C.PANEL2}; }}
        """

    def _back_btn(self, lay, cb, label="< BACK TO SETTINGS"):
        row = QHBoxLayout()
        btn = QPushButton(label)
        btn.setFixedHeight(30); btn.setFont(QFont(_FONT_MONO, 8))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ background: {C.BG}; color: {C.TEXT_MUTED};
                border: 1px solid {C.BORDER}; border-radius: 3px; }}
            QPushButton:hover {{ color: {C.TEXT_BRIGHT}; border: 1px solid {C.TEXT_MUTED}; }}
        """)
        btn.clicked.connect(cb); row.addWidget(btn); lay.addLayout(row)

    def _build_page_settings(self) -> QWidget:
        w = QWidget(); lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 8, 0, 0); lay.setSpacing(8)

        def _card(icon, title, desc, cb):
            btn = QPushButton(); btn.setFixedHeight(56)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{ background: {C.PANEL}; border: 1px solid {C.BORDER};
                    border-radius: 6px; text-align: left; padding: 6px 12px; }}
                QPushButton:hover {{ border: 1px solid {C.PRI}; background: {C.PANEL2}; }}
            """)
            cl = QHBoxLayout(btn); cl.setContentsMargins(10, 4, 10, 4)
            ic = QLabel(icon); ic.setFont(QFont(_FONT_MONO, 12))
            ic.setStyleSheet("background: transparent;"); cl.addWidget(ic)
            tx = QVBoxLayout(); tx.setSpacing(0)
            t1 = QLabel(title); t1.setFont(QFont(_FONT_MONO, 9, QFont.Weight.Bold))
            t1.setStyleSheet(f"color: {C.TEXT_BRIGHT}; background: transparent;")
            t2 = QLabel(desc); t2.setFont(QFont(_FONT_MONO, 7))
            t2.setStyleSheet(f"color: {C.TEXT_MUTED}; background: transparent;")
            tx.addWidget(t1); tx.addWidget(t2); cl.addLayout(tx, stretch=1)
            ar = QLabel(">"); ar.setFont(QFont(_FONT_MONO, 9, QFont.Weight.Bold))
            ar.setStyleSheet(f"color: {C.PRI}; background: transparent;"); cl.addWidget(ar)
            btn.clicked.connect(cb)
            return btn

        lay.addWidget(_card("[MIC]", "MICROPHONE & AUDIO INPUT",
                            "Select mic device, gain boost & live VU meter", self._goto_audio))
        lay.addWidget(_card("[KEY]", "API KEYS & CREDENTIALS",
                            "Gemini, OpenRouter & NVIDIA API access", self._goto_api_keys))
        lay.addWidget(_card("[HUD]", "THEME & DISPLAY MODE",
                            "Dark / Light mode enforcement", self._goto_theme))
        lay.addWidget(_card("[MEM]", "LONG-TERM MEMORY & HABITS",
                            "Stored facts, routines & conversations", self._goto_memory))
        lay.addStretch()
        cb = QPushButton("[ CLOSE SETTINGS ]"); cb.setFixedHeight(30)
        cb.setFont(QFont(_FONT_MONO, 8)); cb.setCursor(Qt.CursorShape.PointingHandCursor)
        cb.setStyleSheet(f"""
            QPushButton {{ background: {C.BG}; color: {C.TEXT_MUTED};
                border: 1px solid {C.BORDER}; border-radius: 4px; }}
            QPushButton:hover {{ color: {C.TEXT_BRIGHT}; border: 1px solid {C.TEXT_MUTED}; }}
        """)
        cb.clicked.connect(self._close); lay.addWidget(cb)
        return w

    def _build_page_api_keys(self) -> QWidget:
        w = QWidget(); lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 6, 0, 0); lay.setSpacing(8)

        existing = {}
        if API_FILE.exists():
            try: existing = json.loads(API_FILE.read_text(encoding="utf-8"))
            except: pass

        def _prov(icon, name, ptype, kv):
            card = QFrame(); card.setFixedHeight(50)
            card.setStyleSheet(f"QFrame {{ background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 5px; }}")
            cl = QHBoxLayout(card); cl.setContentsMargins(10, 4, 10, 4)
            il = QLabel(icon); il.setFont(QFont(_FONT_MONO, 12)); il.setStyleSheet("background:transparent;"); cl.addWidget(il)
            col = QVBoxLayout(); col.setSpacing(0)
            n = QLabel(name); n.setFont(QFont(_FONT_MONO, 9, QFont.Weight.Bold))
            n.setStyleSheet(f"color: {C.TEXT_BRIGHT}; background: transparent;")
            t = QLabel(ptype); t.setFont(QFont(_FONT_MONO, 7))
            t.setStyleSheet(f"color: {C.TEXT_MUTED}; background: transparent;")
            col.addWidget(n); col.addWidget(t); cl.addLayout(col, stretch=1)
            stxt = "? READY" if bool(kv) else "? MISSING"
            scol = C.PRI if bool(kv) else "#e06c75"
            s = QLabel(stxt); s.setFont(QFont(_FONT_MONO, 8, QFont.Weight.Bold))
            s.setStyleSheet(f"color: {scol}; background: transparent;"); cl.addWidget(s)
            return card

        lay.addWidget(_prov("[G]", "GOOGLE GEMINI API", "Primary Native Audio & Vision Live API", existing.get("gemini_api_key")))
        lay.addWidget(_prov("[O]", "OPENROUTER API", "Multi-Model Intelligent Fallback Engine", existing.get("openrouter_api_key")))
        lay.addWidget(_prov("[N]", "NVIDIA NIM API", "High-Performance Backup Engine", existing.get("nvidia_api_key")))
        lay.addSpacing(6)
        vb = QPushButton("> VIEW & EDIT KEYS"); vb.setFont(QFont(_FONT_MONO, 9, QFont.Weight.Bold))
        vb.setFixedHeight(34); vb.setCursor(Qt.CursorShape.PointingHandCursor)
        vb.setStyleSheet(f"""
            QPushButton {{ background: {C.PANEL2}; color: {C.PRI};
                border: 1px solid {C.PRI}; border-radius: 4px; }}
            QPushButton:hover {{ background: {C.PRI_GHO}; color: {C.TEXT_BRIGHT}; }}
        """)
        vb.clicked.connect(self._goto_keys); lay.addWidget(vb)
        lay.addStretch(); self._back_btn(lay, self._goto_settings)
        return w

    def _build_page_keys(self) -> QWidget:
        w = QWidget(); lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 4, 0, 0); lay.setSpacing(6)
        existing = {}
        if API_FILE.exists():
            try: existing = json.loads(API_FILE.read_text(encoding="utf-8"))
            except: pass

        def _row(title, val, ph):
            lb = QLabel(title); lb.setFont(QFont(_FONT_MONO, 7, QFont.Weight.Bold))
            lb.setStyleSheet(f"color: {C.TEXT_MUTED}; background: transparent;"); lay.addWidget(lb)
            row = QHBoxLayout()
            inp = QLineEdit(val); inp.setEchoMode(QLineEdit.EchoMode.Password)
            inp.setPlaceholderText(ph); inp.setFont(QFont(_FONT_MONO, 9)); inp.setFixedHeight(28)
            inp.setStyleSheet(f"""
                QLineEdit {{ background: {C.PANEL}; color: {C.TEXT_BRIGHT};
                    border: 1px solid {C.BORDER}; border-radius: 3px; padding: 2px 8px; }}
                QLineEdit:focus {{ border: 1px solid {C.PRI}; }}
            """)
            tgl = QPushButton("*"); tgl.setFixedSize(28, 28)
            tgl.setCursor(Qt.CursorShape.PointingHandCursor)
            tgl.setStyleSheet(f"""
                QPushButton {{ background: {C.PANEL2}; color: {C.TEXT_MUTED};
                    border: 1px solid {C.BORDER}; border-radius: 3px; }}
                QPushButton:hover {{ color: {C.PRI}; border: 1px solid {C.PRI}; }}
            """)
            tgl.clicked.connect(lambda: inp.setEchoMode(
                QLineEdit.EchoMode.Normal if inp.echoMode() == QLineEdit.EchoMode.Password
                else QLineEdit.EchoMode.Password
            ))
            row.addWidget(inp, stretch=1); row.addWidget(tgl); lay.addLayout(row)
            return inp

        self._gemini_inp = _row("GEMINI API KEY", existing.get("gemini_api_key", ""), "AIza...")
        self._or_inp     = _row("OPENROUTER API KEY", existing.get("openrouter_api_key", ""), "sk-or-...")
        self._nv_inp     = _row("NVIDIA API KEY (FALLBACK)", existing.get("nvidia_api_key", ""), "nvapi-...")
        self._groq_inp   = _row("GROQ API KEY (ULTRA-FAST LPU)", existing.get("groq_api_key", ""), "gsk_...")


        lay.addSpacing(6)
        br = QHBoxLayout()
        bb = QPushButton("< BACK"); bb.setFixedHeight(32); bb.setFont(QFont(_FONT_MONO, 8))
        bb.setCursor(Qt.CursorShape.PointingHandCursor)
        bb.setStyleSheet(f"""
            QPushButton {{ background: {C.BG}; color: {C.TEXT_MUTED};
                border: 1px solid {C.BORDER}; border-radius: 3px; }}
            QPushButton:hover {{ color: {C.TEXT_BRIGHT}; border: 1px solid {C.TEXT_MUTED}; }}
        """)
        bb.clicked.connect(self._goto_api_keys)
        sb = QPushButton("[SAVE CHANGES]"); sb.setFont(QFont(_FONT_MONO, 9, QFont.Weight.Bold))
        sb.setFixedHeight(32); sb.setCursor(Qt.CursorShape.PointingHandCursor)
        sb.setStyleSheet(f"""
            QPushButton {{ background: {C.PANEL2}; color: {C.PRI};
                border: 1px solid {C.PRI_DIM}; border-radius: 3px; }}
            QPushButton:hover {{ background: {C.PRI_GHO}; border: 1px solid {C.PRI}; }}
        """)
        sb.clicked.connect(self._save)
        br.addWidget(bb); br.addWidget(sb, stretch=1); lay.addLayout(br)
        return w

    def _build_page_audio(self) -> QWidget:
        w = QWidget(); lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 6, 0, 0); lay.setSpacing(8)
        def _h(txt):
            lb = QLabel(txt); lb.setFont(QFont(_FONT_MONO, 8, QFont.Weight.Bold))
            lb.setStyleSheet(f"color: {C.TEXT_MUTED}; background: transparent;")
            return lb
        lay.addWidget(_h("SELECT ACTIVE MICROPHONE DEVICE:"))
        self._mic_combo = QComboBox(); self._mic_combo.setFixedHeight(34)
        self._mic_combo.setFont(QFont(_FONT_MONO, 8))
        self._mic_combo.setStyleSheet(f"""
            QComboBox {{ background: {C.PANEL}; color: {C.TEXT_BRIGHT};
                border: 1px solid {C.PRI}; border-radius: 4px; padding: 4px 8px; }}
            QComboBox QAbstractItemView {{ background: {C.PANEL2}; color: {C.TEXT_BRIGHT};
                selection-background-color: {C.PRI_GHO}; selection-color: {C.PRI};
                border: 1px solid {C.BORDER}; }}
        """)
        lay.addWidget(self._mic_combo)
        gh = QHBoxLayout()
        gl = _h("MIC GAIN BOOST:")
        self._gain_lbl = QLabel("1.6x"); self._gain_lbl.setFont(QFont(_FONT_MONO, 8, QFont.Weight.Bold))
        self._gain_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        gh.addWidget(gl); gh.addStretch(); gh.addWidget(self._gain_lbl); lay.addLayout(gh)
        self._gain_slider = QSlider(Qt.Orientation.Horizontal)
        self._gain_slider.setRange(10, 35); self._gain_slider.setValue(16)
        self._gain_slider.valueChanged.connect(lambda v: self._gain_lbl.setText(f"{v/10.0:.1f}x"))
        self._gain_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{ height: 4px; background: {C.BORDER}; border-radius: 2px; }}
            QSlider::sub-page:horizontal {{ background: {C.PRI}; border-radius: 2px; }}
            QSlider::handle:horizontal {{ background: {C.TEXT_BRIGHT}; width: 12px;
                margin-top: -4px; margin-bottom: -4px; border-radius: 6px; }}
        """)
        lay.addWidget(self._gain_slider)
        lay.addWidget(_h("LIVE INPUT LEVEL:"))
        self._audio_meter = QProgressBar(); self._audio_meter.setRange(0, 100)
        self._audio_meter.setValue(0); self._audio_meter.setTextVisible(False); self._audio_meter.setFixedHeight(10)
        self._audio_meter.setStyleSheet(f"""
            QProgressBar {{ background: {C.BG}; border: 1px solid {C.BORDER}; border-radius: 4px; }}
            QProgressBar::chunk {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 {C.PRI_DIM}, stop:0.7 {C.PRI}, stop:1.0 {C.AMBER}); border-radius: 3px; }}
        """)
        lay.addWidget(self._audio_meter)
        br = QHBoxLayout(); br.setSpacing(8)
        self._test_mic_btn = QPushButton("[TEST MIC 3s]")
        self._test_mic_btn.setFixedHeight(34); self._test_mic_btn.setFont(QFont(_FONT_MONO, 8, QFont.Weight.Bold))
        self._test_mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._test_mic_btn.setStyleSheet(f"""
            QPushButton {{ background: {C.PANEL2}; color: {C.CYAN};
                border: 1px solid {C.BORDER}; border-radius: 4px; }}
            QPushButton:hover {{ background: {C.PRI_GHO}; border: 1px solid {C.PRI}; }}
        """)
        self._test_mic_btn.clicked.connect(self._start_mic_test); br.addWidget(self._test_mic_btn)
        smb = QPushButton("[SAVE & APPLY MIC]"); smb.setFixedHeight(34)
        smb.setFont(QFont(_FONT_MONO, 8, QFont.Weight.Bold)); smb.setCursor(Qt.CursorShape.PointingHandCursor)
        smb.setStyleSheet(f"""
            QPushButton {{ background: {C.PANEL2}; color: {C.PRI};
                border: 1px solid {C.PRI}; border-radius: 4px; }}
            QPushButton:hover {{ background: {C.PRI_GHO}; color: {C.TEXT_BRIGHT}; }}
        """)
        smb.clicked.connect(self._save_selected_mic); br.addWidget(smb); lay.addLayout(br)
        self._save_status_lbl = QLabel(""); self._save_status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._save_status_lbl.setFont(QFont(_FONT_MONO, 7)); lay.addWidget(self._save_status_lbl)
        lay.addStretch(); self._back_btn(lay, self._goto_settings)
        return w

    def _refresh_mics_ui(self):
        try:
            from actions.audio_service import get_available_mics, get_configured_mic_index, get_configured_gain
            mics = get_available_mics(); saved_idx = get_configured_mic_index()
            self._mic_combo.clear(); sel = 0
            for i, m in enumerate(mics):
                self._mic_combo.addItem(m["label"], userData=m["index"])
                if saved_idx is not None and m["index"] == saved_idx: sel = i
                elif saved_idx is None and m.get("is_default"): sel = i
            if mics: self._mic_combo.setCurrentIndex(sel)
            gain = get_configured_gain(); self._gain_slider.setValue(int(gain * 10))
            self._gain_lbl.setText(f"{gain:.1f}x"); self._save_status_lbl.setText("")
        except Exception as e: print(f"[UI] Refresh mics error: {e}")

    def _start_mic_test(self):
        if getattr(self, "_test_running", False): return
        self._test_running = True
        self._test_mic_btn.setText("? SPEAK NOW...")
        self._test_mic_btn.setStyleSheet(f"background: {C.PRI_GHO}; color: {C.AMBER}; border: 1px solid {C.AMBER};")
        self._save_status_lbl.setText("Listening for 3 seconds...")
        self._save_status_lbl.setStyleSheet(f"color: {C.CYAN}; font-size: 7pt;")
        dev_idx = self._mic_combo.currentData(); gain = self._gain_slider.value() / 10.0

        def _worker():
            import sounddevice as sd
            from actions.audio_service import calculate_rms
            end_t = time.time() + 3.0
            def _cb(indata, frames, t_info, status):
                mono = indata[:, 0] if indata.ndim > 1 else indata.flatten()
                rms  = calculate_rms(mono) * gain
                pct  = min(100, int((rms / 2500.0) * 100)) if rms > 1 else 0
                QTimer.singleShot(0, lambda p=pct: self._audio_meter.setValue(p))
            try:
                with sd.InputStream(device=dev_idx, channels=1, dtype='int16', callback=_cb):
                    while time.time() < end_t: time.sleep(0.05)
            except Exception as e: print(f"[UI] Mic test error: {e}")
            finally: QTimer.singleShot(0, self._finish_mic_test)
        threading.Thread(target=_worker, daemon=True).start()

    def _finish_mic_test(self):
        self._test_running = False
        self._test_mic_btn.setText("[TEST MIC 3s]")
        self._test_mic_btn.setStyleSheet(f"background: {C.PANEL2}; color: {C.CYAN}; border: 1px solid {C.BORDER};")
        self._audio_meter.setValue(0); self._save_status_lbl.setText("Test finished.")

    def _save_selected_mic(self):
        dev_idx = self._mic_combo.currentData(); gain = self._gain_slider.value() / 10.0
        try:
            from actions.audio_service import set_configured_mic, set_configured_gain
            set_configured_mic(dev_idx); set_configured_gain(gain)
            self._save_status_lbl.setText("[OK] Saved! Active microphone updated.")
            self._save_status_lbl.setStyleSheet(f"color: {C.PRI}; font-size: 7pt;")
        except Exception as e:
            self._save_status_lbl.setText(f"[ERR] {e}")
            self._save_status_lbl.setStyleSheet("color: #ff4a4a; font-size: 7pt;")

    def _build_page_theme(self) -> QWidget:
        w = QWidget(); lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 6, 0, 0); lay.setSpacing(8)
        h = QLabel("WINDOWS & INDUS SYSTEM THEME:"); h.setFont(QFont(_FONT_MONO, 8, QFont.Weight.Bold))
        h.setStyleSheet(f"color: {C.TEXT_MUTED}; background: transparent;"); lay.addWidget(h)
        self._theme_status_lbl = QLabel("Current Theme: DARK"); self._theme_status_lbl.setFont(QFont(_FONT_MONO, 9, QFont.Weight.Bold))
        self._theme_status_lbl.setStyleSheet(f"color: {C.TEXT_BRIGHT}; background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 5px; padding: 8px;")
        lay.addWidget(self._theme_status_lbl)
        br = QHBoxLayout(); br.setSpacing(8)
        for label, mode, col in [("[DARK MODE]", "dark", C.PRI), ("[LIGHT MODE]", "light", C.AMBER)]:
            b = QPushButton(label); b.setFixedHeight(36); b.setFont(QFont(_FONT_MONO, 8, QFont.Weight.Bold))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(f"""
                QPushButton {{ background: {C.PANEL2}; color: {col};
                    border: 1px solid {col}; border-radius: 4px; }}
                QPushButton:hover {{ background: {C.PRI_GHO}; color: {C.TEXT_BRIGHT}; }}
            """)
            b.clicked.connect(lambda _, m=mode: self._apply_theme(m)); br.addWidget(b)
        lay.addLayout(br)
        desc = QLabel("Autonomous daemon monitors Windows theme. Dark Mode enforced if changed externally.")
        desc.setFont(QFont(_FONT_MONO, 7)); desc.setStyleSheet(f"color: {C.TEXT_MUTED};")
        lay.addWidget(desc); lay.addStretch(); self._back_btn(lay, self._goto_settings)
        return w

    def _refresh_theme_ui(self):
        try:
            from actions.computer_settings import get_theme_mode
            curr = get_theme_mode()
            self._theme_status_lbl.setText(f"System Theme: {curr.upper()} | Autonomous Watcher: ACTIVE")
        except Exception: pass

    def _apply_theme(self, mode: str):
        try:
            from actions.computer_settings import set_theme_mode
            set_theme_mode(mode)
            from memory.memory_manager import set_preference
            set_preference("theme", mode)
            self._refresh_theme_ui()
        except Exception as e: print(f"[UI] Apply theme error: {e}")

    def _build_page_memory(self) -> QWidget:
        w = QWidget(); lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 6, 0, 0); lay.setSpacing(6)
        h = QLabel("SQLITE PERMANENT KNOWLEDGE & HABITS:"); h.setFont(QFont(_FONT_MONO, 8, QFont.Weight.Bold))
        h.setStyleSheet(f"color: {C.TEXT_MUTED}; background: transparent;"); lay.addWidget(h)
        self._mem_text_area = QTextEdit(); self._mem_text_area.setReadOnly(True)
        self._mem_text_area.setFont(QFont(_FONT_MONO, 8))
        self._mem_text_area.setStyleSheet(f"""
            QTextEdit {{ background: {C.PANEL}; color: {C.TEXT_BRIGHT};
                border: 1px solid {C.BORDER}; border-radius: 4px; padding: 6px; }}
        """)
        lay.addWidget(self._mem_text_area, stretch=1)
        rb = QPushButton("[REFRESH MEMORY]"); rb.setFixedHeight(32)
        rb.setFont(QFont(_FONT_MONO, 8, QFont.Weight.Bold)); rb.setCursor(Qt.CursorShape.PointingHandCursor)
        rb.setStyleSheet(f"""
            QPushButton {{ background: {C.PANEL2}; color: {C.PRI};
                border: 1px solid {C.BORDER}; border-radius: 4px; }}
            QPushButton:hover {{ background: {C.PRI_GHO}; border: 1px solid {C.PRI}; }}
        """)
        rb.clicked.connect(self._refresh_memory_ui); lay.addWidget(rb)
        self._back_btn(lay, self._goto_settings)
        return w

    def _refresh_memory_ui(self):
        try:
            import memory.db_engine as db
            import memory.memory_manager as mm
            facts    = mm.load_memory(); mem_str = mm.format_memory_for_prompt(facts)
            recent   = db.db_get_recent_conversations(3); frequent = db.db_get_frequent_apps()
            lines    = ["=== USER PROFILE & PREFERENCES ==="]
            lines.append(mem_str if mem_str else "  No preferences recorded yet.")
            lines.append("\n=== LEARNED APP FREQUENCIES ===")
            lines.append("  Top Apps: " + ", ".join(frequent) if frequent else "  Tracking...")
            lines.append(f"\n=== RECENT CONVERSATIONS ({len(recent)} shown) ===")
            for c in recent:
                lines.append(f"  [{c.get('timestamp','')[:19]}]")
                lines.append(f"  User:  {c.get('user_text','')}")
                lines.append(f"  Indus: {c.get('indus_text', c.get('jarvis_text',''))[:120]}...\n")
            self._mem_text_area.setPlainText("\n".join(lines))
        except Exception as e:
            self._mem_text_area.setPlainText(f"Error loading memory: {e}")

    def _save(self):
        existing = {}
        if API_FILE.exists():
            try: existing = json.loads(API_FILE.read_text(encoding="utf-8"))
            except: pass
        existing["gemini_api_key"]     = self._gemini_inp.text().strip()
        existing["openrouter_api_key"] = self._or_inp.text().strip()
        existing["nvidia_api_key"]     = self._nv_inp.text().strip()
        if hasattr(self, "_groq_inp"):
            existing["groq_api_key"]   = self._groq_inp.text().strip()
        existing["os_system"]          = _OS.lower()
        os.makedirs(CONFIG_DIR, exist_ok=True)
        API_FILE.write_text(json.dumps(existing, indent=4), encoding="utf-8")
        try:
            from or_client import client; client.reload_keys()
        except Exception: pass
        self.saved.emit(existing); self.hide()

    def _close(self):
        self.closed.emit(); self.hide()



# --- Main Window -------------------------------------------------------------
class MainWindow(QMainWindow):
    _log_sig         = pyqtSignal(str)
    _state_sig       = pyqtSignal(str)
    _audio_level_sig = pyqtSignal(float)

    def __init__(self, face_path: str):
        super().__init__()
        self.setWindowTitle("INDUS  --  PERSONAL INTELLIGENCE SYSTEM")
        self.setMinimumSize(_MIN_W, _MIN_H)
        self.resize(_DEFAULT_W, _DEFAULT_H)
        screen = QApplication.primaryScreen().availableGeometry()
        self.move((screen.width() - _DEFAULT_W) // 2, (screen.height() - _DEFAULT_H) // 2)

        self.on_text_command  = None
        self._muted           = False
        self._commands_count  = 0
        self._start_time      = time.time()

        central = QWidget()
        central.setStyleSheet(f"background: {C.BG};")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(14, 10, 14, 12)
        root.setSpacing(10)
        root.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(12)
        self._left_col   = self._build_left_col()
        self._center_col = self._build_center_col(face_path)
        self._right_col  = self._build_right_col()
        body.addWidget(self._left_col,   stretch=0)
        body.addWidget(self._center_col, stretch=1)
        body.addWidget(self._right_col,  stretch=0)
        root.addLayout(body, stretch=1)

        self._clock_tmr = QTimer(self)
        self._clock_tmr.timeout.connect(self._tick_clock)
        self._clock_tmr.start(1000)
        self._tick_clock()

        self._metric_tmr = QTimer(self)
        self._metric_tmr.timeout.connect(self._update_metrics)
        self._metric_tmr.start(2000)
        self._update_metrics()

        self._log_sig.connect(self._log.append_log)
        self._state_sig.connect(self._apply_state)
        self._audio_level_sig.connect(self.hud.set_audio_level)

        self._overlay: SetupOverlay | None = None
        self._ready = self._check_config()
        if not self._ready:
            self._show_setup()

        QShortcut(QKeySequence("F4"),     self).activated.connect(self._toggle_mute)
        QShortcut(QKeySequence("F11"),    self).activated.connect(self._toggle_fullscreen)
        QShortcut(QKeySequence("Ctrl+,"), self).activated.connect(self._show_settings)

        # -- Info Card, Weather Card & Image Card Managers --------------------
        self._info_card_mgr = InfoCardManager(parent=self)
        self._weather_card_mgr = WeatherCardManager(parent=self)
        self._image_card_mgr = ImageCardManager(parent=self)

        # -- EventBus ? HUD log subscription ---------------------------------
        # Route key backend pipeline events to the CONSOLE // LIVE panel.
        # The callback fires from arbitrary threads ? use _log_sig (thread-safe Qt signal).
        self._eb_handler = self._on_bus_event   # keep strong ref so GC doesn't collect it
        try:
            from core.event_bus import event_bus
            event_bus.subscribe(None, self._eb_handler)   # wildcard: receive all events
            self._event_bus_ref = event_bus               # keep ref for closeEvent cleanup
        except Exception:
            self._event_bus_ref = None

    # -- EventBus callback (called from background thread) ---------------------
    _EVENT_LABELS = {
        "LLM_CONNECTED":       "[LLM]  Gemini Live connected",
        "TOOL_REQUESTED":      "[REQ] ",
        "TOOL_STARTED":        "[RUN] ",
        "TOOL_COMPLETED":      "[OK]  ",
        "TOOL_FAILED":         "[ERR] ",
        "TOOL_CANCELLED":      "[CANC]",
        "CANCEL_REQUESTED":    "[STOP] Cancellation requested",
        "REPLAN_STARTED":      "[PLAN] Re-planning task",
        "VERIFICATION_FAILED": "[VFY] Verification FAILED",
        "SECURITY_CHECK":      "[SEC] Security check",
        "MEMORY_UPDATE":       "[MEM] Memory updated",
    }

    def _on_bus_event(self, evt) -> None:
        """Translate EventBus events to HUD log lines via thread-safe Qt signal."""
        try:
            label = self._EVENT_LABELS.get(evt.name)
            if label is None:
                return   # skip events we don't want to display (e.g. AUDIO_CHUNK)

            data = evt.data or {}
            if evt.name in ("TOOL_REQUESTED", "TOOL_STARTED",
                            "TOOL_COMPLETED", "TOOL_FAILED", "TOOL_CANCELLED"):
                tool = data.get("tool") or data.get("name") or ""
                suffix = f" '{tool}'" if tool else ""
                msg = f"SYS:{label}{suffix}"
            elif evt.name == "REPLAN_STARTED":
                count = data.get("replan_count", "?")
                msg = f"SYS: [PLAN] Re-planning (attempt {count})"
            elif evt.name == "VERIFICATION_FAILED":
                action = data.get("action", "")
                msg = f"SYS: [VFY] Verification FAILED: {action}"
            elif evt.name == "MEMORY_UPDATE":
                keys = data.get("keys", [])
                msg = f"SYS: [MEM] Stored: {', '.join(keys[:3])}"
            else:
                msg = f"SYS: {label}"

            self._log_sig.emit(msg)
        except Exception:
            pass   # never crash the UI from a backend event

    def closeEvent(self, event):
        """Unsubscribe from EventBus before Qt destroys this window."""
        if getattr(self, "_event_bus_ref", None) is not None:
            try:
                self._event_bus_ref.unsubscribe(None, self._eb_handler)
            except Exception:
                pass
        super().closeEvent(event)

    @property
    def avatar(self):
        """Access the central AvatarController instance."""
        return self.hud.avatar_controller

    @property
    def info_card_manager(self) -> InfoCardManager:
        """Access the InfoCardManager for this window."""
        return self._info_card_mgr

    @property
    def weather_card_manager(self) -> WeatherCardManager:
        """Access the WeatherCardManager for this window."""
        return self._weather_card_mgr

    def show_weather_card(self, data: dict):
        """Display the floating Weather Card."""
        self._weather_card_mgr.show_card(data)

    @property
    def image_card_manager(self) -> ImageCardManager:
        """Access the ImageCardManager for this window."""
        return self._image_card_mgr

    def show_image_card(self, data: dict):
        """Display the floating Image Card."""
        self._image_card_mgr.show_card(data)

    def hide_image_card(self):
        """Hide the floating Image Card."""
        self._image_card_mgr.hide_card()

    def _show_settings(self):
        ov = SettingsOverlay(self.centralWidget())
        cw = self.centralWidget()
        ow, oh = 490, 430
        ov.setGeometry((cw.width() - ow) // 2, (cw.height() - oh) // 2, ow, oh)
        ov.saved.connect(lambda _: self._log.append_log("SYS: API keys updated."))
        ov.show()

    def _build_header(self) -> QWidget:
        w = QWidget(); w.setFixedHeight(48)
        w.setStyleSheet(f"background: {C.PANEL}; border-bottom: 1px solid {C.BORDER};")
        lay = QHBoxLayout(w); lay.setContentsMargins(16, 0, 16, 0)

        logo = QLabel("IN"); logo.setFixedSize(32, 32)
        logo.setFont(QFont(_FONT_MONO, 10, QFont.Weight.Bold))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet(f"QLabel {{ background: {C.PANEL2}; color: {C.PRI}; border: 1.5px solid {C.PRI}; border-radius: 2px; }}")
        lay.addWidget(logo); lay.addSpacing(10)

        tc = QVBoxLayout(); tc.setSpacing(0)
        t1 = QLabel("INDUS"); t1.setFont(QFont(_FONT_MONO, 14, QFont.Weight.Bold))
        t1.setStyleSheet(f"color: {C.TEXT_BRIGHT}; background: transparent;")
        t2 = QLabel("AI CONTROL CENTER"); t2.setFont(QFont(_FONT_MONO, 7, QFont.Weight.Bold))
        t2.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        tc.addWidget(t1); tc.addWidget(t2); lay.addLayout(tc); lay.addStretch()

        cc = QVBoxLayout(); cc.setSpacing(0)
        self._clock_lbl = QLabel("--:--:--"); self._clock_lbl.setFont(QFont(_FONT_MONO, 14, QFont.Weight.Bold))
        self._clock_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        self._clock_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._date_lbl = QLabel("--- -- --- ----"); self._date_lbl.setFont(QFont(_FONT_MONO, 7, QFont.Weight.Bold))
        self._date_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        self._date_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        cc.addWidget(self._clock_lbl); cc.addWidget(self._date_lbl)
        lay.addLayout(cc); lay.addSpacing(12)

        self._status_pill = QPushButton("? ACTIVE"); self._status_pill.setFixedSize(110, 28)
        self._status_pill.setFont(QFont(_FONT_MONO, 8, QFont.Weight.Bold))
        self._status_pill.setCursor(Qt.CursorShape.PointingHandCursor)
        self._status_pill.clicked.connect(self._toggle_mute)
        self._style_status_pill("LISTENING"); lay.addWidget(self._status_pill); lay.addSpacing(8)

        sg = QPushButton("[*]"); sg.setFixedSize(30, 30); sg.setFont(QFont(_FONT_MONO, 9, QFont.Weight.Bold))
        sg.setToolTip("Settings (Ctrl+,)"); sg.setCursor(Qt.CursorShape.PointingHandCursor)
        sg.setStyleSheet(f"""
            QPushButton {{ background: {C.PANEL2}; color: {C.PRI}; border: 1px solid {C.PRI_DIM}; border-radius: 2px; }}
            QPushButton:hover {{ background: {C.PRI_GHO}; color: {C.TEXT_BRIGHT}; border: 1px solid {C.PRI}; }}
        """)
        sg.clicked.connect(self._show_settings); lay.addWidget(sg)
        return w

    def _build_left_col(self) -> QWidget:
        w = QWidget(); w.setFixedWidth(_LEFT_W)
        lay = QVBoxLayout(w); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(10)

        vc = GlassPanel("SYSTEM VITALS")
        v_lay = QVBoxLayout(vc); v_lay.setContentsMargins(14, 24, 14, 14); v_lay.setSpacing(6)
        self._bar_cpu  = MetricBar("CPU COGNITION",  "0%",       C.PRI)
        self._bar_mem  = MetricBar("RAM MEMORY",     "0%",       C.PRI)
        self._bar_disk = MetricBar("DRIVE STORAGE",  "0%",       C.PRI)
        self._bar_net  = MetricBar("NETWORK FLOW",   "^0K v0K",  C.CYAN)
        self._bar_lat  = MetricBar("CLOUD LATENCY",  "0ms",      C.CYAN)
        for bar in [self._bar_cpu, self._bar_mem, self._bar_disk, self._bar_net, self._bar_lat]:
            v_lay.addWidget(bar)
        v_lay.addStretch(); lay.addWidget(vc, stretch=1)

        ic = GlassPanel("DATA INTAKE")
        i_lay = QVBoxLayout(ic); i_lay.setContentsMargins(14, 24, 14, 14); i_lay.setSpacing(8)
        self._drop_zone = FileDropZone(); self._drop_zone.file_selected.connect(self._on_file_selected)
        i_lay.addWidget(self._drop_zone); lay.addWidget(ic, stretch=0)
        return w

    def _build_center_col(self, face_path: str) -> QWidget:
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(10)
        self.hud = HudCanvas(face_path); lay.addWidget(self.hud, stretch=3)

        cc = GlassPanel("CONSOLE // LIVE")
        c_lay = QVBoxLayout(cc); c_lay.setContentsMargins(12, 24, 12, 10); c_lay.setSpacing(6)
        dots_row = QHBoxLayout()
        dots = QLabel("* * *"); dots.setFont(QFont(_FONT_MONO, 9))
        dots.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        dots_row.addStretch(); dots_row.addWidget(dots); c_lay.addLayout(dots_row)

        self._log = LogWidget(); c_lay.addWidget(self._log, stretch=1)

        ir = QHBoxLayout(); ir.setSpacing(6)
        self._input = QLineEdit(); self._input.setPlaceholderText("INPUT...")
        self._input.setFont(QFont(_FONT_MONO, 9)); self._input.setFixedHeight(34)
        self._input.setStyleSheet(f"""
            QLineEdit {{ background: {C.BG}; color: {C.TEXT_BRIGHT};
                border: 1.5px solid {C.PRI}; border-radius: 2px; padding: 4px 10px; }}
            QLineEdit:focus {{ border: 1.5px solid {C.PRI}; background: #030F1A; }}
        """)
        self._input.returnPressed.connect(self._send); ir.addWidget(self._input)
        sb = QPushButton(">"); sb.setFixedSize(34, 34); sb.setFont(QFont(_FONT_MONO, 11, QFont.Weight.Bold))
        sb.setCursor(Qt.CursorShape.PointingHandCursor)
        sb.setStyleSheet(f"""
            QPushButton {{ background: {C.PANEL2}; color: {C.PRI};
                border: 1.5px solid {C.PRI}; border-radius: 2px; }}
            QPushButton:hover {{ background: {C.PRI_GHO}; color: #FFFFFF; }}
        """)
        sb.clicked.connect(self._send); ir.addWidget(sb); c_lay.addLayout(ir)
        lay.addWidget(cc, stretch=2)
        return w

    def _build_right_col(self) -> QWidget:
        w = QWidget(); w.setFixedWidth(_RIGHT_W)
        lay = QVBoxLayout(w); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(10)

        qc = GlassPanel("QUICK DIRECTIVES")
        q_lay = QVBoxLayout(qc); q_lay.setContentsMargins(12, 24, 12, 12); q_lay.setSpacing(6)
        directives = [
            ("[WX] WEATHER BRIEF",  "Get the current weather report for my location", C.PRI),
            ("[DS] DAILY SUMMARY",  "Give me a daily executive summary of my tasks, reminders and updates", C.PRI),
            ("[RM] SET REMINDER",   "Help me set a new reminder with time and task", C.PRI),
            ("[SW] WEB SEARCH",     "Search the web for latest news and updates", C.MAGENTA),
            ("[CD] CODE SESSION",   "I need assistance with coding and software engineering", C.MAGENTA),
            ("[*]  INDUS SETTINGS", "__SETTINGS__", C.MAGENTA),
        ]
        for label, cmd, border_col in directives:
            btn = QPushButton(label); btn.setFixedHeight(33)
            btn.setFont(QFont(_FONT_MONO, 8, QFont.Weight.Bold))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{ background: {C.BG}; color: {C.TEXT_BRIGHT};
                    border: 1px solid {border_col}; border-radius: 2px;
                    text-align: left; padding-left: 10px; }}
                QPushButton:hover {{ color: {C.TEXT_BRIGHT}; border: 1.5px solid {border_col}; background: {C.PANEL2}; }}
            """)
            if cmd == "__SETTINGS__": btn.clicked.connect(self._show_settings)
            else: btn.clicked.connect(lambda _, c=cmd: self._trigger_quick_cmd(c))
            q_lay.addWidget(btn)
        q_lay.addStretch(); lay.addWidget(qc, stretch=1)

        sc_card = GlassPanel("SESSION LOG")
        s_lay = QVBoxLayout(sc_card); s_lay.setContentsMargins(14, 24, 14, 12); s_lay.setSpacing(5)

        def _row(title, init):
            r = QHBoxLayout()
            lb = QLabel(title); lb.setFont(QFont(_FONT_MONO, 7, QFont.Weight.Bold))
            lb.setStyleSheet(f"color: {C.TEXT_DIM}; border: none;")
            vl = QLabel(init); vl.setFont(QFont(_FONT_MONO, 9, QFont.Weight.Bold))
            vl.setStyleSheet(f"color: {C.AMBER}; border: none;")   # amber/gold -- Image 3
            vl.setAlignment(Qt.AlignmentFlag.AlignRight)
            r.addWidget(lb); r.addWidget(vl); s_lay.addLayout(r)
            return vl

        self._uptime_lbl      = _row("UPTIME",     "00:00:00")
        self._cmd_count_lbl   = _row("COMMANDS",   "0")
        self._db_status_lbl   = _row("MEM SYNC",   "? SQLITE")
        self._auto_status_lbl = _row("AUTONOMOUS", "? ACTIVE")

        lay.addWidget(sc_card, stretch=0)
        return w

    # -- Handlers -------------------------------------------------------------
    def _trigger_quick_cmd(self, cmd: str):
        self._input.setText(cmd); self._send()

    def _tick_clock(self):
        self._clock_lbl.setText(time.strftime("%H:%M:%S"))
        self._date_lbl.setText(time.strftime("%a %d %b %Y").upper())
        elapsed = int(time.time() - self._start_time)
        self._uptime_lbl.setText(f"{elapsed//3600:02d}:{(elapsed%3600)//60:02d}:{elapsed%60:02d}")

    def _update_metrics(self):
        snap = _metrics.snapshot()
        cpu_val = snap["cpu"]
        self._bar_cpu.set_value(cpu_val, f"{cpu_val:.0f}%  {snap['cpu_freq']}".strip())
        mem_pct = snap["mem"]
        self._bar_mem.set_value(mem_pct, f"{snap['mem_used_gb']:.1f}/{snap['mem_total_gb']:.0f}G ({mem_pct:.0f}%)")
        disk_pct = snap["disk_pct"]
        self._bar_disk.set_value(disk_pct, f"{snap['disk_free_gb']:.0f}G Free ({disk_pct:.0f}%)")
        self._bar_net.set_value(min(100.0, snap.get("net_sent", 0) + snap.get("net_recv", 0)), snap["net_str"])
        lat = snap["latency_ms"]
        self._bar_lat.set_value(min(100.0, (lat / 200.0) * 100.0) if lat > 0 else 100.0, f"{lat:.0f}ms" if lat > 0 else "Offline")

    def _style_status_pill(self, state: str):
        if self._muted or state == "MUTED":
            txt, col = "x MUTED", C.RED
        elif state == "SPEAKING":
            txt, col = "? SPEAKING", C.CYAN
        elif state in ("THINKING", "EXECUTING"):
            txt, col = "~ THINKING", C.AMBER
        elif state in ("STANDBY", "IDLE"):
            txt, col = "? ACTIVE", C.PRI
        elif state == "ACTIVATING":
            txt, col = "? ACTIVATING", C.PRI
        elif state in ("CANCELLING", "CANCELLED"):
            txt, col = "x CANCELLED", C.RED
        else:
            txt, col = "? ACTIVE", C.PRI
        self._status_pill.setText(txt)
        self._status_pill.setStyleSheet(f"""
            QPushButton {{ background: {C.PANEL2}; color: {col};
                border: 1.5px solid {col}; border-radius: 4px; font-weight: bold; }}
            QPushButton:hover {{ background: {C.PRI_GHO}; }}
        """)


    def _toggle_mute(self):
        self._muted = not self._muted
        self.hud.muted = self._muted
        state = "MUTED" if self._muted else "LISTENING"
        self.hud.state = state
        self._style_status_pill(state)
        self._log.append_log(f"SYS: Microphone {'muted' if self._muted else 'active'}.")

    def _toggle_fullscreen(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def _send(self):
        txt = self._input.text().strip()
        if not txt: return
        self._input.clear()
        self._commands_count += 1
        self._cmd_count_lbl.setText(str(self._commands_count))
        self._log.append_log(f"You: {txt}")
        if self.on_text_command:
            threading.Thread(target=self.on_text_command, args=(txt,), daemon=True).start()

    def _on_file_selected(self, path: str):
        p = Path(path)
        self._log.append_log(f"FILE: {p.name} loaded")
        if self.on_text_command:
            threading.Thread(target=self.on_text_command,
                             args=(f"[FILE_UPLOADED] path={path} | name={p.name}",), daemon=True).start()

    def _apply_state(self, state: str):
        self.hud.state    = state
        self.hud.speaking = (state == "SPEAKING")
        self._style_status_pill(state)

    def _check_config(self) -> bool:
        if not API_FILE.exists(): return False
        try:
            d = json.loads(API_FILE.read_text(encoding="utf-8"))
            return bool(d.get("gemini_api_key")) and (
                bool(d.get("openrouter_api_key")) or bool(d.get("nvidia_api_key"))
            )
        except Exception: return False

    def _show_setup(self):
        ov = SetupOverlay(self.centralWidget())
        cw = self.centralWidget()
        ov.setGeometry((cw.width() - 450) // 2, (cw.height() - 400) // 2, 450, 400)
        ov.done.connect(self._on_setup_done)
        ov.show(); self._overlay = ov

    def _on_setup_done(self, key: str, or_key: str, nv_key: str, os_name: str):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        API_FILE.write_text(json.dumps({
            "gemini_api_key": key, "openrouter_api_key": or_key,
            "nvidia_api_key": nv_key, "os_system": os_name,
        }, indent=4), encoding="utf-8")
        self._ready = True
        if self._overlay: self._overlay.hide(); self._overlay = None
        self._apply_state("LISTENING")
        self._log.append_log("SYS: INDUS core initialised. Vitals nominal.")


# --- Root Shim ---------------------------------------------------------------
class _RootShim:
    def __init__(self, app: QApplication):
        self._app = app
    def mainloop(self): self._app.exec()
    def protocol(self, *_): pass


# --- Public JarvisUI (all signals & methods preserved) -----------------------
class JarvisUI:
    def __init__(self, face_path: str, size=None):
        # ── HighDPI + crisp text fix (must be set BEFORE QApplication) ──
        os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
        os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")

        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setStyle("Fusion")

        self._win = MainWindow(face_path)
        self._win.show()
        self.root = _RootShim(self._app)

    @property
    def main_win(self):
        return self._win

    @property
    def avatar(self):
        """Access the central AvatarController instance."""
        return self._win.avatar

    @property
    def state(self) -> str:
        return self._win.hud.state

    @property
    def muted(self) -> bool:
        return self._win._muted


    @muted.setter
    def muted(self, v: bool):
        if v != self._win._muted:
            self._win._toggle_mute()

    @property
    def current_file(self) -> str | None:
        return self._win._drop_zone.current_file()

    @property
    def on_text_command(self):
        return self._win.on_text_command

    @on_text_command.setter
    def on_text_command(self, cb):
        self._win.on_text_command = cb

    def set_state(self, state: str):
        self._win._state_sig.emit(state)

    def set_audio_level(self, level: float):
        """Pass live audio amplitude (0.0 to 1.0) to HUD visualizer."""
        self._win._audio_level_sig.emit(float(level))

    def write_log(self, text: str):
        self._win._log_sig.emit(text)

    def wait_for_api_key(self):
        while not self._win._ready:
            time.sleep(0.1)

    def start_speaking(self):
        self.set_state("SPEAKING")

    def stop_speaking(self):
        if not self.muted:
            self.set_state("LISTENING")

    def show_info_card(self, query: str, result: str = "") -> None:
        """
        Display the floating Info Card with a search query and (optionally) result.
        Safe to call from any thread — marshalled to GUI thread via Qt signal.

        Usage in main.py::

            # Show card immediately with 'searching' state:
            self.ui.show_info_card(query=user_question)

            # ... later, when result is ready:
            self.ui.update_info_card(result=search_result_text)

            # Or show with result already populated:
            self.ui.show_info_card(query=user_question, result=answer_text)
        """
        self._win.info_card_manager.show_card(query, result)

    def update_info_card(self, result: str) -> None:
        """Update the info card result text (call after show_info_card with no result)."""
        self._win.info_card_manager.update_result(result)

    def hide_info_card(self) -> None:
        """Slide the info card out. Safe to call from any thread."""
        self._win.info_card_manager.hide_card()

    def show_weather_card(self, data: dict) -> None:
        """
        Display the floating Weather Card with meteorological data.
        Safe to call from any thread.
        """
        self._win.show_weather_card(data)

    def hide_weather_card(self) -> None:
        """Slide the weather card out. Safe to call from any thread."""
        self._win.hide_weather_card()

    def show_image_card(self, data: dict) -> None:
        """
        Display the floating Image Card with generated artwork preview.
        Safe to call from any thread.
        """
        self._win.show_image_card(data)

    def hide_image_card(self) -> None:
        """Slide the image card out. Safe to call from any thread."""
        self._win.hide_image_card()

    def show_security_confirmation_card(self, action: str, target: str, risk: str, token: str) -> None:
        """Display a structured high-visibility security confirmation card in the HUD."""
        card_text = (
            f"ACTION: {action.upper()}\n"
            f"TARGET: {target}\n"
            f"RISK LEVEL: {risk}\n"
            f"WARNING: This action cannot be automatically reversed.\n"
            f"TOKEN: {token}"
        )
        self.show_info_card(query="[SECURITY CONFIRMATION REQUIRED]", result=card_text)