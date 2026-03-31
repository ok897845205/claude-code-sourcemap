/**
 * EventBus — singleton publish/subscribe hub.
 * All inter-module communication MUST go through EventBus.
 */
class EventBusClass {
  constructor() {
    this._listeners = {};
  }

  on(event, callback) {
    if (!this._listeners[event]) this._listeners[event] = [];
    this._listeners[event].push(callback);
    return () => this.off(event, callback);
  }

  off(event, callback) {
    if (!this._listeners[event]) return;
    this._listeners[event] = this._listeners[event].filter(cb => cb !== callback);
  }

  emit(event, ...args) {
    if (!this._listeners[event]) return;
    [...this._listeners[event]].forEach(cb => cb(...args));
  }

  once(event, callback) {
    const unsub = this.on(event, (...args) => { callback(...args); unsub(); });
  }

  clear() { this._listeners = {}; }
}

export const EventBus = new EventBusClass();
export default EventBus;
