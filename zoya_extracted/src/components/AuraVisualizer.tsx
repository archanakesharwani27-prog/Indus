import React, { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Shield, Zap, Radio, Cpu, Activity, Sparkles, Sliders, Volume2, Eye } from 'lucide-react';
import { AuraTheme, SessionStatus } from '../types';

interface AuraVisualizerProps {
  status: SessionStatus;
  theme: AuraTheme;
  micVolume: number;
  speakerVolume: number;
  lastCrossDeviceLog?: { text: string; from: string; time: string } | null;
  onThemeChange?: (newTheme: AuraTheme) => void;
}

const THEME_COLORS: Record<AuraTheme, { primary: string; secondary: string; glow: string; accent: string; name: string }> = {
  'neon-cyber': {
    primary: '#00f0ff',
    secondary: '#ff007f',
    glow: 'rgba(0, 240, 255, 0.5)',
    accent: '#7000ff',
    name: 'MARK-VII CYAN',
  },
  'sassy-pink': {
    primary: '#ff2a85',
    secondary: '#ff7300',
    glow: 'rgba(255, 42, 133, 0.5)',
    accent: '#ff0055',
    name: 'PEPPER PINK',
  },
  'electric-violet': {
    primary: '#a855f7',
    secondary: '#00ffff',
    glow: 'rgba(168, 85, 247, 0.5)',
    accent: '#da70d6',
    name: 'QUANTUM VIOLET',
  },
  'cosmic-emerald': {
    primary: '#10b981',
    secondary: '#00bfff',
    glow: 'rgba(16, 185, 129, 0.5)',
    accent: '#00fa9a',
    name: 'VIBRANIUM GREEN',
  },
  'midnight-gold': {
    primary: '#f59e0b',
    secondary: '#ef4444',
    glow: 'rgba(245, 158, 11, 0.5)',
    accent: '#ffd700',
    name: 'STARK ARMOR GOLD',
  },
};

export const AuraVisualizer: React.FC<AuraVisualizerProps> = ({
  status,
  theme,
  micVolume,
  speakerVolume,
  lastCrossDeviceLog,
  onThemeChange,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [activeTheme, setActiveTheme] = useState<AuraTheme>(theme);

  useEffect(() => {
    setActiveTheme(theme);
  }, [theme]);

  const colors = THEME_COLORS[activeTheme] || THEME_COLORS['neon-cyber'];

  // Render Arc Reactor canvas with spectrum rings and audio reactive pulse
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let phase = 0;

    const render = () => {
      const width = canvas.width;
      const height = canvas.height;
      const centerX = width / 2;
      const centerY = height / 2;

      ctx.clearRect(0, 0, width, height);

      phase += 0.04;

      const activeVol = status === 'speaking' ? speakerVolume : status === 'listening' ? micVolume : 0.08;
      const baseRadius = Math.min(width, height) * 0.22;
      const currentRadius = baseRadius + activeVol * 40;

      // 1. Ambient Background Core Glow
      const glowGrad = ctx.createRadialGradient(centerX, centerY, currentRadius * 0.1, centerX, centerY, currentRadius * 2.5);
      glowGrad.addColorStop(0, colors.glow);
      glowGrad.addColorStop(0.4, colors.primary + '22');
      glowGrad.addColorStop(1, 'transparent');

      ctx.save();
      ctx.fillStyle = glowGrad;
      ctx.beginPath();
      ctx.arc(centerX, centerY, currentRadius * 2.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();

      // 2. Radial Audio Spectrum Bars (JARVIS Hologram Ring)
      const barCount = 48;
      const barBaseLen = 8;
      ctx.save();
      for (let i = 0; i < barCount; i++) {
        const angle = (i / barCount) * Math.PI * 2 + phase * 0.2;
        // Frequency wave simulation
        const wave = Math.sin(angle * 8 + phase * 3) * 0.5 + 0.5;
        const barHeight = barBaseLen + activeVol * 45 * wave + Math.random() * (activeVol * 15);

        const innerR = currentRadius + 18;
        const outerR = innerR + barHeight;

        const x1 = centerX + Math.cos(angle) * innerR;
        const y1 = centerY + Math.sin(angle) * innerR;
        const x2 = centerX + Math.cos(angle) * outerR;
        const y2 = centerY + Math.sin(angle) * outerR;

        ctx.strokeStyle = i % 2 === 0 ? colors.primary : colors.secondary;
        ctx.lineWidth = 2.5;
        ctx.lineCap = 'round';
        ctx.globalAlpha = 0.4 + wave * 0.6;

        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }
      ctx.restore();

      // 3. Fluid Pulsing Arc Core
      ctx.save();
      ctx.beginPath();
      const points = 100;
      for (let i = 0; i <= points; i++) {
        const angle = (i / points) * Math.PI * 2;
        let wave = 0;

        if (status === 'speaking') {
          wave = Math.sin(angle * 8 + phase * 2.5) * (14 + speakerVolume * 35) + Math.cos(angle * 12 - phase * 2) * (8 + speakerVolume * 20);
        } else if (status === 'listening') {
          wave = Math.sin(angle * 6 + phase * 2) * (8 + micVolume * 25) + Math.cos(angle * 10 - phase) * (6 + micVolume * 15);
        } else if (status === 'connecting') {
          wave = Math.sin(angle * 14 + phase * 5) * 10;
        } else {
          wave = Math.sin(angle * 6 + phase) * 4;
        }

        const r = currentRadius + wave;
        const x = centerX + Math.cos(angle) * r;
        const y = centerY + Math.sin(angle) * r;

        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.closePath();

      const coreGrad = ctx.createRadialGradient(
        centerX - currentRadius * 0.3,
        centerY - currentRadius * 0.3,
        currentRadius * 0.1,
        centerX,
        centerY,
        currentRadius * 1.4
      );
      coreGrad.addColorStop(0, '#ffffff');
      coreGrad.addColorStop(0.3, colors.primary);
      coreGrad.addColorStop(0.8, colors.secondary);
      coreGrad.addColorStop(1, colors.accent);

      ctx.fillStyle = coreGrad;
      ctx.shadowColor = colors.primary;
      ctx.shadowBlur = 35 + activeVol * 50;
      ctx.fill();
      ctx.restore();

      // 4. Inner Arc Glass Highlights
      ctx.save();
      ctx.fillStyle = 'rgba(255, 255, 255, 0.4)';
      ctx.beginPath();
      ctx.arc(centerX - currentRadius * 0.3, centerY - currentRadius * 0.3, currentRadius * 0.25, 0, Math.PI * 2);
      ctx.fill();

      // Core Tri-Arc Reactor Symbol Lines
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2;
      ctx.globalAlpha = 0.8;
      for (let a = 0; a < 3; a++) {
        const triAngle = (a / 3) * Math.PI * 2 + phase * 0.5;
        const tx1 = centerX + Math.cos(triAngle) * (currentRadius * 0.2);
        const ty1 = centerY + Math.sin(triAngle) * (currentRadius * 0.2);
        const tx2 = centerX + Math.cos(triAngle) * (currentRadius * 0.7);
        const ty2 = centerY + Math.sin(triAngle) * (currentRadius * 0.7);

        ctx.beginPath();
        ctx.moveTo(tx1, ty1);
        ctx.lineTo(tx2, ty2);
        ctx.stroke();
      }
      ctx.restore();

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [status, activeTheme, micVolume, speakerVolume, colors]);

  // Resize canvas automatically
  useEffect(() => {
    const handleResize = () => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * window.devicePixelRatio;
      canvas.height = rect.height * window.devicePixelRatio;
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleSelectTheme = (t: AuraTheme) => {
    setActiveTheme(t);
    if (onThemeChange) {
      onThemeChange(t);
    }
  };

  return (
    <div className="relative flex flex-col items-center justify-center w-full max-w-3xl px-2 py-1 my-1">
      {/* JARVIS Sci-Fi Telemetry Banner Top */}
      <div className="mb-2 flex flex-wrap items-center justify-center gap-2 sm:gap-4 z-10">
        <div className="px-3 py-1 rounded-full bg-cyan-950/80 border border-cyan-400/50 text-cyan-300 text-[10px] font-mono font-bold tracking-widest uppercase flex items-center gap-2 shadow-lg shadow-cyan-950/60 backdrop-blur-md">
          <Shield className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
          <span>STARK MARK-VII // ARC REACTOR ONLINE</span>
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
        </div>

        <div className="hidden sm:flex items-center gap-3 text-[10px] font-mono text-cyan-400/80 bg-slate-950/80 px-3 py-1 rounded-full border border-cyan-500/20 backdrop-blur-md">
          <span className="flex items-center gap-1">
            <Cpu className="w-3 h-3 text-cyan-300" />
            CORE: <strong className="text-white">QUANTUM-9</strong>
          </span>
          <span>|</span>
          <span className="flex items-center gap-1">
            <Activity className="w-3 h-3 text-emerald-400 animate-pulse" />
            LATENCY: <strong className="text-emerald-300">12ms</strong>
          </span>
          <span>|</span>
          <span className="flex items-center gap-1">
            <Zap className="w-3 h-3 text-amber-400" />
            POWER: <strong className="text-amber-300">100% ARC</strong>
          </span>
        </div>
      </div>

      {/* Main Holographic Outer Container */}
      <div className="relative w-56 h-56 sm:w-64 sm:h-64 flex items-center justify-center my-1 shrink-0">
        {/* Outer Hexagon Grid Ambient Light */}
        <div
          className="absolute inset-0 rounded-full blur-3xl opacity-30 animate-pulse transition-all duration-700 pointer-events-none"
          style={{ background: `radial-gradient(circle, ${colors.primary} 0%, ${colors.secondary} 50%, transparent 80%)` }}
        />

        {/* HUD Rotating Gear Ring 1 (Outer Clockwise) */}
        <div
          className="absolute w-[92%] h-[92%] rounded-full border border-dashed border-cyan-400/30 animate-spin-slow pointer-events-none flex items-center justify-center"
          style={{ borderColor: colors.primary + '55' }}
        >
          {/* Degree Ticks */}
          <span className="absolute top-1 text-[8px] font-mono text-cyan-400/60 font-bold">0° N</span>
          <span className="absolute bottom-1 text-[8px] font-mono text-cyan-400/60 font-bold">180° S</span>
          <span className="absolute left-1 text-[8px] font-mono text-cyan-400/60 font-bold">270° W</span>
          <span className="absolute right-1 text-[8px] font-mono text-cyan-400/60 font-bold">90° E</span>
        </div>

        {/* HUD Rotating Gear Ring 2 (Inner Counter-Clockwise with Crosshair Marks) */}
        <div
          className="absolute w-[80%] h-[80%] rounded-full border-2 border-cyan-500/20 animate-spin-reverse pointer-events-none"
          style={{ borderColor: colors.secondary + '44' }}
        >
          <div className="absolute inset-0 flex items-center justify-between px-2">
            <div className="w-3 h-0.5 bg-cyan-400/60" />
            <div className="w-3 h-0.5 bg-cyan-400/60" />
          </div>
          <div className="absolute inset-0 flex flex-col items-center justify-between py-2">
            <div className="w-0.5 h-3 bg-cyan-400/60" />
            <div className="w-0.5 h-3 bg-cyan-400/60" />
          </div>
        </div>

        {/* Outer Corner HUD Target Frames */}
        <div className="absolute inset-2 pointer-events-none flex flex-col justify-between p-1">
          <div className="flex justify-between text-cyan-400/60">
            <span className="text-[9px] font-mono font-bold">┌─ ARC_VII</span>
            <span className="text-[9px] font-mono font-bold">SYS.OK ─┐</span>
          </div>
          <div className="flex justify-between text-cyan-400/60">
            <span className="text-[9px] font-mono font-bold">└─ TACTICAL</span>
            <span className="text-[9px] font-mono font-bold">AI_ZOYA ─┘</span>
          </div>
        </div>

        {/* Center Orb Canvas Frame */}
        <div
          className="relative w-40 h-40 sm:w-48 sm:h-48 rounded-full p-1 flex items-center justify-center transition-all duration-500"
          style={{
            background: `linear-gradient(135deg, ${colors.primary}, ${colors.secondary}, ${colors.accent})`,
            boxShadow: `0 0 45px ${colors.glow}`,
          }}
        >
          <div className="w-full h-full rounded-full bg-[#020617] flex items-center justify-center overflow-hidden relative border border-white/20">
            <canvas ref={canvasRef} className="w-full h-full object-contain" />
          </div>
        </div>
      </div>

      {/* Cross-Device Remote Command Live Text Overlay */}
      <AnimatePresence>
        {lastCrossDeviceLog && (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            className="mt-2 px-4 py-2 rounded-2xl bg-cyan-950/90 border border-cyan-400/60 text-cyan-200 text-xs font-medium flex items-center gap-2.5 shadow-xl shadow-cyan-950/80 backdrop-blur-md z-20 max-w-sm"
          >
            <div className="p-1.5 rounded-lg bg-cyan-500/20 text-cyan-300 shrink-0">
              <Radio className="w-4 h-4 animate-pulse" />
            </div>
            <div className="flex-1 min-w-0 text-left">
              <div className="flex items-center justify-between text-[10px] text-cyan-400/80 font-bold uppercase tracking-wider">
                <span>From Mobile/Remote ({lastCrossDeviceLog.from})</span>
                <span>{lastCrossDeviceLog.time}</span>
              </div>
              <p className="text-xs font-semibold text-white truncate mt-0.5">
                {lastCrossDeviceLog.text}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Interactive Status Caption */}
      <div className="mt-3 text-center z-10 space-y-1">
        <p className="text-cyan-300 font-mono text-xs tracking-widest uppercase font-bold animate-pulse flex items-center justify-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-pink-400" />
          {status === 'speaking'
            ? 'ZOYA: "Executing vocal response, Master..."'
            : status === 'listening'
            ? 'ZOYA: "Listening for your voice command..."'
            : status === 'connecting'
            ? 'ZOYA: "Connecting Neural Core Live Stream..."'
            : 'ZOYA: "Standing by. Tap reactor button to initialize."'}
        </p>

        <h2 className="text-2xl sm:text-3xl font-black text-white tracking-wider font-sans uppercase">
          {status === 'listening'
            ? '⚡ LISTENING LINK ACTIVE'
            : status === 'speaking'
            ? '🎵 VOICE TRANSMISSION'
            : status === 'connecting'
            ? '🔄 INITIALIZING ZOYA'
            : status === 'error'
            ? '⚠️ CORE RE-CONNECTING'
            : 'SYSTEM READY'}
        </h2>
      </div>

      {/* Quick Theme Selector Pills */}
      <div className="mt-4 flex flex-wrap items-center justify-center gap-1.5 bg-slate-950/90 p-1.5 rounded-2xl border border-cyan-500/30 backdrop-blur-md">
        <span className="text-[10px] font-mono font-bold text-cyan-400 uppercase px-2 flex items-center gap-1">
          <Sliders className="w-3 h-3 text-cyan-300" /> Arc Theme:
        </span>
        {(Object.keys(THEME_COLORS) as AuraTheme[]).map((tKey) => {
          const tInfo = THEME_COLORS[tKey];
          const isSelected = activeTheme === tKey;
          return (
            <button
              key={tKey}
              onClick={() => handleSelectTheme(tKey)}
              className={`px-2.5 py-1 rounded-xl text-[10px] font-mono font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                isSelected
                  ? 'bg-cyan-500/20 text-white border border-cyan-400 shadow-[0_0_10px_rgba(6,182,212,0.4)]'
                  : 'bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 border border-transparent'
              }`}
            >
              <span className="w-2 h-2 rounded-full" style={{ background: tInfo.primary }} />
              <span>{tInfo.name}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
