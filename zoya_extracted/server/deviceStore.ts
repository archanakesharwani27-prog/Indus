import fs from 'fs';
import path from 'path';

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
  targetDeviceId?: string; // Specific device or 'all' or 'mobile' or 'desktop'
  targetType?: 'all' | 'mobile' | 'desktop';
  action: 'openWebsite' | 'changeAuraTheme' | 'triggerAlert' | 'speakMessage' | 'syncMemory';
  payload: Record<string, unknown>;
  createdAt: string;
  executedBy: string[]; // deviceIds that executed this command
}

const DEVICES_FILE_PATH = path.join(process.cwd(), 'data', 'devices.json');
const COMMANDS_FILE_PATH = path.join(process.cwd(), 'data', 'remote_commands.json');

function ensureDataDirExists() {
  const dir = path.dirname(DEVICES_FILE_PATH);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

export function loadDevices(): ConnectedDevice[] {
  try {
    ensureDataDirExists();
    if (!fs.existsSync(DEVICES_FILE_PATH)) {
      return [];
    }
    const raw = fs.readFileSync(DEVICES_FILE_PATH, 'utf-8');
    return JSON.parse(raw) || [];
  } catch (err) {
    console.error('Error loading devices:', err);
    return [];
  }
}

export function saveDevices(devices: ConnectedDevice[]) {
  try {
    ensureDataDirExists();
    fs.writeFileSync(DEVICES_FILE_PATH, JSON.stringify(devices, null, 2), 'utf-8');
  } catch (err) {
    console.error('Error saving devices:', err);
  }
}

export function registerOrHeartbeatDevice(deviceInfo: Omit<ConnectedDevice, 'lastSeen'>): ConnectedDevice {
  const devices = loadDevices();
  const now = new Date().toISOString();
  const existingIdx = devices.findIndex((d) => d.deviceId === deviceInfo.deviceId);

  const updatedDevice: ConnectedDevice = {
    ...deviceInfo,
    lastSeen: now,
  };

  if (existingIdx >= 0) {
    devices[existingIdx] = updatedDevice;
  } else {
    devices.push(updatedDevice);
  }

  saveDevices(devices);
  return updatedDevice;
}

export function loadRemoteCommands(): RemoteCommand[] {
  try {
    ensureDataDirExists();
    if (!fs.existsSync(COMMANDS_FILE_PATH)) {
      return [];
    }
    const raw = fs.readFileSync(COMMANDS_FILE_PATH, 'utf-8');
    return JSON.parse(raw) || [];
  } catch (err) {
    console.error('Error loading remote commands:', err);
    return [];
  }
}

export function saveRemoteCommands(commands: RemoteCommand[]) {
  try {
    ensureDataDirExists();
    fs.writeFileSync(COMMANDS_FILE_PATH, JSON.stringify(commands, null, 2), 'utf-8');
  } catch (err) {
    console.error('Error saving remote commands:', err);
  }
}

export function createRemoteCommand(cmd: Omit<RemoteCommand, 'id' | 'createdAt' | 'executedBy'>): RemoteCommand {
  const commands = loadRemoteCommands();
  const newCmd: RemoteCommand = {
    ...cmd,
    id: 'cmd_' + Date.now().toString(36) + Math.random().toString(36).substring(2, 5),
    createdAt: new Date().toISOString(),
    executedBy: [],
  };

  commands.unshift(newCmd);
  // Keep last 50 commands
  if (commands.length > 50) {
    commands.length = 50;
  }

  saveRemoteCommands(commands);
  return newCmd;
}

export function markCommandExecuted(commandId: string, deviceId: string) {
  const commands = loadRemoteCommands();
  const cmd = commands.find((c) => c.id === commandId);
  if (cmd && !cmd.executedBy.includes(deviceId)) {
    cmd.executedBy.push(deviceId);
    saveRemoteCommands(commands);
  }
}

export function getPendingCommandsForDevice(deviceId: string, deviceType: 'desktop' | 'mobile' | 'tablet'): RemoteCommand[] {
  const commands = loadRemoteCommands();
  return commands.filter((c) => {
    if (c.fromDeviceId === deviceId) return false; // Don't re-execute own command
    if (c.executedBy.includes(deviceId)) return false; // Already executed

    if (c.targetDeviceId && c.targetDeviceId === deviceId) return true;
    if (c.targetType === 'all') return true;
    if (c.targetType && c.targetType === deviceType) return true;

    return false;
  });
}
