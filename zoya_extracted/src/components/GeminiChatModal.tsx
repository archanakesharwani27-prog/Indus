import React, { useState, useRef, useEffect } from 'react';
import {
  MessageSquare,
  Sparkles,
  X,
  Send,
  Search,
  MapPin,
  Image as ImageIcon,
  Zap,
  Brain,
  Globe,
  Loader2,
  Trash2,
  ExternalLink,
  Bot,
  User,
  Paperclip
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface ChatMessage {
  id: string;
  role: 'user' | 'model';
  content: string;
  timestamp: string;
  modelUsed?: string;
  imageUrl?: string;
  groundingSources?: Array<{ title?: string; uri?: string }>;
}

interface GeminiChatModalProps {
  isOpen: boolean;
  onClose: () => void;
  showToast: (msg: string, type?: 'info' | 'error' | 'success') => void;
}

export const GeminiChatModal: React.FC<GeminiChatModalProps> = ({
  isOpen,
  onClose,
  showToast,
}) => {
  // Chat state
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'model',
      content:
        'Hey there! I am Zoya AI. I can search real-time web info with Google Search, locate places with Google Maps, analyze uploaded photos, and perform complex reasoning! How can I help you today?',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      modelUsed: 'gemini-3.5-flash',
    },
  ]);

  const [input, setInput] = useState('');
  const [selectedModel, setSelectedModel] = useState<
    'gemini-3.1-pro-preview' | 'gemini-3.5-flash' | 'gemini-3.1-flash-lite'
  >('gemini-3.5-flash');

  const [enableSearchGrounding, setEnableSearchGrounding] = useState(true);
  const [enableMapsGrounding, setEnableMapsGrounding] = useState(false);
  const [attachedImage, setAttachedImage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [isOpen, messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const result = event.target?.result as string;
      if (result) {
        setAttachedImage(result);
        showToast('Image attached to conversation!', 'info');
      }
    };
    reader.readAsDataURL(file);
  };

  const handleSendMessage = async (textToSend?: string) => {
    const promptText = (textToSend || input).trim();
    if (!promptText && !attachedImage) return;

    const userMsgId = 'msg_' + Date.now();
    const newUserMsg: ChatMessage = {
      id: userMsgId,
      role: 'user',
      content: promptText || (attachedImage ? 'Analyze this uploaded photo' : ''),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      imageUrl: attachedImage || undefined,
    };

    setMessages((prev) => [...prev, newUserMsg]);
    setInput('');
    const currentImg = attachedImage;
    setAttachedImage(null);
    setIsLoading(true);

    try {
      // Build previous conversation history
      const historyPayload = messages
        .filter((m) => m.id !== 'welcome')
        .map((m) => ({
          role: m.role,
          parts: [{ text: m.content }],
        }));

      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: promptText,
          image: currentImg,
          model: selectedModel,
          enableSearchGrounding,
          enableMapsGrounding,
          history: historyPayload,
        }),
      });

      const data = await res.json();
      if (data.success) {
        const aiMsg: ChatMessage = {
          id: 'ai_' + Date.now(),
          role: 'model',
          content: data.reply || 'No response generated.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          modelUsed: data.modelUsed || selectedModel,
          groundingSources: data.groundingSources || [],
        };
        setMessages((prev) => [...prev, aiMsg]);
      } else {
        showToast(data.error || 'Failed to get Gemini response', 'error');
      }
    } catch (err) {
      console.error('Chat error:', err);
      showToast('Error communicating with Gemini AI server.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const clearChatHistory = () => {
    setMessages([
      {
        id: 'welcome_' + Date.now(),
        role: 'model',
        content: 'Conversation history cleared! Ask me anything.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        modelUsed: selectedModel,
      },
    ]);
    showToast('Chat thread cleared.', 'info');
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-md">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 10 }}
          className="relative w-full max-w-4xl h-[88vh] flex flex-col rounded-3xl bg-slate-950 border border-purple-500/30 text-white shadow-2xl overflow-hidden"
        >
          {/* Top Bar Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-slate-900/60">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-2xl bg-gradient-to-tr from-purple-600 to-pink-500 text-white shadow-lg shadow-purple-500/30">
                <Sparkles className="w-5 h-5 animate-spin-slow" />
              </div>
              <div>
                <h2 className="text-base font-extrabold flex items-center gap-2">
                  Gemini Intelligence & Multi-Turn Chat
                  <span className="px-2 py-0.5 text-[10px] uppercase font-bold rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
                    Live Grounded
                  </span>
                </h2>
                <p className="text-xs text-slate-400">
                  Google Search Grounding, Maps Grounding, Vision Analysis & Low-Latency AI
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={clearChatHistory}
                title="Clear Chat History"
                className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-400 hover:text-rose-400 transition-colors cursor-pointer"
              >
                <Trash2 className="w-4 h-4" />
              </button>
              <button
                onClick={onClose}
                className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Controls Bar: Model & Grounding Toggles */}
          <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-3 border-b border-white/10 bg-slate-900/40 text-xs">
            {/* Model Selector */}
            <div className="flex items-center gap-1.5 bg-slate-900/80 p-1 rounded-2xl border border-white/10">
              <button
                onClick={() => setSelectedModel('gemini-3.1-pro-preview')}
                className={`flex items-center gap-1 px-2.5 py-1.5 rounded-xl font-bold transition-all cursor-pointer ${
                  selectedModel === 'gemini-3.1-pro-preview'
                    ? 'bg-purple-600 text-white shadow-md'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <Brain className="w-3.5 h-3.5" />
                Gemini 3.1 Pro
              </button>
              <button
                onClick={() => setSelectedModel('gemini-3.5-flash')}
                className={`flex items-center gap-1 px-2.5 py-1.5 rounded-xl font-bold transition-all cursor-pointer ${
                  selectedModel === 'gemini-3.5-flash'
                    ? 'bg-purple-600 text-white shadow-md'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                Gemini 3.5 Flash
              </button>
              <button
                onClick={() => setSelectedModel('gemini-3.1-flash-lite')}
                className={`flex items-center gap-1 px-2.5 py-1.5 rounded-xl font-bold transition-all cursor-pointer ${
                  selectedModel === 'gemini-3.1-flash-lite'
                    ? 'bg-purple-600 text-white shadow-md'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <Zap className="w-3.5 h-3.5" />
                Flash-Lite (Fast)
              </button>
            </div>

            {/* Grounding Options */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  setEnableSearchGrounding(!enableSearchGrounding);
                  if (!enableSearchGrounding) setEnableMapsGrounding(false);
                }}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl font-semibold border transition-all cursor-pointer ${
                  enableSearchGrounding
                    ? 'bg-blue-950/80 border-blue-400/60 text-blue-300 shadow-sm'
                    : 'bg-slate-900/50 border-white/10 text-slate-400 hover:text-white'
                }`}
              >
                <Globe className="w-3.5 h-3.5 text-blue-400" />
                Google Search
              </button>

              <button
                onClick={() => {
                  setEnableMapsGrounding(!enableMapsGrounding);
                  if (!enableMapsGrounding) setEnableSearchGrounding(false);
                }}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl font-semibold border transition-all cursor-pointer ${
                  enableMapsGrounding
                    ? 'bg-emerald-950/80 border-emerald-400/60 text-emerald-300 shadow-sm'
                    : 'bg-slate-900/50 border-white/10 text-slate-400 hover:text-white'
                }`}
              >
                <MapPin className="w-3.5 h-3.5 text-emerald-400" />
                Google Maps
              </button>
            </div>
          </div>

          {/* Quick Preset Prompt Pills */}
          <div className="flex gap-2 px-6 py-2 border-b border-white/5 bg-slate-900/20 overflow-x-auto text-[11px] no-scrollbar">
            <button
              onClick={() => handleSendMessage('Search current trending news and headlines today using Google Search')}
              className="shrink-0 flex items-center gap-1 px-2.5 py-1 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 cursor-pointer"
            >
              <Search className="w-3 h-3 text-blue-400" /> Live Search News
            </button>
            <button
              onClick={() => {
                setEnableMapsGrounding(true);
                setEnableSearchGrounding(false);
                handleSendMessage('Find popular coffee shops and places nearby on Google Maps');
              }}
              className="shrink-0 flex items-center gap-1 px-2.5 py-1 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 cursor-pointer"
            >
              <MapPin className="w-3 h-3 text-emerald-400" /> Google Maps Places
            </button>
            <button
              onClick={() => {
                setSelectedModel('gemini-3.1-pro-preview');
                handleSendMessage('Perform deep reasoning and breakdown: How do modern LLMs perform tool calling?');
              }}
              className="shrink-0 flex items-center gap-1 px-2.5 py-1 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 cursor-pointer"
            >
              <Brain className="w-3 h-3 text-purple-400" /> Deep Reasoning (Pro)
            </button>
            <button
              onClick={() => {
                setSelectedModel('gemini-3.1-flash-lite');
                handleSendMessage('Give me a fast 3-bullet list on effective time management');
              }}
              className="shrink-0 flex items-center gap-1 px-2.5 py-1 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 cursor-pointer"
            >
              <Zap className="w-3 h-3 text-amber-400" /> Low-Latency Summary
            </button>
          </div>

          {/* Chat Messages Thread */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 max-w-[85%] ${
                  msg.role === 'user' ? 'ml-auto flex-row-reverse' : ''
                }`}
              >
                {/* Avatar */}
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-xs font-bold ${
                    msg.role === 'user'
                      ? 'bg-purple-600 text-white'
                      : 'bg-gradient-to-tr from-pink-500 to-purple-600 text-white'
                  }`}
                >
                  {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                </div>

                {/* Message Bubble */}
                <div className="space-y-2">
                  <div
                    className={`p-4 rounded-2xl text-xs leading-relaxed ${
                      msg.role === 'user'
                        ? 'bg-purple-600/90 text-white rounded-tr-none'
                        : 'bg-slate-900 border border-white/10 text-slate-200 rounded-tl-none shadow-md'
                    }`}
                  >
                    {/* Attached Image if any */}
                    {msg.imageUrl && (
                      <div className="mb-3 rounded-xl overflow-hidden max-w-xs border border-white/20">
                        <img src={msg.imageUrl} alt="User Attachment" className="w-full object-cover" />
                      </div>
                    )}

                    <p className="whitespace-pre-line">{msg.content}</p>

                    {/* Grounding Source Citations if present */}
                    {msg.groundingSources && msg.groundingSources.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-white/10 space-y-1.5">
                        <div className="text-[10px] font-bold text-blue-400 uppercase tracking-wider flex items-center gap-1">
                          <Globe className="w-3 h-3" /> Grounded Source Citations:
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {msg.groundingSources.map((source, idx) => (
                            <a
                              key={idx}
                              href={source.uri}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-blue-950/60 hover:bg-blue-900/80 border border-blue-500/30 text-[10px] text-blue-300 hover:text-white transition-all"
                            >
                              <ExternalLink className="w-2.5 h-2.5" />
                              {source.title || source.uri || 'Source Link'}
                            </a>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  <div
                    className={`flex items-center gap-2 text-[10px] text-slate-500 ${
                      msg.role === 'user' ? 'justify-end' : ''
                    }`}
                  >
                    <span>{msg.timestamp}</span>
                    {msg.modelUsed && (
                      <span className="px-1.5 py-0.2 rounded bg-white/5 font-mono text-[9px] text-purple-400">
                        {msg.modelUsed}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex gap-3 max-w-[80%]">
                <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-pink-500 to-purple-600 flex items-center justify-center shrink-0">
                  <Bot className="w-4 h-4 text-white" />
                </div>
                <div className="p-4 rounded-2xl bg-slate-900 border border-white/10 text-xs text-purple-300 flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
                  Zoya is generating response with {selectedModel}...
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Attachment Preview Bar */}
          {attachedImage && (
            <div className="px-6 py-2 bg-slate-900/80 border-t border-white/10 flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs text-purple-300">
                <ImageIcon className="w-4 h-4 text-purple-400" />
                <span className="font-semibold">Photo Attached for Multimodal Vision</span>
              </div>
              <button
                onClick={() => setAttachedImage(null)}
                className="text-slate-400 hover:text-white text-xs p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Bottom Input Area */}
          <div className="p-4 border-t border-white/10 bg-slate-900/80">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="flex items-center gap-2"
            >
              <input
                type="file"
                ref={fileInputRef}
                accept="image/*"
                onChange={handleImageSelect}
                className="hidden"
              />

              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                title="Attach photo for Gemini multimodal vision analysis"
                className="p-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-slate-400 hover:text-purple-300 transition-colors cursor-pointer"
              >
                <Paperclip className="w-5 h-5" />
              </button>

              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={`Ask Zoya AI (${selectedModel})...`}
                className="flex-1 px-4 py-3 rounded-2xl bg-slate-950 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-purple-400"
              />

              <button
                type="submit"
                disabled={isLoading || (!input.trim() && !attachedImage)}
                className="p-3 rounded-2xl bg-purple-600 hover:bg-purple-500 disabled:opacity-40 text-white transition-all cursor-pointer shadow-lg shadow-purple-900/40"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
