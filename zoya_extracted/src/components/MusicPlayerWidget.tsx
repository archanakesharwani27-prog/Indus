import React, { useState } from 'react';
import { Play, Pause, X, Music, Youtube, ExternalLink, Volume2, Sparkles, Radio } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface MusicPlayerWidgetProps {
  query: string;
  youtubeUrl?: string;
  onClose: () => void;
}

export const MusicPlayerWidget: React.FC<MusicPlayerWidgetProps> = ({
  query,
  youtubeUrl,
  onClose,
}) => {
  const [isPlaying, setIsPlaying] = useState(true);

  // Derive YouTube embed URL
  let embedUrl = `https://www.youtube.com/embed?listType=search&list=${encodeURIComponent(query)}&autoplay=1`;
  
  if (youtubeUrl) {
    // Extract video ID if full URL provided
    const match = youtubeUrl.match(/(?:v=|\/)([a-zA-Z0-9_-]{11})/);
    if (match && match[1]) {
      embedUrl = `https://www.youtube.com/embed/${match[1]}?autoplay=1&enablejsapi=1`;
    }
  }

  const directUrl = youtubeUrl || `https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 20, scale: 0.95 }}
        className="fixed bottom-6 right-6 z-50 w-full max-w-md bg-slate-950/95 border border-purple-500/40 rounded-3xl p-4 shadow-2xl backdrop-blur-xl text-white"
      >
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-white/10 mb-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-purple-500/20 border border-purple-500/40 text-purple-300 animate-pulse">
              <Music className="w-4 h-4 text-pink-400" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-bold text-white uppercase tracking-wider">
                  Zoya Music Player
                </span>
                <span className="px-1.5 py-0.2 rounded-full bg-red-500/20 text-red-400 text-[9px] font-extrabold border border-red-500/30 flex items-center gap-1">
                  <Youtube className="w-3 h-3" /> Playing Now
                </span>
              </div>
              <p className="text-[11px] text-slate-300 font-semibold truncate max-w-[220px]">
                "{query}"
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <a
              href={directUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="p-1.5 rounded-xl bg-white/10 hover:bg-white/20 text-slate-300 hover:text-white transition-all text-xs"
              title="Open on YouTube"
            >
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
            <button
              onClick={onClose}
              className="p-1.5 rounded-xl bg-white/10 hover:bg-rose-900/60 text-slate-400 hover:text-rose-200 transition-all cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Embedded YouTube Iframe Player */}
        <div className="relative rounded-2xl overflow-hidden aspect-video bg-black border border-white/10 shadow-inner">
          <iframe
            src={embedUrl}
            title={`Playing ${query}`}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
            className="w-full h-full border-0"
          />
        </div>

        {/* Footer info bar */}
        <div className="mt-3 flex items-center justify-between text-[11px] text-slate-400 px-1">
          <span className="flex items-center gap-1 text-purple-300 font-medium">
            <Radio className="w-3.5 h-3.5 text-pink-400 animate-pulse" /> Live YouTube Stream
          </span>
          <a
            href={directUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-pink-300 hover:underline font-semibold flex items-center gap-1"
          >
            Open in new window <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </motion.div>
    </AnimatePresence>
  );
};
