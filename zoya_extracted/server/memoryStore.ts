import fs from 'fs';
import path from 'path';

export interface MemoryItem {
  id: string;
  category: 'profile' | 'preference' | 'conversation' | 'fact' | 'secret';
  key: string;
  value: string;
  createdAt: string;
  updatedAt: string;
}

const MEMORIES_FILE_PATH = path.join(process.cwd(), 'data', 'memories.json');

// Initial default memories
const DEFAULT_MEMORIES: MemoryItem[] = [
  {
    id: 'mem_1',
    category: 'profile',
    key: "User's Preferred AI Companion",
    value: "Zoya (Sassy, witty, flirty, smart assistant)",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: 'mem_2',
    category: 'preference',
    key: "Communication Style",
    value: "Conversational, casual, witty one-liners, no robotic formal jargon",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: 'mem_3',
    category: 'fact',
    key: "Memory Vault Status",
    value: "Permanent long-term memory active across all sessions & chats",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
];

function ensureDataDirExists() {
  const dir = path.dirname(MEMORIES_FILE_PATH);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

export function loadMemories(): MemoryItem[] {
  try {
    ensureDataDirExists();
    if (!fs.existsSync(MEMORIES_FILE_PATH)) {
      fs.writeFileSync(MEMORIES_FILE_PATH, JSON.stringify(DEFAULT_MEMORIES, null, 2), 'utf-8');
      return DEFAULT_MEMORIES;
    }
    const raw = fs.readFileSync(MEMORIES_FILE_PATH, 'utf-8');
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed) && parsed.length > 0) {
      return parsed;
    }
    return DEFAULT_MEMORIES;
  } catch (err) {
    console.error('Error loading memories file:', err);
    return DEFAULT_MEMORIES;
  }
}

export function saveMemories(memories: MemoryItem[]) {
  try {
    ensureDataDirExists();
    fs.writeFileSync(MEMORIES_FILE_PATH, JSON.stringify(memories, null, 2), 'utf-8');
  } catch (err) {
    console.error('Error saving memories file:', err);
  }
}

export function addOrUpdateMemory(key: string, value: string, category: MemoryItem['category'] = 'fact'): MemoryItem {
  const memories = loadMemories();
  const lowerKey = key.toLowerCase();

  // Smart key matching: if key relates to user name, update existing name entry
  const existingIndex = memories.findIndex(m => {
    const k = m.key.toLowerCase();
    if (k === lowerKey) return true;
    if (lowerKey.includes('name') && k.includes('name')) return true;
    return false;
  });

  const now = new Date().toISOString();

  if (existingIndex >= 0) {
    memories[existingIndex] = {
      ...memories[existingIndex],
      key: key.toLowerCase().includes('name') ? "User's Name" : key,
      value,
      category: category || memories[existingIndex].category || 'profile',
      updatedAt: now,
    };
    saveMemories(memories);
    return memories[existingIndex];
  } else {
    const newMemory: MemoryItem = {
      id: 'mem_' + Date.now().toString(36) + Math.random().toString(36).substring(2, 5),
      category: lowerKey.includes('name') ? 'profile' : category,
      key: lowerKey.includes('name') ? "User's Name" : key,
      value,
      createdAt: now,
      updatedAt: now,
    };
    memories.unshift(newMemory);
    saveMemories(memories);
    return newMemory;
  }
}

export function deleteMemory(idOrKey: string): boolean {
  const memories = loadMemories();
  const initialLength = memories.length;
  const filtered = memories.filter(m => m.id !== idOrKey && m.key.toLowerCase() !== idOrKey.toLowerCase());
  
  if (filtered.length !== initialLength) {
    saveMemories(filtered);
    return true;
  }
  return false;
}

export function clearAllMemories() {
  saveMemories([]);
}

export function buildSystemMemoryPrompt(): string {
  const memories = loadMemories();
  if (memories.length === 0) {
    return "No memories stored yet.";
  }

  // Sort profile items first so Zoya sees user name immediately
  const sorted = [...memories].sort((a, b) => {
    if (a.category === 'profile' && b.category !== 'profile') return -1;
    if (a.category !== 'profile' && b.category === 'profile') return 1;
    return 0;
  });

  return sorted
    .map(m => `- [${m.category.toUpperCase()}] ${m.key}: ${m.value}`)
    .join("\n");
}
