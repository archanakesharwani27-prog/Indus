import { useState, useRef, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { AuraVisualizer } from './components/AuraVisualizer';
import { MicPowerButton } from './components/MicPowerButton';
import { PersonalityCard } from './components/PersonalityCard';
import { ToolDrawer } from './components/ToolDrawer';
import { VoiceSettingsModal } from './components/VoiceSettingsModal';
import { MemoryVaultModal } from './components/MemoryVaultModal';
import { DeviceSyncModal } from './components/DeviceSyncModal';
import { VisionModal } from './components/VisionModal';
import { JarvisCompanionHUD } from './components/JarvisCompanionHUD';
import { HabitTrackerModal } from './components/HabitTrackerModal';
import { GeminiChatModal } from './components/GeminiChatModal';
import { IncomingCallModal, CallerInfo } from './components/IncomingCallModal';
import { ConversationSection } from './components/ConversationSection';
import { PcControlModal } from './components/PcControlModal';
import { MusicPlayerWidget } from './components/MusicPlayerWidget';
import { LiveSession } from './services/LiveSession';
import { AuraTheme, SessionStatus, ToolActionLog, ConnectedDevice, RemoteCommand, ConversationMessage } from './types';
import { ExternalLink, Sparkles, AlertCircle, CheckCircle2, ShieldCheck, Monitor } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

export default function App() {
  const [status, setStatus] = useState<SessionStatus>('disconnected');
  const [isMuted, setIsMuted] = useState(false);
  const [micVolume, setMicVolume] = useState(0);
  const [speakerVolume, setSpeakerVolume] = useState(0);
  const [selectedVoice, setSelectedVoice] = useState('Aoede');
  const [auraTheme, setAuraTheme] = useState<AuraTheme>('sassy-pink');
  const [toolLogs, setToolLogs] = useState<ToolActionLog[]>([]);
  const [memoryCount, setMemoryCount] = useState<number>(0);
  const [deviceCount, setDeviceCount] = useState<number>(1);
  const [userEmail, setUserEmail] = useState<string>('archanakesharwani820@gmail.com');
  const [toastMessage, setToastMessage] = useState<{ text: string; type: 'info' | 'error' | 'success'; url?: string } | null>(null);
  const [lastCrossDeviceLog, setLastCrossDeviceLog] = useState<{ text: string; from: string; time: string } | null>(null);

  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isToolLogsOpen, setIsToolLogsOpen] = useState(false);
  const [isMemoryVaultOpen, setIsMemoryVaultOpen] = useState(false);
  const [isDeviceSyncOpen, setIsDeviceSyncOpen] = useState(false);
  const [isVisionOpen, setIsVisionOpen] = useState(false);
  const [isJarvisOpen, setIsJarvisOpen] = useState(false);
  const [isHabitsOpen, setIsHabitsOpen] = useState(false);
  const [isGeminiChatOpen, setIsGeminiChatOpen] = useState(false);
  const [isPcControlOpen, setIsPcControlOpen] = useState(false);
  const [activeMusicTrack, setActiveMusicTrack] = useState<{ query: string; youtubeUrl?: string } | null>(null);

  // Conversation history state
  const [conversations, setConversations] = useState<ConversationMessage[]>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('zoya_conversations');
      if (saved) {
        try {
          return JSON.parse(saved);
        } catch {}
      }
    }
    return [
      {
        id: 'welcome-1',
        sender: 'zoya',
        text: 'Aapka swagat hai! Main Zoya hoon. Aap mujhse Voice Chat kar sakte hain, questions pooch sakte hain ya apne PC ko control kar sakte hain!',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        type: 'voice',
      },
    ];
  });

  // Incoming Call & Read Caller's Name Announcer State
  const [incomingCall, setIncomingCall] = useState<CallerInfo | null>(null);
  const [autoAnnounceCaller, setAutoAnnounceCaller] = useState<boolean>(true);

  // Device & Cross-Device state
  const deviceIdRef = useRef<string>('');
  const deviceTypeRef = useRef<'desktop' | 'mobile' | 'tablet'>('desktop');

  const liveSessionRef = useRef<LiveSession | null>(null);

  const showToast = useCallback((text: string, type: 'info' | 'error' | 'success' = 'info', url?: string) => {
    setToastMessage({ text, type, url });
    setTimeout(() => {
      setToastMessage(null);
    }, 5000);
  }, []);

  // Initialize or retrieve unique Device ID and detect Device Type
  useEffect(() => {
    let devId = localStorage.getItem('zoya_device_id');
    if (!devId) {
      devId = 'dev_' + Date.now().toString(36) + Math.random().toString(36).substring(2, 6);
      localStorage.setItem('zoya_device_id', devId);
    }
    deviceIdRef.current = devId;

    const savedEmail = localStorage.getItem('zoya_user_email');
    if (savedEmail) {
      setUserEmail(savedEmail);
    }

    const isMobileDevice = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || window.innerWidth < 768;
    deviceTypeRef.current = isMobileDevice ? 'mobile' : 'desktop';
  }, []);

  // Register device & Heartbeat
  const registerDeviceHeartbeat = useCallback(async () => {
    if (!deviceIdRef.current) return;
    try {
      const res = await fetch('/api/devices/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          deviceId: deviceIdRef.current,
          userEmail,
          deviceName: deviceTypeRef.current === 'mobile' ? 'Mobile Phone' : 'PC / Laptop',
          deviceType: deviceTypeRef.current,
          browser: navigator.userAgent.includes('Chrome') ? 'Chrome' : 'Browser',
          status: status === 'listening' || status === 'speaking' ? 'active_voice' : 'online',
        }),
      });
      if (!res.ok) return;
      const data = await res.json();
      if (data.success) {
        // Also get total connected devices count
        const devRes = await fetch('/api/devices');
        if (devRes.ok) {
          const devData = await devRes.json();
          if (devData.success && Array.isArray(devData.devices)) {
            setDeviceCount(devData.devices.length);
          }
        }
      }
    } catch {
      // Ignore transient network errors during server restarts
    }
  }, [userEmail, status]);

  // Poll for Remote Commands targeted to this device
  const pollRemoteCommands = useCallback(async () => {
    if (!deviceIdRef.current) return;
    try {
      const res = await fetch(`/api/devices/commands/${encodeURIComponent(deviceIdRef.current)}?deviceType=${deviceTypeRef.current}`);
      if (!res.ok) return;
      const data = await res.json();
      if (data.success && Array.isArray(data.commands) && data.commands.length > 0) {
        for (const cmd of data.commands as RemoteCommand[]) {
          // Mark as executed
          fetch(`/api/devices/commands/${cmd.id}/executed`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ deviceId: deviceIdRef.current }),
          }).catch(() => {});

          // Execute Command
          let commandText = '';
          if (cmd.action === 'openWebsite' && cmd.payload.url) {
            const url = cmd.payload.url as string;
            commandText = `Opened URL: ${url}`;
            showToast(`📱 Remote Command from ${cmd.fromDeviceName}: Opening ${url}`, 'success', url);
            window.open(url, '_blank', 'noopener,noreferrer');
          } else if (cmd.action === 'changeAuraTheme' && cmd.payload.theme) {
            const theme = cmd.payload.theme as AuraTheme;
            commandText = `Switched theme to ${theme}`;
            setAuraTheme(theme);
            showToast(`📱 Remote Command from ${cmd.fromDeviceName}: Switched Aura Theme to ${theme}!`, 'success');
          } else if (cmd.action === 'triggerAlert' && cmd.payload.message) {
            commandText = `Alert: "${cmd.payload.message}"`;
            showToast(`🔔 Message from ${cmd.fromDeviceName}: "${cmd.payload.message}"`, 'info');
          }

          if (commandText) {
            setLastCrossDeviceLog({
              text: commandText,
              from: cmd.fromDeviceName,
              time: new Date().toLocaleTimeString(),
            });
          }
        }
      }
    } catch {
      // Ignore transient network errors during server restarts
    }
  }, [showToast]);

  useEffect(() => {
    registerDeviceHeartbeat();
    pollRemoteCommands();

    const heartbeatInterval = setInterval(registerDeviceHeartbeat, 5000);
    const commandPollInterval = setInterval(pollRemoteCommands, 2500);

    return () => {
      clearInterval(heartbeatInterval);
      clearInterval(commandPollInterval);
    };
  }, [registerDeviceHeartbeat, pollRemoteCommands]);

  const handleUpdateEmail = (newEmail: string) => {
    setUserEmail(newEmail);
    localStorage.setItem('zoya_user_email', newEmail);
    showToast(`Account email set to: ${newEmail}`, 'success');
  };

  const fetchMemoryCount = useCallback(async () => {
    try {
      const res = await fetch('/api/memories');
      const data = await res.json();
      if (data.success && Array.isArray(data.memories)) {
        setMemoryCount(data.memories.length);
      }
    } catch (err) {
      console.error('Error fetching memory count:', err);
    }
  }, []);

  useEffect(() => {
    fetchMemoryCount();
  }, [fetchMemoryCount]);

  const handleSimulateCall = useCallback(
    (callerName = 'Papa', relation = 'Father', number = '+91 98765 43210', isSpam = false, isUnknown = false) => {
      setIncomingCall({
        id: 'call_' + Date.now(),
        name: callerName,
        relation: relation,
        number: number,
        isRinging: true,
        isConnected: false,
        isSpam: isSpam || callerName.toLowerCase().includes('spam') || relation.toLowerCase().includes('spam'),
        isUnknown: isUnknown || callerName.toLowerCase().includes('unknown') || relation.toLowerCase().includes('unknown'),
      });
      showToast(`📞 Incoming call simulated from ${callerName} (${relation})`, 'info');
    },
    [showToast]
  );

  const handleAcceptCall = useCallback(() => {
    setIncomingCall((prev) => (prev ? { ...prev, isRinging: false, isConnected: true } : null));
    showToast(`✅ Call Accepted! Connected with caller.`, 'success');
  }, [showToast]);

  const handleDeclineCall = useCallback(
    (reason?: string) => {
      setIncomingCall(null);
      showToast(reason ? `❌ Call declined with reply: "${reason}"` : `❌ Call declined.`, 'info');
    },
    [showToast]
  );

  const handleEndCall = useCallback(() => {
    setIncomingCall(null);
    showToast(`📞 Call ended.`, 'info');
  }, [showToast]);

  const handleToolCall = useCallback((toolName: string, args: Record<string, unknown>, log: ToolActionLog) => {
    setToolLogs((prev) => [log, ...prev]);

    if (toolName === 'changeAuraTheme' && args.theme) {
      setAuraTheme(args.theme as AuraTheme);
      showToast(`Zoya changed aura theme to ${args.theme}!`, 'success');
    } else if (toolName === 'playMusicOrVideo') {
      const query = (args.query as string) || 'Music';
      const youtubeUrl = args.youtubeUrl as string;
      setActiveMusicTrack({ query, youtubeUrl });
      showToast(`🎵 Zoya is playing: "${query}"`, 'success');
      if (youtubeUrl) {
        window.open(youtubeUrl, '_blank', 'noopener,noreferrer');
      }
    } else if (toolName === 'openWebsite') {
      const url = log.url || (args.url as string);
      showToast(`Zoya opened website: ${args.targetName || url}`, 'success', url);
      if (url) {
        window.open(url, '_blank', 'noopener,noreferrer');
      }
      if (url && (url.includes('youtube.com') || url.includes('spotify.com') || url.includes('music'))) {
        setActiveMusicTrack({ query: (args.targetName as string) || 'YouTube Song', youtubeUrl: url });
      }
    } else if (toolName === 'controlPcApp') {
      const appName = (args.appName as string) || 'App';
      const url = args.url as string;
      showToast(`💻 Opening PC App: ${appName}`, 'success', url);
      if (url) {
        window.open(url, '_blank', 'noopener,noreferrer');
      } else {
        window.open(`https://www.youtube.com/results?search_query=${encodeURIComponent(appName)}`, '_blank', 'noopener,noreferrer');
      }
      setActiveMusicTrack({ query: appName, youtubeUrl: url });
    } else if (toolName === 'triggerQuickAction') {
      showToast(`Zoya executed action: ${args.action}`, 'info');
    } else if (toolName === 'saveMemory') {
      const key = (args.key as string) || 'Fact';
      const value = (args.value as string) || '';
      showToast(`🧠 Zoya saved to memory: "${key}" = "${value}"!`, 'success');
      fetchMemoryCount();
    } else if (toolName === 'forgetMemory') {
      const key = (args.key as string) || '';
      showToast(`🗑️ Zoya removed memory: "${key}"`, 'info');
      fetchMemoryCount();
    } else if (toolName === 'announceIncomingCall') {
      const callerName = (args.callerName as string) || 'Unknown Contact';
      const relationship = (args.relationship as string) || 'Calling...';
      const number = (args.phoneNumber as string) || '+91 98765 43210';
      handleSimulateCall(callerName, relationship, number);
    } else if (toolName === 'handleCallAction') {
      const action = (args.action as string) || 'accept';
      if (action === 'accept') {
        handleAcceptCall();
      } else {
        handleDeclineCall(args.replyMessage as string);
      }
    }
  }, [showToast, fetchMemoryCount, handleSimulateCall, handleAcceptCall, handleDeclineCall]);

  const handleVoiceTranscript = useCallback((text: string, sender: 'user' | 'zoya') => {
    if (!text || !text.trim()) return;
    const newMsg: ConversationMessage = {
      id: `msg-voice-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
      sender,
      text: text.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      type: 'voice',
    };

    setConversations((prev) => {
      if (prev.length > 0) {
        const last = prev[prev.length - 1];
        if (last.sender === sender && last.text === text.trim()) {
          return prev;
        }
      }
      const updated = [...prev, newMsg];
      try {
        localStorage.setItem('zoya_conversations', JSON.stringify(updated));
      } catch {}
      return updated;
    });
  }, []);

  const toggleConnection = useCallback(() => {
    if (status === 'disconnected' || status === 'error') {
      liveSessionRef.current = new LiveSession({
        voiceName: selectedVoice,
        onStatusChange: (newStatus) => setStatus(newStatus),
        onMicVolume: (vol) => setMicVolume(vol),
        onSpeakerVolume: (vol) => setSpeakerVolume(vol),
        onToolCall: (toolName, args, log) => {
          handleToolCall(toolName, args, log);
          handleVoiceTranscript(`⚡ Action: ${log.details}`, 'zoya');
        },
        onTranscript: (text, sender) => handleVoiceTranscript(text, sender),
        onError: (errMsg) => {
          showToast(errMsg, 'error');
        },
      });

      liveSessionRef.current.connect();
    } else {
      if (liveSessionRef.current) {
        liveSessionRef.current.disconnect();
        liveSessionRef.current = null;
      }
      setStatus('disconnected');
      setIsMuted(false);
      setMicVolume(0);
      setSpeakerVolume(0);
    }
  }, [status, selectedVoice, handleToolCall, showToast]);

  const toggleMute = useCallback(() => {
    const nextMute = !isMuted;
    setIsMuted(nextMute);
    if (liveSessionRef.current) {
      liveSessionRef.current.setMuted(nextMute);
    }
  }, [isMuted]);

  const handleSelectPrompt = useCallback((promptText: string) => {
    if (status === 'disconnected' || status === 'error') {
      showToast(`Tap the central power button first to connect to Zoya! Prompt: "${promptText}"`, 'info');
    } else {
      showToast(`Speak to Zoya: "${promptText}"`, 'info');
    }
  }, [status, showToast]);

  const handleInstantScreenAnalysis = useCallback(async () => {
    try {
      showToast('🖥️ Select a screen window to share with Zoya...', 'info');
      const mediaStream = await navigator.mediaDevices.getDisplayMedia({
        video: { cursor: 'always' } as any,
        audio: false,
      });

      const video = document.createElement('video');
      video.srcObject = mediaStream;
      await video.play();

      await new Promise((resolve) => setTimeout(resolve, 300));

      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth || 1280;
      canvas.height = video.videoHeight || 720;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      }
      const dataUrl = canvas.toDataURL('image/jpeg', 0.85);

      mediaStream.getTracks().forEach((track) => track.stop());

      showToast('⚡ Zoya is reading & analyzing your screen...', 'info');

      const res = await fetch('/api/vision-analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image: dataUrl,
          mode: 'screen',
          prompt: 'Zoya, analyze my screen in detail! Read all visible text, explain any videos, code, or images, and give me a clear witty reply in Hinglish!',
        }),
      });

      const data = await res.json();
      if (data.success && data.reply) {
        const replyText = data.reply;
        handleVoiceTranscript(replyText, 'zoya');
        showToast('Screen analysis complete!', 'success');

        // Speak response out loud using Web Speech API
        if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
          window.speechSynthesis.cancel();
          const cleanText = replyText.replace(/[\*\#\`\_]/g, '');
          const utterance = new SpeechSynthesisUtterance(cleanText);
          utterance.lang = 'hi-IN';
          window.speechSynthesis.speak(utterance);
        }
      } else {
        showToast(data.error || 'Failed to analyze screen screenshot.', 'error');
      }
    } catch (err) {
      console.error('Instant screen capture error:', err);
      showToast('Screen capture cancelled or unavailable.', 'info');
    }
  }, [showToast, handleVoiceTranscript]);

  const handleExecuteTextCommand = useCallback(
    async (commandText: string) => {
      const lowerText = commandText.toLowerCase();

      // Check if user is asking to play a song/music
      if (
        lowerText.includes('hanuman chalisa') ||
        lowerText.includes('lut le gya') ||
        lowerText.includes('play song') ||
        lowerText.includes('play music') ||
        lowerText.includes('gaana chalao') ||
        lowerText.includes('baja')
      ) {
        let trackQuery = commandText.replace(/zoya|play|chalao|baja|song|gaana|music|on youtube/gi, '').trim();
        if (!trackQuery) trackQuery = commandText;
        setActiveMusicTrack({ query: trackQuery });
        showToast(`🎵 Zoya is playing: "${trackQuery}"`, 'success');
      }

      // Check if user is asking for screen analysis
      if (
        lowerText.includes('screen') &&
        (lowerText.includes('dikh') ||
          lowerText.includes('analyze') ||
          lowerText.includes('kya hai') ||
          lowerText.includes('capture') ||
          lowerText.includes('read') ||
          lowerText.includes('share') ||
          lowerText.includes('dekh'))
      ) {
        handleInstantScreenAnalysis();
      }

      try {
        const res = await fetch('/api/text-command', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: commandText,
            fromDeviceId: deviceIdRef.current,
            deviceType: deviceTypeRef.current,
          }),
        });

        const data = await res.json();
        if (data.success) {
          // Process function calls
          if (Array.isArray(data.functionCalls)) {
            for (const fc of data.functionCalls) {
              const { name, args } = fc;
              if (name === 'playMusicOrVideo') {
                const query = (args.query as string) || 'Music';
                const youtubeUrl = args.youtubeUrl as string;
                setActiveMusicTrack({ query, youtubeUrl });
                showToast(`🎵 Zoya is playing: "${query}"`, 'success');
              } else if (name === 'changeAuraTheme' && args.theme) {
                setAuraTheme(args.theme as AuraTheme);
                showToast(`Zoya changed theme to ${args.theme}!`, 'success');
              } else if (name === 'openWebsite' && args.url) {
                showToast(`Zoya opened website: ${args.url}`, 'success', args.url);
                window.open(args.url, '_blank', 'noopener,noreferrer');
                if (args.url.includes('youtube.com') || args.url.includes('spotify.com') || args.url.includes('music')) {
                  setActiveMusicTrack({ query: (args.targetName as string) || 'Music Video', youtubeUrl: args.url });
                }
              } else if (name === 'saveMemory') {
                showToast(`🧠 Saved memory: "${args.key}" = "${args.value}"!`, 'success');
                fetchMemoryCount();
              } else if (name === 'forgetMemory') {
                showToast(`🗑️ Removed memory: "${args.key}"`, 'info');
                fetchMemoryCount();
              } else if (name === 'sendCrossDeviceCommand') {
                showToast(`📱 Remote command sent to ${args.targetDevice || 'mobile'}!`, 'success');
              }
            }
          }

          return { reply: data.reply || 'Command executed!', success: true };
        } else {
          return { reply: data.error || 'Failed to process text command.', success: false };
        }
      } catch (err) {
        console.error('Error executing text command:', err);
        return { reply: 'Server communication error.', success: false };
      }
    },
    [showToast, fetchMemoryCount, handleInstantScreenAnalysis]
  );

  const handleSendMessage = useCallback(
    async (userText: string) => {
      const userMsg: ConversationMessage = {
        id: `msg-user-${Date.now()}`,
        sender: 'user',
        text: userText,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        type: 'text',
      };

      setConversations((prev) => {
        const updated = [...prev, userMsg];
        try {
          localStorage.setItem('zoya_conversations', JSON.stringify(updated));
        } catch {}
        return updated;
      });

      const res = await handleExecuteTextCommand(userText);

      const zoyaMsg: ConversationMessage = {
        id: `msg-zoya-${Date.now()}`,
        sender: 'zoya',
        text: res.reply,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        type: 'text',
      };

      setConversations((prev) => {
        const updated = [...prev, zoyaMsg];
        try {
          localStorage.setItem('zoya_conversations', JSON.stringify(updated));
        } catch {}
        return updated;
      });
    },
    [handleExecuteTextCommand]
  );

  const handleClearConversations = useCallback(() => {
    setConversations([]);
    try {
      localStorage.removeItem('zoya_conversations');
    } catch {}
    showToast('Conversation history cleared', 'info');
  }, [showToast]);

  // Clean up session on unmount
  useEffect(() => {
    return () => {
      if (liveSessionRef.current) {
        liveSessionRef.current.disconnect();
      }
    };
  }, []);

  return (
    <div className="relative w-screen h-screen overflow-hidden bg-[#020617] bg-hud-grid text-white flex flex-col items-center select-none font-mono">
      {/* Background Cyan & Indigo Atmospheric Glows */}
      <div className="absolute top-[-10%] left-[-10%] w-[45%] h-[45%] bg-cyan-900/15 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-indigo-900/15 rounded-full blur-[160px] pointer-events-none" />

      {/* Header */}
      <Header
        status={status}
        currentTheme={auraTheme}
        executedToolsCount={toolLogs.length}
        memoryCount={memoryCount}
        deviceCount={deviceCount}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onOpenPcControl={() => setIsPcControlOpen(true)}
        onOpenToolLogs={() => setIsToolLogsOpen(true)}
        onOpenThemePicker={() => setIsToolLogsOpen(true)}
        onOpenMemoryVault={() => setIsMemoryVaultOpen(true)}
        onOpenDeviceSync={() => setIsDeviceSyncOpen(true)}
        onOpenVision={() => setIsVisionOpen(true)}
        onOpenJarvis={() => setIsJarvisOpen(true)}
        onOpenHabits={() => setIsHabitsOpen(true)}
        onOpenGeminiChat={() => setIsGeminiChatOpen(true)}
      />

      {/* Main Interactive Stage */}
      <main className="relative flex-1 min-h-0 w-full max-w-5xl flex flex-col items-center px-3 py-2 z-10 overflow-y-auto scrollbar-thin scrollbar-thumb-cyan-500/30">
        {/* Real-Time Toast Notification Banner */}
        <AnimatePresence>
          {toastMessage && (
            <motion.div
              initial={{ opacity: 0, y: -20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -20, scale: 0.95 }}
              className={`absolute top-4 px-4 py-2.5 rounded-xl border backdrop-blur-md shadow-2xl flex items-center gap-3 text-xs font-mono font-bold z-30 max-w-md text-center ${
                toastMessage.type === 'error'
                  ? 'bg-rose-950/90 border-rose-500/80 text-rose-200'
                  : toastMessage.type === 'success'
                  ? 'bg-emerald-950/90 border-emerald-500/80 text-emerald-200'
                  : 'bg-cyan-950/90 border-cyan-400/80 text-cyan-200'
              }`}
            >
              {toastMessage.type === 'error' ? (
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              ) : (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              )}
              <span>{toastMessage.text}</span>
              {toastMessage.url && (
                <a
                  href={toastMessage.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-1 rounded bg-white/20 hover:bg-white/30 text-cyan-300"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Central Stage: Telemetry (Left) | Arc Reactor (Center) | Voice Link Controls (Right) */}
        <div className="w-full flex-1 flex flex-col md:flex-row items-center justify-between gap-4 my-2 px-2">
          {/* Left Side Panel: STARK OS Telemetry & Live AI Core Status */}
          <div className="w-full md:w-60 flex flex-col items-start gap-2 p-3 rounded-2xl bg-slate-950/85 border border-cyan-500/30 backdrop-blur-xl text-xs font-mono shadow-[0_0_20px_rgba(6,182,212,0.15)] shrink-0">
            <div className="flex flex-col gap-1 w-full">
              <span className="text-[10px] font-bold uppercase tracking-widest text-cyan-400 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
                STARK OS TELEMETRY
              </span>
              <div className="flex items-center gap-1.5 text-xs text-cyan-200 font-mono font-medium">
                <ExternalLink className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                <span className="truncate">
                  {toolLogs.length > 0 ? toolLogs[0].details : 'Core Operational'}
                </span>
              </div>
            </div>

            <div className="w-full h-[1px] bg-cyan-500/20 my-0.5" />

            <div className="flex items-center justify-between w-full text-[10px] text-cyan-300 font-bold">
              <span className="flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-pink-400" /> AI CORE:
              </span>
              <span className="text-white">Gemini Live</span>
            </div>

            {/* Quick Prompts inside Left Panel */}
            <div className="w-full pt-1.5 border-t border-cyan-500/20">
              <PersonalityCard onSelectPrompt={handleSelectPrompt} />
            </div>
          </div>

          {/* Center Stage: Visualizer Arc Reactor */}
          <div className="flex-1 flex flex-col items-center justify-center min-w-0">
            <AuraVisualizer
              status={status}
              theme={auraTheme}
              micVolume={micVolume}
              speakerVolume={speakerVolume}
              lastCrossDeviceLog={lastCrossDeviceLog}
              onThemeChange={(newTheme) => setAuraTheme(newTheme)}
            />
          </div>

          {/* Right Side Panel: Mic Power Arc Reactor Activation Control */}
          <div className="w-full md:w-56 flex flex-col items-center justify-center gap-2 p-3 rounded-2xl bg-slate-950/90 border border-cyan-400/50 backdrop-blur-xl shadow-[0_0_25px_rgba(6,182,212,0.25)] font-mono text-xs shrink-0">
            <div className="flex flex-col items-center text-center gap-0.5">
              <span className="text-[10px] font-mono font-bold text-cyan-300 uppercase tracking-widest flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" /> VOICE LINK CORE
              </span>
              <span className="text-[9px] text-cyan-400/80 font-bold uppercase">
                {status === 'listening'
                  ? '⚡ LISTENING ACTIVE'
                  : status === 'speaking'
                  ? '🎵 SPEAKING'
                  : status === 'connecting'
                  ? '🔄 CONNECTING'
                  : 'TAP TO LINK VOICE'}
              </span>
            </div>

            <MicPowerButton
              status={status}
              isMuted={isMuted}
              onToggleConnection={toggleConnection}
              onToggleMute={toggleMute}
            />

            <div className="text-[9px] text-cyan-300/80 text-center font-mono font-bold uppercase tracking-wider">
              {isMuted ? '⚠️ MIC MUTED' : 'ARC REACTOR READY'}
            </div>
          </div>
        </div>

        {/* Live Conversation & Holographic Transcripts Feed */}
        <ConversationSection
          conversations={conversations}
          onSendMessage={handleSendMessage}
          onClearConversations={handleClearConversations}
          status={status}
          onTriggerScreenAnalysis={handleInstantScreenAnalysis}
        />
      </main>

      {/* Embedded Music & Video Auto-Play Widget */}
      {activeMusicTrack && (
        <MusicPlayerWidget
          query={activeMusicTrack.query}
          youtubeUrl={activeMusicTrack.youtubeUrl}
          onClose={() => setActiveMusicTrack(null)}
        />
      )}

      {/* Tool & Action Logs Drawer */}
      <ToolDrawer
        isOpen={isToolLogsOpen}
        onClose={() => setIsToolLogsOpen(false)}
        logs={toolLogs}
        currentTheme={auraTheme}
        onSelectTheme={(theme) => setAuraTheme(theme)}
        onOpenMemoryVault={() => setIsMemoryVaultOpen(true)}
      />

      {/* Voice Settings & Control Panel Modal */}
      <VoiceSettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        selectedVoice={selectedVoice}
        onSelectVoice={(voice) => {
          setSelectedVoice(voice);
          showToast(`Selected voice: ${voice}. Reconnect to apply!`, 'info');
        }}
        memoryCount={memoryCount}
        deviceCount={deviceCount}
        executedToolsCount={toolLogs.length}
        onOpenGeminiChat={() => setIsGeminiChatOpen(true)}
        onOpenVision={() => setIsVisionOpen(true)}
        onOpenJarvis={() => setIsJarvisOpen(true)}
        onOpenDeviceSync={() => setIsDeviceSyncOpen(true)}
        onOpenHabits={() => setIsHabitsOpen(true)}
        onOpenMemoryVault={() => setIsMemoryVaultOpen(true)}
        onOpenPcControl={() => setIsPcControlOpen(true)}
        onOpenToolLogs={() => setIsToolLogsOpen(true)}
        onOpenThemePicker={() => setIsToolLogsOpen(true)}
        onSimulateCall={handleSimulateCall}
      />

      {/* PC Controller & System Automation Modal */}
      <PcControlModal
        isOpen={isPcControlOpen}
        onClose={() => setIsPcControlOpen(false)}
        showToast={showToast}
        onExecuteCommand={handleExecuteTextCommand}
      />

      {/* Memory Vault Modal */}
      <MemoryVaultModal
        isOpen={isMemoryVaultOpen}
        onClose={() => setIsMemoryVaultOpen(false)}
        onMemoryUpdated={fetchMemoryCount}
        onAskZoya={(promptText) => {
          handleSelectPrompt(promptText);
        }}
      />

      {/* PC & Mobile Device Sync Modal */}
      <DeviceSyncModal
        isOpen={isDeviceSyncOpen}
        onClose={() => setIsDeviceSyncOpen(false)}
        currentDeviceId={deviceIdRef.current}
        currentDeviceType={deviceTypeRef.current}
        userEmail={userEmail}
        onUpdateEmail={handleUpdateEmail}
        onSelectTheme={(theme) => setAuraTheme(theme)}
        onTriggerToast={(msg, type) => showToast(msg, type)}
      />

      {/* Zoya Camera Vision & Screen Reader Modal */}
      <VisionModal
        isOpen={isVisionOpen}
        onClose={() => setIsVisionOpen(false)}
        onMemoryUpdate={fetchMemoryCount}
        onThemeChange={(theme) => setAuraTheme(theme as AuraTheme)}
        showToast={showToast}
      />

      {/* JARVIS & Nova Autonomous Companion Protocol Modal */}
      <JarvisCompanionHUD
        isOpen={isJarvisOpen}
        onClose={() => setIsJarvisOpen(false)}
        onExecuteCommand={handleExecuteTextCommand}
        showToast={showToast}
      />

      {/* Daily Habit & Streak Tracker Modal */}
      <HabitTrackerModal
        isOpen={isHabitsOpen}
        onClose={() => setIsHabitsOpen(false)}
        onExecuteCommand={handleExecuteTextCommand}
        showToast={showToast}
      />

      {/* Gemini Multi-Turn Chat, Grounding & Multimodal Vision Modal */}
      <GeminiChatModal
        isOpen={isGeminiChatOpen}
        onClose={() => setIsGeminiChatOpen(false)}
        showToast={showToast}
      />

      {/* Read Caller's Name & Call Assistant Modal */}
      <IncomingCallModal
        call={incomingCall}
        onAccept={handleAcceptCall}
        onDecline={handleDeclineCall}
        onEndCall={handleEndCall}
        autoAnnounceEnabled={autoAnnounceCaller}
        onToggleAutoAnnounce={() => setAutoAnnounceCaller(!autoAnnounceCaller)}
      />
    </div>
  );
}
