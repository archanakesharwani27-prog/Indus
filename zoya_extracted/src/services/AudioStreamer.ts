export class AudioStreamer {
  private audioCtx: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private processor: ScriptProcessorNode | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private isMuted = false;
  private onAudioChunk: (base64Pcm: string) => void;
  private onVolumeChange?: (volume: number) => void;

  constructor(onAudioChunk: (base64Pcm: string) => void, onVolumeChange?: (volume: number) => void) {
    this.onAudioChunk = onAudioChunk;
    this.onVolumeChange = onVolumeChange;
  }

  async start(): Promise<void> {
    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      const AudioCtxClass =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      this.audioCtx = new AudioCtxClass();

      if (this.audioCtx.state === 'suspended') {
        await this.audioCtx.resume();
      }

      const sampleRate = this.audioCtx.sampleRate;
      this.source = this.audioCtx.createMediaStreamSource(this.mediaStream);
      this.processor = this.audioCtx.createScriptProcessor(2048, 1, 1);

      this.processor.onaudioprocess = (e: AudioProcessingEvent) => {
        if (this.isMuted) return;

        const inputData = e.inputBuffer.getChannelData(0);

        // Calculate RMS volume for visualizer
        let sum = 0;
        for (let i = 0; i < inputData.length; i++) {
          sum += inputData[i] * inputData[i];
        }
        const rms = Math.sqrt(sum / inputData.length);
        if (this.onVolumeChange) {
          this.onVolumeChange(Math.min(1, rms * 4));
        }

        const pcm16Data = this.resampleAndConvertToPCM16(inputData, sampleRate, 16000);
        if (pcm16Data.byteLength > 0) {
          const base64 = this.arrayBufferToBase64(pcm16Data);
          this.onAudioChunk(base64);
        }
      };

      this.source.connect(this.processor);
      this.processor.connect(this.audioCtx.destination);
    } catch (err) {
      console.error('Failed to access microphone audio stream:', err);
      throw err;
    }
  }

  setMuted(muted: boolean) {
    this.isMuted = muted;
  }

  private resampleAndConvertToPCM16(
    float32Array: Float32Array,
    inSampleRate: number,
    outSampleRate: number
  ): ArrayBuffer {
    let samples: Float32Array;
    if (inSampleRate === outSampleRate) {
      samples = float32Array;
    } else {
      const ratio = inSampleRate / outSampleRate;
      const newLength = Math.round(float32Array.length / ratio);
      samples = new Float32Array(newLength);
      for (let i = 0; i < newLength; i++) {
        const originIndex = i * ratio;
        const indexFloor = Math.floor(originIndex);
        const indexCeil = Math.min(float32Array.length - 1, Math.ceil(originIndex));
        const t = originIndex - indexFloor;
        samples[i] = float32Array[indexFloor] * (1 - t) + float32Array[indexCeil] * t;
      }
    }

    const buffer = new ArrayBuffer(samples.length * 2);
    const view = new DataView(buffer);
    for (let i = 0; i < samples.length; i++) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }
    return buffer;
  }

  private arrayBufferToBase64(buffer: ArrayBuffer): string {
    let binary = '';
    const bytes = new Uint8Array(buffer);
    const len = bytes.byteLength;
    for (let i = 0; i < len; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }

  stop() {
    if (this.processor && this.source) {
      this.source.disconnect();
      this.processor.disconnect();
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
    }
    if (this.audioCtx) {
      this.audioCtx.close();
    }
    this.processor = null;
    this.source = null;
    this.mediaStream = null;
    this.audioCtx = null;
  }
}
