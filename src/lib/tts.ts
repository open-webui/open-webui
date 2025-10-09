// src/lib/tts.ts

export interface TTSOptions {
  volume?: number; // 0.0 to 1.0
  rate?: number;   // 0.1 to 10
  pitch?: number;  // 0 to 2
  voice?: string;
}

export function speakText(text: string, options: TTSOptions = {}) {
  const utter = new SpeechSynthesisUtterance(text);

  utter.volume = options.volume ?? 1.0;
  utter.rate = options.rate ?? 1.0;
  utter.pitch = options.pitch ?? 1.0;

   const voices = speechSynthesis.getVoices();
   if (options.voice) {
    const voice = voices.find((v: SpeechSynthesisVoice) => v.name === options.voice);
   if (voice) utter.voice = voice;
}
    speechSynthesis.speak(utter);
    utter.voice = voices.find(v => v.name === options.voice) || null;
    speechSynthesis.speak(utter);
    speechSynthesis.speak(utter);
    utter.voice = voices.find(v => v.name === options.voice) || null;
    speechSynthesis.speak(utter);
    speechSynthesis.speak(utter);
    utter.voice = voices.find(v => v.name === options.voice) || null;
    speechSynthesis.speak(utter);
}
