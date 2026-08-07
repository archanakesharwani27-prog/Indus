import React, { useState, useRef, useEffect } from 'react';
import {
  Camera,
  Monitor,
  X,
  Sparkles,
  Loader2,
  Scan,
  UserCheck,
  Shirt,
  Activity,
  FileText,
  Upload,
  RefreshCw,
  Eye,
  CheckCircle2,
  Brain,
  Play
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface VisionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onMemoryUpdate?: () => void;
  onThemeChange?: (theme: string) => void;
  showToast: (msg: string, type?: 'info' | 'error' | 'success') => void;
}

export const VisionModal: React.FC<VisionModalProps> = ({
  isOpen,
  onClose,
  onMemoryUpdate,
  onThemeChange,
  showToast,
}) => {
  const [activeTab, setActiveTab] = useState<'camera' | 'screen'>('camera');

  // Camera State
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [capturedCameraImage, setCapturedCameraImage] = useState<string | null>(null);

  // Screen State
  const [screenImage, setScreenImage] = useState<string | null>(null);

  // Analysis State
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<{
    reply: string;
    functionCalls?: Array<{ name: string; args: any }>;
  } | null>(null);

  const [customPrompt, setCustomPrompt] = useState('');

  // Start Live Camera stream when modal opens on Camera tab
  useEffect(() => {
    if (isOpen && activeTab === 'camera' && !capturedCameraImage) {
      startCamera();
    } else {
      stopCamera();
    }
    return () => {
      stopCamera();
    };
  }, [isOpen, activeTab]);

  const startCamera = async () => {
    setCameraError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        setIsCameraActive(true);
      }
    } catch (err: any) {
      console.error('Failed to access camera:', err);
      setCameraError('Camera access denied or unavailable. Please check permissions.');
      setIsCameraActive(false);
    }
  };

  const stopCamera = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach((track) => track.stop());
      videoRef.current.srcObject = null;
    }
    setIsCameraActive(false);
  };

  const captureCameraSnapshot = (): string | null => {
    if (!videoRef.current || !canvasRef.current) return null;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg', 0.85);
  };

  const handleAnalyzeCamera = async () => {
    const base64Img = captureCameraSnapshot();
    if (!base64Img) {
      showToast('Please enable camera or capture a frame first.', 'error');
      return;
    }

    setCapturedCameraImage(base64Img);
    setIsAnalyzing(true);
    setAnalysisResult(null);

    try {
      const res = await fetch('/api/vision-analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image: base64Img,
          mode: 'camera',
          prompt: customPrompt || 'Zoya, look at me through the camera! Identify who I am, what I am wearing, my expression, mood, and what I am doing in your witty style!',
        }),
      });

      const data = await res.json();
      if (data.success) {
        setAnalysisResult({ reply: data.reply, functionCalls: data.functionCalls });
        showToast('Zoya analyzed your camera feed!', 'success');

        // Check if Zoya called saveMemory or changeAuraTheme
        if (data.functionCalls) {
          for (const fc of data.functionCalls) {
            if (fc.name === 'saveMemory' && onMemoryUpdate) {
              onMemoryUpdate();
              showToast(`🧠 Zoya saved details about you to Memory Vault!`, 'info');
            } else if (fc.name === 'changeAuraTheme' && fc.args?.theme && onThemeChange) {
              onThemeChange(fc.args.theme);
            }
          }
        }
      } else {
        showToast(data.error || 'Failed to analyze camera image', 'error');
      }
    } catch (err) {
      console.error('Camera vision error:', err);
      showToast('Error sending image to Zoya Vision AI.', 'error');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Screen Capture using getDisplayMedia
  const handleCaptureScreen = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getDisplayMedia({
        video: { cursor: 'always' } as any,
        audio: false,
      });

      const video = document.createElement('video');
      video.srcObject = mediaStream;
      await video.play();

      // Small delay to ensure frame is loaded
      await new Promise((resolve) => setTimeout(resolve, 300));

      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth || 1280;
      canvas.height = video.videoHeight || 720;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
        setScreenImage(dataUrl);
      }

      // Stop media tracks
      mediaStream.getTracks().forEach((track) => track.stop());
    } catch (err: any) {
      console.error('Screen capture error:', err);
      showToast('Screen capture cancelled or unavailable.', 'info');
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const result = event.target?.result as string;
      if (result) {
        setScreenImage(result);
      }
    };
    reader.readAsDataURL(file);
  };

  const handleAnalyzeScreen = async () => {
    if (!screenImage) {
      showToast('Please capture your screen or upload a screenshot first.', 'error');
      return;
    }

    setIsAnalyzing(true);
    setAnalysisResult(null);

    try {
      const res = await fetch('/api/vision-analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image: screenImage,
          mode: 'screen',
          prompt: customPrompt || 'Zoya, analyze my screen! Read all visible text, explain images/videos or code on screen, and give a clear witty breakdown!',
        }),
      });

      const data = await res.json();
      if (data.success) {
        setAnalysisResult({ reply: data.reply, functionCalls: data.functionCalls });
        showToast('Screen analysis complete!', 'success');
      } else {
        showToast(data.error || 'Failed to analyze screen', 'error');
      }
    } catch (err) {
      console.error('Screen vision error:', err);
      showToast('Error analyzing screen screenshot.', 'error');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const resetCameraCapture = () => {
    setCapturedCameraImage(null);
    setAnalysisResult(null);
    startCamera();
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 10 }}
          className="relative w-full max-w-4xl max-h-[90vh] flex flex-col rounded-3xl bg-slate-950 border border-purple-500/30 text-white shadow-2xl overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-5 border-b border-white/10 bg-slate-900/50">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-2xl bg-purple-500/20 text-purple-300 border border-purple-500/40">
                <Eye className="w-5 h-5 animate-pulse" />
              </div>
              <div>
                <h2 className="text-lg font-bold flex items-center gap-2">
                  Zoya Vision & Screen Reader
                  <span className="px-2 py-0.5 text-[10px] uppercase tracking-wider rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30 font-semibold">
                    Multimodal AI
                  </span>
                </h2>
                <p className="text-xs text-slate-400">
                  Analyze face, clothing, emotions from Camera or read text, images & videos from Screen
                </p>
              </div>
            </div>

            <button
              onClick={onClose}
              className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation Tabs */}
          <div className="flex border-b border-white/10 bg-slate-900/30 px-6">
            <button
              onClick={() => {
                setActiveTab('camera');
                setAnalysisResult(null);
              }}
              className={`flex items-center gap-2 px-5 py-3 text-xs font-semibold border-b-2 transition-all cursor-pointer ${
                activeTab === 'camera'
                  ? 'border-purple-400 text-purple-300 bg-purple-500/10'
                  : 'border-transparent text-slate-400 hover:text-white'
              }`}
            >
              <Camera className="w-4 h-4" />
              Face & Outfit Camera Vision
            </button>

            <button
              onClick={() => {
                setActiveTab('screen');
                setAnalysisResult(null);
                stopCamera();
              }}
              className={`flex items-center gap-2 px-5 py-3 text-xs font-semibold border-b-2 transition-all cursor-pointer ${
                activeTab === 'screen'
                  ? 'border-cyan-400 text-cyan-300 bg-cyan-500/10'
                  : 'border-transparent text-slate-400 hover:text-white'
              }`}
            >
              <Monitor className="w-4 h-4" />
              Screen Reader & Analyzer
            </button>
          </div>

          {/* Hidden Canvas for Canvas Processing */}
          <canvas ref={canvasRef} className="hidden" />

          {/* Content Area */}
          <div className="flex-1 overflow-y-auto p-6 space-y-5">
            {activeTab === 'camera' ? (
              /* TAB 1: CAMERA VISION */
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Left: Camera Feed / Captured Image */}
                <div className="space-y-3">
                  <div className="relative rounded-2xl overflow-hidden bg-slate-900 border border-purple-500/30 aspect-video flex items-center justify-center shadow-inner">
                    {capturedCameraImage ? (
                      <img
                        src={capturedCameraImage}
                        alt="Captured Camera"
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <>
                        <video
                          ref={videoRef}
                          playsInline
                          muted
                          className={`w-full h-full object-cover ${!isCameraActive && 'hidden'}`}
                        />

                        {/* Scanner Animation Effect when Camera Active */}
                        {isCameraActive && (
                          <div className="absolute inset-0 pointer-events-none flex flex-col justify-between p-4 border-2 border-purple-400/40 rounded-2xl">
                            <div className="flex justify-between items-center text-[10px] text-purple-300 font-mono uppercase bg-black/40 px-2 py-1 rounded">
                              <span className="flex items-center gap-1">
                                <Scan className="w-3 h-3 text-purple-400 animate-spin" /> Live Face Target Box
                              </span>
                              <span>HD 720P</span>
                            </div>
                            <div className="w-full h-1 bg-gradient-to-r from-transparent via-purple-400 to-transparent animate-pulse" />
                          </div>
                        )}

                        {!isCameraActive && (
                          <div className="p-6 text-center space-y-3">
                            <Camera className="w-10 h-10 text-slate-600 mx-auto" />
                            <p className="text-xs text-slate-400">{cameraError || 'Camera is inactive'}</p>
                            <button
                              onClick={startCamera}
                              className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-xs font-semibold text-white transition-all cursor-pointer"
                            >
                              Enable Camera
                            </button>
                          </div>
                        )}
                      </>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2">
                    {capturedCameraImage ? (
                      <button
                        onClick={resetCameraCapture}
                        className="flex-1 py-2.5 rounded-xl bg-white/10 hover:bg-white/20 text-xs font-semibold flex items-center justify-center gap-2 cursor-pointer transition-all"
                      >
                        <RefreshCw className="w-4 h-4" /> Retake Photo
                      </button>
                    ) : (
                      <button
                        onClick={handleAnalyzeCamera}
                        disabled={!isCameraActive || isAnalyzing}
                        className="flex-1 py-3 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-40 text-xs font-bold text-white flex items-center justify-center gap-2 shadow-lg shadow-purple-900/50 cursor-pointer transition-all"
                      >
                        {isAnalyzing ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" /> Zoya is Analyzing Face & Outfit...
                          </>
                        ) : (
                          <>
                            <Sparkles className="w-4 h-4" /> Scan Face & Outfit
                          </>
                        )}
                      </button>
                    )}
                  </div>

                  {/* Custom Prompt Input */}
                  <div className="pt-2">
                    <label className="text-[11px] font-semibold text-slate-400 mb-1 block">
                      Custom Prompt for Camera (Optional)
                    </label>
                    <input
                      type="text"
                      value={customPrompt}
                      onChange={(e) => setCustomPrompt(e.target.value)}
                      placeholder="e.g. 'Pahchano main kaun hoon aur kapde kaise lag rhe hain?'"
                      className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-purple-400"
                    />
                  </div>
                </div>

                {/* Right: Analysis Results */}
                <div className="space-y-4">
                  <div className="p-4 rounded-2xl bg-purple-950/40 border border-purple-500/30 space-y-3 min-h-[300px]">
                    <div className="flex items-center justify-between border-b border-purple-500/20 pb-2">
                      <h3 className="text-xs font-bold text-purple-300 uppercase tracking-wider flex items-center gap-1.5">
                        <Brain className="w-4 h-4 text-purple-400" /> Zoya Analysis Result
                      </h3>
                      {analysisResult && (
                        <span className="text-[10px] text-emerald-400 font-semibold flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Complete
                        </span>
                      )}
                    </div>

                    {isAnalyzing ? (
                      <div className="py-12 text-center space-y-3">
                        <Loader2 className="w-8 h-8 text-purple-400 animate-spin mx-auto" />
                        <p className="text-xs text-purple-200 font-medium animate-pulse">
                          Zoya is observing your face, clothes, and posture...
                        </p>
                      </div>
                    ) : analysisResult ? (
                      <div className="space-y-3">
                        <div className="p-3 rounded-xl bg-slate-900/80 border border-purple-500/20 text-xs leading-relaxed text-slate-200 whitespace-pre-line">
                          {analysisResult.reply}
                        </div>

                        {/* Breakdown Badges */}
                        <div className="grid grid-cols-2 gap-2 text-[11px]">
                          <div className="p-2.5 rounded-xl bg-purple-900/30 border border-purple-500/20 flex items-center gap-2">
                            <UserCheck className="w-4 h-4 text-purple-300 shrink-0" />
                            <div>
                              <div className="text-[10px] text-purple-400 font-bold uppercase">Face/Mood</div>
                              <div className="text-slate-200 font-medium">Recognized</div>
                            </div>
                          </div>
                          <div className="p-2.5 rounded-xl bg-purple-900/30 border border-purple-500/20 flex items-center gap-2">
                            <Shirt className="w-4 h-4 text-purple-300 shrink-0" />
                            <div>
                              <div className="text-[10px] text-purple-400 font-bold uppercase">Outfit</div>
                              <div className="text-slate-200 font-medium">Analyzed</div>
                            </div>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="py-12 text-center text-slate-500 text-xs space-y-2">
                        <Scan className="w-8 h-8 text-slate-600 mx-auto" />
                        <p>Click "Scan Face & Outfit" to let Zoya identify you, your clothing, and activity!</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              /* TAB 2: SCREEN READER & ANALYZER */
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Left: Screen Capture Controls & Preview */}
                <div className="space-y-3">
                  <div className="relative rounded-2xl overflow-hidden bg-slate-900 border border-cyan-500/30 aspect-video flex items-center justify-center shadow-inner">
                    {screenImage ? (
                      <img src={screenImage} alt="Screen Preview" className="w-full h-full object-contain" />
                    ) : (
                      <div className="p-6 text-center space-y-3">
                        <Monitor className="w-10 h-10 text-cyan-500/60 mx-auto" />
                        <p className="text-xs text-slate-400">No screen screenshot captured yet</p>
                        <div className="flex items-center justify-center gap-2 pt-1">
                          <button
                            onClick={handleCaptureScreen}
                            className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-xs font-semibold text-white flex items-center gap-1.5 transition-all cursor-pointer shadow-md"
                          >
                            <Monitor className="w-4 h-4" /> Capture Live Screen
                          </button>
                          <label className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-xs font-semibold text-white flex items-center gap-1.5 transition-all cursor-pointer">
                            <Upload className="w-4 h-4" /> Upload Image
                            <input
                              type="file"
                              accept="image/*"
                              onChange={handleFileUpload}
                              className="hidden"
                            />
                          </label>
                        </div>
                      </div>
                    )}
                  </div>

                  {screenImage && (
                    <div className="flex gap-2">
                      <button
                        onClick={handleCaptureScreen}
                        className="py-2.5 px-3 rounded-xl bg-white/10 hover:bg-white/20 text-xs font-semibold flex items-center justify-center gap-1.5 cursor-pointer transition-all"
                      >
                        <RefreshCw className="w-3.5 h-3.5" /> Re-capture Screen
                      </button>
                      <button
                        onClick={handleAnalyzeScreen}
                        disabled={isAnalyzing}
                        className="flex-1 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 disabled:opacity-40 text-xs font-bold text-white flex items-center justify-center gap-2 shadow-lg shadow-cyan-900/50 cursor-pointer transition-all"
                      >
                        {isAnalyzing ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" /> Reading Screen Text & Content...
                          </>
                        ) : (
                          <>
                            <FileText className="w-4 h-4" /> Read & Analyze Screen
                          </>
                        )}
                      </button>
                    </div>
                  )}

                  {/* Prompt for Screen Analysis */}
                  <div className="pt-1">
                    <label className="text-[11px] font-semibold text-slate-400 mb-1 block">
                      Specific Screen Question (Optional)
                    </label>
                    <input
                      type="text"
                      value={customPrompt}
                      onChange={(e) => setCustomPrompt(e.target.value)}
                      placeholder="e.g. 'Read all paragraph text', 'Summarize this video frame', 'Explain this chart'"
                      className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400"
                    />
                  </div>
                </div>

                {/* Right: Screen Analysis Output */}
                <div className="space-y-4">
                  <div className="p-4 rounded-2xl bg-cyan-950/40 border border-cyan-500/30 space-y-3 min-h-[300px]">
                    <div className="flex items-center justify-between border-b border-cyan-500/20 pb-2">
                      <h3 className="text-xs font-bold text-cyan-300 uppercase tracking-wider flex items-center gap-1.5">
                        <FileText className="w-4 h-4 text-cyan-400" /> Screen Reading Breakdown
                      </h3>
                      {analysisResult && (
                        <span className="text-[10px] text-emerald-400 font-semibold flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Analyzed
                        </span>
                      )}
                    </div>

                    {isAnalyzing ? (
                      <div className="py-12 text-center space-y-3">
                        <Loader2 className="w-8 h-8 text-cyan-400 animate-spin mx-auto" />
                        <p className="text-xs text-cyan-200 font-medium animate-pulse">
                          Zoya is parsing text, images, and video frames from your screen...
                        </p>
                      </div>
                    ) : analysisResult ? (
                      <div className="p-3 rounded-xl bg-slate-900/80 border border-cyan-500/20 text-xs leading-relaxed text-slate-200 whitespace-pre-line max-h-80 overflow-y-auto">
                        {analysisResult.reply}
                      </div>
                    ) : (
                      <div className="py-12 text-center text-slate-500 text-xs space-y-2">
                        <Monitor className="w-8 h-8 text-slate-600 mx-auto" />
                        <p>Capture your screen to let Zoya read text, summarize articles, video frames, or code!</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
