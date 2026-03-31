/**
 * GameSprites — Pixel art data for all game entities.
 *
 * Each export is a 2-D array of hex color strings (null = transparent).
 * The AI asset generation step replaces this file with game-specific sprites.
 *
 * Usage with Three.js:
 *   import { createThreeTexture } from './PixelArtRenderer.js';
 *   import { PLAYER_SPRITE } from './GameSprites.js';
 *   const texture = createThreeTexture(PLAYER_SPRITE, 8);
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

// 4×4 placeholder enemy sprite (red)
export const ENEMY_SPRITE = [
  [null,      '#cc0000', '#cc0000', null],
  ['#cc0000', '#ff4444', '#ff4444', '#cc0000'],
  ['#cc0000', '#cc0000', '#cc0000', '#cc0000'],
  [null,      '#cc0000', '#cc0000', null],
];

// 4×4 placeholder obstacle / wall (grey)
export const OBSTACLE_SPRITE = [
  ['#888888', '#aaaaaa', '#aaaaaa', '#888888'],
  ['#aaaaaa', '#cccccc', '#cccccc', '#aaaaaa'],
  ['#888888', '#aaaaaa', '#aaaaaa', '#888888'],
  ['#888888', '#888888', '#888888', '#888888'],
];
