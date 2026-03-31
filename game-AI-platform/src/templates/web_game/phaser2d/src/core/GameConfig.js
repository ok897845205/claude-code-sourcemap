import Phaser from 'phaser';
import { CANVAS_WIDTH, CANVAS_HEIGHT, PHYSICS_GRAVITY } from './Constants.js';
import BootScene from '../scenes/BootScene.js';
import GameScene from '../scenes/GameScene.js';
import GameOverScene from '../scenes/GameOverScene.js';

const GameConfig = {
  type: Phaser.AUTO,
  width: CANVAS_WIDTH,
  height: CANVAS_HEIGHT,
  backgroundColor: '#1a1a2e',
  physics: {
    default: 'arcade',
    arcade: {
      gravity: { y: PHYSICS_GRAVITY },
      debug: false,
    },
  },
  scene: [BootScene, GameScene, GameOverScene],
};

export default GameConfig;
