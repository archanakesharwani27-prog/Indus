import React, { useState } from 'react';
import {
  Shield,
  Smile,
  HeartHandshake,
  Sparkles,
  Zap,
  Music,
  HelpCircle,
  X,
  Compass,
  MessageCircle,
  Lightbulb,
  Radio,
  Check,
  Target
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface JarvisCompanionHUDProps {
  isOpen: boolean;
  onClose: () => void;
  onExecuteCommand: (cmd: string) => Promise<{ reply: string; success: boolean }>;
  showToast: (msg: string, type?: 'info' | 'error' | 'success') => void;
}

export const JarvisCompanionHUD: React.FC<JarvisCompanionHUDProps> = ({
  isOpen,
  onClose,
  onExecuteCommand,
  showToast,
}) => {
  const [activeProtocol, setActiveProtocol] = useState<string | null>(null);
  const [protocolResponse, setProtocolResponse] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const protocols = [
    {
      id: 'cheer_up',
      icon: Smile,
      title: 'Mood Boost & Cheer Up',
      desc: 'Zoya takes autonomous decisions to lift your mood with witty jokes, sweet compliments & cheerfulness.',
      command: 'Zoya, my mood is off today. Take charge, cheer me up, tell me something sweet or witty, and give me a good mood boost like a real best friend!',
      color: 'from-pink-500 to-rose-600',
      badge: 'Proactive Empathy',
    },
    {
      id: 'jarvis_tactical',
      icon: Shield,
      title: 'JARVIS Tactical Problem Solver',
      desc: 'Facing a tough situation? Zoya steps in like Iron Man’s JARVIS to break down complex problems and suggest solutions.',
      command: 'Zoya, act like Iron Man\'s JARVIS! I have a tough situation/problem right now. Analyze, break it down, and give me tactical proactive step-by-step solutions!',
      color: 'from-cyan-500 to-blue-600',
      badge: 'Autonomous AI',
    },
    {
      id: 'friend_talk',
      icon: HeartHandshake,
      title: 'Real Best Friend Heart-to-Heart',
      desc: 'Deep, caring, loyal conversation. Zoya reviews your vault memories and talks to you like a true lifelong partner.',
      command: 'Zoya, let\'s talk like true best friends. Check what you remember about me in your memory vault and ask me caring questions about how I am really doing today.',
      color: 'from-purple-500 to-indigo-600',
      badge: 'Memory Deep Connect',
    },
    {
      id: 'proactive_decision',
      icon: Lightbulb,
      title: 'Zoya Autonomous Decision Engine',
      desc: 'Let Zoya make a surprise decision for you — picked based on your past preferences and mood!',
      command: 'Zoya, use your autonomous decision making! Look at my past preferences or memories, decide what I should do right now (music, game, learn something new, or relax), and execute it!',
      color: 'from-amber-500 to-orange-600',
      badge: 'Self-Decision Mode',
    },
    {
      id: 'mood_music',
      icon: Music,
      title: 'Mood Music & Vibe Selector',
      desc: 'Zoya picks the perfect music or video recommendation based on your current vibe and opens YouTube/Spotify.',
      command: 'Zoya, recommend a song or vibe for my current mood and open YouTube for me to play it!',
      color: 'from-emerald-500 to-teal-600',
      badge: 'Cross-Device Action',
    },
    {
      id: 'habit_monitor',
      icon: Target,
      title: 'Daily Habit & Streak Monitor',
      desc: 'Zoya checks your daily water, exercise & reading habits, logs progress, and offers encouraging witty reminders!',
      command: 'Zoya, check my daily habit streaks (water, exercise, reading) and give me an encouraging, witty reminder and praise for staying on track!',
      color: 'from-cyan-500 to-emerald-600',
      badge: 'Habit Tracker AI',
    },
  ];

  const handleRunProtocol = async (protocol: typeof protocols[0]) => {
    setActiveProtocol(protocol.id);
    setIsLoading(true);
    setProtocolResponse(null);

    try {
      const res = await onExecuteCommand(protocol.command);
      if (res.success) {
        setProtocolResponse(res.reply);
        showToast(`Activated ${protocol.title}!`, 'success');
      } else {
        showToast('Failed to execute protocol.', 'error');
      }
    } catch (err) {
      console.error(err);
      showToast('Error executing JARVIS companion protocol.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-lg">
        <motion.div
          initial={{ opacity: 0, scale: 0.92, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.92, y: 15 }}
          className="relative w-full max-w-3xl max-h-[90vh] flex flex-col rounded-3xl bg-slate-950 border border-cyan-500/40 text-white shadow-[0_0_50px_rgba(6,182,212,0.2)] overflow-hidden"
        >
          {/* JARVIS Sci-Fi Header */}
          <div className="flex items-center justify-between p-5 border-b border-cyan-500/20 bg-slate-900/60">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-2xl bg-cyan-500/20 text-cyan-300 border border-cyan-400/50 shadow-inner">
                <Shield className="w-6 h-6 animate-pulse" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-black tracking-wide bg-gradient-to-r from-cyan-300 via-purple-300 to-pink-300 bg-clip-text text-transparent">
                    ZOYA AI • AUTONOMOUS COMPANION ENGINE
                  </h2>
                  <span className="px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-400/30">
                    AUTONOMOUS
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  Inspired by JARVIS, MJ & Nova — Zoya takes proactive decisions, cheers you up, & solves problems like a true partner!
                </p>
              </div>
            </div>

            <button
              onClick={onClose}
              className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Status HUD Banner */}
          <div className="px-6 py-3 bg-gradient-to-r from-cyan-950/60 via-purple-950/40 to-slate-950 border-b border-cyan-500/10 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2 text-cyan-300 font-semibold">
              <Radio className="w-3.5 h-3.5 text-cyan-400 animate-ping" />
              <span>PROACTIVE COMPANION PROTOCOL: <strong className="text-white">ACTIVE</strong></span>
            </div>
            <div className="flex items-center gap-2 text-slate-400 text-[11px]">
              <Zap className="w-3.5 h-3.5 text-amber-400" />
              <span>Autonomous Empathy & Tactical Decisioning</span>
            </div>
          </div>

          {/* Body Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Protocol Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {protocols.map((proto) => {
                const IconComponent = proto.icon;
                const isSelected = activeProtocol === proto.id;

                return (
                  <button
                    key={proto.id}
                    onClick={() => handleRunProtocol(proto)}
                    disabled={isLoading}
                    className={`group relative text-left p-4 rounded-2xl border transition-all cursor-pointer flex flex-col justify-between space-y-3 ${
                      isSelected
                        ? 'bg-slate-900 border-cyan-400 shadow-[0_0_25px_rgba(6,182,212,0.3)] ring-1 ring-cyan-400/50'
                        : 'bg-slate-900/60 border-white/10 hover:border-cyan-500/40 hover:bg-slate-900/90'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className={`p-2.5 rounded-xl bg-gradient-to-br ${proto.color} text-white shadow-md`}>
                        <IconComponent className="w-5 h-5" />
                      </div>
                      <span className="px-2 py-0.5 text-[10px] font-bold rounded-md bg-white/5 text-cyan-300 border border-white/10">
                        {proto.badge}
                      </span>
                    </div>

                    <div>
                      <h3 className="text-sm font-bold text-white group-hover:text-cyan-200 transition-colors">
                        {proto.title}
                      </h3>
                      <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                        {proto.desc}
                      </p>
                    </div>

                    <div className="pt-2 border-t border-white/5 flex items-center justify-between text-[11px] font-semibold text-cyan-400">
                      <span>Trigger Protocol</span>
                      <Sparkles className="w-3.5 h-3.5 group-hover:rotate-12 transition-transform" />
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Response Output Section */}
            {isLoading && (
              <div className="p-6 rounded-2xl bg-cyan-950/40 border border-cyan-500/30 text-center space-y-3">
                <Sparkles className="w-8 h-8 text-cyan-400 animate-spin mx-auto" />
                <p className="text-xs font-semibold text-cyan-200 animate-pulse">
                  Zoya is computing proactive decision & best-friend response...
                </p>
              </div>
            )}

            {protocolResponse && !isLoading && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-5 rounded-2xl bg-gradient-to-br from-slate-900 via-purple-950/40 to-slate-900 border border-purple-500/40 space-y-3 shadow-xl"
              >
                <div className="flex items-center justify-between border-b border-purple-500/20 pb-2">
                  <div className="flex items-center gap-2 text-xs font-bold text-purple-300">
                    <Sparkles className="w-4 h-4 text-purple-400" />
                    ZOYA PROACTIVE RESPONSE
                  </div>
                  <span className="text-[10px] text-emerald-400 font-bold flex items-center gap-1">
                    <Check className="w-3.5 h-3.5" /> Autonomous Action Executed
                  </span>
                </div>
                <p className="text-xs text-slate-200 leading-relaxed whitespace-pre-line font-medium">
                  {protocolResponse}
                </p>
              </motion.div>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
