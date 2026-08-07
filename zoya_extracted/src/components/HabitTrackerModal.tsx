import React, { useState, useEffect } from 'react';
import {
  Target,
  Flame,
  CheckCircle2,
  Plus,
  Trash2,
  Sparkles,
  X,
  Droplet,
  Dumbbell,
  BookOpen,
  Brain,
  Zap,
  Activity,
  Smile,
  RefreshCw,
  Award
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

export interface HabitItem {
  id: string;
  name: string;
  category: 'health' | 'fitness' | 'mindset' | 'productivity' | 'custom';
  targetFrequency: 'daily' | 'weekly';
  targetCountDaily: number;
  currentCountToday: number;
  currentStreak: number;
  completedToday: boolean;
  totalCompletions: number;
  lastLoggedAt: string | null;
  icon: string;
  zoyaEncouragementNote?: string;
  createdAt: string;
  updatedAt: string;
}

interface HabitTrackerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onExecuteCommand: (cmd: string) => Promise<{ reply: string; success: boolean }>;
  showToast: (msg: string, type?: 'info' | 'error' | 'success') => void;
}

const CATEGORY_COLORS: Record<string, string> = {
  health: 'from-cyan-500 to-blue-600 border-cyan-400/40 text-cyan-300',
  fitness: 'from-rose-500 to-orange-600 border-rose-400/40 text-rose-300',
  mindset: 'from-purple-500 to-indigo-600 border-purple-400/40 text-purple-300',
  productivity: 'from-amber-500 to-emerald-600 border-amber-400/40 text-amber-300',
  custom: 'from-pink-500 to-fuchsia-600 border-pink-400/40 text-pink-300',
};

const ICON_MAP: Record<string, React.FC<{ className?: string }>> = {
  Droplet: Droplet,
  Dumbbell: Dumbbell,
  BookOpen: BookOpen,
  Sparkles: Sparkles,
  Brain: Brain,
  Activity: Activity,
  Target: Target,
  CheckCircle2: CheckCircle2,
};

export const HabitTrackerModal: React.FC<HabitTrackerModalProps> = ({
  isOpen,
  onClose,
  onExecuteCommand,
  showToast,
}) => {
  const [habits, setHabits] = useState<HabitItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isAdding, setIsAdding] = useState(false);

  // New habit form state
  const [newHabitName, setNewHabitName] = useState('');
  const [newCategory, setNewCategory] = useState<HabitItem['category']>('health');
  const [newTargetCount, setNewTargetCount] = useState(1);
  const [newIcon, setNewIcon] = useState('Target');

  // Fetch habits from backend API
  const fetchHabits = async () => {
    setIsLoading(true);
    try {
      const res = await fetch('/api/habits');
      const data = await res.json();
      if (data.success && Array.isArray(data.habits)) {
        setHabits(data.habits);
      }
    } catch (err) {
      console.error('Failed to load habits:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchHabits();
    }
  }, [isOpen]);

  const handleLogHabit = async (habit: HabitItem) => {
    try {
      const res = await fetch('/api/habits/log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ habitName: habit.name }),
      });
      const data = await res.json();
      if (data.success) {
        showToast(`Logged "${habit.name}"! Streak: ${data.habit.currentStreak} days 🔥`, 'success');
        fetchHabits();
      }
    } catch (err) {
      console.error(err);
      showToast('Failed to log habit.', 'error');
    }
  };

  const handleAddHabitSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newHabitName.trim()) return;

    try {
      const res = await fetch('/api/habits', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newHabitName.trim(),
          category: newCategory,
          targetCountDaily: Number(newTargetCount) || 1,
          icon: newIcon,
        }),
      });
      const data = await res.json();
      if (data.success) {
        showToast(`Habit "${newHabitName}" added!`, 'success');
        setNewHabitName('');
        setIsAdding(false);
        fetchHabits();
      }
    } catch (err) {
      console.error(err);
      showToast('Error adding habit.', 'error');
    }
  };

  const handleDeleteHabit = async (id: string, name: string) => {
    try {
      const res = await fetch(`/api/habits/${id}`, { method: 'DELETE' });
      const data = await res.json();
      if (data.success) {
        showToast(`Removed "${name}"`, 'info');
        fetchHabits();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleTriggerQuickVoiceRemind = async (habitName: string) => {
    showToast(`Asking Zoya for habit reminder on ${habitName}...`, 'info');
    try {
      const result = await onExecuteCommand(
        `Zoya, give me a witty, encouraging, sassy reminder about my daily habit "${habitName}"! Boost my motivation!`
      );
      if (result.success) {
        showToast('Zoya responded!', 'success');
        fetchHabits();
      }
    } catch (err) {
      console.error(err);
    }
  };

  if (!isOpen) return null;

  const completedCount = habits.filter((h) => h.completedToday).length;
  const totalHabits = habits.length;
  const completionPercentage = totalHabits > 0 ? Math.round((completedCount / totalHabits) * 100) : 0;
  const totalStreakSum = habits.reduce((acc, h) => acc + h.currentStreak, 0);

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-lg">
        <motion.div
          initial={{ opacity: 0, scale: 0.93, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.93, y: 15 }}
          className="relative w-full max-w-4xl max-h-[92vh] flex flex-col rounded-3xl bg-slate-950 border border-cyan-500/30 text-white shadow-[0_0_60px_rgba(6,182,212,0.15)] overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-5 border-b border-cyan-500/20 bg-slate-900/80">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-2xl bg-cyan-500/20 text-cyan-300 border border-cyan-400/50 shadow-inner">
                <Target className="w-6 h-6 animate-pulse" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-black tracking-wide bg-gradient-to-r from-cyan-300 via-pink-300 to-purple-300 bg-clip-text text-transparent">
                    DAILY HABIT & STREAK TRACKER
                  </h2>
                  <span className="px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-400/30">
                    ZOYA MONITORED
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  Log habits via voice with Zoya/Jarvis ("I drank water", "Finished exercise") & get witty encouraging reminders!
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={fetchHabits}
                title="Refresh Habits"
                className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-colors cursor-pointer"
              >
                <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-cyan-400' : ''}`} />
              </button>
              <button
                onClick={onClose}
                className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Progress & Stats Dashboard Banner */}
          <div className="px-6 py-4 bg-gradient-to-r from-slate-900 via-cyan-950/40 to-slate-900 border-b border-cyan-500/10 grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <div className="p-3 rounded-2xl bg-white/5 border border-white/10 flex items-center gap-3">
              <div className="p-2 rounded-xl bg-cyan-500/20 text-cyan-300">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <div className="text-[10px] text-slate-400 uppercase font-bold">Today's Progress</div>
                <div className="text-base font-black text-white">{completedCount} / {totalHabits} Done</div>
              </div>
            </div>

            <div className="p-3 rounded-2xl bg-white/5 border border-white/10 flex items-center gap-3">
              <div className="p-2 rounded-xl bg-amber-500/20 text-amber-300">
                <Flame className="w-5 h-5 text-amber-400 animate-bounce" />
              </div>
              <div>
                <div className="text-[10px] text-slate-400 uppercase font-bold">Active Streaks</div>
                <div className="text-base font-black text-amber-300">{totalStreakSum} Total Days 🔥</div>
              </div>
            </div>

            <div className="p-3 rounded-2xl bg-white/5 border border-white/10 flex items-center gap-3">
              <div className="p-2 rounded-xl bg-purple-500/20 text-purple-300">
                <Award className="w-5 h-5" />
              </div>
              <div>
                <div className="text-[10px] text-slate-400 uppercase font-bold">Completion Rate</div>
                <div className="text-base font-black text-purple-200">{completionPercentage}% Completed</div>
              </div>
            </div>

            <div className="p-3 rounded-2xl bg-white/5 border border-white/10 flex items-center gap-3">
              <div className="p-2 rounded-xl bg-pink-500/20 text-pink-300">
                <Smile className="w-5 h-5" />
              </div>
              <div>
                <div className="text-[10px] text-slate-400 uppercase font-bold">Zoya Reminders</div>
                <div className="text-base font-bold text-pink-300">Active & Encouraging</div>
              </div>
            </div>
          </div>

          {/* Main Habit Grid */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <Zap className="w-4 h-4 text-cyan-400" /> Active Daily Habits
              </h3>

              <button
                onClick={() => setIsAdding(!isAdding)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-400/50 text-cyan-200 text-xs font-bold transition-all cursor-pointer shadow-md"
              >
                <Plus className="w-4 h-4" /> Add Habit
              </button>
            </div>

            {/* Add Habit Form Modal/Panel */}
            {isAdding && (
              <motion.form
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                onSubmit={handleAddHabitSubmit}
                className="p-4 rounded-2xl bg-slate-900/90 border border-cyan-500/30 space-y-4"
              >
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-400 mb-1">Habit Name</label>
                    <input
                      type="text"
                      placeholder="e.g. Drink 2L Water, Workout, Read"
                      value={newHabitName}
                      onChange={(e) => setNewHabitName(e.target.value)}
                      className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-white/10 text-xs text-white focus:outline-none focus:border-cyan-400"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-slate-400 mb-1">Category</label>
                    <select
                      value={newCategory}
                      onChange={(e) => setNewCategory(e.target.value as any)}
                      className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-white/10 text-xs text-white focus:outline-none focus:border-cyan-400"
                    >
                      <option value="health">💧 Health & Hydration</option>
                      <option value="fitness">🏋️ Fitness & Workout</option>
                      <option value="mindset">📖 Mindset & Reading</option>
                      <option value="productivity">🧘 Productivity & Rest</option>
                      <option value="custom">✨ Custom Habit</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-slate-400 mb-1">Daily Goal Count</label>
                    <input
                      type="number"
                      min={1}
                      max={20}
                      value={newTargetCount}
                      onChange={(e) => setNewTargetCount(Number(e.target.value))}
                      className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-white/10 text-xs text-white focus:outline-none focus:border-cyan-400"
                    />
                  </div>
                </div>

                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setIsAdding(false)}
                    className="px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 text-xs font-semibold text-slate-400 cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-1.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-xs font-bold text-white cursor-pointer shadow-lg"
                  >
                    Save Habit
                  </button>
                </div>
              </motion.form>
            )}

            {/* List of Habits */}
            {habits.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-xs rounded-2xl bg-slate-900/40 border border-white/5">
                No active habits logged yet. Click "Add Habit" above or tell Zoya "Zoya, log I drank water"!
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {habits.map((habit) => {
                  const IconComp = ICON_MAP[habit.icon] || Target;
                  const categoryStyle = CATEGORY_COLORS[habit.category] || CATEGORY_COLORS.custom;
                  const progressPct = Math.min(
                    100,
                    Math.round((habit.currentCountToday / habit.targetCountDaily) * 100)
                  );

                  return (
                    <div
                      key={habit.id}
                      className={`relative p-5 rounded-2xl border transition-all flex flex-col justify-between space-y-4 ${
                        habit.completedToday
                          ? 'bg-slate-900/80 border-emerald-500/40 shadow-[0_0_20px_rgba(16,185,129,0.1)]'
                          : 'bg-slate-900/60 border-white/10 hover:border-cyan-500/30'
                      }`}
                    >
                      {/* Top Header */}
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                          <div className={`p-2.5 rounded-xl bg-gradient-to-br ${categoryStyle} shadow-md`}>
                            <IconComp className="w-5 h-5 text-white" />
                          </div>
                          <div>
                            <h4 className="text-sm font-bold text-white flex items-center gap-2">
                              {habit.name}
                              {habit.completedToday && (
                                <span className="px-2 py-0.5 text-[9px] font-bold rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-400/40">
                                  Done Today ✅
                                </span>
                              )}
                            </h4>
                            <span className="text-[10px] text-slate-400 capitalize">
                              Goal: {habit.targetCountDaily} per day • Total: {habit.totalCompletions} times
                            </span>
                          </div>
                        </div>

                        {/* Streak Badge */}
                        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-black shadow-inner">
                          <Flame className="w-3.5 h-3.5 text-amber-400 animate-pulse" />
                          <span>{habit.currentStreak}d Streak</span>
                        </div>
                      </div>

                      {/* Progress Bar */}
                      <div className="space-y-1.5">
                        <div className="flex justify-between text-[11px] font-semibold text-slate-400">
                          <span>Today's Log: {habit.currentCountToday} / {habit.targetCountDaily}</span>
                          <span>{progressPct}%</span>
                        </div>
                        <div className="w-full h-2 rounded-full bg-slate-950 overflow-hidden border border-white/5">
                          <div
                            className={`h-full transition-all duration-500 rounded-full ${
                              habit.completedToday
                                ? 'bg-gradient-to-r from-emerald-500 to-teal-400'
                                : 'bg-gradient-to-r from-cyan-500 to-blue-500'
                            }`}
                            style={{ width: `${progressPct}%` }}
                          />
                        </div>
                      </div>

                      {/* Zoya Witty Remark Box */}
                      {habit.zoyaEncouragementNote && (
                        <div className="p-2.5 rounded-xl bg-purple-950/30 border border-purple-500/20 flex items-start gap-2 text-[11px] text-purple-200">
                          <Sparkles className="w-3.5 h-3.5 text-purple-400 shrink-0 mt-0.5" />
                          <span className="italic leading-relaxed">
                            "{habit.zoyaEncouragementNote}"
                          </span>
                        </div>
                      )}

                      {/* Action Buttons */}
                      <div className="pt-2 border-t border-white/5 flex items-center justify-between">
                        <button
                          onClick={() => handleTriggerQuickVoiceRemind(habit.name)}
                          className="text-[11px] font-bold text-cyan-400 hover:text-cyan-300 flex items-center gap-1 cursor-pointer"
                        >
                          <Smile className="w-3.5 h-3.5" /> Ask Zoya Reminder
                        </button>

                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleDeleteHabit(habit.id, habit.name)}
                            title="Delete Habit"
                            className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors cursor-pointer"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>

                          <button
                            onClick={() => handleLogHabit(habit)}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white text-xs font-bold cursor-pointer shadow-md transition-all active:scale-95"
                          >
                            <CheckCircle2 className="w-4 h-4" /> + Log Progress
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
