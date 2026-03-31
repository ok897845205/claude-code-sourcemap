import GameOrchestrator from './orchestrator/GameOrchestrator.js';
import GameState from './core/GameState.js';

const container = document.body;
const orchestrator = new GameOrchestrator(container);
orchestrator.init();

/**
 * render_game_to_text() — required by QA agent.
 * Returns a JSON string describing the current game state.
 */
window.render_game_to_text = function () {
  return JSON.stringify({
    engine: 'threejs3d',
    state: GameState.toJSON(),
    timestamp: Date.now(),
  });
};

export default orchestrator;
