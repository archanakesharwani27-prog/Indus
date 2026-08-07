import React, { useState } from 'react';
import { Send, Sparkles, Terminal, Loader2, History, RotateCcw, Trash2, ChevronDown, ChevronUp } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface TextCommandBarProps {
  onExecuteCommand: (commandText: string) => Promise<{ reply: string; success: boolean }>;
  onSelectPrompt?: (prompt: string) => void;
  currentDeviceId: string;
  currentDeviceType: 'desktop' | 'mobile' | 'tablet';
}

const QUICK_TEXT_SUGGESTIONS = [
  { label: '⛅ Weather Today', text: 'Zoya, aaj ka weather kaisa hai?' },
  { label: '📞 Call Papa', text: 'Zoya, Papa ka call aa raha hai announce kar do' },
  { label: '📱 Open YouTube on Phone', text: 'Zoya, open youtube.com on my mobile phone' },
  { label: '🧠 Save My Name', text: 'Zoya, remember my name is Alex' },
  { label: '🎨 Change Theme to Cyber', text: 'Change theme to neon cyber' },
];

export const TextCommandBar: React.FC<TextCommandBarProps> = ({
  onExecuteCommand,
}) => {
  const [inputText, setInputText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [lastResponse, setLastResponse] = useState<string | null>(null);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  // Store & load recent 5 commands from localStorage
  const [recentCommands, setRecentCommands] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem('zoya_recent_commands');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const saveRecentCommand = (cmd: string) => {
    setRecentCommands((prev) => {
      const filtered = prev.filter((item) => item.trim().toLowerCase() !== cmd.trim().toLowerCase());
      const updated = [cmd, ...filtered].slice(0, 5);
      try {
        localStorage.setItem('zoya_recent_commands', JSON.stringify(updated));
      } catch {}
      return updated;
    });
  };

  const clearHistory = () => {
    setRecentCommands([]);
    try {
      localStorage.removeItem('zoya_recent_commands');
    } catch {}
  };

  const handleRunCommand = async (cmdToRun: string) => {
    if (!cmdToRun.trim() || isSubmitting) return;

    const cmd = cmdToRun.trim();
    saveRecentCommand(cmd);
    setInputText('');
    setIsSubmitting(true);
    setIsHistoryOpen(false);

    try {
      const res = await onExecuteCommand(cmd);
      setLastResponse(res.reply);

      setTimeout(() => {
        setLastResponse(null);
      }, 8000);
    } catch (err) {
      console.error('Error submitting text command:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleRunCommand(inputText);
  };

  const handleChipClick = (text: string) => {
    setInputText(text);
  };

  return (
    <div className="w-full max-w-2xl mx-auto px-4 my-3 space-y-2 z-20">
      {/* Response Bubble */}
      <AnimatePresence>
        {lastResponse && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.98 }}
            className="p-3.5 rounded-2xl bg-purple-950/80 border border-purple-500/40 text-purple-100 text-xs shadow-xl backdrop-blur-md flex items-start gap-3"
          >
            <div className="p-1.5 rounded-xl bg-purple-500/20 text-purple-300 shrink-0">
              <Sparkles className="w-4 h-4 animate-spin" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between text-[10px] font-bold text-purple-300 uppercase tracking-wider mb-0.5">
                <span>Zoya Reply</span>
                <button
                  onClick={() => setLastResponse(null)}
                  className="text-purple-400 hover:text-white cursor-pointer"
                >
                  ✕
                </button>
              </div>
              <p className="text-xs text-white leading-relaxed font-medium">{lastResponse}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Text Command Input Form */}
      <div className="relative">
        <form onSubmit={handleSubmit} className="relative flex items-center">
          <div className="relative w-full flex items-center">
            <div className="absolute left-3.5 text-purple-400 flex items-center gap-1.5">
              <Terminal className="w-4 h-4" />
            </div>

            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Type a text command or question for Zoya (e.g. 'open youtube on my phone', 'remember I love sushi')..."
              className="w-full pl-10 pr-20 py-3 rounded-2xl bg-slate-900/90 border border-white/10 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-purple-400 focus:ring-2 focus:ring-purple-500/20 shadow-lg transition-all"
            />

            <div className="absolute right-2 flex items-center gap-1">
              {/* History Dropdown Toggle */}
              {recentCommands.length > 0 && (
                <button
                  type="button"
                  onClick={() => setIsHistoryOpen((prev) => !prev)}
                  title="Recent typed commands"
                  className={`p-2 rounded-xl text-xs font-medium transition-all cursor-pointer flex items-center gap-1 ${
                    isHistoryOpen
                      ? 'bg-purple-500/30 text-purple-200 border border-purple-400/50'
                      : 'bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white'
                  }`}
                >
                  <History className="w-3.5 h-3.5" />
                  <span className="text-[10px] font-semibold hidden sm:inline">{recentCommands.length}</span>
                  {isHistoryOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                </button>
              )}

              {/* Submit Button */}
              <button
                type="submit"
                disabled={!inputText.trim() || isSubmitting}
                className="p-2 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-40 text-white font-bold transition-all shadow-md cursor-pointer disabled:cursor-not-allowed"
              >
                {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              </button>
            </div>
          </div>
        </form>

        {/* Recent Commands Dropdown Menu */}
        <AnimatePresence>
          {isHistoryOpen && recentCommands.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: -6, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -6, scale: 0.98 }}
              className="absolute left-0 right-0 top-full mt-2 z-30 p-2 rounded-2xl bg-slate-900/95 border border-purple-500/30 shadow-2xl backdrop-blur-xl space-y-1.5"
            >
              <div className="flex items-center justify-between px-2.5 py-1 text-[11px] font-bold text-slate-400 border-b border-white/5">
                <span className="flex items-center gap-1.5 text-purple-300">
                  <History className="w-3.5 h-3.5" />
                  Recent Commands (Last {recentCommands.length})
                </span>
                <button
                  type="button"
                  onClick={clearHistory}
                  className="text-slate-400 hover:text-red-400 flex items-center gap-1 transition-colors cursor-pointer text-[10px]"
                >
                  <Trash2 className="w-3 h-3" /> Clear History
                </button>
              </div>

              <div className="max-h-44 overflow-y-auto space-y-1 pr-1 scrollbar-thin scrollbar-thumb-purple-900">
                {recentCommands.map((cmd, idx) => (
                  <div
                    key={idx}
                    className="group flex items-center justify-between p-2 rounded-xl bg-white/5 hover:bg-purple-900/40 border border-transparent hover:border-purple-500/30 transition-all text-xs"
                  >
                    <button
                      type="button"
                      onClick={() => handleChipClick(cmd)}
                      className="flex-1 text-left text-slate-200 hover:text-white truncate font-medium mr-2 cursor-pointer"
                      title="Click to copy into input box"
                    >
                      {cmd}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleRunCommand(cmd)}
                      title="Re-execute command"
                      className="px-2 py-1 rounded-lg bg-purple-600/80 hover:bg-purple-500 text-white text-[10px] font-semibold flex items-center gap-1 transition-all opacity-80 group-hover:opacity-100 cursor-pointer shrink-0"
                    >
                      <RotateCcw className="w-3 h-3" /> Re-run
                    </button>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Quick Suggestion Chips */}
      <div className="flex items-center gap-1.5 overflow-x-auto py-1 scrollbar-none text-[11px]">
        {QUICK_TEXT_SUGGESTIONS.map((chip, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => handleChipClick(chip.text)}
            className="px-2.5 py-1 rounded-full bg-white/5 border border-white/10 hover:border-purple-400/50 hover:bg-purple-950/40 text-slate-300 hover:text-white whitespace-nowrap transition-all shrink-0 cursor-pointer"
          >
            {chip.label}
          </button>
        ))}
      </div>
    </div>
  );
};


