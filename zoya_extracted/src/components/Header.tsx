import React, { useState, useEffect } from 'react';
import { Sliders, Sparkles, Activity, Shield, Monitor, Eye, Radio, Cpu, Clock, Terminal } from 'lucide-react';
import { AuraTheme, SessionStatus } from '../types';

interface HeaderProps {
  status: SessionStatus;
  currentTheme: AuraTheme;
  executedToolsCount: number;
  memoryCount?: number;
  deviceCount?: number;
  onOpenSettings: () => void;
  onOpenPcControl?: () => void;
  onOpenToolLogs?: () => void;
  onOpenThemePicker?: () => void;
  onOpenMemoryVault?: () => void;
  onOpenDeviceSync?: () => void;
  onOpenVision?: () => void;
  onOpenJarvis?: () => void;
  onOpenHabits?: () => void;
  onOpenGeminiChat?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  status,
  memoryCount = 0,
  deviceCount = 1,
  onOpenSettings,
  onOpenPcControl,
  onOpenJarvis,
  onOpenVision,
}) => {
  const isLive = status === 'listening' || status === 'speaking' || status === 'connecting';
  const [currentTime, setCurrentTime] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentTime(now.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="shrink-0 w-full max-w-7xl px-4 py-2.5 flex items-center justify-between z-20 border-b border-cyan-500/30 bg-slate-950/90 backdrop-blur-2xl text-white relative hud-scanline">
      {/* Top Cybernetic Decorative Line */}
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent shadow-[0_0_10px_rgba(6,182,212,0.8)]" />

      {/* Brand & Mark-VII System Title */}
      <div className="flex items-center gap-3">
        <div className="relative group cursor-pointer" onClick={onOpenJarvis}>
          <div className="w-9 h-9 rounded-2xl bg-gradient-to-tr from-cyan-500 via-indigo-500 to-purple-600 p-0.5 shadow-[0_0_20px_rgba(6,182,212,0.5)]">
            <div className="w-full h-full rounded-[14px] bg-slate-950 flex items-center justify-center">
              <Shield className="w-5 h-5 text-cyan-400 animate-pulse" />
            </div>
          </div>
          {/* Rotating Ring overlay */}
          <div className="absolute -inset-1 rounded-2xl border border-cyan-400/30 animate-spin-slow pointer-events-none" />
        </div>

        <div>
          <div className="flex items-center gap-2">
            <span className="text-base sm:text-lg font-black tracking-widest text-white font-mono uppercase text-glow-cyan">
              ZOYA<span className="text-cyan-400">.AI</span>
            </span>
            <span className="px-2 py-0.5 rounded-md bg-cyan-500/20 border border-cyan-400/40 text-[9px] font-mono font-bold text-cyan-300 uppercase tracking-widest shadow-inner">
              MARK-VII HUD
            </span>
          </div>
          <p className="text-[10px] text-cyan-400/80 font-mono hidden sm:block">
            STARK OS // AUTONOMOUS MULTIMODAL ASSISTANT
          </p>
        </div>
      </div>

      {/* Center Tactical Telemetry Dashboard */}
      <div className="hidden lg:flex items-center gap-3 px-4 py-1.5 rounded-2xl bg-slate-900/90 border border-cyan-500/30 text-xs text-slate-300 font-mono shadow-inner">
        <div className="flex items-center gap-1.5">
          <div
            className={`w-2.5 h-2.5 rounded-full ${
              isLive
                ? 'bg-cyan-400 shadow-[0_0_12px_rgba(6,182,212,1)] animate-pulse'
                : 'bg-indigo-400'
            }`}
          />
          <span className="font-bold text-[11px] text-cyan-200 uppercase tracking-wider">
            {status === 'listening'
              ? 'LIVE AUDIO STREAM'
              : status === 'speaking'
              ? 'VOCAL SYNTHESIS'
              : status === 'connecting'
              ? 'INITIALIZING CORE'
              : 'SYSTEM STANDBY'}
          </span>
        </div>

        <span className="text-cyan-500/50">|</span>

        <span className="text-[10px] text-cyan-300 flex items-center gap-1 font-bold">
          <Clock className="w-3 h-3 text-cyan-400" /> {currentTime || '09:48:00'} UTC
        </span>

        <span className="text-cyan-500/50">|</span>

        <span className="text-[10px] text-emerald-400 flex items-center gap-1 font-bold">
          <Activity className="w-3 h-3" /> 12ms
        </span>

        <span className="text-cyan-500/50">|</span>

        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-200 border border-cyan-400/30 flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
          Wake Word: <strong className="text-white">"Hey Zoya"</strong>
        </span>
      </div>

      {/* Action Buttons HUD Bar */}
      <div className="flex items-center gap-2">
        {onOpenJarvis && (
          <button
            onClick={onOpenJarvis}
            title="Open JARVIS Autonomous Companion HUD"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-cyan-950/80 hover:bg-cyan-900/90 border border-cyan-400/50 text-cyan-300 hover:text-white transition-all shadow-[0_0_15px_rgba(6,182,212,0.3)] text-xs font-mono font-bold cursor-pointer"
          >
            <Shield className="w-4 h-4 text-cyan-400 animate-pulse" />
            <span className="hidden sm:inline">JARVIS HUD</span>
          </button>
        )}

        {onOpenVision && (
          <button
            onClick={onOpenVision}
            title="Open Camera Vision & Screen Scanner"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-950/80 hover:bg-indigo-900/90 border border-indigo-400/50 text-indigo-200 hover:text-white transition-all shadow-md text-xs font-mono font-bold cursor-pointer"
          >
            <Eye className="w-4 h-4 text-indigo-400" />
            <span className="hidden sm:inline">Vision AI</span>
          </button>
        )}

        {onOpenPcControl && (
          <button
            onClick={onOpenPcControl}
            title="Open PC App Automation & Media Controller"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-purple-950/80 hover:bg-purple-900/90 border border-purple-400/50 text-purple-200 hover:text-white transition-all shadow-md text-xs font-mono font-bold cursor-pointer"
          >
            <Monitor className="w-4 h-4 text-purple-400" />
            <span className="hidden sm:inline">PC Control</span>
          </button>
        )}

        <button
          onClick={onOpenSettings}
          id="zoya-settings-panel-btn"
          title="Open System Control Panel"
          className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-slate-900 to-slate-950 hover:from-slate-850 hover:to-slate-900 border border-cyan-500/40 text-cyan-200 hover:text-white transition-all shadow-lg cursor-pointer group font-mono text-xs"
        >
          <Sliders className="w-4 h-4 text-cyan-400 group-hover:rotate-90 transition-transform duration-300" />
          <span className="font-bold hidden md:inline">Control Panel</span>
          <div className="flex items-center gap-1 ml-1 text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-500/30">
            <span>{memoryCount}M</span>
            <span>·</span>
            <span>{deviceCount}D</span>
          </div>
        </button>
      </div>
    </header>
  );
};
