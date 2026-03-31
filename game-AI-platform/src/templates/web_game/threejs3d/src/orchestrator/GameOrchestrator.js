import * as THREE from 'three';
import GameConfig from '../core/GameConfig.js';
import GameState from '../core/GameState.js';
import EventBus from '../core/EventBus.js';
import { COLOR_SKY, COLOR_AMBIENT, COLOR_DIRECTIONAL, COLOR_ENEMY, ENEMY_SPEED, ENEMY_SPAWN_INTERVAL } from '../core/Constants.js';
import Player from '../entities/Player.js';
import LevelBuilder from '../systems/LevelBuilder.js';
import InputSystem from '../systems/InputSystem.js';

/**
 * GameOrchestrator — top-level coordinator.
 * Owns the Three.js renderer, scene, camera, and game loop.
 * Delegates to subsystems; communicates via EventBus.
 */
export default class GameOrchestrator {
  constructor(container) {
    this._container = container;
    this._renderer = null;
    this._scene = null;
    this._camera = null;
    this._player = null;
    this._levelBuilder = null;
    this._inputSystem = null;
    this._enemies = [];
    this._clock = new THREE.Clock();
    this._spawnInterval = null;
    this._running = false;
    this._animFrame = null;
  }

  init() {
    // Renderer
    this._renderer = new THREE.WebGLRenderer(GameConfig.renderer);
    this._renderer.setPixelRatio(window.devicePixelRatio);
    this._renderer.setSize(window.innerWidth, window.innerHeight);
    this._renderer.shadowMap.enabled = GameConfig.shadows;
    this._container.appendChild(this._renderer.domElement);

    // Scene
    this._scene = new THREE.Scene();
    this._scene.background = new THREE.Color(COLOR_SKY);

    // Camera
    const cfg = GameConfig.camera;
    this._camera = new THREE.PerspectiveCamera(cfg.fov, window.innerWidth / window.innerHeight, cfg.near, cfg.far);
    this._camera.position.set(cfg.position.x, cfg.position.y, cfg.position.z);
    this._camera.lookAt(0, 0, 0);

    // Lighting
    const ambient = new THREE.AmbientLight(COLOR_AMBIENT, 0.6);
    this._scene.add(ambient);
    const sun = new THREE.DirectionalLight(COLOR_DIRECTIONAL, 1);
    sun.position.set(10, 20, 10);
    sun.castShadow = true;
    this._scene.add(sun);

    // Level
    this._levelBuilder = new LevelBuilder(this._scene);
    this._levelBuilder.build();

    // Player
    this._player = new Player(this._scene, { x: 0, y: 1, z: 0 });

    // Input
    this._inputSystem = new InputSystem();

    // Event subscriptions
    EventBus.on('game:over', () => this._onGameOver());

    // Resize
    window.addEventListener('resize', () => this._onResize());

    // Enemy spawn
    this._spawnInterval = setInterval(() => this._spawnEnemy(), ENEMY_SPAWN_INTERVAL);

    GameState.reset();
    this._running = true;
    this._loop();
  }

  _loop() {
    if (!this._running) return;
    this._animFrame = requestAnimationFrame(() => this._loop());
    const delta = this._clock.getDelta();
    if (!GameState.isPaused && !GameState.isGameOver) {
      this._update(delta);
    }
    this._renderer.render(this._scene, this._camera);
  }

  _update(delta) {
    const input = this._inputSystem.getState();
    this._player.update(delta, input);

    // Update player position in GameState
    const pos = this._player.getPosition();
    GameState.playerPosition = { x: pos.x, y: pos.y, z: pos.z };

    // Enemy movement + collision
    for (let i = this._enemies.length - 1; i >= 0; i--) {
      const e = this._enemies[i];
      e.position.z += ENEMY_SPEED * delta * 3;
      if (e.position.z > 20) {
        this._scene.remove(e);
        this._enemies.splice(i, 1);
        continue;
      }
      // Simple collision
      if (Math.abs(e.position.x - pos.x) < 1.5 && Math.abs(e.position.z - pos.z) < 1.5) {
        this._scene.remove(e);
        this._enemies.splice(i, 1);
        GameState.loseLife();
      }
    }
  }

  _spawnEnemy() {
    if (GameState.isGameOver) return;
    const geo = new THREE.BoxGeometry(1, 1, 1);
    const mat = new THREE.MeshLambertMaterial({ color: COLOR_ENEMY });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set((Math.random() - 0.5) * 16, 0.5, -20);
    this._scene.add(mesh);
    this._enemies.push(mesh);
  }

  _onGameOver() {
    this._running = false;
    clearInterval(this._spawnInterval);
  }

  _onResize() {
    this._camera.aspect = window.innerWidth / window.innerHeight;
    this._camera.updateProjectionMatrix();
    this._renderer.setSize(window.innerWidth, window.innerHeight);
  }

  getScene() { return this._scene; }
  getCamera() { return this._camera; }
  getRenderer() { return this._renderer; }
}
