import React, { useState, useRef, useEffect } from 'react';
import {
  MessageSquare,
  Sparkles,
  User,
  Send,
  Trash2,
  Copy,
  Volume2,
  Check,
  Search,
  Terminal,
  Activity,
  Shield,
  Monitor,
  Eye,
  Radio,
  Zap,
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { ConversationMessage } from '../types';

interface ConversationSectionProps {
  conversations: ConversationMessage[];
  onSendMessage: (text: string) => Promise<void>;
  onClearConversations: () => void;
  status: string;
  onTriggerScreenAnalysis?: () => void;
}

const QUICK_CHIPS = [
  { label: '🖥️ Analyze Screen', text: 'Zoya, analyze my screen in detail!' },
  { label: '🎵 Play Song', text: 'Zoya, play Hanuman Chalisa on YouTube' },
  { label: '🎶 Play Lut Le Gya', text: 'Zoya, play Lut Le Gya song' },
  { label: '⛅ Weather Check', text: 'Zoya, what is the weather today?' },
  { label: '💻 Open Calculator', text: 'Zoya, open Calculator on my PC' },
  { label: '🧠 Save Memory', text: 'Zoya, remember that my favorite color is cyan' },
  { label: '🛡️ JARVIS Protocol', text: 'Zoya, give me a tactical step-by-step problem solver analysis!' },
];

export const ConversationSection: React.FC<ConversationSectionProps> = ({
  conversations,
  onSendMessage,
  onClearConversations,
  status,
  onTriggerScreenAnalysis,
}) => {
  const [inputText, setInputText] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [senderFilter, setSenderFilter] = useState<'all' | 'user' | 'zoya'>('all');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [speakingId, setSpeakingId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversations]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isSending) return;

    const textToSubmit = inputText.trim();
    setInputText('');
    setIsSending(true);

    try {
      await onSendMessage(textToSubmit);
    } catch (err) {
      console.error('Error sending conversation message:', err);
    } finally {
      setIsSending(false);
    }
  };

  const handleChipClick = (chipText: string) => {
    setInputText(chipText);
  };

  const handleCopyText = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleSpeakText = (id: string, text: string) => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;

    window.speechSynthesis.cancel();

    if (speakingId === id) {
      setSpeakingId(null);
      return;
    }

    const cleanText = text.replace(/[\*\#\`\_\~]/g, '').trim();
    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    const voices = window.speechSynthesis.getVoices();

    const hindiFemale = voices.find(
      (v) =>
        v.lang.toLowerCase().startsWith('hi') ||
        v.name.toLowerCase().includes('swara') ||
        v.name.toLowerCase().includes('hindi')
    );
    const female = voices.find(
      (v) =>
        v.name.toLowerCase().includes('zira') ||
        v.name.toLowerCase().includes('samantha') ||
        v.name.toLowerCase().includes('female')
    );

    if (hindiFemale) {
      utterance.voice = hindiFemale;
      utterance.lang = 'hi-IN';
    } else if (female) {
      utterance.voice = female;
    }

    utterance.pitch = 1.1;
    utterance.rate = 1.0;

    utterance.onstart = () => setSpeakingId(id);
    utterance.onend = () => setSpeakingId(null);
    utterance.onerror = () => setSpeakingId(null);

    window.speechSynthesis.speak(utterance);
  };

  const filteredConversations = conversations.filter((msg) => {
    const matchesSearch = msg.text.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesSender =
      senderFilter === 'all'
        ? true
        : senderFilter === 'user'
        ? msg.sender === 'user'
        : msg.sender === 'zoya';
    return matchesSearch && matchesSender;
  });

  return (
    <div className="w-full max-w-5xl mx-auto my-3 px-2">
      <div className="rounded-3xl bg-slate-950/90 border border-cyan-500/40 backdrop-blur-2xl shadow-[0_0_50px_rgba(6,182,212,0.15)] overflow-hidden flex flex-col relative hud-scanline">
        {/* Holographic Top Header */}
        <div className="px-5 py-3.5 bg-slate-900/90 border-b border-cyan-500/30 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-cyan-500/20 text-cyan-300 border border-cyan-400/50 shadow-inner">
              <Terminal className="w-4 h-4 text-cyan-300 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-white font-mono tracking-wider uppercase text-glow-cyan">
                  HOLOGRAPHIC LOG FEED & TRANSCRIPT
                </h3>
                <span className="px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 text-[10px] font-mono font-bold border border-cyan-400/30">
                  {conversations.length} ENTRIES
                </span>
              </div>
              <p className="text-[11px] text-cyan-400/70 font-mono">
                Real-time vocal stream, text commands & tool executions
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {onTriggerScreenAnalysis && (
              <button
                type="button"
                onClick={onTriggerScreenAnalysis}
                className="px-3 py-1.5 rounded-xl bg-cyan-950/80 hover:bg-cyan-900/90 text-cyan-200 border border-cyan-400/50 transition-all cursor-pointer text-xs flex items-center gap-1.5 font-mono font-bold shadow-md"
                title="Instant Screen Analysis & Reading"
              >
                <Eye className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
                <span>Instant Screen Scan</span>
              </button>
            )}

            {/* Search Filter Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-cyan-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search logs..."
                className="pl-8 pr-3 py-1.5 rounded-xl bg-slate-950 border border-cyan-500/30 text-xs font-mono text-cyan-200 placeholder-cyan-600 focus:outline-none focus:border-cyan-400 w-28 sm:w-36"
              />
            </div>

            {/* Clear Button */}
            {conversations.length > 0 && (
              <button
                type="button"
                onClick={onClearConversations}
                className="p-1.5 rounded-xl bg-rose-950/60 hover:bg-rose-900/80 text-rose-300 border border-rose-500/40 transition-all cursor-pointer text-xs flex items-center gap-1 font-mono"
                title="Clear conversation history"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span className="hidden sm:inline text-[11px] font-bold">Clear</span>
              </button>
            )}
          </div>
        </div>

        {/* Conversation Feed Scroll Area */}
        <div className="p-3.5 h-44 sm:h-52 overflow-y-auto space-y-3.5 scrollbar-thin scrollbar-thumb-cyan-500/30">
          {filteredConversations.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-400 space-y-3">
              <div className="p-3.5 rounded-2xl bg-cyan-950/60 border border-cyan-500/30 text-cyan-300 animate-pulse">
                <Shield className="w-7 h-7 text-cyan-400" />
              </div>
              <div>
                <h4 className="text-xs font-mono font-bold text-cyan-300 uppercase tracking-widest mb-1">
                  NO VOCAL OR TEXT COMMANDS LOGGED
                </h4>
                <p className="text-xs text-cyan-400/70 font-mono max-w-md">
                  Speak via the Arc Reactor core button or type a command below.
                  Zoya will log transcripts, responses, and PC automation triggers here!
                </p>
              </div>
            </div>
          ) : (
            filteredConversations.map((msg) => {
              const isUser = msg.sender === 'user';
              return (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex items-start gap-2.5 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
                >
                  {/* Avatar Badge */}
                  <div
                    className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 border text-xs shadow-md ${
                      isUser
                        ? 'bg-slate-900 border-indigo-400/50 text-indigo-300'
                        : 'bg-cyan-950 border-cyan-400/60 text-cyan-300 shadow-[0_0_15px_rgba(6,182,212,0.3)]'
                    }`}
                  >
                    {isUser ? <User className="w-4 h-4" /> : <Shield className="w-4 h-4 text-cyan-400" />}
                  </div>

                  {/* Message Hologram Card */}
                  <div
                    className={`max-w-[85%] sm:max-w-[78%] rounded-2xl p-3.5 text-xs shadow-xl backdrop-blur-md relative group border ${
                      isUser
                        ? 'bg-indigo-950/70 border-indigo-500/40 text-indigo-100 rounded-tr-none'
                        : 'bg-slate-900/90 border-cyan-500/40 text-cyan-100 rounded-tl-none shadow-[0_0_20px_rgba(6,182,212,0.1)]'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3 text-[10px] font-mono font-bold text-cyan-400/80 mb-1 border-b border-white/10 pb-1">
                      <span className="flex items-center gap-1.5">
                        <span className={isUser ? 'text-indigo-300 font-bold' : 'text-cyan-300 font-bold'}>
                          {isUser ? 'OPERATOR (YOU)' : 'ZOYA AI MARK-VII'}
                        </span>
                        {msg.type && (
                          <span className="px-1.5 py-0.2 rounded bg-cyan-950 text-[9px] uppercase font-mono text-cyan-300 border border-cyan-500/30">
                            {msg.type}
                          </span>
                        )}
                      </span>
                      <span className="text-[9px] font-mono text-slate-500">{msg.timestamp}</span>
                    </div>

                    <p className="text-xs text-white leading-relaxed font-medium whitespace-pre-wrap">
                      {msg.text}
                    </p>

                    {/* Executed Tool Call Badge */}
                    {msg.toolCallName && (
                      <div className="mt-2 pt-1.5 border-t border-white/10 flex items-center gap-1.5 text-[10px] text-emerald-300 font-mono font-bold">
                        <Zap className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
                        <span>EXECUTED TOOL: {msg.toolCallName}</span>
                      </div>
                    )}

                    {/* Hover Actions */}
                    <div className="absolute right-2 bottom-1.5 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 bg-slate-950 px-2 py-0.5 rounded-lg border border-cyan-500/30 text-[10px]">
                      <button
                        type="button"
                        onClick={() => handleCopyText(msg.id, msg.text)}
                        className="text-cyan-300 hover:text-white p-0.5 cursor-pointer"
                        title="Copy text"
                      >
                        {copiedId === msg.id ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      </button>
                      {!isUser && (
                        <button
                          type="button"
                          onClick={() => handleSpeakText(msg.id, msg.text)}
                          className="text-cyan-300 hover:text-cyan-100 p-0.5 cursor-pointer"
                          title="Listen with Zoya Voice"
                        >
                          <Volume2 className={`w-3 h-3 ${speakingId === msg.id ? 'text-cyan-400 animate-pulse' : ''}`} />
                        </button>
                      )}
                    </div>
                  </div>
                </motion.div>
              );
            })
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Quick Suggestion Chips */}
        <div className="px-4 py-2 bg-slate-950/80 border-t border-cyan-500/20 flex items-center gap-2 overflow-x-auto no-scrollbar">
          <span className="text-[10px] font-mono font-bold text-cyan-400 uppercase tracking-wider shrink-0 flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-pink-400" /> Quick Command:
          </span>
          {QUICK_CHIPS.map((chip, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleChipClick(chip.text)}
              className="px-2.5 py-1 rounded-xl bg-cyan-950/50 hover:bg-cyan-900/80 text-cyan-200 border border-cyan-500/30 text-[10px] font-mono font-bold whitespace-nowrap transition-all cursor-pointer"
            >
              {chip.label}
            </button>
          ))}
        </div>

        {/* Text Command Form */}
        <form onSubmit={handleSubmit} className="p-3 bg-slate-950 border-t border-cyan-500/30 flex items-center gap-2">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Enter command for Zoya (e.g. 'open calculator', 'play song', 'analyze screen')..."
            className="flex-1 px-4 py-2.5 rounded-xl bg-slate-900 border border-cyan-500/30 text-xs font-mono text-white placeholder-cyan-700 focus:outline-none focus:border-cyan-400"
          />

          <button
            type="submit"
            disabled={!inputText.trim() || isSending}
            className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 disabled:opacity-50 text-white font-mono font-bold text-xs flex items-center gap-1.5 cursor-pointer shadow-lg shadow-cyan-950/50"
          >
            {isSending ? (
              <Activity className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <span>EXECUTE</span>
                <Send className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
};
