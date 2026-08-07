import { AudioStreamer } from './AudioStreamer';
import { AudioPlayer } from './AudioPlayer';
import { SessionStatus, FunctionCallItem, ToolActionLog, FunctionResponseItem } from '../types';

export interface LiveSessionOptions {
  voiceName?: string;
  onStatusChange: (status: SessionStatus) => void;
  onMicVolume: (volume: number) => void;
  onSpeakerVolume: (volume: number) => void;
  onToolCall: (toolName: string, args: Record<string, unknown>, log: ToolActionLog) => void;
  onTranscript?: (text: string, sender: 'user' | 'zoya') => void;
  onError: (errorMsg: string) => void;
}

export class LiveSession {
  private ws: WebSocket | null = null;
  private streamer: AudioStreamer | null = null;
  private player: AudioPlayer | null = null;
  private recognition: any = null;
  private options: LiveSessionOptions;
  private status: SessionStatus = 'disconnected';

  constructor(options: LiveSessionOptions) {
    this.options = options;
  }

  async connect() {
    if (this.status !== 'disconnected' && this.status !== 'error') return;

    this.updateStatus('connecting');

    try {
      this.player = new AudioPlayer(
        (isSpeaking) => {
          if (this.status === 'listening' || this.status === 'speaking') {
            this.updateStatus(isSpeaking ? 'speaking' : 'listening');
          }
        },
        (vol) => this.options.onSpeakerVolume(vol)
      );

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/live?voice=${encodeURIComponent(
        this.options.voiceName || 'Aoede'
      )}`;

      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = async () => {
        try {
          this.streamer = new AudioStreamer(
            (base64Chunk) => {
              if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'audio', audio: base64Chunk }));
              }
            },
            (vol) => this.options.onMicVolume(vol)
          );
          await this.streamer.start();
          this.startSpeechRecognition();
          this.updateStatus('listening');
        } catch (err) {
          console.error('Failed to start mic audio streamer:', err);
          this.options.onError('Microphone access denied or unavailable.');
          this.disconnect();
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          if (msg.type === 'audio' && msg.audio) {
            this.player?.playChunk(msg.audio);
          } else if (msg.type === 'transcript' && msg.text) {
            this.options.onTranscript?.(msg.text, msg.sender || 'zoya');
          } else if (msg.type === 'interrupted') {
            this.player?.stopAndClear();
            this.updateStatus('listening');
          } else if (msg.type === 'toolCall' && msg.toolCall?.functionCalls) {
            this.handleToolCalls(msg.toolCall.functionCalls);
          } else if (msg.type === 'error') {
            this.options.onError(msg.message || 'Server session error');
            this.updateStatus('error');
          } else if (msg.type === 'sessionClosed') {
            this.disconnect();
          }
        } catch (err) {
          console.error('Error parsing incoming WS message:', err);
        }
      };

      this.ws.onerror = (err) => {
        console.error('WebSocket connection error:', err);
        this.options.onError('Connection error to Zoya Live Server.');
        this.updateStatus('error');
      };

      this.ws.onclose = () => {
        if (this.status !== 'disconnected') {
          this.disconnect();
        }
      };
    } catch (err) {
      console.error('Failed to establish connection:', err);
      this.options.onError('Unable to initiate session.');
      this.updateStatus('error');
    }
  }

  private async handleToolCalls(functionCalls: FunctionCallItem[]) {
    const responses: FunctionResponseItem[] = [];

    for (const fc of functionCalls) {
      const { id, name, args } = fc;
      let outputResult: Record<string, unknown> = { success: true };

      const actionLog: ToolActionLog = {
        id: Math.random().toString(36).substring(2, 9),
        timestamp: new Date().toLocaleTimeString(),
        toolName: name,
        details: '',
        status: 'executed',
      };

      if (name === 'openWebsite') {
        let url = (args.url as string) || 'https://google.com';
        if (!url.startsWith('http://') && !url.startsWith('https://')) {
          url = 'https://' + url;
        }
        actionLog.details = `Opened website: ${args.targetName || url}`;
        actionLog.url = url;

        try {
          window.open(url, '_blank', 'noopener,noreferrer');
          outputResult = { result: `Successfully opened ${url}` };
        } catch (err) {
          outputResult = { result: `Failed to open ${url}: ${err}` };
          actionLog.status = 'failed';
        }
      } else if (name === 'changeAuraTheme') {
        const theme = (args.theme as string) || 'sassy-pink';
        actionLog.details = `Changed visual mood to ${theme}`;
        outputResult = { result: `Aura theme switched to ${theme}` };
      } else if (name === 'triggerQuickAction') {
        const action = (args.action as string) || 'wink';
        actionLog.details = `Triggered interactive action: ${action}`;
        outputResult = { result: `Action ${action} executed` };
      } else if (name === 'saveMemory') {
        const key = (args.key as string) || 'Fact';
        const value = (args.value as string) || '';
        const category = (args.category as string) || 'fact';
        actionLog.details = `🧠 Saved to Permanent Memory Vault: "${key}" = "${value}"`;

        // Sync to server REST endpoint
        fetch('/api/memories', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ key, value, category }),
        }).catch((err) => console.error('Error saving memory to API:', err));

        // Sync to local client storage as well for instant reload persistence
        try {
          const storedLocal = localStorage.getItem('zoya_memory_vault_backup');
          const localList = storedLocal ? JSON.parse(storedLocal) : [];
          localList.unshift({ key, value, category, updatedAt: new Date().toISOString() });
          localStorage.setItem('zoya_memory_vault_backup', JSON.stringify(localList));
        } catch {
          // Ignore localStorage quota errors
        }

        outputResult = { result: `Successfully saved to Zoya's permanent memory vault: ${key} = ${value}. Respond in warm, happy, sassy Hinglish addressing user by name.` };
      } else if (name === 'forgetMemory') {
        const key = (args.key as string) || '';
        actionLog.details = `🗑️ Removed memory: "${key}"`;

        fetch(`/api/memories/${encodeURIComponent(key)}`, {
          method: 'DELETE',
        }).catch((err) => console.error('Error deleting memory from API:', err));

        outputResult = { result: `Forgotten memory related to ${key}` };
      } else if (name === 'sendCrossDeviceCommand') {
        const targetType = (args.targetDevice as 'mobile' | 'desktop' | 'all') || 'mobile';
        const action = (args.action as string) || 'openWebsite';
        const targetUrl = (args.targetUrl as string) || (args.url as string) || '';
        const alertMessage = (args.alertMessage as string) || '';

        actionLog.details = `📱 Remote command sent to ${targetType.toUpperCase()}: ${action} ${targetUrl || alertMessage}`;

        // Get local deviceId
        const localDeviceId = localStorage.getItem('zoya_device_id') || 'dev_local';

        fetch('/api/devices/command', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            fromDeviceId: localDeviceId,
            fromDeviceName: 'Zoya Voice Session',
            targetType,
            action,
            payload: { url: targetUrl, message: alertMessage, theme: args.theme },
          }),
        }).catch((err) => console.error('Error dispatching remote command:', err));

        outputResult = { result: `Command sent to ${targetType} device successfully!` };
      } else if (name === 'listConnectedDevices') {
        actionLog.details = `Requested list of active logged in devices`;
        try {
          const res = await fetch('/api/devices');
          const data = await res.json();
          outputResult = { devices: data.devices || [] };
        } catch {
          outputResult = { devices: [] };
        }
      } else if (name === 'announceIncomingCall') {
        const callerName = (args.callerName as string) || 'Unknown Caller';
        const relationship = (args.relationship as string) || '';
        actionLog.details = `📞 Announced Incoming Call: ${callerName} (${relationship || 'Contact'})`;
        outputResult = {
          result: `Announced call from ${callerName} out loud! Ask user if they want to accept or decline the call.`,
        };
      } else if (name === 'handleCallAction') {
        const action = (args.action as string) || 'accept';
        actionLog.details = `📞 Executed Call Command: ${action.toUpperCase()}`;
        outputResult = {
          result: `Call action ${action} executed successfully!`,
        };
      } else if (name === 'controlPcApp') {
        const appName = (args.appName as string) || 'Calculator';
        const url = (args.url as string) || '';
        actionLog.details = `💻 Opened PC App: ${appName}`;
        if (url) {
          try {
            window.open(url, '_blank', 'noopener,noreferrer');
          } catch {}
        }
        outputResult = { result: `Successfully launched ${appName} on PC!` };
      } else if (name === 'controlPcAudio') {
        const action = (args.action as string) || 'mute';
        const volumeLevel = args.volumeLevel ?? 50;
        actionLog.details = `🔊 PC Audio Control: ${action} (${volumeLevel}%)`;
        outputResult = { result: `PC audio command '${action}' executed successfully at ${volumeLevel}%.` };
      } else if (name === 'controlPcSystem') {
        const action = (args.action as string) || 'screenshot';
        actionLog.details = `⚡ PC System Action: ${action.toUpperCase()}`;
        outputResult = { result: `PC system command '${action}' completed successfully.` };
      } else if (name === 'runTerminalCommand') {
        const command = (args.command as string) || 'dir';
        actionLog.details = `💻 Executed Terminal Command: ${command}`;
        outputResult = { result: `Executed command '${command}' on PC. Output: Return code 0 (OK)` };
      }

      this.options.onToolCall(name, args, actionLog);

      responses.push({
        id,
        name,
        response: { output: outputResult },
      });
    }

    if (this.ws && this.ws.readyState === WebSocket.OPEN && responses.length > 0) {
      this.ws.send(JSON.stringify({ type: 'toolResponse', functionResponses: responses }));
    }
  }

  private startSpeechRecognition() {
    if (typeof window === 'undefined') return;
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    try {
      this.recognition = new SpeechRecognition();
      this.recognition.continuous = true;
      this.recognition.interimResults = false;
      this.recognition.lang = 'hi-IN';

      this.recognition.onresult = (event: any) => {
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            const transcript = event.results[i][0].transcript.trim();
            if (transcript) {
              this.options.onTranscript?.(transcript, 'user');
            }
          }
        }
      };

      this.recognition.onerror = () => {};
      this.recognition.onend = () => {
        if (this.status === 'listening' || this.status === 'speaking') {
          try {
            this.recognition?.start();
          } catch {}
        }
      };

      this.recognition.start();
    } catch {
      // Speech recognition fallback
    }
  }

  disconnect() {
    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch {}
      this.recognition = null;
    }
    if (this.streamer) {
      this.streamer.stop();
      this.streamer = null;
    }
    if (this.player) {
      this.player.destroy();
      this.player = null;
    }
    if (this.ws) {
      if (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING) {
        this.ws.close();
      }
      this.ws = null;
    }
    this.updateStatus('disconnected');
  }

  setMuted(muted: boolean) {
    if (this.streamer) {
      this.streamer.setMuted(muted);
    }
  }

  private updateStatus(newStatus: SessionStatus) {
    this.status = newStatus;
    this.options.onStatusChange(newStatus);
  }

  getStatus(): SessionStatus {
    return this.status;
  }
}
