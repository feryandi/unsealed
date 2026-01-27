import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { TGALoader } from 'three/addons/loaders/TGALoader.js';
import { DDSLoader } from 'three/addons/loaders/DDSLoader.js';

// Shared Three.js components
const clock = new THREE.Clock();
let scene, camera, renderer, controls;

// Model viewer state
let currentMixer = null;
let currentAction = null;
let currentModel = null;
let animations = [];
let isPlaying = false;
let isDraggingTimeline = false;

// Map viewer state
const mixers = [];
let mapObjects = [];
let mapGround = null;
const instances = {};
let embeddedTextureMap = {};
let embeddedGLBMap = {};

// Current mode
let currentMode = 'model';

const manager = new THREE.LoadingManager();
const loader = new GLTFLoader(manager);
const ASSET_BASE = (typeof window !== 'undefined' && window.WEB_ASSET_BASE) ? window.WEB_ASSET_BASE : './';

// ========== Event Logging ==========
function addEvent(message, type = 'info', isMapMode = false) {
  const sectionId = isMapMode ? 'map-events-section' : 'events-section';
  const eventsSection = document.getElementById(sectionId);
  if (!eventsSection) return;

  const eventItem = document.createElement('div');
  eventItem.className = `event-item ${type}`;

  const time = new Date().toLocaleTimeString();
  eventItem.innerHTML = `<span class="event-time">[${time}]</span>${message}`;

  eventsSection.appendChild(eventItem);
  eventsSection.scrollTop = eventsSection.scrollHeight;
}

function clearEvents(isMapMode = false) {
  const sectionId = isMapMode ? 'map-events-section' : 'events-section';
  const eventsSection = document.getElementById(sectionId);
  if (eventsSection) {
    eventsSection.innerHTML = '';
  }
}
// ========== Scene Management ==========
let gridHelper = null;

function updateGrid(isMapMode) {
  if (gridHelper) {
    scene.remove(gridHelper);
  }

  if (isMapMode) {
    // No grid for map mode
    gridHelper = null;
  } else {
    // Smaller grid for model mode
    gridHelper = new THREE.GridHelper(60, 60, 0x7DBBE8, 0x999999);
    gridHelper.position.y = 0;
  }

  scene.add(gridHelper);
}

function clearScene() {
  // Clear model viewer objects
  if (currentModel) {
    scene.remove(currentModel);
    currentModel = null;
  }

  if (currentMixer) {
    currentMixer.stopAllAction();
    currentMixer = null;
  }

  // Clear map viewer objects
  mapObjects.forEach(obj => scene.remove(obj));
  mapObjects = [];

  if (mapGround) {
    scene.remove(mapGround);
    mapGround = null;
  }

  mixers.length = 0;

  // Clear other scene objects except lights and grid
  const objectsToRemove = [];
  scene.traverse((object) => {
    if (object !== scene &&
      !(object instanceof THREE.Light) &&
      !(object instanceof THREE.GridHelper)) {
      objectsToRemove.push(object);
    }
  });
  objectsToRemove.forEach(obj => scene.remove(obj));

  currentAction = null;
  animations = [];
  isPlaying = false;
}

// ========== Initialization ==========
function init() {
  try {
    scene = new THREE.Scene();
    updateGrid(false);

    camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.6, 5000);
    camera.position.set(5, 5, 5);
    camera.lookAt(0, 0, 0);

    const dom = document.getElementById("viewer");

    renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setClearColor(0xBBBBBB, 1);
    renderer.setSize(window.innerWidth, window.innerHeight);
    dom.appendChild(renderer.domElement);

    controls = new OrbitControls(camera, renderer.domElement);
    controls.update();

    window.addEventListener('resize', onWindowResize);

    createLight();
    animate();

    addEvent('Viewer initialized', 'info');
  } catch (error) {
    addEvent(`Init Error: ${error.message}`, 'error');
    console.error('Init error:', error);
  }
}

function onWindowResize() {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
}

function animate() {
  requestAnimationFrame(animate);

  const delta = clock.getDelta();

  if (currentMode === 'model') {
    if (currentMixer && isPlaying) {
      currentMixer.update(delta);
      updateTimelineDisplay();
    }
  } else if (currentMode === 'map') {
    for (const mixer of mixers) {
      mixer.update(delta);
    }
  }

  controls.update();
  renderer.render(scene, camera);
}

function createLight() {
  const ambientLight = new THREE.AmbientLight(0xffffff, 2.0);
  scene.add(ambientLight);

  const directionalLight = new THREE.DirectionalLight(0xffffff, 1.0);
  directionalLight.position.set(10, 10, 10);
  scene.add(directionalLight);
}

// ========== MODEL VIEWER FUNCTIONS ==========
function loadGLB(file) {
  clearEvents();
  clearScene();

  const url = URL.createObjectURL(file);

  addEvent(`Loading: ${file.name}`, 'info');

  loader.load(
    url,
    function (gltf) {
      try {
        currentModel = gltf.scene;
        currentModel.position.set(0, 0, 0);
        scene.add(currentModel);

        animations = gltf.animations;

        if (animations.length > 0) {
          currentMixer = new THREE.AnimationMixer(currentModel);
          populateAnimationSelect();
          enableAnimationControls();
          addEvent(`Model loaded with ${animations.length} animation(s)`, 'info');
        } else {
          disableAnimationControls();
          addEvent('Model loaded (no animations)', 'info');
        }

        fitCameraToModel(currentModel);
        URL.revokeObjectURL(url);
      } catch (error) {
        addEvent(`Processing Error: ${error.message}`, 'error');
        console.error('Processing error:', error);
      }
    },
    function (progress) {
      if (progress.lengthComputable) {
        const percentComplete = (progress.loaded / progress.total * 100).toFixed(2);
        console.log(`Loading: ${percentComplete}%`);
      }
    },
    function (error) {
      addEvent(`Load Error: ${error.message || 'Failed to load file'}`, 'error');
      console.error('GLB error:', error);
      URL.revokeObjectURL(url);
    }
  );
}

function fitCameraToModel(model) {
  const box = new THREE.Box3().setFromObject(model);
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());

  const maxDim = Math.max(size.x, size.y, size.z);
  const fov = camera.fov * (Math.PI / 180);
  let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2));
  cameraZ *= 2;

  camera.position.set(center.x + cameraZ, center.y + cameraZ, center.z + cameraZ);
  camera.lookAt(center);
  controls.target.copy(center);
  controls.update();
}

function populateAnimationSelect() {
  const select = document.getElementById('animation-select');
  select.innerHTML = '';

  animations.forEach((anim, index) => {
    const option = document.createElement('option');
    option.value = index;
    option.textContent = anim.name || `Animation ${index + 1}`;
    select.appendChild(option);
  });

  if (animations.length > 0) {
    select.selectedIndex = 0;
    loadAnimation(0);
  }
}

function loadAnimation(index) {
  if (!currentMixer || index < 0 || index >= animations.length) return;

  if (currentAction) {
    currentAction.stop();
  }

  isPlaying = false;
  currentAction = currentMixer.clipAction(animations[index]);
  currentAction.clampWhenFinished = true;
  currentAction.loop = THREE.LoopRepeat;

  const duration = animations[index].duration;
  document.getElementById('duration').textContent = duration.toFixed(2);
  document.getElementById('timeline').max = duration;
  document.getElementById('timeline').value = 0;
  document.getElementById('current-time').textContent = '0.00';
}

function enableAnimationControls() {
  document.getElementById('animation-controls').classList.remove('disabled');
}

function disableAnimationControls() {
  document.getElementById('animation-controls').classList.add('disabled');
  document.getElementById('animation-select').innerHTML = '<option value="">No animations</option>';
}

function updateTimelineDisplay() {
  if (!currentAction || isDraggingTimeline) return;

  const time = currentAction.time;
  document.getElementById('current-time').textContent = time.toFixed(2);
  document.getElementById('timeline').value = time;
}

// ========== MAP VIEWER FUNCTIONS ==========
function base64ToUint8Array(base64) {
  var binary = atob(base64);
  var len = binary.length;
  var bytes = new Uint8Array(len);
  for (var i = 0; i < len; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function decodeF16ToFloat32(uint8arr) {
  var u16 = new Uint16Array(uint8arr.buffer);
  var out = new Float32Array(u16.length);
  for (var i = 0; i < u16.length; i++) {
    var h = u16[i];
    var s = (h & 0x8000) >> 15;
    var e = (h & 0x7C00) >> 10;
    var f = h & 0x03FF;
    var val;
    if (e === 0) {
      if (f === 0) {
        val = s ? -0.0 : 0.0;
      } else {
        val = (s ? -1 : 1) * Math.pow(2, -14) * (f / 1024);
      }
    } else if (e === 31) {
      val = f ? NaN : (s ? -Infinity : Infinity);
    } else {
      val = (s ? -1 : 1) * Math.pow(2, e - 15) * (1 + f / 1024);
    }
    out[i] = val;
  }
  return out;
}

function createGround(heightmap, textures, lightmap, terrain_layer_a, terrain_layer_b) {
  const geometry = new THREE.PlaneGeometry(511, 511, 511, 511);
  geometry.rotateX(Math.PI * -0.5);

  var shader_texture_layer_getter_func = `
    int get_texture_layer(in int layer[64], in int i) {`;
  for (var i = 0; i < 64; i++) {
    shader_texture_layer_getter_func += `if (i == ` + i + `) return layer[` + i + `];`
  }
  shader_texture_layer_getter_func += `
      return layer[0];
    }`;

  var shader_texture_getter_func = `
    vec4 get_texture(in int i, in vec2 uv) {
  `;
  for (var i = 1; i <= 12; i++) {
    var n = i - 1;
    shader_texture_getter_func += `if (i == ` + i + `) return texture2D(textures[` + n + `], uv);`
  }
  shader_texture_getter_func += `
    return texture2D(textures[0], uv);
  }`;

  var pitchMaterialParams = {
    uniforms: THREE.UniformsUtils.merge([{
      textures: null,
      lightMap: null,
      textureLayerA: null,
      textureLayerB: null,
    }]),
    vertexShader:
      `
       precision highp float;
       precision highp int;
       varying vec2 vUv;

       varying vec3 mPosition;
       uniform sampler2D displacementMap;

       void main() {
        vUv = uv;
        mPosition = position;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(mPosition, 1.0);
        vUv = vec2(uv.s, 1.0 - uv.t);
       }
     `,
    fragmentShader:
      `
       precision mediump float;
       varying vec2 vUv;
       uniform int textureLayerA[64];
       uniform int textureLayerB[64];
       uniform sampler2D lightMap;
       uniform sampler2D textures[12];
       
      `+ shader_texture_getter_func + `

      `+ shader_texture_layer_getter_func + `

      void main() {
        vec2 uv1 = vUv;
        uv1 = fract(uv1 * 128.0);

        float i = floor(vUv.y * 8.0) * 8.0 + floor(vUv.x * 8.0);
        int idx = int(i);
        vec4 terrain = get_texture(get_texture_layer(textureLayerB, idx), uv1);
        vec4 path = get_texture(get_texture_layer(textureLayerA, idx), uv1);

        vec4 lightmap = texture2D(lightMap, vUv);

        vec4 combined_path = vec4(mix(path.rgb, lightmap.rgb, lightmap.a + (path.rgb * (1.0 - lightmap.a)) / 1.5), 1.0);
        vec4 combined_terrain = vec4(mix(terrain.rgb, combined_path.rgb, (1.0 - lightmap.a) + (terrain.rgb * lightmap.a) / 1.5), 1.0);
        vec4 combined = mix(combined_terrain * 1.25, mix(vec4(1.0, 1.0, 1.0, 1.0), combined_terrain, 2.25), 0.5);
        gl_FragColor = combined;
      }
     `
  };

  var material = new THREE.ShaderMaterial(pitchMaterialParams);
  material.uniforms.lightMap.value = lightmap;
  material.uniforms.textures.value = textures;
  material.uniforms.textureLayerA.value = terrain_layer_a;
  material.uniforms.textureLayerB.value = terrain_layer_b;

  var mesh = new THREE.Mesh(geometry, material);
  mapGround = mesh;
  scene.add(mesh);

  const totalSegmentsX = 512;
  const totalSegmentsZ = 512;

  var vertices = []
  for (let z = 0; z < totalSegmentsZ; z++) {
    for (let x = 0; x < totalSegmentsX; x++) {
      var i = (z * totalSegmentsX + x);
      var h = heightmap[i];
      vertices.push(x);
      vertices.push(h);
      vertices.push(z);
    }
  }
  geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(vertices), 3));
}

function create_mesh_instance(filename, idx) {
  filename = filename.split(".")[0];
  var modelUrl = (embeddedGLBMap && embeddedGLBMap[filename]) ? embeddedGLBMap[filename].url : (ASSET_BASE + 'output/' + filename + '.gltf');
  loader.load(modelUrl,
    function (gltf) {
      const content = gltf.scene;
      content.traverse(function (child) {
        if (child.isMesh) {
          if (!(idx in instances)) {
            return;
          }

          const value = instances[idx];
          if (gltf.animations.length === 0) {
            const instancedMesh = new THREE.InstancedMesh(child.geometry, child.material, value.length);
            const matrix = new THREE.Matrix4();

            for (let i = 0; i < value.length; i++) {
              const pos = value[i]['pos'];
              const rot = value[i]['rot'];
              const scaleValue = rot[rot.length - 1];

              const position = new THREE.Vector3();
              const quaternion = new THREE.Quaternion();
              const quaternionX = new THREE.Quaternion();
              const quaternionY = new THREE.Quaternion();
              const scale = new THREE.Vector3();

              position.x = child.position.x + pos[0];
              position.y = child.position.y + pos[1];
              position.z = child.position.z + pos[2];

              quaternion.setFromAxisAngle(new THREE.Vector3(1, 0, 0), child.rotation.x);
              quaternion.setFromAxisAngle(new THREE.Vector3(0, 1, 0), child.rotation.y);
              quaternion.setFromAxisAngle(new THREE.Vector3(0, 0, 1), child.rotation.z);

              quaternionY.setFromAxisAngle(new THREE.Vector3(0, 1, 0), (rot[0] * 180) * (Math.PI / 180));
              quaternionX.setFromAxisAngle(new THREE.Vector3(1, 0, 0), (rot[1] * 180) * (Math.PI / 180));
              quaternion.multiplyQuaternions(quaternion, quaternionY);
              quaternion.multiplyQuaternions(quaternion, quaternionX);

              scale.x = scale.y = scale.z = (child.scale.x * scaleValue);

              matrix.compose(position, quaternion, scale);

              instancedMesh.setMatrixAt(i, matrix);
            }

            mapObjects.push(instancedMesh);
            scene.add(instancedMesh);
          } else {
            for (let i = 0; i < value.length; i++) {
              const pos = value[i]['pos'];
              const rot = value[i]['rot'];
              const scaleValue = rot[rot.length - 1];

              const content = gltf.scene.clone();
              content.position.set(pos[0], pos[1], pos[2]);
              content.rotation.y = (rot[0] * 180) * (Math.PI / 180);
              content.rotation.x = (rot[1] * 180) * (Math.PI / 180);
              content.scale.set(scaleValue, scaleValue, scaleValue);

              var mixer;
              mixer = new THREE.AnimationMixer(content);
              var action = mixer.clipAction(gltf.animations[0]);
              action.play();
              mapObjects.push(content);
              scene.add(content)
              mixers.push(mixer);
            }
          }
        }
      });
    }, undefined, function (error) {
      console.error(error);
    });
}

function processMapData(data) {
  clearEvents(true);
  clearScene();

  addEvent('Processing map data...', 'info', true);

  var textures = [];
  embeddedTextureMap = {};
  if (data['embedded_textures']) {
    for (let t of data['embedded_textures']) {
      try {
        var bytes = base64ToUint8Array(t.data_b64);
        var blob = new Blob([bytes], { type: 'application/octet-stream' });
        var url = URL.createObjectURL(blob);
        embeddedTextureMap[t.name] = { url: url, ext: t.ext, filename: t.filename };
      } catch (e) {
        console.warn('Failed to create embedded texture', t.name, e);
      }
    }
  }

  var lightmapTex = null;
  if (data['embedded_lightmap']) {
    try {
      var lb = base64ToUint8Array(data['embedded_lightmap'].data_b64);
      var lblob = new Blob([lb], { type: 'application/octet-stream' });
      lightmapTex = new DDSLoader().load(URL.createObjectURL(lblob));
    } catch (e) {
      console.warn('Failed to create embedded lightmap', e);
      lightmapTex = null;
    }
  }

  for (let i = 0; i < 12; i++) {
    if (i < data["textures"].length) {
      var name = (data["textures"][i].split('.'))[0]
      if (embeddedTextureMap[name]) {
        var tex = new DDSLoader().load(embeddedTextureMap[name].url);
        textures.push(tex);
      } else {
        var tex = new DDSLoader().load(ASSET_BASE + 'output/' + name + '.dds');
        textures.push(tex);
      }
    } else {
      textures.push(null);
    }
  }

  var heightmapArr = null;
  if (data["heightmap_b64"]) {
    var enc = data["heightmap_encoding"] || '';
    try {
      if (enc === 'f16+zlib') {
        var comp = base64ToUint8Array(data["heightmap_b64"]);
        var decomp = pako.inflate(comp);
        heightmapArr = decodeF16ToFloat32(decomp);
      } else if (enc === 'f32+zlib') {
        var comp = base64ToUint8Array(data["heightmap_b64"]);
        var decomp = pako.inflate(comp);
        heightmapArr = new Float32Array(decomp.buffer);
      } else if (enc === 'f32') {
        var bytes = base64ToUint8Array(data["heightmap_b64"]);
        heightmapArr = new Float32Array(bytes.buffer);
      } else {
        try {
          var comp = base64ToUint8Array(data["heightmap_b64"]);
          var decomp = pako.inflate(comp);
          heightmapArr = new Float32Array(decomp.buffer);
        } catch (e) {
          var bytes = base64ToUint8Array(data["heightmap_b64"]);
          heightmapArr = new Float32Array(bytes.buffer);
        }
      }
    } catch (e) {
      console.error('Heightmap decode error:', e);
      heightmapArr = new Float32Array(data["heightmap"] || []);
    }
  } else {
    heightmapArr = new Float32Array(data["heightmap"] || []);
  }

  var lightmapParam = lightmapTex;
  if (!lightmapParam && data["lightmap"]) {
    lightmapParam = new DDSLoader().load(ASSET_BASE + 'output/' + (data["lightmap"].split('.'))[0] + '.dds');
  }

  createGround(heightmapArr, textures, lightmapParam, data["terrain_layer_a"], data["terrain_layer_b"]);

  for (let obj of data['objects']) {
    if (!(obj['idx'] in instances)) {
      instances[obj['idx']] = [];
    }
    instances[obj['idx']].push(obj);
  }

  embeddedGLBMap = {};
  if (data['embedded_glbs']) {
    for (let g of data['embedded_glbs']) {
      try {
        var bytes = base64ToUint8Array(g.data_b64);
        var blob = new Blob([bytes], { type: 'application/octet-stream' });
        var url = URL.createObjectURL(blob);
        embeddedGLBMap[g.name] = { url: url, filename: g.filename };
      } catch (e) {
        console.warn('Failed to create embedded GLB', g.name, e);
      }
    }
  }

  let i = 0;
  for (let file of data['object_files']) {
    create_mesh_instance(file, i);
    i++;
  }

  // Reset camera for map view
  camera.position.set(1000, 1000, 1000);
  camera.lookAt(0, 0, 0);
  controls.target.set(0, 0, 0);
  controls.update();

  addEvent('Map loaded successfully', 'info', true);
}

// ========== TAB SWITCHING ==========
function switchMode(mode) {
  currentMode = mode;
  clearScene();
  updateGrid(mode === 'map'); // Add this line

  // Update tab UI
  document.querySelectorAll('.tab').forEach(tab => {
    tab.classList.remove('active');
  });
  document.querySelectorAll('.tab-content').forEach(content => {
    content.classList.remove('active');
  });

  document.querySelector(`[data-tab="${mode}"]`).classList.add('active');
  document.querySelector(`[data-content="${mode}"]`).classList.add('active');
}

// ========== EVENT LISTENERS ==========
// Tab switching
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', (e) => {
    const mode = e.target.dataset.tab;
    switchMode(mode);
  });
});

// Model viewer controls
document.getElementById('file-input-btn').addEventListener('click', function () {
  document.getElementById('file-input').click();
});

document.getElementById('file-input').addEventListener('change', function (e) {
  const file = e.target.files[0];
  if (file) {
    loadGLB(file);
  }
});

document.getElementById('animation-select').addEventListener('change', function (e) {
  const index = parseInt(e.target.value);
  if (!isNaN(index)) {
    loadAnimation(index);
  }
});

document.getElementById('play-btn').addEventListener('click', function () {
  if (currentAction) {
    if (currentAction.paused) {
      currentAction.paused = false;
    } else {
      currentAction.play();
    }
    isPlaying = true;
  }
});

document.getElementById('pause-btn').addEventListener('click', function () {
  if (currentAction && isPlaying) {
    currentAction.paused = true;
    isPlaying = false;
  }
});

document.getElementById('stop-btn').addEventListener('click', function () {
  if (currentAction) {
    currentAction.stop();
    currentAction.time = 0;
    isPlaying = false;
    updateTimelineDisplay();
  }
});

const timeline = document.getElementById('timeline');

timeline.addEventListener('mousedown', function () {
  isDraggingTimeline = true;
});

timeline.addEventListener('mouseup', function () {
  isDraggingTimeline = false;
});

timeline.addEventListener('input', function (e) {
  if (currentAction) {
    const time = parseFloat(e.target.value);
    currentAction.time = time;
    document.getElementById('current-time').textContent = time.toFixed(2);

    if (!isPlaying) {
      currentMixer.update(0);
    }
  }
});

// Map viewer controls
const mapDropZone = document.getElementById('map-drop-zone');
const mapFileInput = document.getElementById('mapFileInput');

mapDropZone.addEventListener('click', () => {
  mapFileInput.click();
});

mapFileInput.addEventListener('change', function (e) {
  const f = e.target.files && e.target.files[0];
  if (!f) return;
  loadMapFile(f);
});

mapDropZone.addEventListener('dragover', function (e) {
  e.preventDefault();
  mapDropZone.classList.add('drag-over');
});

mapDropZone.addEventListener('dragleave', function (e) {
  e.preventDefault();
  mapDropZone.classList.remove('drag-over');
});

mapDropZone.addEventListener('drop', function (e) {
  e.preventDefault();
  mapDropZone.classList.remove('drag-over');
  const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
  if (!f) return;
  loadMapFile(f);
});

function loadMapFile(file) {
  const reader = new FileReader();
  reader.onload = function () {
    try {
      const ab = reader.result;
      const bytes = new Uint8Array(ab);
      const isGzip = bytes.length > 2 && bytes[0] === 0x1f && bytes[1] === 0x8b;
      let text;
      if (isGzip) {
        const decomp = pako.ungzip(bytes);
        text = new TextDecoder().decode(decomp);
      } else {
        text = new TextDecoder().decode(bytes);
      }
      const data = JSON.parse(text);
      processMapData(data);
    } catch (err) {
      addEvent(`Failed to parse file: ${err.message}`, 'error', true);
      console.error('Failed to parse JSON file', err);
    }
  };
  reader.readAsArrayBuffer(file);
}

// Initialize
init();