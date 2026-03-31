import Phaser from 'phaser';
import {
  SCENE_GAME, SCENE_GAME_OVER,
  CANVAS_WIDTH, CANVAS_HEIGHT,
  COLOR_GROUND, COLOR_PLAYER, COLOR_ENEMY, COLOR_COIN,
  SCORE_PER_ENEMY, ENEMY_SPAWN_INTERVAL,
  FONT_SIZE_MEDIUM,
} from '../core/Constants.js';
import EventBus from '../core/EventBus.js';
import GameState from '../core/GameState.js';
import Player from '../entities/Player.js';
import ScoreSystem from '../systems/ScoreSystem.js';

export default class GameScene extends Phaser.Scene {
  constructor() {
    super({ key: SCENE_GAME });
    this._scoreSystem = null;
    this._player = null;
    this._enemies = null;
    this._scoreText = null;
    this._livesText = null;
    this._spawnTimer = null;
  }

  create() {
    GameState.reset();

    // Ground
    const ground = this.physics.add.staticGroup();
    const groundRect = this.add.rectangle(CANVAS_WIDTH / 2, CANVAS_HEIGHT - 16, CANVAS_WIDTH, 32, COLOR_GROUND);
    this.physics.add.existing(groundRect, true);
    ground.add(groundRect);

    // Player
    this._player = new Player(this, 100, CANVAS_HEIGHT - 100);

    // Enemies group
    this._enemies = this.physics.add.group();

    // Score system
    this._scoreSystem = new ScoreSystem();

    // UI
    this._scoreText = this.add.text(16, 16, 'Score: 0', { fontSize: FONT_SIZE_MEDIUM, color: '#ffffff' });
    this._livesText = this.add.text(16, 48, 'Lives: 3', { fontSize: FONT_SIZE_MEDIUM, color: '#ffffff' });

    // Collisions
    this.physics.add.collider(this._player.sprite, ground);
    this.physics.add.collider(this._enemies, ground);
    this.physics.add.overlap(
      this._player.sprite,
      this._enemies,
      this._onPlayerEnemyCollision,
      null,
      this
    );

    // Spawn timer
    this._spawnTimer = this.time.addEvent({
      delay: ENEMY_SPAWN_INTERVAL,
      callback: this._spawnEnemy,
      callbackScope: this,
      loop: true,
    });

    // EventBus subscriptions
    this._unsubScore = EventBus.on('score:changed', (score) => {
      this._scoreText.setText(`Score: ${score}`);
    });
    this._unsubLives = EventBus.on('lives:changed', (lives) => {
      this._livesText.setText(`Lives: ${lives}`);
    });
    this._unsubGameOver = EventBus.on('game:over', () => {
      this.scene.start(SCENE_GAME_OVER);
    });
  }

  update(time, delta) {
    if (GameState.isPaused || GameState.isGameOver) return;
    this._player.update(this.input.keyboard);
  }

  _spawnEnemy() {
    const x = CANVAS_WIDTH + 32;
    const y = CANVAS_HEIGHT - 80;
    const enemy = this.add.rectangle(x, y, 32, 32, COLOR_ENEMY);
    this.physics.add.existing(enemy);
    enemy.body.setVelocityX(-120);
    this._enemies.add(enemy);

    // Destroy when off-screen
    this.time.addEvent({
      delay: 8000,
      callback: () => { if (enemy && enemy.active) enemy.destroy(); },
    });
  }

  _onPlayerEnemyCollision(playerSprite, enemy) {
    enemy.destroy();
    GameState.loseLife();
  }

  shutdown() {
    if (this._unsubScore) this._unsubScore();
    if (this._unsubLives) this._unsubLives();
    if (this._unsubGameOver) this._unsubGameOver();
    if (this._spawnTimer) this._spawnTimer.destroy();
  }
}
