import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Smartphone,
  Laptop,
  Tablet,
  Radio,
  X,
  RefreshCw,
  Send,
  ExternalLink,
  ShieldCheck,
  Zap,
  Globe,
  BellRing,
  UserCheck,
  CheckCircle2,
  Lock,
} from 'lucide-react';
import { ConnectedDevice, RemoteCommand, AuraTheme } from '../types';

interface DeviceSyncModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentDeviceId: string;
  currentDeviceType: 'desktop' | 'mobile' | 'tablet';
  userEmail: string;
  onUpdateEmail: (newEmail: string) => void;
  onSelectTheme: (theme: AuraTheme) => void;
  onTriggerToast: (msg: string, type?: 'info' | 'error' | 'success') => void;
}

export const DeviceSyncModal: React.FC<DeviceSyncModalProps> = ({
  isOpen,
  onClose,
  currentDeviceId,
  currentDeviceType,
  userEmail,
  onUpdateEmail,
  onSelectTheme,
  onTriggerToast,
}) => {
  const [devices, setDevices] = useState<ConnectedDevice[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Email editing
  const [editingEmail, setEditingEmail] = useState(userEmail);
  const [isEmailSaved, setIsEmailSaved] = useState(false);

  // Send Remote Command Form
  const [targetDeviceType, setTargetDeviceType] = useState<'mobile' | 'desktop' | 'all'>('mobile');
  const [remoteAction, setRemoteAction] = useState<'openWebsite' | 'changeAuraTheme' | 'triggerAlert'>('openWebsite');
  const [remoteUrl, setRemoteUrl] = useState('');
  const [remoteTheme, setRemoteTheme] = useState<AuraTheme>('electric-violet');
  const [remoteAlertText, setRemoteAlertText] = useState('');
  const [isSending, setIsSending] = useState(false);

  // Recent commands feed
  const [recentCommands, setRecentCommands] = useState<RemoteCommand[]>([]);

  const fetchDevicesAndCommands = useCallback(async () => {
    setIsLoading(true);
    try {
      const [devRes, cmdRes] = await Promise.all([
        fetch('/api/devices'),
        fetch(`/api/devices/commands/${encodeURIComponent(currentDeviceId)}?deviceType=${currentDeviceType}`),
      ]);

      if (devRes.ok) {
        const devData = await devRes.json();
        if (devData.success && Array.isArray(devData.devices)) {
          setDevices(devData.devices);
        }
      }
      if (cmdRes.ok) {
        const cmdData = await cmdRes.json();
        if (cmdData.success && Array.isArray(cmdData.commands)) {
          setRecentCommands(cmdData.commands);
        }
      }
    } catch {
      // Ignore transient network errors during server restarts
    } finally {
      setIsLoading(false);
    }
  }, [currentDeviceId, currentDeviceType]);

  useEffect(() => {
    if (isOpen) {
      fetchDevicesAndCommands();
      const interval = setInterval(fetchDevicesAndCommands, 3000);
      return () => clearInterval(interval);
    }
  }, [isOpen, fetchDevicesAndCommands]);

  const handleSaveEmail = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingEmail.trim()) return;
    onUpdateEmail(editingEmail.trim());
    setIsEmailSaved(true);
    setTimeout(() => setIsEmailSaved(false), 2500);
  };

  const handleSendRemoteCommand = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSending(true);

    let payload: Record<string, unknown> = {};
    if (remoteAction === 'openWebsite') {
      if (!remoteUrl.trim()) return setIsSending(false);
      let formattedUrl = remoteUrl.trim();
      if (!formattedUrl.startsWith('http://') && !formattedUrl.startsWith('https://')) {
        formattedUrl = 'https://' + formattedUrl;
      }
      payload = { url: formattedUrl };
    } else if (remoteAction === 'changeAuraTheme') {
      payload = { theme: remoteTheme };
    } else if (remoteAction === 'triggerAlert') {
      if (!remoteAlertText.trim()) return setIsSending(false);
      payload = { message: remoteAlertText.trim() };
    }

    try {
      const res = await fetch('/api/devices/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fromDeviceId: currentDeviceId,
          fromDeviceName: currentDeviceType === 'desktop' ? 'PC / Desktop' : 'Mobile Device',
          targetType: targetDeviceType,
          action: remoteAction,
          payload,
        }),
      });

      const data = await res.json();
      if (data.success) {
        onTriggerToast(`📱 Remote command sent to ${targetDeviceType.toUpperCase()}!`, 'success');
        setRemoteUrl('');
        setRemoteAlertText('');
        fetchDevicesAndCommands();
      }
    } catch (err) {
      console.error('Failed to send remote command:', err);
    } finally {
      setIsSending(false);
    }
  };

  const getDeviceIcon = (type: string) => {
    if (type === 'mobile') return Smartphone;
    if (type === 'tablet') return Tablet;
    return Laptop;
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
                <div className="p-2.5 rounded-xl bg-cyan-950/60 border border-cyan-500/30 text-cyan-400">
                  <Radio className="w-6 h-6 animate-pulse" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-bold text-white tracking-tight">PC & Mobile Sync Hub</h3>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                      Cross-Device Active
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">
                    Connect Zoya on both PC and Mobile! Control your phone from PC or vice versa with shared long-term memory.
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

            {/* Account Profile Bar */}
            <div className="p-4 bg-white/[0.02] border-b border-white/5 px-5 flex flex-col sm:flex-row items-center justify-between gap-3">
              <form onSubmit={handleSaveEmail} className="flex items-center gap-2 w-full sm:w-auto">
                <div className="flex items-center gap-1.5 text-xs text-slate-400 shrink-0">
                  <UserCheck className="w-4 h-4 text-cyan-400" />
                  <span className="font-semibold text-white">Account:</span>
                </div>
                <input
                  type="email"
                  value={editingEmail}
                  onChange={(e) => setEditingEmail(e.target.value)}
                  className="px-3 py-1.5 rounded-xl bg-white/5 border border-white/10 text-xs text-cyan-200 focus:outline-none focus:border-cyan-400 w-full sm:w-64"
                  placeholder="enter email address"
                />
                <button
                  type="submit"
                  className="px-3 py-1.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs shrink-0 transition-colors"
                >
                  Save
                </button>
              </form>

              {isEmailSaved && (
                <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Account Synced!
                </span>
              )}
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-5 space-y-6">
              {/* Connected Devices Grid */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <ShieldCheck className="w-4 h-4 text-cyan-400" />
                    Connected Active Devices ({devices.length})
                  </h4>
                  <button
                    onClick={fetchDevicesAndCommands}
                    className="text-[11px] text-cyan-400 hover:underline flex items-center gap-1"
                  >
                    <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin' : ''}`} /> Refresh
                  </button>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {devices.map((dev) => {
                    const DeviceIcon = getDeviceIcon(dev.deviceType);
                    const isCurrent = dev.deviceId === currentDeviceId;

                    return (
                      <div
                        key={dev.deviceId}
                        className={`p-3.5 rounded-xl border transition-all ${
                          isCurrent
                            ? 'bg-cyan-950/40 border-cyan-500/50 shadow-lg shadow-cyan-950/50'
                            : 'bg-white/[0.03] border-white/10'
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-center gap-2.5">
                            <div className="p-2 rounded-lg bg-white/5 text-cyan-300">
                              <DeviceIcon className="w-5 h-5" />
                            </div>
                            <div>
                              <div className="flex items-center gap-1.5">
                                <span className="text-xs font-bold text-white">{dev.deviceName}</span>
                                {isCurrent && (
                                  <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                                    THIS DEVICE
                                  </span>
                                )}
                              </div>
                              <p className="text-[10px] text-slate-400 capitalize">{dev.deviceType} • {dev.browser}</p>
                            </div>
                          </div>

                          <div className="flex items-center gap-1 text-[10px] font-bold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded-full border border-emerald-500/30">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                            <span>ONLINE</span>
                          </div>
                        </div>

                        <div className="mt-3 pt-2 border-t border-white/5 flex items-center justify-between text-[10px] text-slate-400">
                          <span>User: {dev.userEmail}</span>
                          <span>Last active: {new Date(dev.lastSeen).toLocaleTimeString()}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Cross-Device Remote Control Form */}
              <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10 space-y-4">
                <div className="flex items-center gap-2">
                  <Zap className="w-4 h-4 text-amber-400" />
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                    Send Cross-Device Remote Command
                  </h4>
                </div>

                <form onSubmit={handleSendRemoteCommand} className="space-y-3">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {/* Target device selector */}
                    <div>
                      <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                        Target Device
                      </label>
                      <select
                        value={targetDeviceType}
                        onChange={(e) => setTargetDeviceType(e.target.value as 'mobile' | 'desktop' | 'all')}
                        className="w-full px-3 py-1.5 rounded-lg bg-slate-900 border border-white/10 text-xs text-white focus:outline-none focus:border-cyan-400"
                      >
                        <option value="mobile">📱 Mobile Phone</option>
                        <option value="desktop">💻 PC / Laptop</option>
                        <option value="all">🌐 Both PC & Mobile</option>
                      </select>
                    </div>

                    {/* Action selector */}
                    <div>
                      <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                        Action to Perform
                      </label>
                      <select
                        value={remoteAction}
                        onChange={(e) =>
                          setRemoteAction(e.target.value as 'openWebsite' | 'changeAuraTheme' | 'triggerAlert')
                        }
                        className="w-full px-3 py-1.5 rounded-lg bg-slate-900 border border-white/10 text-xs text-white focus:outline-none focus:border-cyan-400"
                      >
                        <option value="openWebsite">🌐 Open Website / App URL</option>
                        <option value="changeAuraTheme">🎨 Change Zoya Aura Theme</option>
                        <option value="triggerAlert">🔔 Ring Bell / Send Alert</option>
                      </select>
                    </div>
                  </div>

                  {/* Input details based on selected action */}
                  {remoteAction === 'openWebsite' && (
                    <div>
                      <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                        Website Address / App Link
                      </label>
                      <div className="relative">
                        <Globe className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
                        <input
                          type="text"
                          placeholder="e.g. youtube.com, spotify.com, google.com"
                          value={remoteUrl}
                          onChange={(e) => setRemoteUrl(e.target.value)}
                          required
                          className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-900 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400"
                        />
                      </div>
                    </div>
                  )}

                  {remoteAction === 'changeAuraTheme' && (
                    <div>
                      <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                        Remote Aura Theme
                      </label>
                      <select
                        value={remoteTheme}
                        onChange={(e) => setRemoteTheme(e.target.value as AuraTheme)}
                        className="w-full px-3 py-1.5 rounded-lg bg-slate-900 border border-white/10 text-xs text-white focus:outline-none focus:border-cyan-400"
                      >
                        <option value="sassy-pink">🌸 Sassy Pink</option>
                        <option value="neon-cyber">⚡ Neon Cyber</option>
                        <option value="electric-violet">💜 Electric Violet</option>
                        <option value="cosmic-emerald">🌿 Cosmic Emerald</option>
                        <option value="midnight-gold">✨ Midnight Gold</option>
                      </select>
                    </div>
                  )}

                  {remoteAction === 'triggerAlert' && (
                    <div>
                      <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                        Alert Banner Message
                      </label>
                      <div className="relative">
                        <BellRing className="w-4 h-4 absolute left-3 top-2.5 text-amber-400" />
                        <input
                          type="text"
                          placeholder="e.g. Hey! Zoya sent a reminder to your phone!"
                          value={remoteAlertText}
                          onChange={(e) => setRemoteAlertText(e.target.value)}
                          required
                          className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-900 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400"
                        />
                      </div>
                    </div>
                  )}

                  <div className="pt-1 flex justify-end">
                    <button
                      type="submit"
                      disabled={isSending}
                      className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs transition-colors shadow-lg flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                    >
                      <Send className="w-3.5 h-3.5" />
                      <span>{isSending ? 'Sending...' : 'Transmit Remote Command'}</span>
                    </button>
                  </div>
                </form>
              </div>

              {/* Voice Command Guidance Box */}
              <div className="p-3.5 rounded-xl bg-purple-950/40 border border-purple-500/30 text-xs text-purple-200 space-y-1">
                <p className="font-bold text-white flex items-center gap-1.5">
                  <span>💡 Voice Cross-Device Command Example:</span>
                </p>
                <p className="text-slate-300">
                  Say directly to Zoya: <span className="text-purple-300 italic font-semibold">"Zoya, open YouTube on my phone!"</span> or <span className="text-purple-300 italic font-semibold">"Zoya, change my phone theme to Neon Cyber!"</span> — Zoya will handle the cross-device command automatically!
                </p>
              </div>
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-white/10 bg-white/[0.02] flex items-center justify-between text-xs text-slate-400">
              <span className="flex items-center gap-1 text-[11px]">
                <Lock className="w-3.5 h-3.5 text-cyan-400" />
                End-to-End Encrypted Sync
              </span>

              <button
                onClick={onClose}
                className="px-4 py-1.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};
