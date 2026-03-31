import { CAMERA_FOV, CAMERA_NEAR, CAMERA_FAR, CANVAS_WIDTH, CANVAS_HEIGHT } from './Constants.js';

const GameConfig = {
  renderer: {
    antialias: true,
    alpha: false,
  },
  camera: {
    fov: CAMERA_FOV,
    near: CAMERA_NEAR,
    far: CAMERA_FAR,
    position: { x: 0, y: 10, z: 20 },
  },
  width: CANVAS_WIDTH,
  height: CANVAS_HEIGHT,
  shadows: true,
};

export default GameConfig;
