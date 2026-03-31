/**
 * Constants — all magic numbers, colours, speeds.
 * Never use bare literals in game logic; always reference this file.
 */
export const CANVAS_WIDTH = 800;
export const CANVAS_HEIGHT = 600;

export const PLAYER_SPEED = 300;
export const PLAYER_JUMP_VELOCITY = -450;
export const PLAYER_GRAVITY = 800;

export const ENEMY_SPEED = 120;
export const ENEMY_SPAWN_INTERVAL = 2000;

export const SCORE_PER_ENEMY = 100;
export const SCORE_PER_LEVEL = 500;

export const INITIAL_LIVES = 3;
export const MAX_LEVEL = 10;

export const COLOR_SKY = 0x87ceeb;
export const COLOR_GROUND = 0x4a3728;
export const COLOR_PLAYER = 0x00ff00;
export const COLOR_ENEMY = 0xff0000;
export const COLOR_COIN = 0xffd700;
export const COLOR_UI_BG = 0x000000;
export const COLOR_UI_TEXT = 0xffffff;

export const PHYSICS_GRAVITY = 600;

export const SCENE_BOOT = 'BootScene';
export const SCENE_GAME = 'GameScene';
export const SCENE_GAME_OVER = 'GameOverScene';

export const FONT_SIZE_LARGE = '32px';
export const FONT_SIZE_MEDIUM = '24px';
export const FONT_SIZE_SMALL = '16px';
