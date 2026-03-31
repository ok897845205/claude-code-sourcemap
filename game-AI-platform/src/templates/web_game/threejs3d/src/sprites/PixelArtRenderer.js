/**
 * PixelArtRenderer — Convert pixel art data arrays into Three.js textures.
 *
 * Inspired by OpusGameLabs/game-creator (game-assets skill).
 *
 * Pixel art format:
 *   A sprite is a 2-D array of hex color strings. null means transparent.
 *
 * Usage with Three.js:
 *   import { renderToCanvas, createThreeTexture } from '../sprites/PixelArtRenderer.js';
 *   import { PLAYER_SPRITE } from '../sprites/GameSprites.js';
 *
 *   const texture = createThreeTexture(PLAYER_SPRITE, 8);
 *   const material = new THREE.SpriteMaterial({ map: texture });
 *   const sprite = new THREE.Sprite(material);
 */

/**
 * Render pixel art data to an HTML Canvas element.
 * @param {Array<Array<string|null>>} pixels - 2-D color array
 * @param {number} scale - pixel scale factor (default 8 for 3D context)
 * @returns {HTMLCanvasElement}
 */
export function renderToCanvas(pixels, scale = 8) {
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
 * Create a Three.js CanvasTexture from pixel art data.
 * @param {Array<Array<string|null>>} pixels
 * @param {number} scale - pixel scale factor (default 8)
 * @returns {THREE.CanvasTexture}
 */
export function createThreeTexture(pixels, scale = 8) {
  // Dynamic import to avoid coupling this module to THREE
  const canvas = renderToCanvas(pixels, scale);
  // Caller must pass in THREE or the CanvasTexture constructor
  if (typeof THREE !== 'undefined') {
    const texture = new THREE.CanvasTexture(canvas);
    texture.magFilter = THREE.NearestFilter;
    texture.minFilter = THREE.NearestFilter;
    return texture;
  }
  return canvas;
}
