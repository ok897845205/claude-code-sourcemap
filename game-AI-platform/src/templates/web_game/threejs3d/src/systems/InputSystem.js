/**
 * InputSystem — polls keyboard state each frame.
 * Communicates events via EventBus for discrete actions.
 */
import EventBus from '../core/EventBus.js';

export default class InputSystem {
  constructor() {
    this._keys = {};
    window.addEventListener('keydown', e => {
      this._keys[e.code] = true;
    });
    window.addEventListener('keyup', e => {
      this._keys[e.code] = false;
    });
  }

  getState() {
    return {
      left: !!(this._keys['ArrowLeft'] || this._keys['KeyA']),
      right: !!(this._keys['ArrowRight'] || this._keys['KeyD']),
      forward: !!(this._keys['ArrowUp'] || this._keys['KeyW']),
      backward: !!(this._keys['ArrowDown'] || this._keys['KeyS']),
      jump: !!(this._keys['Space'] || this._keys['ArrowUp'] || this._keys['KeyW']),
    };
  }
}
