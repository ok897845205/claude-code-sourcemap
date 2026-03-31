import * as THREE from 'three';
import { COLOR_PLAYER, PLAYER_SPEED, PLAYER_JUMP_FORCE, GRAVITY, FLOOR_Y } from '../core/Constants.js';
import EventBus from '../core/EventBus.js';

export default class Player {
  constructor(scene, position) {
    const geo = new THREE.BoxGeometry(1, 2, 1);
    const mat = new THREE.MeshLambertMaterial({ color: COLOR_PLAYER });
    this.mesh = new THREE.Mesh(geo, mat);
    this.mesh.position.set(position.x, position.y + 1, position.z);
    this.mesh.castShadow = true;
    scene.add(this.mesh);

    this._velocityY = 0;
    this._onGround = true;
  }

  update(delta, input) {
    const speed = PLAYER_SPEED * delta;

    if (input.left) this.mesh.position.x -= speed;
    if (input.right) this.mesh.position.x += speed;
    if (input.forward) this.mesh.position.z -= speed;
    if (input.backward) this.mesh.position.z += speed;

    // Jump
    if (input.jump && this._onGround) {
      this._velocityY = PLAYER_JUMP_FORCE;
      this._onGround = false;
      EventBus.emit('player:jumped');
    }

    // Gravity
    this._velocityY += GRAVITY * delta;
    this.mesh.position.y += this._velocityY * delta;

    if (this.mesh.position.y <= FLOOR_Y + 1) {
      this.mesh.position.y = FLOOR_Y + 1;
      this._velocityY = 0;
      this._onGround = true;
    }

    // Clamp to floor bounds
    this.mesh.position.x = Math.max(-18, Math.min(18, this.mesh.position.x));
    this.mesh.position.z = Math.max(-18, Math.min(18, this.mesh.position.z));
  }

  getPosition() {
    return { x: this.mesh.position.x, y: this.mesh.position.y, z: this.mesh.position.z };
  }
}
