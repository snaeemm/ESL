import * as THREE from 'three';

// ---------------------------------------------------------------------------
// Coordinate conversion
// ---------------------------------------------------------------------------
// Both pose_world_landmarks and the hand/image landmarks turn out to use
// the same Y-DOWN convention (origin roughly at hip height for world
// landmarks, top-left for image landmarks) — verified empirically and
// deliberately, not assumed:
//
//   t=0.00s (hand down at rest, off-frame low): R_wrist.y = -0.011
//   t=1.00s (hand raised to chest, thumb-up):   R_wrist.y = -0.245
//
// Raising the hand made y MORE negative, so -y is "up" here, i.e. Y-DOWN,
// same as image landmarks. (An earlier pass compared frame10 (t=0.4) to
// frame49 (t=1.96) and concluded the opposite — but the hand's true
// trajectory in this clip rises to a peak around t=0.6-1.6s and is already
// descending by t=1.96s, so that comparison straddled the peak and read
// the wrong half of the motion. Always anchor a sign check on two frames
// with an unambiguous, visually-confirmed height difference, not two
// arbitrary frames.)
//
// So both landmark sets get the same Y flip; only Z's sign is otherwise
// irrelevant to which convention this is.
export function mpWorldToThree(p, out = new THREE.Vector3()) {
  return out.set(p.x, -p.y, -p.z);
}

export function mpImageToThree(p, out = new THREE.Vector3()) {
  return out.set(p.x, -p.y, -p.z);
}

// ---------------------------------------------------------------------------
// Handedness
// ---------------------------------------------------------------------------
// Verified against the extracted Alif landmarks: pose landmark 12
// (RIGHT_SHOULDER) has a consistently *smaller* x than landmark 11
// (LEFT_SHOULDER) in every sampled frame — i.e. MediaPipe's "right" already
// means the signer's own anatomical right (which sits stage-left on an
// unmirrored, camera-facing shot), not a mirrored/selfie-view right. The
// source video is never flipped in extract_landmarks.py. So mapping
// MediaPipe right_* landmarks straight onto VRM right* bones (no manual
// mirroring) is correct — a second flip here would double-mirror it.
// This function is a runtime trip-wire in case a different source clip
// (filmed selfie-style, or already mirrored upstream) violates that
// assumption.
export function checkHandedness(poseWorldThreeFrames) {
  let violations = 0;
  let checked = 0;
  for (const pw of poseWorldThreeFrames) {
    if (!pw) continue;
    checked++;
    if (pw[12].x >= pw[11].x) violations++; // right shoulder should be left of left shoulder (smaller x)
  }
  if (checked > 0 && violations / checked > 0.2) {
    console.warn(
      `[retarget] handedness sanity check failed: right_shoulder.x >= left_shoulder.x in ` +
      `${violations}/${checked} frames. This source clip may be mirrored — right/left bone ` +
      `mapping should be swapped.`
    );
    return false;
  }
  console.log(`[retarget] handedness check OK (${checked - violations}/${checked} frames consistent)`);
  return true;
}

// ---------------------------------------------------------------------------
// Bind-pose (rest pose) directions, read once from the loaded, unposed VRM.
// ---------------------------------------------------------------------------
export const POSE = {
  LEFT_SHOULDER: 11, RIGHT_SHOULDER: 12,
  LEFT_ELBOW: 13, RIGHT_ELBOW: 14,
  LEFT_WRIST: 15, RIGHT_WRIST: 16,
  LEFT_HIP: 23, RIGHT_HIP: 24,
};

// [baseLandmarkIdx, j1, j2, j3] — baseLandmarkIdx is the wrist-side anchor
// used only to seed the raw-angle calculation; the 3 VRM bones map onto the
// 3 consecutive segments (base->j1, j1->j2, j2->j3).
export const HAND_CHAINS = {
  thumb: [1, 2, 3, 4],
  index: [5, 6, 7, 8],
  middle: [9, 10, 11, 12],
  ring: [13, 14, 15, 16],
  little: [17, 18, 19, 20],
};

const FINGER_BONES = {
  thumb: ['ThumbMetacarpal', 'ThumbProximal', 'ThumbDistal'],
  index: ['IndexProximal', 'IndexIntermediate', 'IndexDistal'],
  middle: ['MiddleProximal', 'MiddleIntermediate', 'MiddleDistal'],
  ring: ['RingProximal', 'RingIntermediate', 'RingDistal'],
  little: ['LittleProximal', 'LittleIntermediate', 'LittleDistal'],
};

export function computeBindDirs(vrm) {
  const humanoid = vrm.humanoid;
  const dirs = {};
  function boneDir(name) {
    const bone = humanoid.getNormalizedBoneNode(name);
    if (!bone || bone.children.length === 0) return null;
    return bone.children[0].position.clone().normalize();
  }
  for (const name of ['leftUpperArm', 'leftLowerArm', 'rightUpperArm', 'rightLowerArm']) {
    dirs[name] = boneDir(name);
  }
  return dirs;
}

// ---------------------------------------------------------------------------
// Arm: shoulder->elbow->wrist direction vectors, swing-only rotation
// relative to the VRM's own rest-pose bone directions, calibrated against
// the source clip's own frame-0 pose so that frame 0 maps to exactly the
// VRM's bind pose (zero delta) rather than whatever the raw MediaPipe axes
// happen to read.
// ---------------------------------------------------------------------------

/**
 * For each arm bone, computes the quaternion that would need to be applied
 * to the calibration frame's observed direction to make it equal the VRM's
 * true rest-pose direction (in world space). Applying this same quaternion
 * to every subsequent frame's observed direction re-bases the whole
 * sequence onto the VRM's neutral pose, canceling out camera tilt / body
 * orientation offset between the source video's "rest" stance and the
 * VRM's bind pose.
 */
export function computeArmCalibration(vrm, bindDirs, calibPoseWorldThree) {
  const calib = {};
  for (const side of ['left', 'right']) {
    for (const seg of ['UpperArm', 'LowerArm']) {
      const boneName = side + seg;
      const bone = vrm.humanoid.getNormalizedBoneNode(boneName);
      if (!bone || !bone.parent || !bindDirs[boneName]) continue;

      const parentWorldQuat = new THREE.Quaternion();
      bone.parent.getWorldQuaternion(parentWorldQuat);
      const bindDirWorld = bindDirs[boneName].clone().applyQuaternion(parentWorldQuat);

      const SH = side === 'right' ? POSE.RIGHT_SHOULDER : POSE.LEFT_SHOULDER;
      const EL = side === 'right' ? POSE.RIGHT_ELBOW : POSE.LEFT_ELBOW;
      const WR = side === 'right' ? POSE.RIGHT_WRIST : POSE.LEFT_WRIST;
      const a = seg === 'UpperArm' ? calibPoseWorldThree[SH] : calibPoseWorldThree[EL];
      const b = seg === 'UpperArm' ? calibPoseWorldThree[EL] : calibPoseWorldThree[WR];
      const observedDir = b.clone().sub(a).normalize();

      calib[boneName] = new THREE.Quaternion().setFromUnitVectors(observedDir, bindDirWorld);
    }
  }
  return calib;
}

function aimBoneAt(bone, targetDirWorld, bindDirLocal) {
  if (!bone || !bone.parent || !bindDirLocal) return;
  const parentWorldQuat = new THREE.Quaternion();
  bone.parent.getWorldQuaternion(parentWorldQuat);
  const targetDirParentLocal = targetDirWorld.clone()
    .applyQuaternion(parentWorldQuat.clone().invert())
    .normalize();
  bone.quaternion.setFromUnitVectors(bindDirLocal, targetDirParentLocal);
}

const _sh = new THREE.Vector3();
const _el = new THREE.Vector3();
const _wr = new THREE.Vector3();

export function applyArm(vrm, bindDirs, armCalib, side, poseWorldThree) {
  if (!poseWorldThree) return;
  const SH = side === 'right' ? POSE.RIGHT_SHOULDER : POSE.LEFT_SHOULDER;
  const EL = side === 'right' ? POSE.RIGHT_ELBOW : POSE.LEFT_ELBOW;
  const WR = side === 'right' ? POSE.RIGHT_WRIST : POSE.LEFT_WRIST;

  _sh.copy(poseWorldThree[SH]);
  _el.copy(poseWorldThree[EL]);
  _wr.copy(poseWorldThree[WR]);

  const upperName = side + 'UpperArm';
  const lowerName = side + 'LowerArm';
  const upperArmBone = vrm.humanoid.getNormalizedBoneNode(upperName);
  const lowerArmBone = vrm.humanoid.getNormalizedBoneNode(lowerName);

  let upperDir = _el.clone().sub(_sh).normalize();
  let lowerDir = _wr.clone().sub(_el).normalize();
  if (armCalib[upperName]) upperDir.applyQuaternion(armCalib[upperName]);
  if (armCalib[lowerName]) lowerDir.applyQuaternion(armCalib[lowerName]);

  // Stylistic bias, signing arm only: nudge the elbow up/outward and tilt
  // the forearm so the wrist finishes a bit higher relative to the elbow
  // than the raw MediaPipe direction gives. This is a tunable offset, not
  // a computed correction — applied only to the side actually performing
  // the sign (`right` in this clip) so the resting arm isn't dragged up
  // with it. Implemented as a small blend toward "more vertical" / "more
  // to the side" rather than a fixed-axis rotation, so it scales smoothly
  // with however extended the arm already is instead of overshooting a
  // nearly-vertical arm or barely nudging a horizontal one.
  if (side === 'right') {
    const WORLD_UP = new THREE.Vector3(0, 1, 0);
    const sideSign = Math.sign(upperDir.x) || -1; // right arm leans -X on this model; fall back if exactly 0
    const OUTWARD = new THREE.Vector3(sideSign, 0, 0);

    const ELBOW_LIFT = 0.12;
    const ELBOW_OUTWARD = 0.08;
    const WRIST_LIFT = 0.15;

    upperDir.lerp(WORLD_UP, ELBOW_LIFT).lerp(OUTWARD, ELBOW_OUTWARD).normalize();
    lowerDir.lerp(WORLD_UP, WRIST_LIFT).normalize();
  }

  if (upperArmBone && upperDir.lengthSq() > 0) aimBoneAt(upperArmBone, upperDir, bindDirs[upperName]);
  if (lowerArmBone && lowerDir.lengthSq() > 0) aimBoneAt(lowerArmBone, lowerDir, bindDirs[lowerName]);
}

// ---------------------------------------------------------------------------
// Hand orientation: two-vector (forward + up) full basis alignment, not a
// single-axis swing, because finger curl below is applied as a rotation
// local to the hand bone and needs the hand's roll (not just its aim
// direction) to be right, or the whole hand's twist ends up arbitrary.
// ---------------------------------------------------------------------------

function computeHandBindBasis(vrm, side) {
  const handBone = vrm.humanoid.getNormalizedBoneNode(side + 'Hand');
  const middleProx = vrm.humanoid.getNormalizedBoneNode(side + 'MiddleProximal');
  const indexProx = vrm.humanoid.getNormalizedBoneNode(side + 'IndexProximal');
  const littleProx = vrm.humanoid.getNormalizedBoneNode(side + 'LittleProximal');
  if (!handBone || !middleProx || !indexProx || !littleProx) return null;

  // These finger-root bones are direct children of the hand bone, so their
  // .position is already expressed in the hand bone's own local space.
  const fwd = middleProx.position.clone().normalize();
  const across = indexProx.position.clone().sub(littleProx.position).normalize();
  const normal = new THREE.Vector3().crossVectors(fwd, across).normalize();
  const up = new THREE.Vector3().crossVectors(normal, fwd).normalize(); // re-orthogonalize
  return { fwd, up };
}

function basisQuaternion(fwd, up) {
  const f = fwd.clone().normalize();
  const r = new THREE.Vector3().crossVectors(up, f).normalize();
  const u = new THREE.Vector3().crossVectors(f, r).normalize();
  const m = new THREE.Matrix4().makeBasis(r, u, f);
  return new THREE.Quaternion().setFromRotationMatrix(m);
}

function orientHandBone(bone, fwdWorld, upWorld, bindBasis) {
  if (!bone || !bone.parent || !bindBasis) return;
  const parentWorldQuat = new THREE.Quaternion();
  bone.parent.getWorldQuaternion(parentWorldQuat);
  const parentInv = parentWorldQuat.clone().invert();

  const fwdLocal = fwdWorld.clone().applyQuaternion(parentInv).normalize();
  const upLocal = upWorld.clone().applyQuaternion(parentInv).normalize();

  const targetQuat = basisQuaternion(fwdLocal, upLocal);
  const bindQuat = basisQuaternion(bindBasis.fwd, bindBasis.up);
  // bone.quaternion should map bindBasis -> targetBasis (both already in
  // the same parent-local space): q = targetQuat * bindQuat^-1.
  bone.quaternion.copy(targetQuat.multiply(bindQuat.invert()));
}

// ---------------------------------------------------------------------------
// Fingers: local joint-flexion angles from landmark geometry, applied as a
// pure local rotation around the bone's own +X axis.
//
// +X = flex-into-palm was verified empirically for this VRM sample (not
// assumed): a synthetic +80 deg local-X rotation on rightIndexProximal/
// Intermediate/Distal produced a natural-looking curl into the palm, while
// -80 deg produced an unnatural hyperextension. Verified consistent for
// both rightHand and leftHand on this model (no left/right sign flip
// needed here) — re-verify if a different VRM is swapped in.
//
// Each joint's flexion is measured as the signed angle between the
// incoming and outgoing segment at that joint (or, for the first bone in
// the chain, between the wrist->base vector and the first segment), signed
// around the hand's own "across the palm" axis (index MCP -> little MCP).
//
// The choice of reference vector for the first joint doesn't naturally
// read as zero when a finger is straight — wrist->MCP is not collinear
// with MCP->PIP even on a flat hand — so every angle is expressed as a
// DELTA from a "straight finger" baseline. That baseline is measured from
// the VRM's OWN bind-pose bone geometry (see computeHandCalibration),
// *not* from a video frame: this specific Alif clip only has hand
// landmarks once the hand is already mid-fist (MediaPipe can't detect it
// before it's raised into signing position), so there is no genuinely
// flat-hand frame anywhere in the tracked window to calibrate against — a
// first-tracked-frame baseline would silently absorb that fist shape as
// "zero" and undercurl every frame relative to it. Anchoring to the rig's
// own rest geometry instead gives a baseline that's correct regardless of
// what the video ever shows.
// ---------------------------------------------------------------------------

function signedAngle(v1, v2, axis) {
  const v1n = v1.clone().normalize();
  const v2n = v2.clone().normalize();
  const cross = new THREE.Vector3().crossVectors(v1n, v2n);
  const s = cross.dot(axis);
  const c = v1n.dot(v2n);
  return Math.atan2(s, c);
}

/** Raw (uncalibrated) joint angles for one tracked hand, in radians, keyed by VRM bone name. */
export function computeRawFingerAngles(handLmThree) {
  const wrist = handLmThree[0];
  const indexMcp = handLmThree[HAND_CHAINS.index[0]];
  const littleMcp = handLmThree[HAND_CHAINS.little[0]];
  const axis = new THREE.Vector3().subVectors(indexMcp, littleMcp).normalize();

  const angles = {};
  for (const [finger, chain] of Object.entries(HAND_CHAINS)) {
    const base = handLmThree[chain[0]];
    const p1 = handLmThree[chain[1]];
    const p2 = handLmThree[chain[2]];
    const p3 = handLmThree[chain[3]];
    const ref = new THREE.Vector3().subVectors(base, wrist);
    const seg0 = new THREE.Vector3().subVectors(p1, base);
    const seg1 = new THREE.Vector3().subVectors(p2, p1);
    const seg2 = new THREE.Vector3().subVectors(p3, p2);

    const bones = FINGER_BONES[finger];
    angles[bones[0]] = signedAngle(ref, seg0, axis);
    angles[bones[1]] = signedAngle(seg0, seg1, axis);
    angles[bones[2]] = signedAngle(seg1, seg2, axis);
  }
  return angles;
}

/**
 * "Straight finger" baseline angles, derived from the VRM's own bind-pose
 * bone offsets rather than any video frame. At bind pose every bone has
 * identity local rotation, so each bone's `.position` (an offset relative
 * to its own parent) can be composed directly with its parent's and
 * grandparent's the same way a landmark chain would be, giving an
 * angle computation structurally identical to computeRawFingerAngles but
 * fed from the rig instead of MediaPipe.
 */
export function computeHandCalibration(vrm, side) {
  const h = (name) => vrm.humanoid.getNormalizedBoneNode(side + name);
  const indexProx = h('IndexProximal');
  const littleProx = h('LittleProximal');
  if (!indexProx || !littleProx) return null;
  const axis = indexProx.position.clone().sub(littleProx.position).normalize();

  const angles = {};
  for (const [finger, segNames] of Object.entries(FINGER_BONES)) {
    const proxBone = h(segNames[0]);
    const intBone = h(segNames[1]);
    const distBone = h(segNames[2]);
    if (!proxBone || !intBone || !distBone) continue;

    const ref = proxBone.position;             // hand -> proximal, hand-local
    const seg0 = intBone.position;              // proximal -> intermediate, proximal-local
    const seg1 = distBone.position;              // intermediate -> distal, intermediate-local
    // Bind pose has identity local rotation at every joint, so these are
    // all still expressed in the same (hand-local) orientation and can be
    // compared directly, exactly like a landmark chain.
    const seg2 = distBone.children.length > 0
      ? distBone.children[0].position
      : seg1; // no leaf child to measure a distal-tip segment from; reuse seg1 as a neutral stand-in

    angles[segNames[0]] = signedAngle(ref, seg0, axis);
    angles[segNames[1]] = signedAngle(seg0, seg1, axis);
    angles[segNames[2]] = signedAngle(seg1, seg2, axis);
  }
  return angles;
}

/**
 * Prefer a real, video-derived "most extended" reference over the VRM's
 * own rig geometry when one is available: checked against a second source
 * of the same signer (the untrimmed alif_eb6b778b.mp4, which contains this
 * same active window plus its lead-in) — while this clip never shows a
 * fully flat hand, curl summed across index/middle/ring/little's
 * intermediate+distal joints has a sharp, isolated minimum right as the
 * hand is still lifting into position (t=0.6s in the untrimmed clip, ~230
 * vs 420+ everywhere else tracked), which is visibly a more open hand than
 * the fist held for the rest of the sign. That same instant exists in our
 * own trimmed landmarks too (they're the same footage), so we don't need
 * the second file at runtime — just pick whichever tracked frame in THIS
 * clip has the lowest curl sum and use it as the calibration frame. The
 * VRM bind-pose baseline (computeHandCalibration) remains the fallback for
 * whichever hand never gets a real tracked frame at all (left hand, here).
 */
export function findMostExtendedHandFrame(framesThree) {
  let bestIdx = -1;
  let bestScore = Infinity;
  for (let i = 0; i < framesThree.length; i++) {
    const lm = framesThree[i];
    if (!lm) continue;
    const raw = computeRawFingerAngles(lm);
    let score = 0;
    for (const finger of ['index', 'middle', 'ring', 'little']) {
      const [, intName, distName] = FINGER_BONES[finger];
      score += Math.abs(raw[intName]) + Math.abs(raw[distName]);
    }
    if (score < bestScore) { bestScore = score; bestIdx = i; }
  }
  return bestIdx;
}

export function computeHandCalibrationFromVideo(framesThree) {
  const idx = findMostExtendedHandFrame(framesThree);
  if (idx === -1) return null;
  return { angles: computeRawFingerAngles(framesThree[idx]), frameIdx: idx };
}

export function applyHand(vrm, side, handLmThree, handCalib) {
  if (!handLmThree) return;

  const handBone = vrm.humanoid.getNormalizedBoneNode(side + 'Hand');
  const bindBasis = computeHandBindBasis(vrm, side);
  if (handBone && bindBasis) {
    const wrist = handLmThree[0];
    const middleMcp = handLmThree[HAND_CHAINS.middle[0]];
    const indexMcp = handLmThree[HAND_CHAINS.index[0]];
    const littleMcp = handLmThree[HAND_CHAINS.little[0]];
    const fwdWorld = new THREE.Vector3().subVectors(middleMcp, wrist).normalize();
    const upWorld = new THREE.Vector3().subVectors(indexMcp, littleMcp).normalize();
    orientHandBone(handBone, fwdWorld, upWorld, bindBasis);
  }

  const raw = computeRawFingerAngles(handLmThree);
  for (const [boneName, rawAngle] of Object.entries(raw)) {
    const bone = vrm.humanoid.getNormalizedBoneNode(side + boneName);
    if (!bone) continue;
    const baseline = handCalib ? (handCalib[boneName] || 0) : 0;
    const delta = rawAngle - baseline;
    bone.quaternion.setFromAxisAngle(new THREE.Vector3(1, 0, 0), delta);
  }
}

// ---------------------------------------------------------------------------
// Dropout handling: forward/backward-fill leading and trailing gaps where a
// hand was never seen, and linearly interpolate interior gaps between two
// valid detections, instead of leaving/snapping to identity (bind pose)
// whenever MediaPipe drops a frame.
// ---------------------------------------------------------------------------
export function fillHandGaps(frames, key) {
  const n = frames.length;
  const validIdx = [];
  for (let i = 0; i < n; i++) if (frames[i][key]) validIdx.push(i);
  if (validIdx.length === 0) return frames.map(() => null);

  const filled = new Array(n);
  for (let i = 0; i < n; i++) {
    if (frames[i][key]) { filled[i] = frames[i][key]; continue; }
    // Find bracketing valid indices.
    let lo = -1, hi = -1;
    for (const v of validIdx) { if (v < i) lo = v; if (v > i && hi === -1) hi = v; }
    if (lo === -1) { filled[i] = frames[hi][key]; continue; }         // leading gap: hold first valid
    if (hi === -1) { filled[i] = frames[lo][key]; continue; }         // trailing gap: hold last valid
    const t = (i - lo) / (hi - lo);                                   // interior gap: lerp
    filled[i] = frames[lo][key].map((p, k) => {
      const q = frames[hi][key][k];
      return { x: p.x + (q.x - p.x) * t, y: p.y + (q.y - p.y) * t, z: p.z + (q.z - p.z) * t };
    });
  }
  return filled;
}

// ---------------------------------------------------------------------------
// Debug: world-space positions of a few landmark joints on the posed VRM,
// for side-by-side numeric/visual comparison against the MediaPipe points.
// ---------------------------------------------------------------------------
export function getDebugJointWorldPositions(vrm, side) {
  const names = {
    shoulder: side + 'UpperArm',
    elbow: side + 'LowerArm',
    wrist: side + 'Hand',
    thumbTip: side + 'ThumbDistal',
  };
  const out = {};
  for (const [key, boneName] of Object.entries(names)) {
    const bone = vrm.humanoid.getNormalizedBoneNode(boneName);
    if (!bone) { out[key] = null; continue; }
    const pos = new THREE.Vector3();
    bone.getWorldPosition(pos);
    if (key === 'thumbTip') {
      // Extend past the distal bone's own origin by its own segment length,
      // along its current world orientation, as an approximate fingertip.
      const worldQuat = new THREE.Quaternion();
      bone.getWorldQuaternion(worldQuat);
      const extend = bone.position.clone().applyQuaternion(worldQuat);
      pos.add(extend);
    }
    out[key] = pos;
  }
  return out;
}

export function applyFrame(vrm, bindDirs, armCalib, handCalibRight, handCalibLeft, frame) {
  applyArm(vrm, bindDirs, armCalib, 'left', frame.pose_world_three);
  applyArm(vrm, bindDirs, armCalib, 'right', frame.pose_world_three);
  applyHand(vrm, 'left', frame.left_hand_three, handCalibLeft);
  applyHand(vrm, 'right', frame.right_hand_three, handCalibRight);
}
