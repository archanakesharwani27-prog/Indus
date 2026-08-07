import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Brain,
  X,
  Search,
  Plus,
  Trash2,
  Sparkles,
  User,
  Heart,
  MessageSquare,
  Bookmark,
  Lock,
  RefreshCw,
  CheckCircle2,
} from 'lucide-react';
import { MemoryItem, MemoryCategory } from '../types';

interface MemoryVaultModalProps {
  isOpen: boolean;
  onClose: () => void;
  onMemoryUpdated?: () => void;
  onAskZoya?: (promptText: string) => void;
}

export const MemoryVaultModal: React.FC<MemoryVaultModalProps> = ({
  isOpen,
  onClose,
  onMemoryUpdated,
  onAskZoya,
}) => {
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  // Form states
  const [isAddingNew, setIsAddingNew] = useState(false);
  const [newKey, setNewKey] = useState('');
  const [newValue, setNewValue] = useState('');
  const [newCategory, setNewCategory] = useState<MemoryCategory>('fact');
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const fetchMemories = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await fetch('/api/memories');
      const data = await res.json();
      if (data.success && Array.isArray(data.memories)) {
        setMemories(data.memories);
      }
    } catch (err) {
      console.error('Failed to fetch memories:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      fetchMemories();
    }
  }, [isOpen, fetchMemories]);

  const handleAddMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKey.trim() || !newValue.trim()) return;

    try {
      const res = await fetch('/api/memories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          key: newKey.trim(),
          value: newValue.trim(),
          category: newCategory,
        }),
      });
      const data = await res.json();
      if (data.success) {
        setNewKey('');
        setNewValue('');
        setIsAddingNew(false);
        setStatusMessage('Memory saved successfully!');
        setTimeout(() => setStatusMessage(null), 3000);
        fetchMemories();
        if (onMemoryUpdated) onMemoryUpdated();
      }
    } catch (err) {
      console.error('Error adding memory:', err);
    }
  };

  const handleDeleteMemory = async (id: string) => {
    try {
      const res = await fetch(`/api/memories/${encodeURIComponent(id)}`, {
        method: 'DELETE',
      });
      const data = await res.json();
      if (data.success) {
        fetchMemories();
        if (onMemoryUpdated) onMemoryUpdated();
      }
    } catch (err) {
      console.error('Error deleting memory:', err);
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm("Are you sure you want to clear Zoya's entire memory vault?")) return;
    try {
      await fetch('/api/memories', { method: 'DELETE' });
      fetchMemories();
      if (onMemoryUpdated) onMemoryUpdated();
    } catch (err) {
      console.error('Error clearing memories:', err);
    }
  };

  const filteredMemories = memories.filter((m) => {
    const matchesCategory = selectedCategory === 'all' || m.category === selectedCategory;
    const query = searchQuery.toLowerCase().trim();
    const matchesSearch =
      !query ||
      m.key.toLowerCase().includes(query) ||
      m.value.toLowerCase().includes(query) ||
      m.category.toLowerCase().includes(query);
    return matchesCategory && matchesSearch;
  });

  const getCategoryBadge = (category: MemoryCategory) => {
    switch (category) {
      case 'profile':
        return { label: 'User Profile', bg: 'bg-pink-950/60 text-pink-300 border-pink-500/30', icon: User };
      case 'preference':
        return { label: 'Preference', bg: 'bg-purple-950/60 text-purple-300 border-purple-500/30', icon: Heart };
      case 'conversation':
        return { label: 'Past Chat Topic', bg: 'bg-cyan-950/60 text-cyan-300 border-cyan-500/30', icon: MessageSquare };
      case 'secret':
        return { label: 'Secret / Fun Fact', bg: 'bg-amber-950/60 text-amber-300 border-amber-500/30', icon: Lock };
      default:
        return { label: 'Fact / Note', bg: 'bg-emerald-950/60 text-emerald-300 border-emerald-500/30', icon: Bookmark };
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
            initial={{ scale: 0.92, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.92, opacity: 0, y: 20 }}
            className="relative w-full max-w-2xl max-h-[85vh] bg-[#0a0a0f] border border-white/10 rounded-2xl shadow-2xl text-slate-100 z-10 flex flex-col overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-5 border-b border-white/10 bg-white/[0.02]">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-purple-950/60 border border-purple-500/30 text-purple-400">
                  <Brain className="w-6 h-6 animate-pulse" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-bold text-white tracking-tight">Zoya's Memory Vault</h3>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                      {memories.length} Saved
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">
                    Zoya remembers past conversation topics, personal details, and user facts across all chats!
                  </p>
                </div>
              </div>

              <button
                onClick={onClose}
                className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Notification Toast */}
            {statusMessage && (
              <div className="mx-5 mt-4 p-3 rounded-xl bg-emerald-950/80 border border-emerald-500/40 text-emerald-200 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{statusMessage}</span>
              </div>
            )}

            {/* Sub-Header & Controls */}
            <div className="p-5 pb-3 border-b border-white/5 space-y-3">
              <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
                {/* Search Bar */}
                <div className="relative w-full sm:w-72">
                  <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
                  <input
                    type="text"
                    placeholder="Search memories..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-9 pr-3 py-1.5 rounded-xl bg-white/5 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                  />
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
                  <button
                    onClick={() => setIsAddingNew(!isAddingNew)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs transition-colors shadow-md cursor-pointer"
                  >
                    <Plus className="w-4 h-4" />
                    <span>{isAddingNew ? 'Cancel' : 'Add Memory'}</span>
                  </button>

                  <button
                    onClick={fetchMemories}
                    title="Refresh memories"
                    className="p-1.5 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 text-slate-300 hover:text-white transition-colors"
                  >
                    <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                  </button>
                </div>
              </div>

              {/* Category Filter Tabs */}
              <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
                {[
                  { id: 'all', label: 'All Memories' },
                  { id: 'profile', label: 'Profile' },
                  { id: 'preference', label: 'Preferences' },
                  { id: 'conversation', label: 'Past Chats' },
                  { id: 'fact', label: 'Facts' },
                  { id: 'secret', label: 'Secrets' },
                ].map((cat) => (
                  <button
                    key={cat.id}
                    onClick={() => setSelectedCategory(cat.id)}
                    className={`px-3 py-1 rounded-lg transition-all font-medium whitespace-nowrap cursor-pointer ${
                      selectedCategory === cat.id
                        ? 'bg-purple-900/60 border border-purple-500/50 text-purple-200'
                        : 'bg-white/5 text-slate-400 hover:text-white hover:bg-white/10'
                    }`}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Add Memory Form Dropdown */}
            <AnimatePresence>
              {isAddingNew && (
                <motion.form
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  onSubmit={handleAddMemory}
                  className="p-4 mx-5 my-2 rounded-xl bg-white/5 border border-white/10 space-y-3"
                >
                  <p className="text-xs font-semibold text-purple-300 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-pink-400" />
                    <span>Store a New Permanent Fact for Zoya</span>
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                        Topic / Key
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. My Favorite Movie, My Name"
                        value={newKey}
                        onChange={(e) => setNewKey(e.target.value)}
                        required
                        className="w-full px-3 py-1.5 rounded-lg bg-slate-900 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                        Category
                      </label>
                      <select
                        value={newCategory}
                        onChange={(e) => setNewCategory(e.target.value as MemoryCategory)}
                        className="w-full px-3 py-1.5 rounded-lg bg-slate-900 border border-white/10 text-xs text-white focus:outline-none focus:border-purple-500"
                      >
                        <option value="profile">User Profile</option>
                        <option value="preference">Preference</option>
                        <option value="conversation">Past Chat Topic</option>
                        <option value="fact">Fact / Note</option>
                        <option value="secret">Secret / Fun Detail</option>
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                      Detail Value
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Interstellar, Rahul, Loves spicy tacos"
                      value={newValue}
                      onChange={(e) => setNewValue(e.target.value)}
                      required
                      className="w-full px-3 py-1.5 rounded-lg bg-slate-900 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                    />
                  </div>
                  <div className="flex justify-end gap-2 pt-1">
                    <button
                      type="button"
                      onClick={() => setIsAddingNew(false)}
                      className="px-3 py-1 rounded-lg bg-slate-800 text-slate-300 hover:text-white text-xs font-semibold"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="px-4 py-1 rounded-lg bg-pink-600 hover:bg-pink-500 text-white text-xs font-semibold"
                    >
                      Save to Vault
                    </button>
                  </div>
                </motion.form>
              )}
            </AnimatePresence>

            {/* Memories List */}
            <div className="flex-1 overflow-y-auto p-5 space-y-3">
              {filteredMemories.length === 0 ? (
                <div className="text-center py-12 text-slate-400 space-y-2">
                  <Brain className="w-10 h-10 mx-auto text-slate-600" />
                  <p className="text-sm font-medium">No memories found in this category.</p>
                  <p className="text-xs text-slate-500 max-w-xs mx-auto">
                    Speak to Zoya in live chat and share personal facts! Zoya will automatically save them to her brain.
                  </p>
                </div>
              ) : (
                filteredMemories.map((item) => {
                  const badge = getCategoryBadge(item.category);
                  const BadgeIcon = badge.icon;

                  return (
                    <motion.div
                      key={item.id}
                      layout
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      className="p-3.5 rounded-xl bg-white/[0.03] border border-white/10 hover:border-purple-500/40 transition-all flex items-start justify-between gap-3 group"
                    >
                      <div className="space-y-1.5 flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold border ${badge.bg}`}
                          >
                            <BadgeIcon className="w-3 h-3" />
                            {badge.label}
                          </span>
                          <span className="text-xs font-bold text-white truncate">{item.key}</span>
                        </div>
                        <p className="text-xs text-slate-300 font-medium break-words leading-relaxed">
                          "{item.value}"
                        </p>
                        <p className="text-[10px] text-slate-500">
                          Stored {new Date(item.updatedAt || item.createdAt).toLocaleDateString()}
                        </p>
                      </div>

                      <div className="flex items-center gap-1 shrink-0 opacity-80 group-hover:opacity-100">
                        {onAskZoya && (
                          <button
                            onClick={() => {
                              onAskZoya(`Do you remember my ${item.key}?`);
                              onClose();
                            }}
                            title="Ask Zoya about this memory"
                            className="p-1.5 rounded-lg bg-white/5 hover:bg-purple-900/40 text-purple-300 hover:text-purple-200 text-xs font-medium transition-colors flex items-center gap-1"
                          >
                            <Sparkles className="w-3.5 h-3.5" />
                            <span className="hidden sm:inline text-[10px]">Ask Zoya</span>
                          </button>
                        )}
                        <button
                          onClick={() => handleDeleteMemory(item.id)}
                          title="Delete memory"
                          className="p-1.5 rounded-lg hover:bg-rose-950/60 text-slate-400 hover:text-rose-400 transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </motion.div>
                  );
                })
              )}
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-white/10 bg-white/[0.02] flex items-center justify-between text-xs text-slate-400">
              <button
                onClick={handleClearAll}
                className="text-rose-400 hover:text-rose-300 text-xs font-medium hover:underline flex items-center gap-1 cursor-pointer"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear All Memory</span>
              </button>

              <button
                onClick={onClose}
                className="px-4 py-1.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold transition-colors cursor-pointer"
              >
                Done
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};
