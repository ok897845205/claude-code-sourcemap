import * as THREE from 'three';
import { COLOR_FLOOR, FLOOR_SIZE } from '../core/Constants.js';

export default class LevelBuilder {
  constructor(scene) {
    this._scene = scene;
  }

  build() {
    // Floor
    const floorGeo = new THREE.PlaneGeometry(FLOOR_SIZE, FLOOR_SIZE);
    const floorMat = new THREE.MeshLambertMaterial({ color: COLOR_FLOOR });
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    this._scene.add(floor);

    // Boundary walls (invisible physics only)
    this._addWall(-20, 1, 0, 1, 2, FLOOR_SIZE);
    this._addWall(20, 1, 0, 1, 2, FLOOR_SIZE);
  }

  _addWall(x, y, z, w, h, d) {
    const geo = new THREE.BoxGeometry(w, h, d);
    const mat = new THREE.MeshLambertMaterial({ color: 0x888888, transparent: true, opacity: 0 });
    const wall = new THREE.Mesh(geo, mat);
    wall.position.set(x, y, z);
    this._scene.add(wall);
    return wall;
  }
}
