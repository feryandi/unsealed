
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const clock = new THREE.Clock();
let scene, camera, renderer, controls;
let currentMixer = null;
let currentAction = null;
let currentModel = null;
let animations = [];
let isPlaying = false;
let isDraggingTimeline = false;

const manager = new THREE.LoadingManager();

manager.onError = (url) => {
  addEvent(`Error loading resource`, 'error');
};

function addEvent(message, type = 'info') {
  const eventsSection = document.getElementById('events-section');
  const eventItem = document.createElement('div');
  eventItem.className = `event-item ${type}`;

  const time = new Date().toLocaleTimeString();
  eventItem.innerHTML = `<span class="event-time">[${time}]</span>${message}`;

  eventsSection.appendChild(eventItem);
  eventsSection.scrollTop = eventsSection.scrollHeight;
}

function clearEvents() {
  const eventsSection = document.getElementById('events-section');
  eventsSection.innerHTML = '';
}

function init() {
  try {
    scene = new THREE.Scene();
    scene.add(new THREE.GridHelper(60, 60, 0x7DBBE8, 0x999999));

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

    create_light();
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
  if (currentMixer && isPlaying) {
    currentMixer.update(delta);
    updateTimelineDisplay();
  }

  controls.update();
  renderer.render(scene, camera);
}

function create_light() {
  const ambientLight = new THREE.AmbientLight(0xffffff, 2.0);
  scene.add(ambientLight);

  const directionalLight = new THREE.DirectionalLight(0xffffff, 1.0);
  directionalLight.position.set(10, 10, 10);
  scene.add(directionalLight);
}

const loader = new GLTFLoader(manager);

function loadGLB(file) {
  clearEvents();

  const url = URL.createObjectURL(file);

  if (currentModel) {
    scene.remove(currentModel);
    currentModel = null;
  }

  if (currentMixer) {
    currentMixer.stopAllAction();
    currentMixer = null;
  }

  currentAction = null;
  animations = [];
  isPlaying = false;

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

init();