import Phaser from 'phaser';
import GameConfig from './core/GameConfig.js';
import GameState from './core/GameState.js';

// Boot Phaser
const game = new Phaser.Game(GameConfig);

/**
 * render_game_to_text() — required by QA agent.
 * Returns a JSON string describing the current game state.
 */
window.render_game_to_text = function () {
  const state = GameState.toJSON();
  const activeScene = game.scene.getScenes(true).map(s => s.sys.settings.key);
  return JSON.stringify({
    engine: 'phaser2d',
    activeScenes: activeScene,
    state,
    timestamp: Date.now(),
  });
};

export default game;
