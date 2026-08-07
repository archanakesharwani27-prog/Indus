export type SessionStatus = 'disconnected' | 'connecting' | 'listening' | 'speaking' | 'error';

export type AuraTheme = 'neon-cyber' | 'sassy-pink' | 'electric-violet' | 'cosmic-emerald' | 'midnight-gold';

export type MemoryCategory = 'profile' | 'preference' | 'conversation' | 'fact' | 'secret';

export interface MemoryItem {
  id: string;
  category: MemoryCategory;
  key: string;
  value: string;
  createdAt: string;
  updatedAt: string;
}

export interface VoiceOption {
  id: string;
  name: string;
  description: string;
  gender: 'female' | 'male';
}

export interface ConnectedDevice {
  deviceId: string;
  userEmail: string;
  deviceName: string;
  deviceType: 'desktop' | 'mobile' | 'tablet';
  browser: string;
  status: 'online' | 'active_voice' | 'idle';
  lastSeen: string;
}

export interface RemoteCommand {
  id: string;
  fromDeviceId: string;
  fromDeviceName: string;
  targetDeviceId?: string;
  targetType?: 'all' | 'mobile' | 'desktop';
  action: 'openWebsite' | 'changeAuraTheme' | 'triggerAlert' | 'speakMessage' | 'syncMemory';
  payload: Record<string, unknown>;
  createdAt: string;
  executedBy: string[];
}

export interface FunctionCallArg {
  url?: string;
  targetName?: string;
  theme?: AuraTheme;
  action?: string;
  key?: string;
  value?: string;
  category?: MemoryCategory;
  targetDevice?: 'mobile' | 'desktop' | 'all';
  targetUrl?: string;
  remoteAction?: string;
  alertMessage?: string;
  [key: string]: unknown;
}

export interface FunctionCallItem {
  id: string;
  name: string;
  args: FunctionCallArg;
}

export interface ToolCallPayload {
  functionCalls: FunctionCallItem[];
}

export interface FunctionResponseItem {
  id: string;
  name: string;
  response: {
    output: Record<string, unknown>;
  };
}

export interface ToolActionLog {
  id: string;
  timestamp: string;
  toolName: string;
  details: string;
  url?: string;
  status: 'executed' | 'pending' | 'failed';
}

export interface QuickPrompt {
  id: string;
  label: string;
  text: string;
  iconName: string;
}

export interface ConversationMessage {
  id: string;
  sender: 'user' | 'zoya';
  text: string;
  timestamp: string;
  type?: 'voice' | 'text' | 'tool';
  mood?: string;
  toolCallName?: string;
}

export interface PcAppAction {
  id: string;
  name: string;
  appKey: string;
  category: 'system' | 'media' | 'utility' | 'browser';
  icon: string;
  command: string;
  description: string;
}


