import Phaser from 'phaser';
import { SCENE_GAME_OVER, SCENE_GAME, CANVAS_WIDTH, CANVAS_HEIGHT, FONT_SIZE_LARGE, FONT_SIZE_MEDIUM } from '../core/Constants.js';
import GameState from '../core/GameState.js';

export default class GameOverScene extends Phaser.Scene {
  constructor() {
    super({ key: SCENE_GAME_OVER });
  }

  create() {
    const cx = CANVAS_WIDTH / 2;
    const cy = CANVAS_HEIGHT / 2;

    this.add.text(cx, cy - 80, 'GAME OVER', {
      fontSize: FONT_SIZE_LARGE, color: '#ff0000', fontStyle: 'bold',
    }).setOrigin(0.5);

    this.add.text(cx, cy, `Score: ${GameState.score}`, {
      fontSize: FONT_SIZE_MEDIUM, color: '#ffffff',
    }).setOrigin(0.5);

    this.add.text(cx, cy + 40, `Best: ${GameState.highScore}`, {
      fontSize: FONT_SIZE_MEDIUM, color: '#ffd700',
    }).setOrigin(0.5);

    const restartText = this.add.text(cx, cy + 100, 'Press SPACE or Click to Restart', {
      fontSize: FONT_SIZE_MEDIUM, color: '#00ff00',
    }).setOrigin(0.5);

    // Blink effect
    this.tweens.add({
      targets: restartText,
      alpha: 0,
      duration: 500,
      yoyo: true,
      repeat: -1,
    });

    this.input.keyboard.once('keydown-SPACE', () => this.scene.start(SCENE_GAME));
    this.input.on('pointerdown', () => this.scene.start(SCENE_GAME));
  }
}
