/**
 * GameSprites — Pixel art data for all game entities.
 *
 * Each export is a 2-D array of hex color strings (null = transparent).
 * The AI asset generation step replaces this file with game-specific sprites.
 *
 * To use sprites in a Phaser scene:
 *   import { createPhaserTexture } from './PixelArtRenderer.js';
 *   import { PLAYER_SPRITE, ENEMY_SPRITE } from './GameSprites.js';
 *   createPhaserTexture(this, 'player', PLAYER_SPRITE, 4);
 *   createPhaserTexture(this, 'enemy',  ENEMY_SPRITE,  4);
 */

// 4×6 placeholder player sprite (green figure)
export const PLAYER_SPRITE = [
  [null,      '#00cc44', '#00cc44', null],
  ['#00cc44', '#ffff88', '#ffff88', '#00cc44'],
  ['#00cc44', '#00cc44', '#00cc44', '#00cc44'],
  [null,      '#00cc44', '#00cc44', null],
  [null,      '#00cc44', '#00cc44', null],
  ['#00cc44', null,      null,      '#00cc44'],
];

// 4×4 placeholder enemy sprite (red shape)
export const ENEMY_SPRITE = [
  [null,      '#cc0000', '#cc0000', null],
  ['#cc0000', '#ff4444', '#ff4444', '#cc0000'],
  ['#cc0000', '#cc0000', '#cc0000', '#cc0000'],
  [null,      '#cc0000', '#cc0000', null],
];

// 4×5 placeholder coin / collectible sprite (gold)
export const COIN_SPRITE = [
  [null,      '#ffdd00', '#ffdd00', null],
  ['#ffdd00', '#ffff88', '#ffff88', '#ffdd00'],
  ['#ffdd00', '#ffff88', '#ffdd00', '#ffdd00'],
  ['#ffdd00', '#ffdd00', '#ffdd00', '#ffdd00'],
  [null,      '#ffdd00', '#ffdd00', null],
];
