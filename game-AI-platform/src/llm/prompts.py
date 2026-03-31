"""
Prompt templates for every pipeline stage.

Each prompt is a plain function returning (system, user) tuple.
Prompts reference the template architecture (EventBus / GameState / Constants).
"""

from __future__ import annotations

from src.models import EngineType, GameAnalysis, GamePlan

# ── Stage 1: Analyze ────────────────────────────────────────────────────────

ANALYZE_SYSTEM = """\
You are a game design analyst.  Given a natural-language game idea from the \
user, produce a structured JSON analysis.

Return ONLY a JSON object (no markdown fences, no extra text) with these fields:
{
  "title": "Short game title",
  "engine": "phaser2d" | "threejs3d",
  "genre": "platformer | shooter | puzzle | racing | rpg | arcade | ...",
  "description": "One-paragraph expanded description",
  "mechanics": ["mechanic1", "mechanic2", ...],
  "entities": ["Player", "Enemy", "Coin", ...],
  "visual_style": "retro pixel | cartoon | sci-fi | fantasy | ...",
  "difficulty": "easy | medium | hard"
}

Engine selection rules:
- For side-scrolling, top-down, classic 2D games → "phaser2d"
- For 3D, first-person, third-person, 3D world → "threejs3d"
- If ambiguous, prefer "phaser2d" (simpler, higher success rate)
"""


def analyze(user_prompt: str) -> tuple[str, str]:
    return ANALYZE_SYSTEM, f"Game idea:\n{user_prompt}"


# ── Stage 2: Plan ───────────────────────────────────────────────────────────

_PLAN_SYSTEM_TEMPLATE = """\
You are a game architect.  Given a game analysis, plan which source files \
must be written for a {engine} project.

The project template already has these files that CAN be overwritten:
- src/core/Constants.js     (export const values — must be overwritten)
- src/core/GameState.js     (centralised state — must be overwritten)
- src/core/EventBus.js      (pub/sub — usually keep as-is)
- src/core/GameConfig.js    (Phaser/Three config — may need tweaks)
- src/sprites/GameSprites.js  (pixel art data — must be overwritten)
- src/sprites/PixelArtRenderer.js  (renderer — usually keep as-is)
- src/audio/AudioManager.js  (audio engine — usually keep as-is)
- src/audio/sfx.js           (sound definitions — must be overwritten)
- src/entities/Player.js     (player entity — must be overwritten)
{scenes_note}
- src/main.js               (entry point — usually keep as-is)

ARCHITECTURE RULES (mandatory):
1. All inter-module communication goes through EventBus — never import between sibling modules.
2. All numeric constants go in Constants.js — no magic numbers.
3. All shared state goes in GameState.js — scenes/entities never own shared state.
4. Scenes must NOT import from other scenes.
5. Entities must NOT import from scenes.

Return ONLY a JSON object:
{{
  "files": [
    {{"path": "entities/Enemy.js", "purpose": "Enemy AI entity"}},
    {{"path": "entities/Coin.js", "purpose": "Collectible coin"}},
    ...
  ],
  "constants_overrides": {{
    "CANVAS_WIDTH": 800,
    "PLAYER_SPEED": 200,
    ...
  }},
  "extra_scenes": ["ShopScene", "BossScene"]
}}

- "files" must include ALL files that need to be generated or overwritten.
  Always include: core/Constants.js, core/GameState.js, sprites/GameSprites.js,
  audio/sfx.js, entities/Player.js, and all scene files.
- The path is relative to src/ inside the project.
- Do NOT include EventBus.js, AudioManager.js, PixelArtRenderer.js unless changes are needed.
"""


def plan(analysis: GameAnalysis) -> tuple[str, str]:
    engine = analysis.engine.value
    if engine == "phaser2d":
        scenes_note = (
            "- src/scenes/BootScene.js      (boot/preload)\n"
            "- src/scenes/GameScene.js       (main gameplay — must be overwritten)\n"
            "- src/scenes/GameOverScene.js   (game over screen — must be overwritten)"
        )
    else:
        scenes_note = (
            "- src/orchestrator/GameOrchestrator.js  (main game loop — must be overwritten)\n"
            "- src/systems/LevelBuilder.js          (level geometry — must be overwritten)\n"
            "- src/systems/InputSystem.js            (input polling — usually keep as-is)"
        )

    system = _PLAN_SYSTEM_TEMPLATE.format(engine=engine, scenes_note=scenes_note)
    user = (
        f"Game analysis:\n"
        f"Title: {analysis.title}\n"
        f"Engine: {analysis.engine.value}\n"
        f"Genre: {analysis.genre}\n"
        f"Description: {analysis.description}\n"
        f"Mechanics: {', '.join(analysis.mechanics)}\n"
        f"Entities: {', '.join(analysis.entities)}\n"
        f"Visual style: {analysis.visual_style}\n"
        f"Difficulty: {analysis.difficulty}\n"
    )
    return system, user


# ── Stage 3: Code generation (per file) ─────────────────────────────────────

_CODEGEN_SYSTEM_TEMPLATE = """\
You are an expert JavaScript game developer.  Write the COMPLETE content of \
a single source file for a {engine} web game.

ARCHITECTURE RULES (mandatory):
1. Constants.js MUST use NAMED exports (export const FOO = ...):
   Example: export const CANVAS_WIDTH = 800;
   NEVER use: const Constants = {{ ... }}; export default Constants;
   GameConfig.js imports as: import {{ CANVAS_WIDTH }} from './Constants.js'
2. GameState.js MUST use a default export:
   Example: export default GameState; or export default gameStateInstance;
3. Import Constants with destructuring: import {{ CANVAS_WIDTH, PLAYER_SPEED }} from '../core/Constants.js'
4. Import EventBus from '../core/EventBus.js' — use for all inter-module messages.
5. Import GameState from '../core/GameState.js' — for all shared state reads/writes.
6. Scenes must NOT import from other scenes.
7. Entities must NOT import from scenes or orchestrator.
8. Use ES module syntax (import/export).
9. The file must be self-contained and complete — no TODOs or placeholders.
10. Import sprites as: import GameSprites from '../sprites/GameSprites.js'
    Then access as: GameSprites.PLAYER_IDLE, GameSprites.FOOD_IDLE, etc.
11. Import audio as: import AudioManager from '../audio/AudioManager.js'
    Then use: AudioManager.play('sound_name')

CANVAS_WIDTH and CANVAS_HEIGHT MUST always be exported from Constants.js.

{engine_note}

Return ONLY the JavaScript source code.  No markdown fences, no explanation.
"""


def codegen(
    engine: EngineType,
    file_path: str,
    purpose: str,
    analysis: GameAnalysis,
    plan: GamePlan,
) -> tuple[str, str]:
    if engine == EngineType.PHASER2D:
        engine_note = (
            "This is a Phaser 3 project.  Scenes extend Phaser.Scene.\n"
            "Sprites are pixel art arrays from GameSprites.js rendered via "
            "createPhaserTexture() from PixelArtRenderer.js.\n"
            "Sound effects use AudioManager.play('name').\n"
            "Physics: Phaser Arcade Physics (this.physics.add.*)."
        )
        template_files_note = (
            "\nTEMPLATE HELPER FILES (already exist, use correct import paths):\n"
            "  - src/core/EventBus.js      → import EventBus from '../core/EventBus.js'\n"
            "  - src/core/GameConfig.js     → import GameConfig from '../core/GameConfig.js'\n"
            "  - src/sprites/PixelArtRenderer.js → import { createPhaserTexture } from '../sprites/PixelArtRenderer.js'\n"
            "  - src/audio/AudioManager.js  → import AudioManager from '../audio/AudioManager.js'\n"
            "  - src/main.js               → entry point (do NOT import this)\n"
            "\nIMPORTANT: PixelArtRenderer.js is at 'sprites/', NOT 'utils/'. "
            "AudioManager.js is at 'audio/', NOT 'utils/'."
        )
    else:
        engine_note = (
            "This is a Three.js project.  No Phaser.\n"
            "Player/entities create THREE.Mesh objects added to the scene.\n"
            "GameOrchestrator owns renderer, scene, camera, game loop.\n"
            "Sound effects use AudioManager.play('name')."
        )
        template_files_note = (
            "\nTEMPLATE HELPER FILES (already exist, use correct import paths):\n"
            "  - src/core/EventBus.js      → import EventBus from '../core/EventBus.js'\n"
            "  - src/core/GameConfig.js     → import GameConfig from '../core/GameConfig.js'\n"
            "  - src/sprites/PixelArtRenderer.js → import { createThreeTexture } from '../sprites/PixelArtRenderer.js'\n"
            "  - src/audio/AudioManager.js  → import AudioManager from '../audio/AudioManager.js'\n"
            "  - src/main.js               → entry point (do NOT import this)\n"
            "\nIMPORTANT: PixelArtRenderer.js is at 'sprites/', NOT 'utils/'. "
            "AudioManager.js is at 'audio/', NOT 'utils/'."
        )

    system = _CODEGEN_SYSTEM_TEMPLATE.format(
        engine=engine.value, engine_note=engine_note,
    )

    # Build context about the full project
    file_list = "\n".join(f"  - {f.path}: {f.purpose}" for f in plan.files)
    constants_info = ""
    if plan.constants_overrides:
        pairs = [f"  {k} = {v}" for k, v in plan.constants_overrides.items()]
        constants_info = "\nConstants that will be defined:\n" + "\n".join(pairs)

    user = (
        f"Game: {analysis.title}\n"
        f"Genre: {analysis.genre}\n"
        f"Description: {analysis.description}\n"
        f"Mechanics: {', '.join(analysis.mechanics)}\n"
        f"Entities: {', '.join(analysis.entities)}\n"
        f"Visual style: {analysis.visual_style}\n\n"
        f"Project files (files being generated):\n{file_list}\n{constants_info}\n"
        f"{template_files_note}\n\n"
        f"FILE TO WRITE: src/{file_path}\n"
        f"PURPOSE: {purpose}\n\n"
        f"Write the complete JavaScript source code for this file."
    )
    return system, user


# ── Stage 3b: Sprite generation ─────────────────────────────────────────────

SPRITE_SYSTEM = """\
You are an expert pixel artist and game graphics programmer.  Generate rich, \
detailed pixel art sprite data for a game as a JavaScript ES module.

== COMPACT FORMAT ==
Define a palette object first, then reference palette keys in sprite arrays.
Example:
  const P = { bg: null, skin: '#ffcc99', hair: '#442200', eye: '#000000' };
  export const PLAYER_IDLE = [
    [P.bg, P.hair, P.hair, P.bg],
    [P.bg, P.skin, P.skin, P.bg],
    ...
  ];

This keeps the file small and avoids repeating long hex strings.

== SPRITE SIZES (IMPORTANT — keep small to avoid output truncation) ==
- Tiny items (coins, bullets, particles): 4×4 to 6×6
- Standard entities (player, enemies, items): 8×8
- Large entities (bosses): 10×10 max
- Background tiles: 8×8

CRITICAL: Do NOT use 16×16 or larger sprites. Keep ALL sprites 10×10 or smaller
to ensure the output fits within token limits.

== ANIMATION FRAMES ==
For animated entities, provide 2 frames max (idle + action):
  export const PLAYER_IDLE = [ [...], ... ];
  export const PLAYER_WALK = [ [...], ... ];

== REQUIRED EXPORTS ==
1. A "SPRITE_PALETTE" object mapping style names to hex colours used.
2. At least 2 animation frames per moving entity (idle + action).
3. At least one set of environment/tile sprites (ground, wall).
4. Collectible / item sprites.
5. UI elements (heart, coin icon).
6. One particle sprite (explosion — 4×4).
7. A DEFAULT EXPORT object that aggregates ALL sprites for easy access:
   export default { SPRITE_PALETTE, PLAYER_IDLE, PLAYER_WALK, ... };

CRITICAL: You MUST include a default export at the end of the file.
Other files import this as `import GameSprites from '../sprites/GameSprites.js'`
and access sprites as `GameSprites.PLAYER_IDLE`, etc.

== QUALITY GUIDELINES ==
- Give characters clear silhouettes with a darker outline shade.
- Use 2-3 shading levels per surface.
- Moving entities must look distinct between frames.

Return ONLY valid JavaScript with export statements.  No markdown fences.
"""


def sprite_gen(analysis: GameAnalysis) -> tuple[str, str]:
    user = (
        f"Game: {analysis.title}\n"
        f"Genre: {analysis.genre}\n"
        f"Visual style: {analysis.visual_style}\n"
        f"Entities that need sprites: {', '.join(analysis.entities)}\n"
        f"Mechanics: {', '.join(analysis.mechanics)}\n\n"
        f"Generate a compact GameSprites.js with:\n"
        f"1. SPRITE_PALETTE — colour palette for the '{analysis.visual_style}' style\n"
        f"2. Define a short alias object (const P = {{...}}) for all palette colors\n"
        f"3. For each entity ({', '.join(analysis.entities)}): IDLE + one action frame (8×8 max)\n"
        f"4. Environment tiles: ground, wall (8×8)\n"
        f"5. Collectibles: coin/food item (6×6 max)\n"
        f"6. UI icons: heart, score icon (6×6 max)\n"
        f"7. One explosion particle (4×4)\n\n"
        f"CRITICAL: Keep ALL sprites 10×10 or smaller. Use the palette alias (P.xxx)\n"
        f"to keep file size minimal. The output MUST be complete — no truncation."
    )
    return SPRITE_SYSTEM, user


# ── Stage 3c: Audio generation ──────────────────────────────────────────────

AUDIO_SYSTEM = """\
You are an expert chiptune composer and sound designer.  Generate procedural \
Web Audio API sound effects AND background music for a game.

== SOUND EFFECTS ==
Use this pattern for each sound effect:
  AudioManager.register('name', (ctx) => {
    // create oscillators, gains, filters
    // schedule notes with precise timing via .start(time) and .stop(time)
    // connect to ctx.destination
  });

Available nodes: OscillatorNode, GainNode, BiquadFilterNode, \
DelayNode, DynamicsCompressorNode, WaveShaperNode.
Oscillator types: 'sine', 'square', 'sawtooth', 'triangle'.

Tips for expressive SFX:
- Use gain ramps (linearRampToValueAtTime) for attack/decay envelopes.
- Use frequency sweeps for laser/jump effects.
- Layer 2-3 oscillators for richer sounds.
- Add a short delay for echo effects.
- Use noise (random buffer) for explosions and impacts.

== BACKGROUND MUSIC ==
Register a special looping music track:
  AudioManager.registerMusic('bgm', (ctx) => {
    // Build a short 4-8 bar melody using scheduled oscillators
    // Use setInterval or a scheduling loop for looping
    // Return { stop() { /* cleanup */ } } so AudioManager can stop it
  });

Music guidelines:
- Use a simple chord progression (4-8 bars, loop-friendly).
- Layer bass (sine/triangle low freq) + melody (square/sawtooth) + rhythm (noise bursts).
- Tempo should match the game feel: fast for action, moderate for puzzle, slow for ambient.
- Use pentatonic or simple scales for easy-to-listen melodies.
- Schedule notes precisely with ctx.currentTime + offsets.
- Keep the loop under 8 seconds for memory efficiency.

== REQUIRED SOUNDS ==
At minimum, generate:
1. Core gameplay SFX (genre-specific: jump, shoot, hit, score, etc.)
2. UI sounds: 'menu_select', 'menu_back'
3. State sounds: 'game_over', 'level_complete'
4. Ambient/background: at least one 'bgm' music loop
5. Feedback sounds: 'success' and 'fail' for positive/negative events

Start with:
  import AudioManager from './AudioManager.js';

Return ONLY valid JavaScript. No markdown fences.
"""


def audio_gen(analysis: GameAnalysis) -> tuple[str, str]:
    # Map genre to suggested sounds
    genre_sounds = {
        "platformer": "jump, land, coin, spring, stomp, fall",
        "shooter": "shoot, reload, explode, shield_hit, missile, laser",
        "puzzle": "rotate, snap, clear_line, combo, hint",
        "racing": "engine, boost, crash, drift, checkpoint, lap",
        "rpg": "sword_slash, magic_cast, heal, level_up, chest_open, dialogue",
        "arcade": "bounce, score, powerup, speed_up, bonus",
    }
    genre_key = analysis.genre.lower()
    suggested = genre_sounds.get(genre_key, "score, hit, powerup, special")

    user = (
        f"Game: {analysis.title}\n"
        f"Genre: {analysis.genre}\n"
        f"Mechanics: {', '.join(analysis.mechanics)}\n"
        f"Visual style: {analysis.visual_style}\n"
        f"Entities: {', '.join(analysis.entities)}\n\n"
        f"Generate a comprehensive sfx.js with:\n\n"
        f"1. GENRE-SPECIFIC sound effects (suggested: {suggested})\n"
        f"2. UI sounds: 'menu_select', 'menu_back'\n"
        f"3. State sounds: 'game_over', 'level_complete'\n"
        f"4. Background music: a looping 'bgm' track matching the "
        f"'{analysis.visual_style}' atmosphere and '{analysis.genre}' pace\n"
        f"5. Feedback sounds: 'success', 'fail'\n\n"
        f"Make each sound distinct, with proper envelopes and layered oscillators.\n"
        f"The BGM should be a catchy, loop-friendly chiptune melody."
    )
    return AUDIO_SYSTEM, user


# ── Stage 5: Fix / iterate ──────────────────────────────────────────────────

FIX_SYSTEM = """\
You are a game debugger.  You will be given:
1. The current source code of a file
2. Error messages or user feedback
3. The list of ALL files in the project

Fix the code and return the COMPLETE corrected file.
Follow all architecture rules (EventBus, GameState, Constants).

IMPORTANT import path rules:
- PixelArtRenderer.js is at 'sprites/PixelArtRenderer.js' (NOT 'utils/')
- AudioManager.js is at 'audio/AudioManager.js' (NOT 'utils/')
- EventBus.js is at 'core/EventBus.js'
- GameState.js is at 'core/GameState.js'
- Constants.js is at 'core/Constants.js'
- All imports use relative paths like '../core/EventBus.js'

If the error is "Could not resolve" an import, fix the import path to match
the actual file location listed in the project files.

Return ONLY the corrected JavaScript source code. No markdown fences.
"""


def fix(file_path: str, current_code: str, errors: str,
        project_files: list[str] | None = None) -> tuple[str, str]:
    files_info = ""
    if project_files:
        files_info = "\n\nProject files that exist:\n" + "\n".join(f"  - src/{f}" for f in project_files)
    user = (
        f"File: {file_path}\n\n"
        f"Current code:\n```\n{current_code}\n```\n\n"
        f"Errors / feedback:\n{errors}\n"
        f"{files_info}\n\n"
        f"Return the complete corrected file."
    )
    return FIX_SYSTEM, user


# ── Iterate (user feedback) ────────────────────────────────────────────────

ITERATE_SYSTEM = """\
You are a game developer.  The user wants to modify an existing game.
You will receive:
1. The current game analysis
2. A list of current source files and their content
3. User feedback requesting changes

Determine which files need to change.  Return a JSON object:
{
  "files_to_update": [
    {"path": "relative/path.js", "reason": "why this file needs updating"}
  ],
  "constants_changes": {"KEY": "new_value", ...},
  "new_files": [
    {"path": "relative/path.js", "purpose": "why this new file is needed"}
  ]
}

Return ONLY JSON. No markdown fences.
"""


def iterate_plan(analysis: GameAnalysis, file_list: str, feedback: str) -> tuple[str, str]:
    user = (
        f"Game: {analysis.title} ({analysis.engine.value})\n"
        f"Genre: {analysis.genre}\n"
        f"Description: {analysis.description}\n\n"
        f"Current files:\n{file_list}\n\n"
        f"User feedback:\n{feedback}\n\n"
        f"What files need to change?"
    )
    return ITERATE_SYSTEM, user


# ── Multi-turn conversation ────────────────────────────────────────────────

CHAT_SYSTEM = """\
You are a game development assistant helping the user iteratively refine \
their game through conversation.  You have two responsibilities:

1. REPLY to the user in natural language (Chinese preferred) — briefly \
   acknowledge what they asked, explain what you will change and why.
2. OUTPUT a JSON action block at the end of your reply, wrapped in \
   <action>...</action> tags.

Action JSON format:
<action>
{
  "summary": "一句话概括本次修改",
  "files_to_update": [
    {"path": "relative/path.js", "reason": "why"}
  ],
  "new_files": [
    {"path": "relative/path.js", "purpose": "why"}
  ],
  "no_change": false
}
</action>

If the user is just chatting or asking a question (no code change needed), \
set "no_change": true and leave files arrays empty.

Game context:
- Title: {title}
- Engine: {engine}
- Genre: {genre}
- Description: {description}
- Current files: {file_list}

Keep replies concise and helpful.  Always include the <action> block.
"""


def chat_system(analysis: GameAnalysis, file_list: str) -> str:
    """Build the system prompt for multi-turn conversation."""
    return CHAT_SYSTEM.format(
        title=analysis.title,
        engine=analysis.engine.value,
        genre=analysis.genre,
        description=analysis.description,
        file_list=file_list,
    )
