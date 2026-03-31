import {
  PLAYER_SPEED, PLAYER_JUMP_VELOCITY,
  COLOR_PLAYER,
  CANVAS_HEIGHT,
} from '../core/Constants.js';
import EventBus from '../core/EventBus.js';
import GameState from '../core/GameState.js';

/**
 * Player entity — wraps Phaser physics sprite.
 * Handles input and movement; communicates state changes via EventBus.
 */
export default class Player {
  constructor(scene, x, y) {
    this.scene = scene;
    this.sprite = scene.add.rectangle(x, y, 32, 48, COLOR_PLAYER);
    scene.physics.add.existing(this.sprite);
    this.sprite.body.setCollideWorldBounds(true);
    this._cursors = scene.input.keyboard.createCursorKeys();
    this._wasd = scene.input.keyboard.addKeys('W,A,S,D');
    this._onGround = false;
  }

  update(keyboard) {
    const body = this.sprite.body;
    const onGround = body.blocked.down;

    // Horizontal movement
    if (this._cursors.left.isDown || this._wasd.A.isDown) {
      body.setVelocityX(-PLAYER_SPEED);
    } else if (this._cursors.right.isDown || this._wasd.D.isDown) {
      body.setVelocityX(PLAYER_SPEED);
    } else {
      body.setVelocityX(0);
    }

    // Jump
    if ((this._cursors.up.isDown || this._wasd.W.isDown) && onGround) {
      body.setVelocityY(PLAYER_JUMP_VELOCITY);
      EventBus.emit('player:jumped');
    }

    this._onGround = onGround;
  }

  get x() { return this.sprite.x; }
  get y() { return this.sprite.y; }
  get isOnGround() { return this._onGround; }

  destroy() {
    this.sprite.destroy();
  }
}
