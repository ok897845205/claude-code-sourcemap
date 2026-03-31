/**
 * sfx.js — Procedural sound effect definitions for this game.
 *
 * The AI audio generation step replaces this file with game-specific SFX.
 * Uses Web Audio API — no external audio files required.
 */
import AudioManager from './AudioManager.js';

function tone(ctx, startHz, endHz, durationSec, type = 'square', volume = 0.18) {
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.type = type;
  osc.frequency.setValueAtTime(startHz, ctx.currentTime);
  if (endHz !== startHz) {
    osc.frequency.exponentialRampToValueAtTime(endHz, ctx.currentTime + durationSec);
  }
  gain.gain.setValueAtTime(volume, ctx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + durationSec);
  osc.start(ctx.currentTime);
  osc.stop(ctx.currentTime + durationSec + 0.01);
}

AudioManager.register('score',   (ctx) => tone(ctx, 440, 880, 0.1, 'square', 0.18));
AudioManager.register('death',   (ctx) => tone(ctx, 440, 110, 0.4, 'sawtooth', 0.22));
AudioManager.register('jump',    (ctx) => tone(ctx, 220, 440, 0.12, 'sine', 0.15));
AudioManager.register('hit',     (ctx) => tone(ctx, 300, 150, 0.15, 'square', 0.20));
AudioManager.register('levelup', (ctx) => {
  tone(ctx, 440, 880, 0.08, 'sine', 0.15);
  setTimeout(() => tone(ctx, 880, 1320, 0.08, 'sine', 0.15), 90);
  setTimeout(() => tone(ctx, 1320, 1760, 0.12, 'sine', 0.18), 180);
});
