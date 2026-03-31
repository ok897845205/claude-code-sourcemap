/**
 * AudioManager — Web Audio API wrapper for game sound effects.
 *
 * Inspired by OpusGameLabs/game-creator (game-audio skill).
 * Uses the browser-native Web Audio API; no external dependencies required.
 *
 * Usage:
 *   import AudioManager from '../audio/AudioManager.js';
 *   import '../audio/sfx.js';  // registers all SFX
 *
 *   AudioManager.init();       // call once on first user interaction
 *   AudioManager.play('score');
 */

let _ctx = null;
const _sounds = {};

const AudioManager = {
  init() {
    if (_ctx) return;
    try {
      _ctx = new (window.AudioContext || window.webkitAudioContext)();
    } catch (e) {
      // Audio not supported
    }
  },

  resume() {
    if (_ctx && _ctx.state === 'suspended') {
      _ctx.resume().catch(() => {});
    }
  },

  register(name, fn) {
    _sounds[name] = fn;
  },

  /**
   * Play a registered sound by name.
   * Internally calls fn(audioContext) — fn must take exactly one AudioContext argument.
   * No-op if AudioManager is not initialised or sound is not registered.
   */
  play(name) {
    if (!_ctx) return;
    const fn = _sounds[name];
    if (!fn) return;
    try {
      this.resume();
      fn(_ctx);
    } catch (e) {
      // Ignore audio errors
    }
  },

  get context() {
    return _ctx;
  },
};

export default AudioManager;
