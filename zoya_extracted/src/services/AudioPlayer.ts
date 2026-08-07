export class AudioPlayer {
  private audioCtx: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private nextStartTime = 0;
  private activeSources: AudioBufferSourceNode[] = [];
  private onStateChange?: (isSpeaking: boolean) => void;
  private onVolumeChange?: (volume: number) => void;
  private isPlaying = false;
  private checkInterval: number | null = null;

  constructor(onStateChange?: (isSpeaking: boolean) => void, onVolumeChange?: (volume: number) => void) {
    this.onStateChange = onStateChange;
    this.onVolumeChange = onVolumeChange;
  }

  private initContext() {
    if (!this.audioCtx) {
      const AudioCtxClass =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      this.audioCtx = new AudioCtxClass({ sampleRate: 24000 });
      this.analyser = this.audioCtx.createAnalyser();
      this.analyser.fftSize = 256;
      this.analyser.connect(this.audioCtx.destination);
    }
    if (this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
  }

  playChunk(base64Pcm: string) {
    this.initContext();
    if (!this.audioCtx || !this.analyser) return;

    const binary = atob(base64Pcm);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }

    const float32Data = this.pcm16ToFloat32(bytes);
    if (float32Data.length === 0) return;

    const audioBuffer = this.audioCtx.createBuffer(1, float32Data.length, 24000);
    audioBuffer.getChannelData(0).set(float32Data);

    const source = this.audioCtx.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(this.analyser);

    const currentTime = this.audioCtx.currentTime;
    const startTime = Math.max(currentTime, this.nextStartTime);
    source.start(startTime);
    this.nextStartTime = startTime + audioBuffer.duration;

    this.activeSources.push(source);

    if (!this.isPlaying) {
      this.isPlaying = true;
      if (this.onStateChange) this.onStateChange(true);
      this.startVolumeMonitoring();
    }

    source.onended = () => {
      const idx = this.activeSources.indexOf(source);
      if (idx !== -1) {
        this.activeSources.splice(idx, 1);
      }
      if (this.activeSources.length === 0) {
        this.isPlaying = false;
        if (this.onStateChange) this.onStateChange(false);
        this.stopVolumeMonitoring();
      }
    };
  }

  private startVolumeMonitoring() {
    if (this.checkInterval) return;
    this.checkInterval = window.setInterval(() => {
      if (!this.analyser || !this.onVolumeChange) return;
      const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
      this.analyser.getByteFrequencyData(dataArray);
      let sum = 0;
      for (let i = 0; i < dataArray.length; i++) {
        sum += dataArray[i];
      }
      const avg = sum / dataArray.length;
      this.onVolumeChange(Math.min(1, avg / 128));
    }, 50);
  }

  private stopVolumeMonitoring() {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
    }
    if (this.onVolumeChange) {
      this.onVolumeChange(0);
    }
  }

  stopAndClear() {
    this.activeSources.forEach((source) => {
      try {
        source.stop();
        source.disconnect();
      } catch {
        // Source already ended
      }
    });
    this.activeSources = [];
    if (this.audioCtx) {
      this.nextStartTime = this.audioCtx.currentTime;
    }
    if (this.isPlaying) {
      this.isPlaying = false;
      if (this.onStateChange) this.onStateChange(false);
      this.stopVolumeMonitoring();
    }
  }

  getAnalyser(): AnalyserNode | null {
    return this.analyser;
  }

  private pcm16ToFloat32(bytes: Uint8Array): Float32Array {
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    const numSamples = Math.floor(bytes.byteLength / 2);
    const float32 = new Float32Array(numSamples);
    for (let i = 0; i < numSamples; i++) {
      const int16 = view.getInt16(i * 2, true);
      float32[i] = int16 < 0 ? int16 / 32768 : int16 / 32767;
    }
    return float32;
  }

  destroy() {
    this.stopAndClear();
    if (this.audioCtx) {
      this.audioCtx.close();
      this.audioCtx = null;
    }
  }
}
