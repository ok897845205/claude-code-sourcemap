import EventBus from './EventBus.js';

const GameState = {
  score: 0,
  lives: 3,
  level: 1,
  isGameOver: false,
  isPaused: false,
  highScore: 0,
  playerPosition: { x: 0, y: 0, z: 0 },

  incrementScore(points) {
    this.score += points;
    if (this.score > this.highScore) this.highScore = this.score;
    EventBus.emit('score:changed', this.score);
  },

  loseLife() {
    this.lives -= 1;
    EventBus.emit('lives:changed', this.lives);
    if (this.lives <= 0) {
      this.isGameOver = true;
      EventBus.emit('game:over', { score: this.score });
    }
  },

  nextLevel() {
    this.level += 1;
    EventBus.emit('level:changed', this.level);
  },

  setPaused(paused) {
    this.isPaused = paused;
    EventBus.emit('game:paused', paused);
  },

  reset() {
    this.score = 0;
    this.lives = 3;
    this.level = 1;
    this.isGameOver = false;
    this.isPaused = false;
    this.playerPosition = { x: 0, y: 0, z: 0 };
    EventBus.emit('state:reset');
  },

  toJSON() {
    return {
      score: this.score,
      lives: this.lives,
      level: this.level,
      isGameOver: this.isGameOver,
      isPaused: this.isPaused,
      highScore: this.highScore,
      playerPosition: { ...this.playerPosition },
    };
  },
};

export default GameState;
