/**
 * PixelArtRenderer — Convert pixel art data arrays into Phaser 3 textures.
 *
 * Inspired by OpusGameLabs/game-creator (game-assets skill).
 *
 * Pixel art format:
 *   A sprite is a 2-D array of hex color strings. null means transparent.
 *   Example:
 *     [
 *       [null,   '#ff0000', '#ff0000', null],
 *       ['#ff0000', '#ffff00', '#ffff00', '#ff0000'],
 *       [null,   '#ff0000', '#ff0000', null],
 *     ]
 *
 * Usage inside a Phaser Scene:
 *   import { createPhaserTexture } from '../sprites/PixelArtRenderer.js';
 *   import { PLAYER_SPRITE } from '../sprites/GameSprites.js';
 *
 *   // Call once in preload() or create():
 *   createPhaserTexture(this, 'player', PLAYER_SPRITE, 4);
 *
 *   // Then use the texture key like any Phaser texture:
 *   this.physics.add.image(x, y, 'player');
 */

/**
 * Render pixel art data to an HTML Canvas element.
 * @param {Array<Array<string|null>>} pixels - 2-D color array
 * @param {number} scale - pixel scale factor (default 4 → each pixel = 4×4 screen pixels)
 * @returns {HTMLCanvasElement}
 */
export function renderToCanvas(pixels, scale = 4) {
  const rows = pixels.length;
  const cols = rows > 0 ? pixels[0].length : 0;
  const canvas = document.createElement('canvas');
  canvas.width = cols * scale;
  canvas.height = rows * scale;
  const ctx = canvas.getContext('2d');
  for (let y = 0; y < rows; y++) {
    for (let x = 0; x < cols; x++) {
      const color = pixels[y][x];
      if (color) {
        ctx.fillStyle = color;
        ctx.fillRect(x * scale, y * scale, scale, scale);
      }
    }
  }
  return canvas;
}

/**
 * Add a pixel art texture to the Phaser texture manager.
 * Safe to call multiple times — skips if the key already exists.
 *
 * @param {Phaser.Scene} scene
 * @param {string} key - texture key (used in this.add.image / this.physics.add.image)
 * @param {Array<Array<string|null>>} pixels
 * @param {number} scale - default 4
 */
export function createPhaserTexture(scene, key, pixels, scale = 4) {
  if (scene.textures.exists(key)) return;
  const canvas = renderToCanvas(pixels, scale);
  scene.textures.addCanvas(key, canvas);
}

/**
 * Add a sprite-sheet texture (multiple animation frames) from an array of frames.
 * Each frame is a 2-D pixel art array with the same dimensions.
 *
 * @param {Phaser.Scene} scene
 * @param {string} key
 * @param {Array<Array<Array<string|null>>>} frames - array of pixel art frames
 * @param {number} scale - default 4
 */
export function createPhaserSpriteSheet(scene, key, frames, scale = 4) {
  if (!frames || frames.length === 0) return;
  if (scene.textures.exists(key)) return;
  const rows = frames[0].length;
  const cols = rows > 0 ? frames[0][0].length : 0;
  const frameW = cols * scale;
  const frameH = rows * scale;
  const canvas = document.createElement('canvas');
  canvas.width = frameW * frames.length;
  canvas.height = frameH;
  const ctx = canvas.getContext('2d');
  frames.forEach((frame, i) => {
    for (let y = 0; y < rows; y++) {
      for (let x = 0; x < cols; x++) {
        const color = frame[y][x];
        if (color) {
          ctx.fillStyle = color;
          ctx.fillRect(i * frameW + x * scale, y * scale, scale, scale);
        }
      }
    }
  });
  scene.textures.addSpriteSheet(key, canvas, { frameWidth: frameW, frameHeight: frameH });
}
