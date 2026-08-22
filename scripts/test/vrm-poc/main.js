import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { VRMLoaderPlugin } from '@pixiv/three-vrm';
import {
  mpWorldToThree, mpImageToThree, checkHandedness,
  computeBindDirs, computeArmCalibration, computeHandCalibration,
  computeHandCalibrationFromVideo,
  fillHandGaps, applyFrame, getDebugJointWorldPositions,
} from './retarget.js';

const vrmPane = document.getElementById('vrm-pane');
const statusEl = document.getElementById('status');
const video = document.getElementById('source-video');
const overlayCanvas = document.getElementById('video-overlay');
const overlayCtx = overlayCanvas.getContext('2d');

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x222222);

// Front-facing camera: same head-on perspective as the source clip.
const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 20);
camera.position.set(0, 1.3, 2.5);
camera.lookAt(0, 1.1, 0);

const renderer = new THREE.WebGLRenderer({ antialias: true });
vrmPane.appendChild(renderer.domElement);

scene.add(new THREE.AmbientLight(0xffffff, 1.2));
const dirLight = new THREE.DirectionalLight(0xffffff, 1.5);
dirLight.position.set(1, 1, 1);
scene.add(dirLight);

function resize() {
  const w = vrmPane.clientWidth;
  const h = vrmPane.clientHeight;
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
  overlayCanvas.width = video.clientWidth;
  overlayCanvas.height = video.clientHeight;
}
window.addEventListener('resize', resize);

// Debug spheres on the VRM: one per joint we compare against MediaPipe.
const DEBUG_COLORS = { shoulder: 0xff5555, elbow: 0x55ff55, wrist: 0x5599ff, thumbTip: 0xffdd33 };
const debugSpheres = {};
for (const [key, color] of Object.entries(DEBUG_COLORS)) {
  const mesh = new THREE.Mesh(
    new THREE.SphereGeometry(0.015, 12, 12),
    new THREE.MeshBasicMaterial({ color, depthTest: false })
  );
  mesh.renderOrder = 999;
  mesh.visible = false;
  scene.add(mesh);
  debugSpheres[key] = mesh;
}

let vrm = null;
let bindDirs = null;
let armCalib = null;
let handCalibRight = null;
let handCalibLeft = null;
let frames = null; // preprocessed frames with *_three fields
let fps = 25;

const loader = new GLTFLoader();
loader.register((parser) => new VRMLoaderPlugin(parser));

const loadVrm = new Promise((resolve, reject) => {
  loader.load(
    '/assets/VRM1_Constraint_Twist_Sample.vrm',
    (gltf) => {
      vrm = gltf.userData.vrm;
      scene.add(vrm.scene);
      // VRM 1.0 models face +Z by spec; camera sits at +Z, so no extra
      // rotation is needed for the avatar to face the camera.
      resolve(vrm);
    },
    undefined,
    reject
  );
});

const loadLandmarks = fetch('/assets/alif_landmarks.json').then((r) => r.json());

Promise.all([loadVrm, loadLandmarks]).then(([loadedVrm, lm]) => {
  fps = lm.fps;
  bindDirs = computeBindDirs(loadedVrm);

  // --- Preprocess: convert every landmark set to Three.js space once, and
  // fill hand-tracking gaps (hold-last / interpolate) instead of leaving
  // frames with no hand data at all. ---
  const filledRight = fillHandGaps(lm.frames, 'right_hand');
  const filledLeft = fillHandGaps(lm.frames, 'left_hand');

  frames = lm.frames.map((fr, i) => ({
    ...fr,
    pose_world_three: fr.pose_world ? fr.pose_world.map((p) => mpWorldToThree(p)) : null,
    right_hand_three: filledRight[i] ? filledRight[i].map((p) => mpImageToThree(p)) : null,
    left_hand_three: filledLeft[i] ? filledLeft[i].map((p) => mpImageToThree(p)) : null,
    right_hand_tracked: !!fr.right_hand,
    left_hand_tracked: !!fr.left_hand,
  }));

  checkHandedness(frames.map((f) => f.pose_world_three));

  // --- Calibration: frame 0 for the arms (pose is present in every frame);
  // each hand's own first tracked frame for fingers, so calibration always
  // uses a real detection rather than a gap-filled placeholder. ---
  // Arm calibration (forcing frame-0's observed direction to equal the
  // VRM's bind-pose direction) is OFF by default: this VRM's normalized
  // humanoid rest reference is a T-pose (arms ~horizontal), which is a
  // completely different convention from a person's natural relaxed
  // "arms at sides" stance, not just a small camera-tilt offset. Forcing
  // them equal collapses the whole performance toward a T-pose baseline —
  // verified directly (screenshots with calibration on showed a persistent
  // T-pose bleed-through; with it off, the retarget matches the source
  // video's down-at-rest / raised-to-chest / down-again motion frame for
  // frame). The swing-only aim in applyArm already rotates FROM the VRM's
  // own rest-pose bone direction (bindDirs) TO each frame's absolute
  // observed direction, which is itself "rotation relative to a calibrated
  // rest pose" — the calibration is in the bind direction, not a separate
  // step. Pass ?calibrate=1 to re-enable the frame-0 lock for comparison.
  const calibrate = new URLSearchParams(window.location.search).get('calibrate') === '1';
  armCalib = calibrate ? computeArmCalibration(loadedVrm, bindDirs, frames[0].pose_world_three) : {};

  // Finger-curl baseline: the VRM's own bind-pose geometry, not a video
  // frame. A video-derived baseline (computeHandCalibrationFromVideo,
  // still below) was tried first, on the idea that other footage of this
  // signer might supply a real "flat hand" reference — checked against
  // both this clip's full tracked window and the untrimmed source
  // (alif_eb6b778b.mp4, same footage plus lead-in/out). Neither ever shows
  // a genuinely flat hand: the least-curled real frame available still has
  // substantial curl baked in, so using it as "zero" still partially
  // cancels the true motion — visually undercurled the fingers next to the
  // rig-based baseline. Kept for a clip that might actually contain a flat
  // frame, but the VRM's bind pose is the better reference for this one.
  const rightVideoCalib = computeHandCalibrationFromVideo(
    frames.map((f) => (f.right_hand_tracked ? f.right_hand_three : null))
  );
  const leftVideoCalib = computeHandCalibrationFromVideo(
    frames.map((f) => (f.left_hand_tracked ? f.left_hand_three : null))
  );
  handCalibRight = computeHandCalibration(loadedVrm, 'right');
  handCalibLeft = computeHandCalibration(loadedVrm, 'left');

  const firstRightIdx = frames.findIndex((f) => f.right_hand_tracked);
  const firstLeftIdx = frames.findIndex((f) => f.left_hand_tracked);

  resize();
  for (const s of Object.values(debugSpheres)) s.visible = true;

  video.play().catch(() => {
    document.body.addEventListener('click', () => video.play(), { once: true });
  });

  console.log(
    `VRM + landmarks loaded: frames=${frames.length} fps=${fps} ` +
    `firstRightHandFrame=${firstRightIdx} firstLeftHandFrame=${firstLeftIdx} ` +
    `rightHandCalibFrame=${rightVideoCalib ? rightVideoCalib.frameIdx : '(VRM bind-pose fallback)'} ` +
    `leftHandCalibFrame=${leftVideoCalib ? leftVideoCalib.frameIdx : '(VRM bind-pose fallback)'}`
  );
  window.__vrmReady = true;
});

function currentFrame() {
  if (!frames) return null;
  const idx = Math.min(frames.length - 1, Math.max(0, Math.round(video.currentTime * fps)));
  return { idx, frame: frames[idx] };
}

function drawOverlay(frame) {
  overlayCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
  if (!frame || !video.videoWidth) return;

  // The <video> uses object-fit:contain, so its drawn pixels are letterboxed
  // inside the element's box; account for that or the dots drift off the
  // actual picture as soon as the box aspect ratio isn't 16:9.
  const cw = overlayCanvas.width;
  const ch = overlayCanvas.height;
  const scale = Math.min(cw / video.videoWidth, ch / video.videoHeight);
  const renderedW = video.videoWidth * scale;
  const renderedH = video.videoHeight * scale;
  const offsetX = (cw - renderedW) / 2;
  const offsetY = (ch - renderedH) / 2;

  function dot(nx, ny, color, r = 5) {
    overlayCtx.beginPath();
    overlayCtx.arc(offsetX + nx * renderedW, offsetY + ny * renderedH, r, 0, Math.PI * 2);
    overlayCtx.fillStyle = color;
    overlayCtx.fill();
  }

  if (frame.pose) {
    dot(frame.pose[12].x, frame.pose[12].y, '#ff5555'); // right shoulder
    dot(frame.pose[14].x, frame.pose[14].y, '#55ff55'); // right elbow
    dot(frame.pose[16].x, frame.pose[16].y, '#5599ff'); // right wrist
  }
  if (frame.right_hand) {
    dot(frame.right_hand[4].x, frame.right_hand[4].y, '#ffdd33', 4); // thumb tip
    overlayCtx.fillStyle = 'rgba(255,255,255,0.7)';
    for (const i of [8, 12, 16, 20]) { // other fingertips, dimmer
      overlayCtx.beginPath();
      overlayCtx.arc(offsetX + frame.right_hand[i].x * renderedW, offsetY + frame.right_hand[i].y * renderedH, 3, 0, Math.PI * 2);
      overlayCtx.fill();
    }
  }
}

function fmt(v) {
  return v ? `(${v.x.toFixed(2)}, ${v.y.toFixed(2)}, ${v.z.toFixed(2)})` : 'n/a';
}

function animate() {
  requestAnimationFrame(animate);

  if (vrm && frames) {
    const { idx, frame } = currentFrame();
    applyFrame(vrm, bindDirs, armCalib, handCalibRight, handCalibLeft, frame);
    vrm.update(1 / 60);

    const debugPos = getDebugJointWorldPositions(vrm, 'right');
    for (const [key, pos] of Object.entries(debugPos)) {
      if (pos) debugSpheres[key].position.copy(pos);
    }

    drawOverlay(frame);

    const mpWrist = frame.pose ? frame.pose[16] : null;
    const mpElbow = frame.pose ? frame.pose[14] : null;
    const mpThumb = frame.right_hand ? frame.right_hand[4] : null;

    statusEl.textContent =
      `frame ${idx + 1}/${frames.length}  t=${video.currentTime.toFixed(2)}s\n` +
      `right hand: ${frame.right_hand_tracked ? 'tracked' : 'held/interpolated'}   ` +
      `left hand: ${frame.left_hand_tracked ? 'tracked' : 'held/interpolated'}\n` +
      `--- debug joints (VRM world m  vs  MediaPipe image [0-1]) ---\n` +
      `elbow  VRM=${fmt(debugPos.elbow)}  MP=${mpElbow ? `(${mpElbow.x.toFixed(2)}, ${mpElbow.y.toFixed(2)})` : 'n/a'}\n` +
      `wrist  VRM=${fmt(debugPos.wrist)}  MP=${mpWrist ? `(${mpWrist.x.toFixed(2)}, ${mpWrist.y.toFixed(2)})` : 'n/a'}\n` +
      `thumbTip VRM=${fmt(debugPos.thumbTip)}  MP=${mpThumb ? `(${mpThumb.x.toFixed(2)}, ${mpThumb.y.toFixed(2)})` : 'n/a'}`;
  }

  renderer.render(scene, camera);
}
animate();
