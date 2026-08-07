import React from 'react';
import { motion } from 'motion/react';
import { Sparkles, Globe, Smile, Zap, Flame } from 'lucide-react';
import { QuickPrompt } from '../types';

interface PersonalityCardProps {
  onSelectPrompt: (promptText: string) => void;
}

const QUICK_PROMPTS: QuickPrompt[] = [
  {
    id: 'flirt-hot-take',
    label: 'Hot Take',
    text: "What's your hot take on human dating?",
    iconName: 'flame',
  },
  {
    id: 'open-youtube',
    label: 'Open YouTube',
    text: 'Open YouTube for me right now.',
    iconName: 'globe',
  },
  {
    id: 'confidence-boost',
    label: 'Hype Me Up',
    text: 'Give me a sassy, unhinged confidence boost!',
    iconName: 'zap',
  },
  {
    id: 'tease-me',
    label: 'Tease Me',
    text: 'Tease me like a close girlfriend talking casually.',
    iconName: 'smile',
  },
  {
    id: 'cheeky-secret',
    label: 'Secret',
    text: 'Tell me a juicy secret or a bold witty joke.',
    iconName: 'sparkles',
  },
];

export const PersonalityCard: React.FC<PersonalityCardProps> = ({ onSelectPrompt }) => {
  const getIcon = (iconName: string) => {
    switch (iconName) {
      case 'flame':
        return <Flame className="w-3.5 h-3.5 text-orange-400" />;
      case 'globe':
        return <Globe className="w-3.5 h-3.5 text-cyan-400" />;
      case 'zap':
        return <Zap className="w-3.5 h-3.5 text-amber-400" />;
      case 'smile':
        return <Smile className="w-3.5 h-3.5 text-pink-400" />;
      default:
        return <Sparkles className="w-3.5 h-3.5 text-purple-400" />;
    }
  };

  return (
    <div className="z-10 flex flex-wrap items-center justify-center gap-1.5 py-0.5">
      <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-cyan-400/80 mr-1 hidden sm:inline">
        Try saying:
      </span>
      {QUICK_PROMPTS.map((prompt, idx) => (
        <motion.button
          key={prompt.id}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: idx * 0.05 }}
          onClick={() => onSelectPrompt(prompt.text)}
          className="group flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-cyan-950/60 hover:bg-cyan-900/80 border border-cyan-500/30 hover:border-cyan-400 text-cyan-200 hover:text-white text-[10px] font-mono font-bold transition-all cursor-pointer shadow-sm"
        >
          {getIcon(prompt.iconName)}
          <span>"{prompt.label}"</span>
        </motion.button>
      ))}
    </div>
  );
};
