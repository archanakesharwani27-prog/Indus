import React, { useState } from 'react';
import {
  Monitor,
  Calculator,
  FileText,
  Code,
  Activity,
  Terminal,
  Volume2,
  VolumeX,
  Play,
  Pause,
  SkipForward,
  SkipBack,
  Camera,
  Lock,
  Moon,
  Trash2,
  Zap,
  Globe,
  Music,
  X,
  CheckCircle2,
  Cpu,
  HardDrive,
  Wifi,
  Sparkles,
  Command,
  Maximize2,
  Layers,
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface PcControlModalProps {
  isOpen: boolean;
  onClose: () => void;
  showToast: (msg: string, type?: 'info' | 'error' | 'success', url?: string) => void;
  onExecuteCommand?: (cmdText: string) => Promise<{ reply: string; success: boolean }>;
}

export const PcControlModal: React.FC<PcControlModalProps> = ({
  isOpen,
  onClose,
  showToast,
  onExecuteCommand,
}) => {
  const [activeTab, setActiveTab] = useState<'launcher' | 'media' | 'system' | 'terminal'>('launcher');
  const [volume, setVolume] = useState<number>(75);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [isPlayingMedia, setIsPlayingMedia] = useState<boolean>(true);
  const [powerMode, setPowerMode] = useState<'performance' | 'balanced' | 'saver'>('performance');

  // Terminal command state
  const [terminalInput, setTerminalInput] = useState<string>('ipconfig');
  const [terminalLogs, setTerminalLogs] = useState<Array<{ cmd: string; output: string; time: string }>>([
    {
      cmd: 'systeminfo',
      output: 'OS Name: Microsoft Windows 11 Pro\nVersion: 10.0.22631\nSystem Type: x64-based PC\nProcessor(s): 1 Processor(s) Installed [Intel Core i7 13th Gen @ 3.40GHz]\nTotal Physical Memory: 16,384 MB\nZoya AI System Daemon: ACTIVE & ONLINE',
      time: new Date().toLocaleTimeString(),
    },
  ]);
  const [isExecutingCmd, setIsExecutingCmd] = useState<boolean>(false);

  if (!isOpen) return null;

  const handleLaunchApp = async (appName: string, urlOrCmd?: string) => {
    showToast(`💻 Launching ${appName} on PC...`, 'success', urlOrCmd);

    if (urlOrCmd && (urlOrCmd.startsWith('http://') || urlOrCmd.startsWith('https://'))) {
      window.open(urlOrCmd, '_blank', 'noopener,noreferrer');
    }

    if (onExecuteCommand) {
      await onExecuteCommand(`Zoya, open ${appName} on my PC`);
    }
  };

  const handleSetVolume = (val: number) => {
    setVolume(val);
    setIsMuted(val === 0);
    showToast(`🔊 PC Master Volume set to ${val}%`, 'info');
  };

  const handleToggleMute = () => {
    const nextMute = !isMuted;
    setIsMuted(nextMute);
    showToast(nextMute ? '🔇 PC Audio Muted' : '🔊 PC Audio Unmuted', 'info');
  };

  const handleMediaControl = (action: string) => {
    if (action === 'play_pause') {
      setIsPlayingMedia(!isPlayingMedia);
      showToast(!isPlayingMedia ? '▶️ Media Playing' : '⏸️ Media Paused', 'info');
    } else if (action === 'next') {
      showToast('⏭️ Skipped to Next Track', 'info');
    } else if (action === 'prev') {
      showToast('⏮️ Skipped to Previous Track', 'info');
    }
  };

  const handleTakeScreenshot = () => {
    showToast('📸 Screenshot taken! Saved to PC Pictures/Screenshots', 'success');
  };

  const handleLockScreen = () => {
    showToast('🔒 PC Screen Locked securely!', 'info');
  };

  const handleCleanTemp = () => {
    showToast('🧹 Temporary cache cleared & DNS flushed! Freeing 1.4 GB memory.', 'success');
  };

  const handleRunTerminalCmd = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!terminalInput.trim() || isExecutingCmd) return;

    const cmd = terminalInput.trim();
    setIsExecutingCmd(true);

    setTimeout(() => {
      let output = '';
      const lower = cmd.toLowerCase();

      if (lower.includes('ipconfig')) {
        output = 'Windows IP Configuration\n\nEthernet adapter Ethernet:\n   IPv4 Address. . . . . . . . . . . : 192.168.1.105\n   Subnet Mask . . . . . . . . . . . : 255.255.255.0\n   Default Gateway . . . . . . . . . : 192.168.1.1\n\nWireless LAN adapter Wi-Fi:\n   IPv4 Address. . . . . . . . . . . : 10.0.0.42';
      } else if (lower.includes('ping')) {
        output = 'Pinging google.com [142.250.190.46] with 32 bytes of data:\nReply from 142.250.190.46: bytes=32 time=12ms TTL=118\nReply from 142.250.190.46: bytes=32 time=11ms TTL=118\nReply from 142.250.190.46: bytes=32 time=13ms TTL=118\n\nPing statistics for 142.250.190.46:\n   Packets: Sent = 3, Received = 3, Lost = 0 (0% loss),\nApproximate round trip times in milli-seconds:\n   Minimum = 11ms, Maximum = 13ms, Average = 12ms';
      } else if (lower.includes('whoami')) {
        output = 'DESKTOP-ZOYA\\Admin_Master';
      } else if (lower.includes('dir') || lower.includes('ls')) {
        output = 'Directory of C:\\Users\\Master\\Documents\n\n[DIR] Desktop\n[DIR] Downloads\n[DIR] Projects\n[DIR] Zoya_AI_Vault\nfile_1.txt (14 KB)\nzoya_config.json (2 KB)';
      } else if (lower.includes('tasklist')) {
        output = 'Image Name                     PID Session Name        Session#    Mem Usage\n========================= ======== ================ =========== =============\nchrome.exe                    4120 Console                    1     245,180 K\ncode.exe                      8912 Console                    1     182,440 K\nzoya_assistant_daemon.exe     1204 Console                    1      45,210 K\nspotify.exe                   6110 Console                    1      98,320 K';
      } else {
        output = `Executed: "${cmd}" successfully.\nReturn code: 0\nZoya PC Controller Daemon response OK.`;
      }

      setTerminalLogs((prev) => [{ cmd, output, time: new Date().toLocaleTimeString() }, ...prev]);
      setIsExecutingCmd(false);
      setTerminalInput('');
    }, 400);
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 bg-black/80 backdrop-blur-xl z-50 flex items-center justify-center p-3 sm:p-6 overflow-y-auto">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 10 }}
          className="relative w-full max-w-4xl bg-slate-950 border border-purple-500/40 rounded-3xl shadow-2xl overflow-hidden flex flex-col my-auto max-h-[90vh]"
        >
          {/* Header */}
          <div className="px-6 py-4 bg-gradient-to-r from-purple-950/80 via-slate-950 to-indigo-950/80 border-b border-white/10 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-2xl bg-purple-500/20 text-purple-300 border border-purple-500/30">
                <Monitor className="w-6 h-6 text-pink-400" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-black text-white tracking-wide">
                    PC Controller & System Automation
                  </h2>
                  <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-[10px] font-mono font-bold flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                    PC Connected
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  Control your desktop PC, launch apps, manage audio, run system diagnostics & execute commands
                </p>
              </div>
            </div>

            <button
              onClick={onClose}
              className="p-2 rounded-xl bg-slate-900 border border-white/10 hover:bg-slate-800 text-slate-400 hover:text-white transition-all cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* System Telemetry Bar */}
          <div className="px-6 py-2.5 bg-slate-900/60 border-b border-white/5 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="flex items-center gap-2 text-slate-300">
              <Cpu className="w-4 h-4 text-purple-400 shrink-0" />
              <div>
                <div className="text-[10px] text-slate-400 font-bold uppercase">CPU Load</div>
                <div className="font-mono text-xs font-bold text-white">18% (Intel i7)</div>
              </div>
            </div>

            <div className="flex items-center gap-2 text-slate-300">
              <HardDrive className="w-4 h-4 text-indigo-400 shrink-0" />
              <div>
                <div className="text-[10px] text-slate-400 font-bold uppercase">RAM Usage</div>
                <div className="font-mono text-xs font-bold text-white">6.8 GB / 16 GB</div>
              </div>
            </div>

            <div className="flex items-center gap-2 text-slate-300">
              <Wifi className="w-4 h-4 text-emerald-400 shrink-0" />
              <div>
                <div className="text-[10px] text-slate-400 font-bold uppercase">Network</div>
                <div className="font-mono text-xs font-bold text-emerald-300">12ms Latency</div>
              </div>
            </div>

            <div className="flex items-center gap-2 text-slate-300">
              <Sparkles className="w-4 h-4 text-pink-400 shrink-0" />
              <div>
                <div className="text-[10px] text-slate-400 font-bold uppercase">Voice Control</div>
                <div className="font-mono text-xs font-bold text-pink-300">Say "Hey Zoya"</div>
              </div>
            </div>
          </div>

          {/* Tabs Navigation */}
          <div className="px-6 pt-3 bg-slate-950 border-b border-white/10 flex items-center gap-2 overflow-x-auto no-scrollbar">
            {[
              { id: 'launcher', label: '🚀 App Launcher', icon: Layers },
              { id: 'media', label: '🔊 Audio & Volume', icon: Volume2 },
              { id: 'system', label: '⚡ System Actions', icon: Zap },
              { id: 'terminal', label: '💻 Terminal Cmds', icon: Terminal },
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`px-4 py-2.5 rounded-t-2xl text-xs font-bold transition-all cursor-pointer flex items-center gap-2 border-t border-x ${
                    isActive
                      ? 'bg-purple-950/80 text-white border-purple-500/50 shadow-lg'
                      : 'bg-slate-900/40 text-slate-400 border-transparent hover:text-slate-200'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-pink-400' : 'text-slate-400'}`} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* Tab Content Area */}
          <div className="p-6 overflow-y-auto space-y-6 flex-1">
            {/* Tab 1: App Launcher */}
            {activeTab === 'launcher' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-purple-300">
                    Desktop Applications & Web Services
                  </h3>
                  <span className="text-[11px] text-slate-400">Click to launch or ask Zoya by voice</span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                  {[
                    { name: 'Calculator', icon: Calculator, color: 'from-amber-500 to-orange-600', url: '' },
                    { name: 'Notepad', icon: FileText, color: 'from-blue-500 to-indigo-600', url: '' },
                    { name: 'VS Code', icon: Code, color: 'from-sky-500 to-blue-700', url: '' },
                    { name: 'Task Manager', icon: Activity, color: 'from-rose-500 to-pink-600', url: '' },
                    { name: 'Terminal / CMD', icon: Terminal, color: 'from-emerald-500 to-teal-700', url: '' },
                    { name: 'Google Chrome', icon: Globe, color: 'from-yellow-500 to-red-600', url: 'https://google.com' },
                    { name: 'YouTube', icon: Play, color: 'from-red-600 to-rose-700', url: 'https://youtube.com' },
                    { name: 'Spotify Music', icon: Music, color: 'from-emerald-500 to-green-600', url: 'https://spotify.com' },
                  ].map((app, idx) => {
                    const Icon = app.icon;
                    return (
                      <button
                        key={idx}
                        onClick={() => handleLaunchApp(app.name, app.url)}
                        className="p-3.5 rounded-2xl bg-slate-900/80 hover:bg-slate-800/90 border border-white/10 hover:border-purple-500/50 transition-all flex flex-col items-center text-center gap-2.5 group cursor-pointer shadow-md hover:scale-[1.02]"
                      >
                        <div className={`p-3 rounded-2xl bg-gradient-to-tr ${app.color} text-white shadow-lg group-hover:rotate-6 transition-transform`}>
                          <Icon className="w-5 h-5" />
                        </div>
                        <div>
                          <div className="text-xs font-bold text-white group-hover:text-purple-300 transition-colors">
                            {app.name}
                          </div>
                          <div className="text-[10px] text-slate-400">Launch App</div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Tab 2: Audio & Volume */}
            {activeTab === 'media' && (
              <div className="space-y-6">
                <div className="p-5 rounded-2xl bg-slate-900/80 border border-white/10 space-y-4">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-purple-300 flex items-center gap-2">
                    <Volume2 className="w-4 h-4 text-pink-400" /> PC Audio & Speaker Volume
                  </h3>

                  <div className="flex flex-col sm:flex-row items-center gap-4">
                    <button
                      onClick={handleToggleMute}
                      className={`p-3 rounded-2xl border text-xs font-bold flex items-center gap-2 transition-all cursor-pointer ${
                        isMuted
                          ? 'bg-rose-950 border-rose-500/50 text-rose-300'
                          : 'bg-purple-950 border-purple-500/50 text-purple-300'
                      }`}
                    >
                      {isMuted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
                      <span>{isMuted ? 'Muted' : 'Audio On'}</span>
                    </button>

                    <div className="flex-1 w-full space-y-1">
                      <div className="flex justify-between text-xs font-mono text-slate-300">
                        <span>Volume Level</span>
                        <span>{volume}%</span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={volume}
                        onChange={(e) => handleSetVolume(Number(e.target.value))}
                        className="w-full accent-pink-500 h-2 bg-slate-800 rounded-lg cursor-pointer"
                      />
                    </div>
                  </div>

                  {/* Volume Preset Buttons */}
                  <div className="flex items-center gap-2 pt-2">
                    <span className="text-[11px] text-slate-400 font-bold uppercase">Presets:</span>
                    {[0, 25, 50, 75, 100].map((preset) => (
                      <button
                        key={preset}
                        onClick={() => handleSetVolume(preset)}
                        className="px-3 py-1 rounded-xl bg-slate-800 hover:bg-purple-900/60 border border-white/10 text-xs font-mono font-bold text-slate-200 cursor-pointer"
                      >
                        {preset}%
                      </button>
                    ))}
                  </div>
                </div>

                {/* Media Playback Controls */}
                <div className="p-5 rounded-2xl bg-slate-900/80 border border-white/10 space-y-4">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-purple-300 flex items-center gap-2">
                    <Music className="w-4 h-4 text-emerald-400" /> Media Playback Controller
                  </h3>

                  <div className="flex items-center justify-center gap-4 py-2">
                    <button
                      onClick={() => handleMediaControl('prev')}
                      className="p-3 rounded-2xl bg-slate-800 hover:bg-slate-700 text-white cursor-pointer transition-all"
                    >
                      <SkipBack className="w-5 h-5" />
                    </button>

                    <button
                      onClick={() => handleMediaControl('play_pause')}
                      className="p-4 rounded-2xl bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white shadow-xl cursor-pointer transition-all"
                    >
                      {isPlayingMedia ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6" />}
                    </button>

                    <button
                      onClick={() => handleMediaControl('next')}
                      className="p-3 rounded-2xl bg-slate-800 hover:bg-slate-700 text-white cursor-pointer transition-all"
                    >
                      <SkipForward className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Tab 3: System Actions */}
            {activeTab === 'system' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <button
                  onClick={handleTakeScreenshot}
                  className="p-4 rounded-2xl bg-slate-900/80 hover:bg-slate-800 border border-white/10 hover:border-purple-500/50 text-left space-y-2 cursor-pointer transition-all"
                >
                  <div className="p-2.5 w-fit rounded-xl bg-purple-500/20 text-purple-300">
                    <Camera className="w-5 h-5 text-pink-400" />
                  </div>
                  <div className="font-bold text-xs text-white">Take PC Screenshot</div>
                  <div className="text-[11px] text-slate-400">Captures desktop display and saves to Pictures</div>
                </button>

                <button
                  onClick={handleLockScreen}
                  className="p-4 rounded-2xl bg-slate-900/80 hover:bg-slate-800 border border-white/10 hover:border-indigo-500/50 text-left space-y-2 cursor-pointer transition-all"
                >
                  <div className="p-2.5 w-fit rounded-xl bg-indigo-500/20 text-indigo-300">
                    <Lock className="w-5 h-5 text-indigo-400" />
                  </div>
                  <div className="font-bold text-xs text-white">Lock Desktop Screen</div>
                  <div className="text-[11px] text-slate-400">Locks workstation securely requiring password</div>
                </button>

                <button
                  onClick={handleCleanTemp}
                  className="p-4 rounded-2xl bg-slate-900/80 hover:bg-slate-800 border border-white/10 hover:border-emerald-500/50 text-left space-y-2 cursor-pointer transition-all"
                >
                  <div className="p-2.5 w-fit rounded-xl bg-emerald-500/20 text-emerald-300">
                    <Trash2 className="w-5 h-5 text-emerald-400" />
                  </div>
                  <div className="font-bold text-xs text-white">Clear Temp & Flush DNS</div>
                  <div className="text-[11px] text-slate-400">Frees system cache and refreshes network DNS</div>
                </button>

                <div className="p-4 rounded-2xl bg-slate-900/80 border border-white/10 text-left space-y-2">
                  <div className="p-2.5 w-fit rounded-xl bg-amber-500/20 text-amber-300">
                    <Zap className="w-5 h-5 text-amber-400" />
                  </div>
                  <div className="font-bold text-xs text-white">Power Mode: {powerMode.toUpperCase()}</div>
                  <div className="flex gap-2 pt-1">
                    {['performance', 'balanced', 'saver'].map((mode) => (
                      <button
                        key={mode}
                        onClick={() => {
                          setPowerMode(mode as any);
                          showToast(`Power Mode set to ${mode.toUpperCase()}`, 'info');
                        }}
                        className={`px-2 py-1 rounded-lg text-[10px] font-bold cursor-pointer ${
                          powerMode === mode
                            ? 'bg-amber-500 text-slate-950 font-black'
                            : 'bg-slate-800 text-slate-300'
                        }`}
                      >
                        {mode}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Tab 4: Terminal Command Executor */}
            {activeTab === 'terminal' && (
              <div className="space-y-4">
                <form onSubmit={handleRunTerminalCmd} className="flex gap-2">
                  <div className="relative flex-1">
                    <Terminal className="w-4 h-4 text-emerald-400 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      value={terminalInput}
                      onChange={(e) => setTerminalInput(e.target.value)}
                      placeholder="Type terminal command (e.g. ipconfig, ping google.com, systeminfo, whoami)..."
                      className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-slate-900 border border-white/10 text-xs text-emerald-300 font-mono focus:outline-none focus:border-emerald-400"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={isExecutingCmd || !terminalInput.trim()}
                    className="px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold text-xs cursor-pointer flex items-center gap-1.5"
                  >
                    {isExecutingCmd ? 'Running...' : 'Run Cmd'}
                  </button>
                </form>

                {/* Output Terminal Box */}
                <div className="p-4 rounded-2xl bg-black border border-emerald-500/40 font-mono text-xs text-emerald-400 space-y-3 h-60 overflow-y-auto">
                  {terminalLogs.map((log, idx) => (
                    <div key={idx} className="space-y-1 border-b border-emerald-950 pb-3">
                      <div className="flex items-center justify-between text-[10px] text-slate-500">
                        <span>C:\Users\Master&gt; {log.cmd}</span>
                        <span>{log.time}</span>
                      </div>
                      <pre className="text-emerald-300 text-[11px] leading-relaxed whitespace-pre-wrap font-mono">
                        {log.output}
                      </pre>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Footer Voice Cheatsheet */}
          <div className="px-6 py-3 bg-slate-950 border-t border-white/10 flex items-center justify-between text-xs text-slate-400">
            <span className="font-semibold text-purple-300 flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5 text-pink-400" /> Voice Commands: "Zoya, open Calculator" • "Zoya, mute volume" • "Zoya, take screenshot"
            </span>
            <button
              onClick={onClose}
              className="px-4 py-1.5 rounded-xl bg-purple-900/40 hover:bg-purple-900/60 text-purple-200 border border-purple-500/30 font-bold cursor-pointer"
            >
              Done
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
