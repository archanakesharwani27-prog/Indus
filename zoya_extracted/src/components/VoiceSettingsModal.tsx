import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  X,
  Mic,
  Check,
  Volume2,
  Sparkles,
  HeartHandshake,
  MessageSquare,
  Eye,
  Shield,
  Smartphone,
  Target,
  Brain,
  Terminal,
  Palette,
  Sliders,
  PhoneCall,
  Monitor,
} from 'lucide-react';
import { VoiceOption } from '../types';

interface VoiceSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedVoice: string;
  onSelectVoice: (voiceName: string) => void;
  memoryCount?: number;
  deviceCount?: number;
  executedToolsCount?: number;
  onOpenGeminiChat?: () => void;
  onOpenVision?: () => void;
  onOpenJarvis?: () => void;
  onOpenDeviceSync?: () => void;
  onOpenHabits?: () => void;
  onOpenMemoryVault?: () => void;
  onOpenPcControl?: () => void;
  onOpenToolLogs?: () => void;
  onOpenThemePicker?: () => void;
  onSimulateCall?: (name?: string, relation?: string, number?: string, isSpam?: boolean, isUnknown?: boolean) => void;
}

const VOICE_OPTIONS: VoiceOption[] = [
  { id: 'Aoede', name: 'Aoede (Recommended)', description: 'Vibrant, sassy, warm female voice', gender: 'female' },
  { id: 'Kore', name: 'Kore', description: 'Confident, expressive, clear female voice', gender: 'female' },
  { id: 'Zephyr', name: 'Zephyr', description: 'Smooth, relaxed, playful female voice', gender: 'female' },
  { id: 'Puck', name: 'Puck', description: 'Mischievous, energetic male voice', gender: 'male' },
  { id: 'Fenrir', name: 'Fenrir', description: 'Bold, charismatic male voice', gender: 'male' },
];

export const VoiceSettingsModal: React.FC<VoiceSettingsModalProps> = ({
  isOpen,
  onClose,
  selectedVoice,
  onSelectVoice,
  memoryCount = 0,
  deviceCount = 1,
  executedToolsCount = 0,
  onOpenGeminiChat,
  onOpenVision,
  onOpenJarvis,
  onOpenDeviceSync,
  onOpenHabits,
  onOpenMemoryVault,
  onOpenPcControl,
  onOpenToolLogs,
  onOpenThemePicker,
  onSimulateCall,
}) => {
  const handleToolClick = (action?: () => void) => {
    if (action) {
      onClose();
      action();
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-slate-950/80 backdrop-blur-md"
          />

          <motion.div
            initial={{ scale: 0.9, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.9, opacity: 0, y: 20 }}
            className="relative w-full max-w-lg bg-[#0a0a0f] border border-white/10 rounded-2xl p-6 shadow-2xl text-slate-100 z-10 max-h-[90vh] overflow-y-auto no-scrollbar"
          >
            {/* Header */}
            <div className="flex items-center justify-between pb-4 border-b border-white/10">
              <div className="flex items-center gap-2">
                <Sliders className="w-5 h-5 text-purple-400" />
                <h3 className="text-base font-bold">Control Panel & AI Tools</h3>
              </div>
              <button
                onClick={onClose}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* AI Capabilities & Tools Launcher Grid */}
            <div className="my-5 space-y-2">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
                Zoya Features & Tools
              </label>

              <div className="grid grid-cols-2 gap-2.5">
                {/* PC Control */}
                <button
                  onClick={() => handleToolClick(onOpenPcControl)}
                  className="flex items-center gap-3 p-3 rounded-xl bg-pink-950/40 hover:bg-pink-900/60 border border-pink-500/30 text-left transition-all cursor-pointer group"
                >
                  <div className="p-2 rounded-lg bg-pink-900/80 text-pink-300 group-hover:scale-110 transition-transform">
                    <Monitor className="w-4 h-4 text-pink-400" />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-pink-200">PC Controller</p>
                    <p className="text-[10px] text-slate-400">Apps, Audio & Cmds</p>
                  </div>
                </button>

                {/* Gemini Chat */}
                <button
                  onClick={() => handleToolClick(onOpenGeminiChat)}
                  className="flex items-center gap-3 p-3 rounded-xl bg-purple-950/40 hover:bg-purple-900/60 border border-purple-500/30 text-left transition-all cursor-pointer group"
                >
                  <div className="p-2 rounded-lg bg-purple-900/80 text-purple-300 group-hover:scale-110 transition-transform">
                    <MessageSquare className="w-4 h-4" />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-purple-200">Gemini Chat</p>
                    <p className="text-[10px] text-slate-400">Search & Maps Grounded</p>
                  </div>
                </button>

                {/* Vision & Screen */}
                <button
                  onClick={() => handleToolClick(onOpenVision)}
                  className="flex items-center gap-3 p-3 rounded-xl bg-indigo-950/40 hover:bg-indigo-900/60 border border-indigo-500/30 text-left transition-all cursor-pointer group"
                >
                  <div className="p-2 rounded-lg bg-indigo-900/80 text-indigo-300 group-hover:scale-110 transition-transform">
                    <Eye className="w-4 h-4" />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-indigo-200">Vision & Screen</p>
                    <p className="text-[10px] text-slate-400">Camera & Screen Reader</p>
                  </div>
                </button>

                {/* ZOYA Protocol / JARVIS */}
                <button
                  onClick={() => handleToolClick(onOpenJarvis)}
                  className="flex items-center gap-3 p-3 rounded-xl bg-cyan-950/40 hover:bg-cyan-900/60 border border-cyan-500/30 text-left transition-all cursor-pointer group"
                >
                  <div className="p-2 rounded-lg bg-cyan-900/80 text-cyan-300 group-hover:scale-110 transition-transform">
                    <Shield className="w-4 h-4" />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-cyan-200">Zoya Protocol</p>
                    <p className="text-[10px] text-slate-400">JARVIS Companion HUD</p>
                  </div>
                </button>

                {/* Device Sync */}
                <button
                  onClick={() => handleToolClick(onOpenDeviceSync)}
                  className="flex items-center gap-3 p-3 rounded-xl bg-blue-950/40 hover:bg-blue-900/60 border border-blue-500/30 text-left transition-all cursor-pointer group"
                >
                  <div className="p-2 rounded-lg bg-blue-900/80 text-blue-300 group-hover:scale-110 transition-transform">
                    <Smartphone className="w-4 h-4" />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-blue-200">Device Sync</p>
                    <p className="text-[10px] text-slate-400">PC & Mobile ({deviceCount})</p>
                  </div>
                </button>

                {/* Daily Habits */}
                <button
                  onClick={() => handleToolClick(onOpenHabits)}
                  className="flex items-center gap-3 p-3 rounded-xl bg-emerald-950/40 hover:bg-emerald-900/60 border border-emerald-500/30 text-left transition-all cursor-pointer group"
                >
                  <div className="p-2 rounded-lg bg-emerald-900/80 text-emerald-300 group-hover:scale-110 transition-transform">
                    <Target className="w-4 h-4" />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-emerald-200">Habit Tracker</p>
                    <p className="text-[10px] text-slate-400">Streaks & Logs</p>
                  </div>
                </button>

                {/* Memory Vault */}
                <button
                  onClick={() => handleToolClick(onOpenMemoryVault)}
                  className="flex items-center gap-3 p-3 rounded-xl bg-pink-950/40 hover:bg-pink-900/60 border border-pink-500/30 text-left transition-all cursor-pointer group"
                >
                  <div className="p-2 rounded-lg bg-pink-900/80 text-pink-300 group-hover:scale-110 transition-transform">
                    <Brain className="w-4 h-4" />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-pink-200">Memory Vault</p>
                    <p className="text-[10px] text-slate-400">{memoryCount} Saved Facts</p>
                  </div>
                </button>

                {/* Tool Logs */}
                <button
                  onClick={() => handleToolClick(onOpenToolLogs)}
                  className="flex items-center gap-3 p-3 rounded-xl bg-slate-900/60 hover:bg-slate-800/80 border border-white/10 text-left transition-all cursor-pointer group"
                >
                  <div className="p-2 rounded-lg bg-slate-800 text-slate-300 group-hover:scale-110 transition-transform">
                    <Terminal className="w-4 h-4" />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-slate-200">Tool Executions</p>
                    <p className="text-[10px] text-slate-400">{executedToolsCount} Browser Actions</p>
                  </div>
                </button>

                {/* Theme Mood */}
                <button
                  onClick={() => handleToolClick(onOpenThemePicker)}
                  className="flex items-center gap-3 p-3 rounded-xl bg-slate-900/60 hover:bg-slate-800/80 border border-white/10 text-left transition-all cursor-pointer group"
                >
                  <div className="p-2 rounded-lg bg-slate-800 text-pink-400 group-hover:scale-110 transition-transform">
                    <Palette className="w-4 h-4" />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-slate-200">Theme Aura</p>
                    <p className="text-[10px] text-slate-400">Visual Mood Engine</p>
                  </div>
                </button>
              </div>

              {/* Read Caller's Name Announcer Feature */}
              {onSimulateCall && (
                <div className="mt-4 p-3.5 rounded-xl bg-gradient-to-r from-purple-950/60 via-slate-900 to-slate-950 border border-purple-500/30 text-left">
                  <div className="flex items-center gap-2 mb-2">
                    <PhoneCall className="w-4 h-4 text-emerald-400 animate-pulse" />
                    <p className="text-xs font-extrabold text-purple-200">
                      Read Caller's Name & Call Assistant
                    </p>
                  </div>
                  <p className="text-[11px] text-slate-400 mb-3 leading-relaxed">
                    Zoya reads out loud who is calling (e.g. "Papa ka phone aa raha hai...") and lets you accept or decline via voice command or buttons!
                  </p>

                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => {
                        onClose();
                        onSimulateCall('Papa', 'Father', '+91 98765 12345', false, false);
                      }}
                      className="px-2.5 py-1.5 rounded-lg bg-purple-900/50 hover:bg-purple-800/80 border border-purple-500/30 text-[11px] font-semibold text-purple-200 cursor-pointer transition-colors"
                    >
                      📞 Call Papa
                    </button>
                    <button
                      onClick={() => {
                        onClose();
                        onSimulateCall('Mom', 'Mother', '+91 98765 67890', false, false);
                      }}
                      className="px-2.5 py-1.5 rounded-lg bg-pink-900/50 hover:bg-pink-800/80 border border-pink-500/30 text-[11px] font-semibold text-pink-200 cursor-pointer transition-colors"
                    >
                      📞 Call Mom
                    </button>
                    <button
                      onClick={() => {
                        onClose();
                        onSimulateCall('Spam Telemarketer', 'Telemarketer / Spam', '+91 14000 99999', true, false);
                      }}
                      className="px-2.5 py-1.5 rounded-lg bg-rose-900/60 hover:bg-rose-800/90 border border-rose-500/40 text-[11px] font-semibold text-rose-200 cursor-pointer transition-colors"
                    >
                      🛡️ Spam Call (Test Shield)
                    </button>
                    <button
                      onClick={() => {
                        onClose();
                        onSimulateCall('Unknown Number', 'Not in Contacts', '+91 90000 11111', false, true);
                      }}
                      className="px-2.5 py-1.5 rounded-lg bg-amber-900/60 hover:bg-amber-800/90 border border-amber-500/40 text-[11px] font-semibold text-amber-200 cursor-pointer transition-colors"
                    >
                      ❓ Unknown Call
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Persona Summary Card */}
            <div className="my-4 p-3 rounded-xl bg-gradient-to-r from-pink-950/40 to-purple-950/40 border border-pink-500/20 flex items-start gap-3">
              <Sparkles className="w-5 h-5 text-pink-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-semibold text-pink-200">Zoya's Persona Profile</p>
                <p className="text-[11px] text-slate-300 mt-0.5">
                  Young, witty, sassy, and flirty tone. Smart, expressive, and remembers your details!
                </p>
              </div>
            </div>

            {/* Voice Options */}
            <div className="space-y-2 mt-4">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
                Select Prebuilt Voice Engine
              </label>

              {VOICE_OPTIONS.map((voice) => (
                <button
                  key={voice.id}
                  onClick={() => onSelectVoice(voice.id)}
                  className={`w-full flex items-center justify-between p-3 rounded-xl border text-left transition-all cursor-pointer ${
                    selectedVoice === voice.id
                      ? 'bg-slate-800 border-cyan-500 shadow-md'
                      : 'bg-slate-950/50 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-slate-900 text-cyan-400">
                      <Mic className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="text-xs font-bold text-white">{voice.name}</p>
                      <p className="text-[11px] text-slate-400">{voice.description}</p>
                    </div>
                  </div>
                  {selectedVoice === voice.id && <Check className="w-4 h-4 text-cyan-400" />}
                </button>
              ))}
            </div>

            <div className="mt-6 pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
              <div className="flex items-center gap-1">
                <HeartHandshake className="w-3.5 h-3.5 text-pink-400" />
                <span>Safe & respectful conversation</span>
              </div>
              <button
                onClick={onClose}
                className="px-4 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs transition-colors cursor-pointer"
              >
                Close Panel
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

