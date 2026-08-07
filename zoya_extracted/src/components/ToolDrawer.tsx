import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { X, ExternalLink, CheckCircle2, Clock, Palette, Terminal, Globe, Sparkles } from 'lucide-react';
import { AuraTheme, ToolActionLog } from '../types';

interface ToolDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  logs: ToolActionLog[];
  currentTheme: AuraTheme;
  onSelectTheme: (theme: AuraTheme) => void;
  onOpenMemoryVault?: () => void;
}

const THEMES: { id: AuraTheme; name: string; color: string; desc: string }[] = [
  { id: 'sassy-pink', name: 'Sassy Pink', color: 'from-pink-500 to-rose-600', desc: 'Flirty, vibrant & fiery' },
  { id: 'neon-cyber', name: 'Neon Cyber', color: 'from-cyan-400 to-blue-600', desc: 'Futuristic high-tech glow' },
  { id: 'electric-violet', name: 'Electric Violet', color: 'from-purple-500 to-indigo-600', desc: 'Deep cosmic aura' },
  { id: 'cosmic-emerald', name: 'Cosmic Emerald', color: 'from-emerald-400 to-teal-600', desc: 'Fresh cyber green' },
  { id: 'midnight-gold', name: 'Midnight Gold', color: 'from-amber-400 to-orange-600', desc: 'Luxurious warm glow' },
];

const PRESET_WEBSITES = [
  { name: 'Google', url: 'https://google.com' },
  { name: 'YouTube', url: 'https://youtube.com' },
  { name: 'GitHub', url: 'https://github.com' },
  { name: 'Spotify', url: 'https://open.spotify.com' },
  { name: 'Wikipedia', url: 'https://wikipedia.org' },
];

export const ToolDrawer: React.FC<ToolDrawerProps> = ({
  isOpen,
  onClose,
  logs,
  currentTheme,
  onSelectTheme,
  onOpenMemoryVault,
}) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm z-40"
          />

          {/* Drawer Panel */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed top-0 right-0 h-full w-full max-w-md bg-[#0a0a0f] border-l border-white/10 text-slate-100 z-50 p-6 flex flex-col justify-between overflow-y-auto shadow-2xl"
          >
            <div>
              {/* Header */}
              <div className="flex items-center justify-between pb-4 border-b border-white/10">
                <div className="flex items-center gap-2">
                  <Terminal className="w-5 h-5 text-pink-400" />
                  <h2 className="text-lg font-bold">Tools & Aura Controls</h2>
                </div>
                <button
                  onClick={onClose}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Memory Vault Banner */}
              {onOpenMemoryVault && (
                <div className="mt-5 p-4 rounded-xl bg-purple-950/50 border border-purple-500/40 flex items-center justify-between gap-3">
                  <div className="space-y-0.5">
                    <p className="text-xs font-bold text-white flex items-center gap-1.5">
                      <span>🧠 Zoya Memory Vault</span>
                    </p>
                    <p className="text-[11px] text-purple-200">
                      Manage permanent facts, user details & cross-session topics.
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      onClose();
                      onOpenMemoryVault();
                    }}
                    className="px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs shrink-0 cursor-pointer"
                  >
                    Open Brain
                  </button>
                </div>
              )}

              {/* Aura Mood Selector */}
              <div className="mt-6">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
                  <Palette className="w-4 h-4 text-cyan-400" />
                  <span>Aura Visual Mood</span>
                </div>
                <div className="grid grid-cols-1 gap-2">
                  {THEMES.map((t) => (
                    <button
                      key={t.id}
                      onClick={() => onSelectTheme(t.id)}
                      className={`flex items-center justify-between p-3 rounded-xl border text-left transition-all ${
                        currentTheme === t.id
                          ? 'bg-slate-800 border-pink-500/80 shadow-lg'
                          : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-4 h-4 rounded-full bg-gradient-to-r ${t.color}`} />
                        <div>
                          <p className="text-xs font-semibold text-white">{t.name}</p>
                          <p className="text-[10px] text-slate-400">{t.desc}</p>
                        </div>
                      </div>
                      {currentTheme === t.id && <Sparkles className="w-4 h-4 text-pink-400" />}
                    </button>
                  ))}
                </div>
              </div>

              {/* Website Shortcuts */}
              <div className="mt-6">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
                  <Globe className="w-4 h-4 text-purple-400" />
                  <span>Website Shortcuts (openWebsite Tool)</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {PRESET_WEBSITES.map((site) => (
                    <a
                      key={site.name}
                      href={site.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-950/80 border border-slate-800 hover:border-cyan-500/50 text-xs text-slate-300 hover:text-white transition-all"
                    >
                      <span>{site.name}</span>
                      <ExternalLink className="w-3 h-3 text-cyan-400" />
                    </a>
                  ))}
                </div>
              </div>

              {/* Executed Function Call Logs */}
              <div className="mt-6">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
                  <Clock className="w-4 h-4 text-amber-400" />
                  <span>Real-Time Tool Execution Logs</span>
                </div>

                {logs.length === 0 ? (
                  <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800/60 text-center">
                    <p className="text-xs text-slate-500">No tools executed yet.</p>
                    <p className="text-[11px] text-slate-600 mt-1">
                      Ask Zoya "Open YouTube" or "Change theme to Neon Cyber" to trigger function calls!
                    </p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {logs.map((log) => (
                      <div
                        key={log.id}
                        className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 flex items-start justify-between gap-2"
                      >
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-pink-300 font-mono">
                              {log.toolName}
                            </span>
                            <span className="text-[10px] text-slate-500 font-mono">{log.timestamp}</span>
                          </div>
                          <p className="text-xs text-slate-300 mt-1">{log.details}</p>
                          {log.url && (
                            <a
                              href={log.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-[11px] text-cyan-400 hover:underline inline-flex items-center gap-1 mt-1"
                            >
                              <span>{log.url}</span>
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          )}
                        </div>
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="mt-8 pt-4 border-t border-slate-800/80 text-center text-[11px] text-slate-500">
              Function calling active via Gemini Live API WebSocket stream.
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};
