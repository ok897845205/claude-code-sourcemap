/**
 * AudioManager — Web Audio API wrapper for game sound effects.
 *
 * Inspired by OpusGameLabs/game-creator (game-audio skill).
 * Uses the browser-native Web Audio API; no external dependencies required.
 *
 * Usage:
 *   import AudioManager from '../audio/AudioManager.js';
 *   import '../audio/sfx.js';  // registers all SFX via AudioManager.register()
 *
 *   // Call once on first user interaction (required by browser autoplay policy):
 *   AudioManager.init();
 *
 *   // Play a registered sound:
 *   AudioManager.play('score');
 *   AudioManager.play('death');
 */

let _ctx = null;
const _sounds = {};

const AudioManager = {
  /**
   * Initialise the Web Audio context.
   * Must be called from a user interaction handler (click, keydown, etc.)
   * to satisfy browser autoplay policies.
   */
  init() {
    if (_ctx) return;
    try {
      _ctx = new (window.AudioContext || window.webkitAudioContext)();
    } catch (e) {
      // Audio not supported — silently continue
    }
  },

  /** Resume a suspended context (e.g. after tab switch). */
  resume() {
    if (_ctx && _ctx.state === 'suspended') {
      _ctx.resume().catch(() => {});
    }
  },

  /**
   * Register a named sound effect.
   * CONTRACT: `fn` must accept exactly one argument — the AudioContext — and play
   * a sound immediately using that context. Example:
   *   AudioManager.register('score', (ctx) => {
   *     const osc = ctx.createOscillator(); ... osc.start(); osc.stop(...);
   *   });
   * @param {string} name - Sound identifier, e.g. 'score', 'death', 'jump'
   * @param {function(AudioContext): void} fn - Function that plays the sound
   */
  register(name, fn) {
    _sounds[name] = fn;
  },

  /**
   * Play a registered sound by name.
   * Internally calls fn(audioContext) — fn must take exactly one AudioContext argument.
   * No-op if AudioManager is not initialised or sound is not registered.
   * @param {string} name
   */
  play(name) {
    if (!_ctx) return;
    const fn = _sounds[name];
    if (!fn) return;
    try {
      this.resume();
      fn(_ctx);
    } catch (e) {
      // Ignore audio playback errors
    }
  },

  /** Access the raw AudioContext (advanced use). */
  get context() {
    return _ctx;
  },
};

export default AudioManager;
