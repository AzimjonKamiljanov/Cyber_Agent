/**
 * AudioWorklet Processor for Cyber Agent.
 * Downsamples mic input to 16,000 Hz mono PCM16 and streams chunks to main thread.
 */

class AudioCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.targetSampleRate = 16000;
    this.buffer = [];
    this.chunkSize = 640; // 40ms at 16kHz
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0]) return true;

    const inputChannel = input[0]; // mono channel
    const inputSampleRate = sampleRate; // global AudioWorklet sampleRate (e.g. 48000)

    // Linear resampling to 16kHz
    const ratio = inputSampleRate / this.targetSampleRate;
    let inIdx = 0;

    while (inIdx < inputChannel.length) {
      const sample = inputChannel[Math.floor(inIdx)];
      // Clamp and convert to 16-bit PCM integer
      const s = Math.max(-1, Math.min(1, sample));
      const pcm16 = s < 0 ? s * 0x8000 : s * 0x7fff;
      this.buffer.push(Math.round(pcm16));

      if (this.buffer.length >= this.chunkSize) {
        const int16Array = new Int16Array(this.buffer);
        this.port.postMessage(int16Array.buffer, [int16Array.buffer]);
        this.buffer = [];
      }

      inIdx += ratio;
    }

    return true;
  }
}

registerProcessor("audio-capture-processor", AudioCaptureProcessor);
