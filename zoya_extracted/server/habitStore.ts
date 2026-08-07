import fs from 'fs';
import path from 'path';

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

const HABITS_FILE_PATH = path.join(process.cwd(), 'data', 'habits.json');

const DEFAULT_HABITS: HabitItem[] = [
  {
    id: 'habit_water',
    name: 'Drink Water (8 Glasses)',
    category: 'health',
    targetFrequency: 'daily',
    targetCountDaily: 8,
    currentCountToday: 3,
    currentStreak: 4,
    completedToday: false,
    totalCompletions: 28,
    lastLoggedAt: new Date(Date.now() - 3600000 * 3).toISOString(),
    icon: 'Droplet',
    zoyaEncouragementNote: 'Stay hydrated, handsome! Your skin & brain will thank me later. 💧',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: 'habit_exercise',
    name: 'Daily Exercise & Workout',
    category: 'fitness',
    targetFrequency: 'daily',
    targetCountDaily: 1,
    currentCountToday: 1,
    currentStreak: 3,
    completedToday: true,
    totalCompletions: 12,
    lastLoggedAt: new Date().toISOString(),
    icon: 'Dumbbell',
    zoyaEncouragementNote: 'Abs loading... Sabash! Keep flexing those muscles hero! 🏋️‍♂️',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: 'habit_read',
    name: 'Read 15 Mins / Book',
    category: 'mindset',
    targetFrequency: 'daily',
    targetCountDaily: 1,
    currentCountToday: 0,
    currentStreak: 2,
    completedToday: false,
    totalCompletions: 9,
    lastLoggedAt: new Date(Date.now() - 86400000).toISOString(),
    icon: 'BookOpen',
    zoyaEncouragementNote: 'Feed your brain! Knowledge is super sexy, trust Zoya. 📖',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: 'habit_meditate',
    name: 'Mindful Breathing & Rest',
    category: 'productivity',
    targetFrequency: 'daily',
    targetCountDaily: 1,
    currentCountToday: 0,
    currentStreak: 1,
    completedToday: false,
    totalCompletions: 5,
    lastLoggedAt: new Date(Date.now() - 86400000 * 2).toISOString(),
    icon: 'Sparkles',
    zoyaEncouragementNote: 'Take a deep breath! JARVIS & Zoya need you stress-free and unstoppable. 🧘',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
];

function ensureDataDirExists() {
  const dir = path.dirname(HABITS_FILE_PATH);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

export function loadHabits(): HabitItem[] {
  try {
    ensureDataDirExists();
    if (!fs.existsSync(HABITS_FILE_PATH)) {
      fs.writeFileSync(HABITS_FILE_PATH, JSON.stringify(DEFAULT_HABITS, null, 2), 'utf-8');
      return DEFAULT_HABITS;
    }
    const raw = fs.readFileSync(HABITS_FILE_PATH, 'utf-8');
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed) && parsed.length > 0) {
      // Check day boundary reset for completedToday & currentCountToday
      const todayStr = new Date().toISOString().split('T')[0];
      let updated = false;

      const checkedHabits = parsed.map((h: HabitItem) => {
        if (h.lastLoggedAt) {
          const lastLoggedDay = h.lastLoggedAt.split('T')[0];
          if (lastLoggedDay !== todayStr) {
            // New day! Reset completedToday & count today, update streak if missed
            const yesterday = new Date();
            yesterday.setDate(yesterday.getDate() - 1);
            const yesterdayStr = yesterday.toISOString().split('T')[0];

            let newStreak = h.currentStreak;
            if (lastLoggedDay !== yesterdayStr && h.currentStreak > 0) {
              // Missed yesterday too, streak breaks
              newStreak = 0;
            }

            updated = true;
            return {
              ...h,
              completedToday: false,
              currentCountToday: 0,
              currentStreak: newStreak,
            };
          }
        }
        return h;
      });

      if (updated) {
        saveHabits(checkedHabits);
      }

      return checkedHabits;
    }
    return DEFAULT_HABITS;
  } catch (err) {
    console.error('Error loading habits file:', err);
    return DEFAULT_HABITS;
  }
}

export function saveHabits(habits: HabitItem[]) {
  try {
    ensureDataDirExists();
    fs.writeFileSync(HABITS_FILE_PATH, JSON.stringify(habits, null, 2), 'utf-8');
  } catch (err) {
    console.error('Error saving habits file:', err);
  }
}

const WITTY_REMARKS = [
  "Shabaash hero! Habit locked and loaded! JARVIS and Zoya are super proud of you! 🔥",
  "Look at you being so consistent! Your future self is already thanking you, handsome! 😉",
  "Boom! Another win today! Streak intact! Keep this energy going! ⚡",
  "Habit logged! You're officially turning into an unstoppable superhero. 💪",
  "Zoya approved! Water/Workout checked. Now don't forget to take a minute to appreciate yourself! ✨",
];

export function logHabitCompletion(habitNameOrKey: string, notes?: string): { habit: HabitItem; remark: string } {
  const habits = loadHabits();
  const searchKey = habitNameOrKey.trim().toLowerCase();

  let habit = habits.find(
    (h) => h.name.toLowerCase().includes(searchKey) || searchKey.includes(h.name.toLowerCase().split(' ')[0])
  );

  const now = new Date();
  const nowIso = now.toISOString();
  const todayStr = nowIso.split('T')[0];

  let randomRemark = WITTY_REMARKS[Math.floor(Math.random() * WITTY_REMARKS.length)];

  if (habit) {
    const isNewDay = !habit.lastLoggedAt || habit.lastLoggedAt.split('T')[0] !== todayStr;

    const newCount = habit.currentCountToday + 1;
    const isCompletedNow = newCount >= habit.targetCountDaily;

    let newStreak = habit.currentStreak;
    if (isNewDay) {
      newStreak += 1;
    }

    habit = {
      ...habit,
      currentCountToday: newCount,
      completedToday: isCompletedNow || habit.completedToday,
      currentStreak: newStreak,
      totalCompletions: habit.totalCompletions + 1,
      lastLoggedAt: nowIso,
      updatedAt: nowIso,
      zoyaEncouragementNote: `${randomRemark} ${notes ? `(Note: ${notes})` : ''}`,
    };

    const index = habits.findIndex((h) => h.id === habit!.id);
    if (index >= 0) habits[index] = habit;
  } else {
    // Auto-create new habit if user logs something new!
    const newHabit: HabitItem = {
      id: 'habit_' + Date.now().toString(36),
      name: habitNameOrKey,
      category: 'custom',
      targetFrequency: 'daily',
      targetCountDaily: 1,
      currentCountToday: 1,
      currentStreak: 1,
      completedToday: true,
      totalCompletions: 1,
      lastLoggedAt: nowIso,
      icon: 'CheckCircle2',
      zoyaEncouragementNote: `Created & Logged habit "${habitNameOrKey}"! ${randomRemark}`,
      createdAt: nowIso,
      updatedAt: nowIso,
    };
    habits.unshift(newHabit);
    habit = newHabit;
  }

  saveHabits(habits);

  const finalRemark = `Logged "${habit.name}"! Day streak: ${habit.currentStreak} 🔥. Zoya says: "${habit.zoyaEncouragementNote}"`;
  return { habit, remark: finalRemark };
}

export function addHabit(
  name: string,
  category: HabitItem['category'] = 'health',
  targetCountDaily: number = 1,
  icon: string = 'Target'
): HabitItem {
  const habits = loadHabits();
  const nowIso = new Date().toISOString();

  const newHabit: HabitItem = {
    id: 'habit_' + Date.now().toString(36),
    name,
    category,
    targetFrequency: 'daily',
    targetCountDaily: targetCountDaily || 1,
    currentCountToday: 0,
    currentStreak: 0,
    completedToday: false,
    totalCompletions: 0,
    lastLoggedAt: null,
    icon: icon || 'Target',
    zoyaEncouragementNote: `New habit added! Let's conquer this together! ✨`,
    createdAt: nowIso,
    updatedAt: nowIso,
  };

  habits.unshift(newHabit);
  saveHabits(habits);
  return newHabit;
}

export function deleteHabit(idOrName: string): boolean {
  const habits = loadHabits();
  const initialLen = habits.length;
  const filtered = habits.filter(
    (h) => h.id !== idOrName && h.name.toLowerCase() !== idOrName.toLowerCase()
  );

  if (filtered.length !== initialLen) {
    saveHabits(filtered);
    return true;
  }
  return false;
}

export function buildHabitSystemPrompt(): string {
  const habits = loadHabits();
  if (habits.length === 0) {
    return "No daily habits currently tracked.";
  }

  return habits
    .map(
      (h) =>
        `- ${h.name} (${h.category.toUpperCase()}): Today ${h.currentCountToday}/${h.targetCountDaily} [${
          h.completedToday ? '✅ DONE' : '⏳ PENDING'
        }], Current Streak: ${h.currentStreak} days, Total Logged: ${h.totalCompletions}`
    )
    .join("\n");
}
