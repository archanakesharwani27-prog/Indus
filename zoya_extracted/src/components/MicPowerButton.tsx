import React from 'react';
import { motion } from 'motion/react';
import { Mic, MicOff, RefreshCw, Volume2, Radio, Zap } from 'lucide-react';
import { SessionStatus } from '../types';

interface MicPowerButtonProps {
  status: SessionStatus;
  isMuted: boolean;
  onToggleConnection: () => void;
  onToggleMute: () => void;
}

export const MicPowerButton: React.FC<MicPowerButtonProps> = ({
  status,
  isMuted,
  onToggleConnection,
  onToggleMute,
}) => {
  const isConnected = status === 'listening' || status === 'speaking' || status === 'connecting';

  const renderIcon = () => {
    if (status === 'connecting') {
      return <RefreshCw className="w-6 h-6 text-cyan-300 animate-spin" />;
    }
    if (status === 'error') {
      return <RefreshCw className="w-6 h-6 text-rose-400 animate-bounce" />;
    }
    if (!isConnected) {
      return <Mic className="w-6 h-6 text-cyan-300 group-hover:scale-110 transition-transform" />;
    }
    if (status === 'speaking') {
      return <Volume2 className="w-6 h-6 text-cyan-200 animate-pulse" />;
    }
    return isMuted ? <MicOff className="w-6 h-6 text-amber-400" /> : <Mic className="w-6 h-6 text-cyan-300 animate-pulse" />;
  };

  return (
    <div className="relative flex items-center justify-center my-0.5 z-20 shrink-0">
      {/* Outer Rotating Energy Ring */}
      <div
        className={`absolute -inset-3 rounded-full border border-dashed transition-all duration-700 pointer-events-none ${
          isConnected
            ? 'border-cyan-400/60 animate-spin-slow shadow-[0_0_20px_rgba(6,182,212,0.6)]'
            : 'border-white/20'
        }`}
      />

      {/* Pulsing Backing Atmosphere Glow */}
      <div
        className={`absolute -inset-2 rounded-full blur-lg transition-all duration-500 pointer-events-none ${
          isConnected
            ? 'bg-cyan-500/40 animate-pulse'
            : 'bg-indigo-600/20 group-hover:bg-cyan-500/30'
        }`}
      />

      {/* Main ARC Reactor Activation Mic Button */}
      <button
        onClick={onToggleConnection}
        id="zoya-main-power-btn"
        aria-label="Toggle Zoya Voice Link"
        className={`group relative w-14 h-14 sm:w-16 sm:h-16 rounded-full flex items-center justify-center text-white shadow-2xl transition-all duration-300 hover:scale-105 active:scale-95 cursor-pointer border-2 ${
          isConnected
            ? 'bg-slate-950 border-cyan-400 shadow-[0_0_30px_rgba(6,182,212,0.8)] ring-2 ring-cyan-400/50'
            : 'bg-slate-900 hover:bg-slate-850 border-cyan-500/40 hover:border-cyan-400 shadow-lg'
        }`}
      >
        {/* Inner Arc Core Circle Gradient */}
        <div className="absolute inset-1.5 rounded-full bg-gradient-to-br from-cyan-950/80 via-slate-950 to-indigo-950/80 flex items-center justify-center border border-cyan-500/30">
          {renderIcon()}
        </div>

        {/* Small Live Signal Indicator */}
        <div className="absolute -bottom-1 px-1.5 py-0.2 rounded-full bg-slate-950 border border-cyan-400/60 text-[8px] font-mono font-bold text-cyan-300 tracking-wider uppercase shadow-md flex items-center gap-1">
          <Zap className="w-2 h-2 text-cyan-400 animate-pulse" />
          <span>{isConnected ? 'LIVE' : 'TAP'}</span>
        </div>
      </button>

      {/* Floating Mute Button */}
      {isConnected && (
        <motion.button
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0, opacity: 0 }}
          onClick={onToggleMute}
          id="zoya-mute-toggle-btn"
          title={isMuted ? 'Unmute microphone' : 'Mute microphone'}
          className={`absolute -right-12 w-9 h-9 rounded-full flex items-center justify-center border shadow-2xl transition-all cursor-pointer ${
            isMuted
              ? 'bg-amber-950/90 border-amber-400 text-amber-300 shadow-[0_0_15px_rgba(245,158,11,0.5)]'
              : 'bg-slate-900/90 border-cyan-500/40 text-cyan-300 hover:border-cyan-400 hover:bg-slate-850'
          }`}
        >
          {isMuted ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
        </motion.button>
      )}
    </div>
  );
};
