import React, { useState } from "react";
import { speakText } from "@/lib/tts";

export default function TTSControls() {
  const [volume, setVolume] = useState(1);
  const [rate, setRate] = useState(1);
  const [pitch, setPitch] = useState(1);

  const testVoice = () => {
    speakText("Hello Janu! Your TTS controls are working.", {
      volume,
      rate,
      pitch,
    });
  };

  return (
    <div style={{ padding: "1rem", background: "#111", color: "#fff", borderRadius: "1rem" }}>
      <h3>🎤 Text-to-Speech Controls</h3>

      <label>Volume: {volume}</label>
      <input type="range" min="0" max="1" step="0.1"
             value={volume} onChange={(e) => setVolume(parseFloat(e.target.value))} />

      <label>Rate: {rate}</label>
      <input type="range" min="0.5" max="2" step="0.1"
             value={rate} onChange={(e) => setRate(parseFloat(e.target.value))} />

      <label>Pitch: {pitch}</label>
      <input type="range" min="0" max="2" step="0.1"
             value={pitch} onChange={(e) => setPitch(parseFloat(e.target.value))} />

      <button onClick={testVoice}>🔊 Test Voice</button>
    </div>
  );
}
