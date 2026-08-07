import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Phone,
  PhoneOff,
  Volume2,
  VolumeX,
  MessageSquare,
  User,
  ShieldAlert,
  Mic,
  MicOff,
  Check,
  X,
  Sparkles
} from 'lucide-react';

export interface CallerInfo {
  id: string;
  name: string;
  number: string;
  relation?: string;
  avatarUrl?: string;
  isRinging: boolean;
  isConnected: boolean;
  callDuration?: number;
  isSpam?: boolean;
  isUnknown?: boolean;
}

interface IncomingCallModalProps {
  call: CallerInfo | null;
  onAccept: () => void;
  onDecline: (reason?: string) => void;
  onEndCall: () => void;
  autoAnnounceEnabled: boolean;
  onToggleAutoAnnounce: () => void;
  userName?: string;
}

const ZOYA_SPAM_QUIPS = [
  "Spam call neutralized! Zoya's shield saved your time.",
  "Telemarketer intercepted! Back to your peaceful flow.",
  "Spam call declined silently. Your phone remains serene!",
];

const ZOYA_UNKNOWN_QUIPS = [
  "Unknown contact auto-declined. Zoya VIP bouncer on duty!",
  "Unrecognized call rejected. Life is too short for unknown callers!",
  "Unknown number blocked! Ask them to text you first.",
];

export const IncomingCallModal: React.FC<IncomingCallModalProps> = ({
  call,
  onAccept,
  onDecline,
  onEndCall,
  autoAnnounceEnabled,
  onToggleAutoAnnounce,
  userName = 'User',
}) => {
  const [isMuted, setIsMuted] = useState(false);
  const [isSpeakerOn, setIsSpeakerOn] = useState(true);
  const [showQuickReplies, setShowQuickReplies] = useState(false);
  const [callTimer, setCallTimer] = useState(0);

  // Auto-decline settings
  const [autoDeclineSpam, setAutoDeclineSpam] = useState(true);
  const [autoDeclineUnknown, setAutoDeclineUnknown] = useState(false);
  const [autoDeclinedQuip, setAutoDeclinedQuip] = useState<string | null>(null);

  const announcementSpokenRef = useRef(false);
  const autoDeclineTimerRef = useRef<any>(null);

  // Determine if current call is spam or unknown
  const isSpamCall =
    call?.isSpam ||
    call?.name.toLowerCase().includes('spam') ||
    call?.relation?.toLowerCase().includes('spam') ||
    call?.relation?.toLowerCase().includes('telemarketer');

  const isUnknownCall =
    call?.isUnknown ||
    call?.name.toLowerCase().includes('unknown') ||
    call?.relation?.toLowerCase().includes('unknown') ||
    call?.relation?.toLowerCase().includes('spam/unknown');

  // Check auto-decline on incoming call
  useEffect(() => {
    if (call && call.isRinging && !call.isConnected) {
      const shouldDeclineSpam = isSpamCall && autoDeclineSpam;
      const shouldDeclineUnknown = isUnknownCall && autoDeclineUnknown;

      if (shouldDeclineSpam || shouldDeclineUnknown) {
        const quips = shouldDeclineSpam ? ZOYA_SPAM_QUIPS : ZOYA_UNKNOWN_QUIPS;
        const randomQuip = quips[Math.floor(Math.random() * quips.length)];
        setAutoDeclinedQuip(randomQuip);

        // Speak quip out loud
        if ('speechSynthesis' in window) {
          window.speechSynthesis.cancel();
          const utterance = new SpeechSynthesisUtterance(`Zoya Shield: ${randomQuip}`);
          utterance.rate = 1.0;
          utterance.pitch = 1.1;
          window.speechSynthesis.speak(utterance);
        }

        // Auto decline after 1.8 seconds showing the shield animation
        autoDeclineTimerRef.current = setTimeout(() => {
          onDecline(`Auto-declined: ${randomQuip}`);
          setAutoDeclinedQuip(null);
        }, 1800);

        return () => {
          if (autoDeclineTimerRef.current) clearTimeout(autoDeclineTimerRef.current);
        };
      }
    } else {
      setAutoDeclinedQuip(null);
    }
  }, [call, autoDeclineSpam, autoDeclineUnknown, isSpamCall, isUnknownCall, onDecline]);

  // Announce caller name out loud via browser speech synthesis when a call arrives (if not auto-declined)
  useEffect(() => {
    if (call && call.isRinging && !call.isConnected && !autoDeclinedQuip) {
      if (!announcementSpokenRef.current && 'speechSynthesis' in window) {
        announcementSpokenRef.current = true;
        window.speechSynthesis.cancel(); // stop any current speech

        const announcementText = call.relation
          ? `${userName}, ${call.name} ka phone aa raha hai. Call pick karein ya decline karein?`
          : `${userName}, ${call.name} is calling you. Accept or decline the call?`;

        const utterance = new SpeechSynthesisUtterance(announcementText);
        utterance.rate = 0.95;
        utterance.pitch = 1.1;
        // Try to pick a female Hindi or English voice
        const voices = window.speechSynthesis.getVoices();
        const preferredVoice = voices.find(
          (v) => v.lang.includes('hi') || v.lang.includes('IN') || v.name.toLowerCase().includes('zira') || v.name.toLowerCase().includes('google')
        );
        if (preferredVoice) utterance.voice = preferredVoice;

        window.speechSynthesis.speak(utterance);
      }
    } else {
      announcementSpokenRef.current = false;
    }
  }, [call, userName, autoDeclinedQuip]);

  // Call duration timer when connected
  useEffect(() => {
    let interval: any = null;
    if (call && call.isConnected) {
      interval = setInterval(() => {
        setCallTimer((prev) => prev + 1);
      }, 1000);
    } else {
      setCallTimer(0);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [call?.isConnected]);

  if (!call || (!call.isRinging && !call.isConnected)) return null;

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const handleSpeechAction = (text: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.0;
      window.speechSynthesis.speak(utterance);
    }
  };

  const quickReplies = [
    'Main abhi busy hu, baad me call karta hu.',
    'I am in a meeting, call back soon.',
    'Can you text me?',
    'Driving right now, will call later.',
  ];

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
        <motion.div
          initial={{ scale: 0.85, opacity: 0, y: 30 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.85, opacity: 0, y: 30 }}
          className="relative w-full max-w-sm rounded-3xl bg-gradient-to-b from-slate-900 via-slate-950 to-black border border-purple-500/30 p-6 text-white shadow-2xl flex flex-col items-center text-center overflow-hidden"
        >
          {/* Ambient Glowing Ripples if Ringing */}
          {call.isRinging && !call.isConnected && (
            <div className="absolute top-12 w-48 h-48 rounded-full bg-purple-500/20 animate-ping -z-0" />
          )}

          {/* Top Status Header & Shield Toggles */}
          <div className="z-10 flex flex-col gap-2 w-full mb-4">
            <div className="flex items-center justify-between w-full text-xs text-slate-400">
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/5 border border-white/10 text-purple-300 font-semibold">
                <Sparkles className="w-3 h-3 text-purple-400" /> ZOYA Caller ID
              </span>

              <button
                onClick={onToggleAutoAnnounce}
                title="Toggle Read Caller Name Aloud"
                className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold border transition-colors cursor-pointer ${
                  autoAnnounceEnabled
                    ? 'bg-emerald-950/80 border-emerald-500/50 text-emerald-300'
                    : 'bg-slate-900 border-white/10 text-slate-400'
                }`}
              >
                <Volume2 className="w-3 h-3" />
                {autoAnnounceEnabled ? 'Read Aloud ON' : 'Read Aloud OFF'}
              </button>
            </div>

            {/* Quick Auto-Decline Shield Toggles */}
            <div className="flex items-center justify-between gap-1.5 p-1.5 rounded-xl bg-slate-900/90 border border-white/10 text-[10px]">
              <button
                onClick={() => setAutoDeclineSpam(!autoDeclineSpam)}
                className={`flex-1 flex items-center justify-center gap-1 py-1 px-2 rounded-lg font-semibold transition-colors cursor-pointer ${
                  autoDeclineSpam
                    ? 'bg-rose-950/90 text-rose-300 border border-rose-500/40'
                    : 'bg-slate-950 text-slate-500 border border-transparent'
                }`}
              >
                <ShieldAlert className="w-3 h-3 text-rose-400" />
                Auto-Block Spam
              </button>

              <button
                onClick={() => setAutoDeclineUnknown(!autoDeclineUnknown)}
                className={`flex-1 flex items-center justify-center gap-1 py-1 px-2 rounded-lg font-semibold transition-colors cursor-pointer ${
                  autoDeclineUnknown
                    ? 'bg-amber-950/90 text-amber-300 border border-amber-500/40'
                    : 'bg-slate-950 text-slate-500 border border-transparent'
                }`}
              >
                <User className="w-3 h-3 text-amber-400" />
                Block Unknowns
              </button>
            </div>
          </div>

          {/* Auto-Declined Quip Banner */}
          {autoDeclinedQuip ? (
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="z-10 w-full my-2 p-3.5 rounded-2xl bg-rose-950/90 border border-rose-500/50 text-rose-200 shadow-lg text-xs flex flex-col items-center gap-1.5"
            >
              <div className="flex items-center gap-1.5 text-rose-300 font-extrabold uppercase tracking-wide">
                <ShieldAlert className="w-4 h-4 animate-bounce text-rose-400" />
                Zoya Call Shield Triggered
              </div>
              <p className="italic font-medium text-center text-white">"{autoDeclinedQuip}"</p>
              <span className="text-[10px] text-rose-400 font-bold">Auto-Declining Call...</span>
            </motion.div>
          ) : null}

          {/* Caller Avatar */}
          <div className="relative z-10 my-2">
            <div className="w-24 h-24 rounded-full bg-gradient-to-tr from-purple-600 to-pink-500 p-1 shadow-xl shadow-purple-900/50 flex items-center justify-center">
              <div className="w-full h-full rounded-full bg-slate-950 flex items-center justify-center overflow-hidden">
                {call.avatarUrl ? (
                  <img src={call.avatarUrl} alt={call.name} className="w-full h-full object-cover" />
                ) : (
                  <User className="w-10 h-10 text-purple-300" />
                )}
              </div>
            </div>

            {call.isRinging && !call.isConnected && (
              <span className="absolute -bottom-1 -right-1 flex h-6 w-6">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-6 w-6 bg-emerald-500 items-center justify-center text-white">
                  <Phone className="w-3 h-3 animate-bounce" />
                </span>
              </span>
            )}
          </div>

          {/* Caller Name & Relation Details */}
          <div className="z-10 my-3">
            <h3 className="text-xl font-extrabold text-white tracking-wide">{call.name}</h3>
            {call.relation && (
              <span className="inline-block mt-1 px-2.5 py-0.5 rounded-full bg-purple-500/20 text-purple-300 text-[11px] font-bold border border-purple-500/30">
                {call.relation}
              </span>
            )}
            <p className="text-xs text-slate-400 mt-1 font-mono">{call.number}</p>

            {/* Call State Message */}
            <p className="text-xs font-semibold mt-3 text-pink-400 animate-pulse">
              {call.isConnected
                ? `Call Connected (${formatTime(callTimer)})`
                : `Incoming Call... Saying "Accept" or "Decline"`}
            </p>
          </div>

          {/* Connected Call Controls */}
          {call.isConnected ? (
            <div className="z-10 w-full mt-4 space-y-4">
              <div className="flex items-center justify-around bg-slate-900/80 p-3 rounded-2xl border border-white/10">
                <button
                  onClick={() => setIsMuted(!isMuted)}
                  className={`p-3 rounded-xl transition-colors cursor-pointer ${
                    isMuted ? 'bg-rose-600 text-white' : 'bg-slate-800 text-slate-300 hover:text-white'
                  }`}
                >
                  {isMuted ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
                </button>

                <button
                  onClick={() => setIsSpeakerOn(!isSpeakerOn)}
                  className={`p-3 rounded-xl transition-colors cursor-pointer ${
                    isSpeakerOn ? 'bg-purple-600 text-white' : 'bg-slate-800 text-slate-300 hover:text-white'
                  }`}
                >
                  {isSpeakerOn ? <Volume2 className="w-5 h-5" /> : <VolumeX className="w-5 h-5" />}
                </button>

                <button
                  onClick={() => handleSpeechAction('Connecting to Zoya assistant background...')}
                  className="p-3 rounded-xl bg-slate-800 text-purple-300 hover:text-white cursor-pointer"
                >
                  <Sparkles className="w-5 h-5" />
                </button>
              </div>

              <button
                onClick={() => {
                  handleSpeechAction('Call ended');
                  onEndCall();
                }}
                className="w-full py-3.5 rounded-2xl bg-rose-600 hover:bg-rose-500 text-white font-extrabold flex items-center justify-center gap-2 shadow-lg shadow-rose-900/40 cursor-pointer transition-all"
              >
                <PhoneOff className="w-5 h-5" /> End Call
              </button>
            </div>
          ) : (
            /* Ringing Actions: Accept / Decline / Quick Reply */
            <div className="z-10 w-full mt-4 space-y-3">
              <div className="flex items-center justify-around gap-4 w-full">
                {/* Decline Button */}
                <button
                  onClick={() => {
                    handleSpeechAction('Call declined');
                    onDecline();
                  }}
                  className="flex-1 py-3.5 rounded-2xl bg-rose-600 hover:bg-rose-500 text-white font-extrabold flex items-center justify-center gap-2 shadow-lg shadow-rose-950/50 cursor-pointer transition-all active:scale-95"
                >
                  <PhoneOff className="w-5 h-5" /> Decline
                </button>

                {/* Accept Button */}
                <button
                  onClick={() => {
                    handleSpeechAction(`Call accepted with ${call.name}`);
                    onAccept();
                  }}
                  className="flex-1 py-3.5 rounded-2xl bg-emerald-600 hover:bg-emerald-500 text-white font-extrabold flex items-center justify-center gap-2 shadow-lg shadow-emerald-950/50 cursor-pointer transition-all active:scale-95 animate-bounce-subtle"
                >
                  <Phone className="w-5 h-5" /> Accept
                </button>
              </div>

              {/* Quick Reply Button Toggle */}
              <button
                onClick={() => setShowQuickReplies(!showQuickReplies)}
                className="text-xs text-slate-400 hover:text-purple-300 flex items-center justify-center gap-1.5 mx-auto pt-1 cursor-pointer"
              >
                <MessageSquare className="w-3.5 h-3.5" />
                {showQuickReplies ? 'Hide Quick Replies' : 'Send Quick Decline SMS'}
              </button>

              {showQuickReplies && (
                <div className="space-y-1.5 pt-2 border-t border-white/10 text-left">
                  {quickReplies.map((reply, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        handleSpeechAction(`Declined call and sent message: ${reply}`);
                        onDecline(reply);
                      }}
                      className="w-full p-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-[11px] text-slate-300 border border-white/5 hover:border-purple-500/40 text-left transition-colors cursor-pointer"
                    >
                      "{reply}"
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          <p className="z-10 text-[10px] text-slate-500 mt-4">
            Tip: You can say <span className="text-purple-300 font-semibold">"Zoya call pick kar lo"</span> or <span className="text-purple-300 font-semibold">"Call decline kar do"</span>!
          </p>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
