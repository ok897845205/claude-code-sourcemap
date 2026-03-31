import Phaser from 'phaser';
import { SCENE_BOOT, SCENE_GAME, COLOR_UI_TEXT, FONT_SIZE_LARGE } from '../core/Constants.js';

export default class BootScene extends Phaser.Scene {
  constructor() {
    super({ key: SCENE_BOOT });
  }

  preload() {
    // Preload assets here
    this.load.on('progress', (value) => {
      if (this._progressText) {
        this._progressText.setText(`Loading... ${Math.floor(value * 100)}%`);
      }
    });
  }

  create() {
    this._progressText = this.add.text(
      this.cameras.main.width / 2,
      this.cameras.main.height / 2,
      'Loading...',
      { fontSize: FONT_SIZE_LARGE, color: '#ffffff' }
    ).setOrigin(0.5);

    this.scene.start(SCENE_GAME);
  }
}
