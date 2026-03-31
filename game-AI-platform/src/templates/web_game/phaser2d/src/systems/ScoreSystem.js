import EventBus from '../core/EventBus.js';
import GameState from '../core/GameState.js';
import { SCORE_PER_ENEMY, SCORE_PER_LEVEL } from '../core/Constants.js';

/**
 * ScoreSystem — listens to game events and updates GameState score.
 * Pure system: no rendering, only state mutations via GameState.
 */
export default class ScoreSystem {
  constructor() {
    this._unsubEnemy = EventBus.on('enemy:killed', () => {
      GameState.incrementScore(SCORE_PER_ENEMY);
    });
    this._unsubLevel = EventBus.on('level:complete', () => {
      GameState.incrementScore(SCORE_PER_LEVEL);
    });
  }

  destroy() {
    if (this._unsubEnemy) this._unsubEnemy();
    if (this._unsubLevel) this._unsubLevel();
  }
}
