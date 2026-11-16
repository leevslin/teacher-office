// 教師辦公室：3D 辦公室畫面（three.js）
// createOffice(容器, { onPick(員工鍵名) }) → { update(狀態板), select(鍵名) }
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const STATUS = {
  idle:    { color: '#9aa0a6', text: '閒著' },
  working: { color: '#2f7de1', text: '工作中' },
  waiting: { color: '#e8930c', text: '等老師確認' },
  done:    { color: '#25a55f', text: '做完了' },
};
const CJK = '"Microsoft JhengHei","PingFang TC","Noto Sans TC",sans-serif';
const KAI = '"DFKai-SB","標楷體","BiauKai","KaiTi","Noto Serif TC",serif';

const PEOPLE = [
  { key: 'beike',  name: '芋圓', role: '備課', shirt: 0xa58bd1, hair: 0x3b2a20, style: 'bun',      seat: [-0.85, -1.2], face: 0, acc: 0xc9b3ec },
  { key: 'chuti',  name: '珍奶', role: '出題', shirt: 0xd6a77a, hair: 0x2a1a12, style: 'pigtails', seat: [0.85, -1.2],  face: 0, acc: 0x1e120c },
  { key: 'shenti', name: '仙草', role: '審題', shirt: 0x3e6b58, hair: 0x141414, style: 'short',    seat: [-0.85, 1.2],  face: Math.PI, glasses: true },
  { key: 'paiban', name: '豆花', role: '排版', shirt: 0xf1e3bd, hair: 0x5a3d26, style: 'bob',      seat: [0.85, 1.2],   face: Math.PI, acc: 0xf2b632 },
  { key: 'shuxue', name: '阿穎', role: '數學', shirt: 0x5b8fd6, hair: 0x2b1d14, style: 'pigtails', seat: [-2.55, -1.2], face: 0, acc: 0xf4d35e },
];

function canvasTex(w, h, draw) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  const g = c.getContext('2d'); draw(g, w, h);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
  t.userData = { canvas: c, ctx: g };
  return t;
}
function roundRect(g, x, y, w, h, r) {
  g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r);
  g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath();
}
const mat = (color, o = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.8, metalness: 0, ...o });
function box(w, h, d, m, x = 0, y = 0, z = 0, parent) {
  const me = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m); me.position.set(x, y, z);
  me.castShadow = true; me.receiveShadow = true; if (parent) parent.add(me); return me;
}
function cyl(rt, rb, h, m, x = 0, y = 0, z = 0, parent, seg = 16) {
  const me = new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg), m); me.position.set(x, y, z);
  me.castShadow = true; me.receiveShadow = true; if (parent) parent.add(me); return me;
}

export function createOffice(el, { onPick } = {}) {
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
  el.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xe9e4da);
  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
  camera.position.set(4.5, 4.3, 5.6);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(-0.7, 1.0, -1.1);
  controls.enableDamping = true; controls.minDistance = 4; controls.maxDistance = 20;
  controls.maxPolarAngle = 1.42; controls.minAzimuthAngle = -0.35; controls.maxAzimuthAngle = 1.45;
  controls.update();

  // ---------- 光 ----------
  const hemi = new THREE.HemisphereLight(0xfffaf0, 0x8a8170, 0.9); scene.add(hemi);
  const sun = new THREE.DirectionalLight(0xfff1d6, 1.6);
  sun.position.set(-9, 9, 4); sun.castShadow = true;
  sun.shadow.mapSize.set(1536, 1536);
  Object.assign(sun.shadow.camera, { left: -10, right: 10, top: 10, bottom: -10, near: 1, far: 30 });
  sun.shadow.bias = -0.0005; scene.add(sun);
  const fill = new THREE.PointLight(0xfff4e0, 6, 14, 1.6); fill.position.set(0, 3.6, 0.5); scene.add(fill);

  // ---------- 房間 ----------
  const RX = 8, RZ = 6, RH = 4.2;
  const terrazzo = canvasTex(512, 512, (g, w, h) => {
    g.fillStyle = '#cfcac0'; g.fillRect(0, 0, w, h);
    const cols = ['#9b958a', '#e8e4dc', '#7d776d', '#b8b1a4', '#f4f1ea', '#a39070'];
    for (let i = 0; i < 2600; i++) {
      g.fillStyle = cols[i % cols.length]; const r = Math.random() * 3 + 0.6;
      g.beginPath(); g.arc(Math.random() * w, Math.random() * h, r, 0, 7); g.fill();
    }
    g.strokeStyle = 'rgba(80,70,60,.35)'; g.lineWidth = 3; g.strokeRect(0, 0, w, h);
  });
  terrazzo.wrapS = terrazzo.wrapT = THREE.RepeatWrapping; terrazzo.repeat.set(8, 6);
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(RX * 2, RZ * 2), mat(0xffffff, { map: terrazzo, roughness: 0.55 }));
  floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);

  const wallM = mat(0xf3eee2, { roughness: 0.95 }), skirtM = mat(0x8fb89a, { roughness: 0.9 });
  // 後牆
  box(RX * 2, RH, 0.15, wallM, 0, RH / 2, -RZ);
  box(RX * 2, 1.0, 0.17, skirtM, 0, 0.5, -RZ + 0.01);
  // 左牆（窗）
  const leftWall = new THREE.Group(); scene.add(leftWall);
  box(0.15, 1.0, RZ * 2, skirtM, -RX, 0.5, 0, leftWall);
  box(0.15, 0.25, RZ * 2, wallM, -RX, 1.12, 0, leftWall);
  box(0.15, RH - 3.3, RZ * 2, wallM, -RX, 3.3 + (RH - 3.3) / 2, 0, leftWall);
  const sky = canvasTex(512, 256, (g, w, h) => {
    const gr = g.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, '#8cc4ef'); gr.addColorStop(1, '#d9eefb');
    g.fillStyle = gr; g.fillRect(0, 0, w, h);
    g.fillStyle = 'rgba(255,255,255,.9)';
    [[90, 60], [300, 40], [430, 80]].forEach(([x, y]) => { for (let k = 0; k < 5; k++) { g.beginPath(); g.arc(x + k * 18, y + (k % 2) * 6, 22, 0, 7); g.fill(); } });
    g.fillStyle = '#5f9e5a';
    for (let x = -20; x < w + 40; x += 46) { g.beginPath(); g.arc(x, h - 10, 40 + (x * 7 % 23), Math.PI, 0); g.fill(); }
    g.fillStyle = '#4b7f47'; for (let x = 10; x < w; x += 70) { g.beginPath(); g.arc(x, h, 30, Math.PI, 0); g.fill(); }
  });
  const glassM = new THREE.MeshBasicMaterial({ map: sky });
  const frameM = mat(0xb9c2c6, { metalness: 0.3, roughness: 0.5 });
  [-3.2, 0, 3.2].forEach(z => {
    const p = new THREE.Mesh(new THREE.PlaneGeometry(2.9, 2.05), glassM); p.rotation.y = Math.PI / 2; p.position.set(-RX + 0.02, 2.27, z); scene.add(p);
    box(0.08, 2.15, 0.06, frameM, -RX + 0.06, 2.27, z - 1.45); box(0.08, 2.15, 0.06, frameM, -RX + 0.06, 2.27, z + 1.45);
    box(0.08, 0.06, 2.95, frameM, -RX + 0.06, 3.3, z); box(0.08, 0.06, 2.95, frameM, -RX + 0.06, 1.24, z);
    box(0.08, 2.05, 0.04, frameM, -RX + 0.07, 2.27, z);
  });

  // ---------- 黑板（狀態板） ----------
  const boardTex = canvasTex(1536, 640, () => {});
  const boardMesh = new THREE.Mesh(new THREE.PlaneGeometry(6.0, 2.5), new THREE.MeshStandardMaterial({ map: boardTex, roughness: 0.9 }));
  boardMesh.position.set(0.6, 2.35, -RZ + 0.09); boardMesh.userData.key = '__board'; scene.add(boardMesh);
  box(6.2, 0.1, 0.1, mat(0x8a6a48), 0.6, 1.07, -RZ + 0.13);
  box(6.2, 0.06, 0.04, mat(0x6f5236), 0.6, 3.62, -RZ + 0.1);
  [[-2, 'white'], [-1.7, '#ffe066'], [-1.45, '#ff8a8a']].forEach(([x, c]) => cyl(0.015, 0.015, 0.12, mat(c), x + 0.6, 1.14, -RZ + 0.15).rotation.z = Math.PI / 2);

  function drawBoard(state) {
    const { ctx: g, canvas: c } = boardTex.userData; const W = c.width, H = c.height;
    g.fillStyle = '#2f5847'; g.fillRect(0, 0, W, H);
    for (let i = 0; i < 1400; i++) { g.fillStyle = `rgba(255,255,255,${Math.random() * 0.035})`; g.fillRect(Math.random() * W, Math.random() * H, 30 + Math.random() * 90, 2); }
    g.strokeStyle = 'rgba(255,255,255,.12)'; g.lineWidth = 2; g.strokeRect(10, 10, W - 20, H - 20);
    const b = (state && state.board) || {};
    g.fillStyle = '#f7f5ec'; g.font = `bold 50px ${KAI}`; g.textBaseline = 'top';
    g.fillText('現在進度：' + (b.current || '—'), 46, 36);
    g.font = `30px ${KAI}`; g.fillStyle = 'rgba(247,245,236,.75)';
    const d = new Date(); g.fillText(`${d.getMonth() + 1} 月 ${d.getDate()} 日　星期${'日一二三四五六'[d.getDay()]}`, 46, 102);
    // 進度表
    const cols = ['單元', '備課', '學習單', '考卷'], cx = [46, 520, 680, 860], top = 160;
    g.font = `bold 32px ${KAI}`; g.fillStyle = '#ffe58a';
    cols.forEach((t, i) => g.fillText(t, cx[i], top));
    g.strokeStyle = 'rgba(247,245,236,.5)'; g.beginPath(); g.moveTo(40, top + 46); g.lineTo(1010, top + 46); g.stroke();
    const rows = Array.isArray(b.progress) ? b.progress.slice(-7) : [];
    g.font = `30px ${KAI}`;
    if (!rows.length) { g.fillStyle = 'rgba(247,245,236,.55)'; g.fillText('（還沒有進度，叫芋圓開始備課吧）', 46, top + 70); }
    rows.forEach((r, i) => {
      const y = top + 62 + i * 52;
      g.fillStyle = '#f7f5ec'; g.fillText(fit(g, r.unit || '', 450), cx[0], y);
      ['備課', '學習單', '考卷'].forEach((k, j) => {
        const v = r[k] || ''; g.fillStyle = /完成|已排版|已審/.test(v) ? '#a6f0b5' : /中|待/.test(v) ? '#ffd27a' : '#f7f5ec';
        g.fillText(fit(g, v || '·', 160), cx[j + 1], y);
      });
    });
    // 便條
    const notes = Array.isArray(b.notes) ? b.notes.slice(0, 5) : [];
    const nc = ['#fff27a', '#ffc6d9', '#bfe8ff', '#c8f2b8', '#ffd9a8'];
    notes.forEach((n, i) => {
      const x = 1080 + (i % 2) * 220, y = 40 + Math.floor(i / 2) * 195, rot = ((i * 37) % 7 - 3) * 0.02;
      g.save(); g.translate(x + 100, y + 85); g.rotate(rot); g.translate(-100, -85);
      g.shadowColor = 'rgba(0,0,0,.35)'; g.shadowBlur = 8; g.shadowOffsetY = 4;
      g.fillStyle = nc[i % nc.length]; g.fillRect(0, 0, 200, 170); g.shadowColor = 'transparent';
      g.fillStyle = '#d33'; g.beginPath(); g.arc(100, 14, 9, 0, 7); g.fill();
      g.fillStyle = '#333'; g.font = `26px ${CJK}`; wrap(g, String(n), 14, 40, 174, 32, 4);
      g.restore();
    });
    boardTex.needsUpdate = true;
  }
  function fit(g, s, w) { if (g.measureText(s).width <= w) return s; while (s.length && g.measureText(s + '…').width > w) s = s.slice(0, -1); return s + '…'; }
  function wrap(g, s, x, y, w, lh, max) {
    let line = '', n = 0;
    for (const ch of s) {
      if (g.measureText(line + ch).width > w) { g.fillText(n === max - 1 ? fit(g, line + ch + '…', w) : line, x, y); y += lh; line = ''; if (++n >= max) return; }
      line += ch;
    }
    if (line) g.fillText(line, x, y);
  }

  // ---------- 牆上的東西：臺灣地圖、課表、時鐘 ----------
  const mapTex = canvasTex(400, 560, (g, w, h) => {
    g.fillStyle = '#f9f6ee'; g.fillRect(0, 0, w, h); g.strokeStyle = '#7a6a55'; g.lineWidth = 10; g.strokeRect(5, 5, w - 10, h - 10);
    g.fillStyle = '#cfe6f2'; g.fillRect(20, 70, w - 40, h - 90);
    g.fillStyle = '#333'; g.font = `bold 40px ${KAI}`; g.textAlign = 'center'; g.fillText('臺灣全圖', w / 2, 52);
    const pts = [[121.55, 25.3], [121.95, 25.02], [121.85, 24.6], [121.82, 24.3], [121.6, 23.9], [121.48, 23.4], [121.3, 22.95], [121.0, 22.6], [120.88, 22.05], [120.75, 21.92], [120.62, 22.3], [120.32, 22.58], [120.15, 23.0], [120.08, 23.45], [120.2, 23.9], [120.48, 24.3], [120.7, 24.68], [121.02, 25.02], [121.3, 25.2]];
    const P = ([lo, la]) => [70 + (lo - 119.4) * 120, 110 + (25.5 - la) * 115];
    g.beginPath(); pts.forEach((p, i) => { const [x, y] = P(p); i ? g.lineTo(x, y) : g.moveTo(x, y); }); g.closePath();
    g.fillStyle = '#9ccf88'; g.fill(); g.strokeStyle = '#4c7a3f'; g.lineWidth = 3; g.stroke();
    g.strokeStyle = '#a9773f'; g.lineWidth = 7; g.lineCap = 'round'; g.beginPath();
    [[121.45, 24.9], [121.25, 24.3], [121.05, 23.6], [120.9, 22.8], [120.82, 22.2]].forEach((p, i) => { const [x, y] = P(p); i ? g.lineTo(x, y) : g.moveTo(x, y); }); g.stroke();
    g.fillStyle = '#9ccf88'; [[119.58, 23.57], [119.65, 23.5], [119.52, 23.42]].forEach(p => { const [x, y] = P(p); g.beginPath(); g.arc(x, y, 7, 0, 7); g.fill(); });
    g.fillStyle = '#c0392b'; [[121.52, 25.04], [120.68, 24.15], [120.3, 22.63], [121.3, 24.99]].forEach(p => { const [x, y] = P(p); g.beginPath(); g.arc(x, y, 6, 0, 7); g.fill(); });
    g.fillStyle = '#555'; g.font = `22px ${CJK}`; g.fillText('中央山脈', P([121.6, 23.5])[0] + 30, P([121.6, 23.5])[1]);
  });
  const mapMesh = new THREE.Mesh(new THREE.PlaneGeometry(1.15, 1.6), new THREE.MeshStandardMaterial({ map: mapTex, roughness: 0.9 }));
  mapMesh.position.set(-5.1, 2.5, -RZ + 0.09); scene.add(mapMesh);

  const ttTex = canvasTex(480, 400, () => {});
  function drawClasses(classes, prog) {
    const { ctx: g, canvas: c } = ttTex.userData, w = c.width, h = c.height;
    classes = classes && typeof classes === 'object' ? classes : { '五年級': ['508', '509', '511'], '六年級': ['602', '603', '604', '605'] };
    prog = prog && typeof prog === 'object' ? prog : {};
    g.fillStyle = '#fffdf6'; g.fillRect(0, 0, w, h); g.strokeStyle = '#5c6bc0'; g.lineWidth = 10; g.strokeRect(5, 5, w - 10, h - 10);
    g.fillStyle = '#283593'; g.font = `bold 36px ${KAI}`; g.textAlign = 'center'; g.fillText('各班進度', w / 2, 50);
    const all = Object.entries(classes).flatMap(([grade, list]) => (list || []).map(cl => [grade, cl]));
    const rowH = Math.min(44, (h - 90) / Math.max(1, all.length));
    all.forEach(([grade, cl], k) => {
      const y = 72 + k * rowH;
      g.fillStyle = grade.includes('六') ? '#c8e6c9' : '#ffe0b2'; roundRect(g, 20, y, 76, rowH - 6, 8); g.fill();
      g.fillStyle = '#333'; g.font = `bold 26px ${CJK}`; g.textAlign = 'center'; g.fillText(String(cl), 58, y + rowH * 0.62);
      g.textAlign = 'left'; g.font = `24px ${CJK}`; g.fillStyle = prog[cl] ? '#333' : '#aaa';
      g.fillText(fit(g, prog[cl] || '還沒回報', w - 130), 108, y + rowH * 0.62);
    });
    ttTex.needsUpdate = true;
  }
  drawClasses(null);
  const tt = new THREE.Mesh(new THREE.PlaneGeometry(1.32, 1.1), new THREE.MeshStandardMaterial({ map: ttTex, roughness: 0.9 }));
  tt.position.set(5.0, 2.55, -RZ + 0.09); tt.userData.key = '__classes'; scene.add(tt);

  const clockTex = canvasTex(256, 256, () => {});
  function drawClock() {
    const { ctx: g } = clockTex.userData, d = new Date();
    g.clearRect(0, 0, 256, 256); g.fillStyle = '#fff'; g.beginPath(); g.arc(128, 128, 120, 0, 7); g.fill();
    g.lineWidth = 12; g.strokeStyle = '#3b4b5a'; g.stroke();
    g.fillStyle = '#333'; for (let i = 0; i < 12; i++) { const a = i * Math.PI / 6; g.fillRect(128 + Math.sin(a) * 96 - 3, 128 - Math.cos(a) * 96 - 3, 6, 6); }
    const hand = (a, len, wdt, col) => { g.strokeStyle = col; g.lineWidth = wdt; g.lineCap = 'round'; g.beginPath(); g.moveTo(128, 128); g.lineTo(128 + Math.sin(a) * len, 128 - Math.cos(a) * len); g.stroke(); };
    hand((d.getHours() % 12 + d.getMinutes() / 60) * Math.PI / 6, 58, 9, '#222');
    hand(d.getMinutes() * Math.PI / 30, 88, 6, '#222');
    hand(d.getSeconds() * Math.PI / 30, 96, 2, '#d33');
    clockTex.needsUpdate = true;
  }
  drawClock();
  const clock = new THREE.Mesh(new THREE.CircleGeometry(0.33, 40), new THREE.MeshBasicMaterial({ map: clockTex, transparent: true }));
  clock.position.set(-3.3, 3.55, -RZ + 0.1); scene.add(clock);

  // ---------- 書櫃、地球儀、植物 ----------
  const shelf = new THREE.Group(); shelf.position.set(6.6, 0, -4.6); scene.add(shelf);
  const woodM = mat(0xa47a52), woodDark = mat(0x7c5a3a);
  box(1.8, 2.2, 0.05, woodDark, 0, 1.1, -0.25, shelf);
  box(0.05, 2.2, 0.55, woodM, -0.9, 1.1, 0, shelf); box(0.05, 2.2, 0.55, woodM, 0.9, 1.1, 0, shelf);
  [0.05, 0.6, 1.15, 1.7, 2.2].forEach(y => box(1.85, 0.05, 0.55, woodM, 0, y, 0, shelf));
  const binderLabels = ['五上', '五下', '六上', '六下', '題庫', '考卷', '教案', '研習'];
  const binderCols = [0xe76f51, 0xf4a261, 0x2a9d8f, 0x264653, 0x8d6cab, 0xc0392b, 0x3d5a98, 0x6a994e];
  [0.08, 0.63, 1.18].forEach((y, row) => {
    let x = -0.82;
    for (let i = 0; i < 9 && x < 0.8; i++) {
      const idx = (row * 3 + i) % binderCols.length, w = 0.09 + ((i * 13 + row * 7) % 5) * 0.015, hgt = 0.38 + ((i * 7 + row) % 4) * 0.04;
      const label = row < 2 && i < 4 ? binderLabels[(row * 4 + i) % binderLabels.length] : null;
      let m = mat(binderCols[idx]);
      if (label) {
        const t = canvasTex(64, 256, (g, w2, h2) => { g.fillStyle = '#' + binderCols[idx].toString(16).padStart(6, '0'); g.fillRect(0, 0, w2, h2); g.fillStyle = '#fff'; g.fillRect(8, 40, 48, 150); g.fillStyle = '#222'; g.font = `bold 40px ${KAI}`; g.textAlign = 'center'; [...label].forEach((ch, k) => g.fillText(ch, 32, 100 + k * 50)); });
        m = [m, m, m, m, new THREE.MeshStandardMaterial({ map: t, roughness: 0.8 }), m];
      }
      const bk = new THREE.Mesh(new THREE.BoxGeometry(w, hgt, 0.4), m); bk.position.set(x + w / 2, y + 0.025 + hgt / 2, 0.02);
      bk.castShadow = true; shelf.add(bk); x += w + 0.012;
    }
  });
  // 地球儀
  const globeTex = canvasTex(512, 256, (g, w, h) => {
    g.fillStyle = '#3a86c8'; g.fillRect(0, 0, w, h); g.fillStyle = '#7cb76b';
    [[90, 70, 60, 40], [140, 150, 35, 55], [260, 60, 70, 35], [280, 140, 40, 50], [380, 80, 80, 45], [430, 170, 35, 20], [400, 120, 6, 9]].forEach(([x, y, rx, ry]) => { g.beginPath(); g.ellipse(x, y, rx, ry, 0.3, 0, 7); g.fill(); });
  });
  const globe = new THREE.Mesh(new THREE.SphereGeometry(0.22, 32, 20), new THREE.MeshStandardMaterial({ map: globeTex, roughness: 0.5 }));
  globe.position.set(0.45, 2.55, 0); globe.rotation.z = 0.41; shelf.add(globe);
  cyl(0.12, 0.15, 0.05, mat(0x6b4f33), 0.45, 2.25, 0, shelf); cyl(0.015, 0.015, 0.1, mat(0xb08d57, { metalness: 0.6 }), 0.45, 2.31, 0, shelf);
  const ring = new THREE.Mesh(new THREE.TorusGeometry(0.26, 0.01, 8, 40, Math.PI), mat(0xb08d57, { metalness: 0.6, roughness: 0.3 }));
  ring.position.set(0.45, 2.55, 0); ring.rotation.z = Math.PI / 2 + 0.41; shelf.add(ring);

  function plant(x, z, s = 1) {
    const p = new THREE.Group(); p.position.set(x, 0, z); p.scale.setScalar(s); scene.add(p);
    cyl(0.2, 0.15, 0.4, mat(0xc9734a), 0, 0.2, 0, p);
    const lm = mat(0x3f8f4f, { roughness: 0.7 });
    for (let i = 0; i < 9; i++) { const l = new THREE.Mesh(new THREE.SphereGeometry(0.16, 10, 8), lm); l.scale.set(1, 1.8, 0.5); const a = i * 0.7; l.position.set(Math.cos(a) * 0.14, 0.62 + (i % 3) * 0.14, Math.sin(a) * 0.14); l.rotation.set(Math.sin(a) * 0.5, a, Math.cos(a) * 0.5); l.castShadow = true; p.add(l); }
  }
  plant(-7.3, -5.3, 1.2); plant(7.3, 2.6, 1);

  // ---------- 桌子 ----------
  const deskTop = mat(0xc8a27a, { roughness: 0.6 }), deskBody = mat(0x8e9aa3, { metalness: 0.25, roughness: 0.6 });
  const deskGroup = new THREE.Group(); scene.add(deskGroup);
  const monitors = {};
  function desk(x, z, faceZ, key) {
    const d = new THREE.Group(); d.position.set(x, 0, z); deskGroup.add(d);
    const near = -faceZ;   // 人坐的那一邊
    box(1.6, 0.05, 0.8, deskTop, 0, 0.76, 0, d);
    box(0.45, 0.7, 0.75, deskBody, 0.55, 0.36, 0, d);
    box(0.04, 0.7, 0.75, deskBody, -0.77, 0.36, 0, d);
    box(1.5, 0.35, 0.03, deskBody, 0, 0.55, -0.37 * near, d);
    [0.18, 0.4, 0.6].forEach(y => box(0.4, 0.004, 0.01, mat(0x555555), 0.55, y, 0.38 * near, d));
    // 螢幕
    const mon = new THREE.Group(); mon.position.set(-0.05, 0.79, -0.2 * near); if (near < 0) mon.rotation.y = Math.PI; d.add(mon);
    box(0.25, 0.02, 0.16, mat(0x333333), 0, 0.01, 0, mon); box(0.04, 0.22, 0.04, mat(0x333333), 0, 0.12, -0.02, mon);
    box(0.62, 0.38, 0.03, mat(0x222222), 0, 0.42, 0, mon);
    const scr = new THREE.Mesh(new THREE.PlaneGeometry(0.57, 0.33), new THREE.MeshStandardMaterial({ color: 0x1a2430, emissive: 0x000000, roughness: 0.3 }));
    scr.position.set(0, 0.42, 0.017); mon.add(scr); monitors[key] = scr;
    box(0.44, 0.02, 0.14, mat(0x2c2c2c), -0.05, 0.79, 0.14 * near, d);
    // 桌上的紙、書、杯子
    const paperM = mat(0xfafafa);
    for (let i = 0; i < 4; i++) { const p = box(0.21, 0.004, 0.29, paperM, 0.52, 0.79 + i * 0.006, 0.05 * faceZ, d); p.rotation.y = (i - 1.5) * 0.08; }
    cyl(0.045, 0.04, 0.1, mat([0xe63946, 0x457b9d, 0xf1faee, 0xffb703, 0x8ecae6][Object.keys(monitors).length - 1] ?? 0xffffff), -0.62, 0.84, 0.18 * faceZ, d);
    d.traverse(o => { o.userData.key = key; });
    return d;
  }
  const desks = {};
  PEOPLE.forEach(p => { const fz = p.seat[1] < 0 ? 1 : -1; desks[p.key] = desk(p.seat[0], p.seat[1] < 0 ? -0.42 : 0.42, fz, p.key); });
  // 各自桌上的小東西
  const red = mat(0xd62828);
  for (let i = 0; i < 4; i++) { const pen = cyl(0.008, 0.008, 0.16, red, 0.16 + i * 0.03, 0.8, 0.3, desks.shenti); pen.rotation.z = Math.PI / 2; pen.rotation.y = i * 0.3; }
  const openBook = new THREE.Group(); openBook.position.set(0.5, 0.8, -0.1); desks.beike.add(openBook);
  [-1, 1].forEach(s => { const pg = box(0.2, 0.01, 0.28, mat(0xfffbef), s * 0.1, 0, 0, openBook); pg.rotation.z = -s * 0.08; });
  ['#fff27a', '#ffc6d9', '#bfe8ff'].forEach((c, i) => box(0.07, 0.003, 0.07, mat(c), -0.65 + i * 0.08, 0.8, -0.3, desks.chuti));
  // 阿穎桌上：直尺、量角器、三角板
  box(0.32, 0.004, 0.04, mat(0xffe08a), 0.5, 0.8, -0.28, desks.shuxue).rotation.y = 0.2;
  { const prot = new THREE.Mesh(new THREE.CircleGeometry(0.09, 24, 0, Math.PI), new THREE.MeshStandardMaterial({ color: 0xbfe6ff, transparent: true, opacity: 0.75, side: THREE.DoubleSide }));
    prot.rotation.x = -Math.PI / 2; prot.position.set(-0.62, 0.795, -0.25); desks.shuxue.add(prot);
    const tri = new THREE.Shape(); tri.moveTo(0, 0); tri.lineTo(0.16, 0); tri.lineTo(0, 0.1); tri.lineTo(0, 0);
    const sq = new THREE.Mesh(new THREE.ShapeGeometry(tri), new THREE.MeshStandardMaterial({ color: 0xffc1d6, transparent: true, opacity: 0.8, side: THREE.DoubleSide }));
    sq.rotation.x = -Math.PI / 2; sq.position.set(-0.45, 0.796, -0.32); desks.shuxue.add(sq); }
  // 印表機（排版旁）
  const printer = new THREE.Group(); printer.position.set(2.25, 0, 1.25); scene.add(printer);
  box(0.6, 0.7, 0.5, mat(0x9aa5ad, { metalness: 0.2 }), 0, 0.35, 0, printer);
  box(0.55, 0.28, 0.45, mat(0xe7e7e7), 0, 0.84, 0, printer);
  box(0.4, 0.02, 0.2, mat(0xfafafa), 0, 0.99, 0.12, printer);
  const printLed = new THREE.Mesh(new THREE.SphereGeometry(0.015, 8, 8), new THREE.MeshBasicMaterial({ color: 0x33dd66 })); printLed.position.set(0.2, 0.92, 0.23); printer.add(printLed);
  printer.traverse(o => { o.userData.key = 'paiban'; });

  // 老師的座位（靠窗）
  const td = new THREE.Group(); td.position.set(-6.1, 0, 1.6); td.rotation.y = Math.PI / 2; scene.add(td);
  box(1.6, 0.05, 0.8, deskTop, 0, 0.76, 0, td); box(0.45, 0.7, 0.75, deskBody, 0.55, 0.36, 0, td); box(0.04, 0.7, 0.75, deskBody, -0.77, 0.36, 0, td);
  const plate = canvasTex(256, 96, (g, w, h) => { g.fillStyle = '#7a4b2a'; g.fillRect(0, 0, w, h); g.fillStyle = '#f5e6c8'; g.font = `bold 52px ${KAI}`; g.textAlign = 'center'; g.fillText('老師', w / 2, 66); });
  const pm = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.12, 0.05), [mat(0x7a4b2a), mat(0x7a4b2a), mat(0x7a4b2a), mat(0x7a4b2a), new THREE.MeshStandardMaterial({ map: plate }), mat(0x7a4b2a)]);
  pm.position.set(-0.3, 0.85, 0.3); td.add(pm);
  cyl(0.05, 0.045, 0.11, mat(0xffffff), 0.3, 0.84, 0.15, td);
  for (let i = 0; i < 6; i++) box(0.22, 0.004, 0.3, mat(0xfafafa), 0.45, 0.79 + i * 0.006, 0.05, td).rotation.y = i * 0.05;
  const tchair = makeChair(); tchair.position.set(0, 0, 0.85); tchair.rotation.y = Math.PI; td.add(tchair);

  // ---------- 人 ----------
  function makeChair() {
    const c = new THREE.Group(), cm = mat(0x3c4650, { roughness: 0.6 });
    box(0.5, 0.07, 0.48, cm, 0, 0.47, 0, c); box(0.48, 0.5, 0.06, cm, 0, 0.8, -0.24, c);
    cyl(0.025, 0.025, 0.38, mat(0x666666, { metalness: 0.5 }), 0, 0.26, 0, c);
    for (let i = 0; i < 5; i++) { const leg = box(0.3, 0.03, 0.04, mat(0x555555, { metalness: 0.5 }), 0, 0.05, 0, null); const g = new THREE.Group(); g.rotation.y = i * Math.PI * 2 / 5; leg.position.x = 0.15; g.add(leg); c.add(g); }
    return c;
  }
  const people = {};
  const skin = mat(0xffd9bd, { roughness: 0.65 });
  const blushM = new THREE.MeshBasicMaterial({ color: 0xff8fa3, transparent: true, opacity: 0.55, depthWrite: false });
  const eyeM = new THREE.MeshStandardMaterial({ color: 0x1b1410, roughness: 0.25 });
  const shineM = new THREE.MeshBasicMaterial({ color: 0xffffff });
  PEOPLE.forEach(p => {
    const chair = makeChair(); chair.position.set(p.seat[0], 0, p.seat[1]); chair.rotation.y = p.face; scene.add(chair);
    chair.traverse(o => { o.userData.key = p.key; });
    const g = new THREE.Group(); g.position.set(p.seat[0], 0, p.seat[1]); g.rotation.y = p.face; scene.add(g);
    const shirt = mat(p.shirt, { roughness: 0.8 }), pants = mat(0x4a4f5e);
    // 短短的腿（髖、膝蓋可以轉：坐著彎、站著直、走路擺）
    const legs = [];
    [-0.09, 0.09].forEach(x => {
      const hip = new THREE.Group(); hip.position.set(x, 0.54, -0.02); g.add(hip);
      box(0.12, 0.3, 0.12, pants, 0, -0.15, 0, hip);
      const knee = new THREE.Group(); knee.position.y = -0.3; hip.add(knee);
      box(0.11, 0.34, 0.11, pants, 0, -0.17, 0, knee);
      const shoe = new THREE.Mesh(new THREE.SphereGeometry(0.075, 12, 10), mat(0x6b4a3a)); shoe.scale.set(1, 0.6, 1.4); shoe.position.set(0, -0.36, 0.04); shoe.castShadow = true; knee.add(shoe);
      hip.rotation.x = -Math.PI / 2; knee.rotation.x = Math.PI / 2;
      legs.push({ hip, knee });
    });
    const body = new THREE.Group(); body.position.set(0, 0.56, -0.02); g.add(body);
    const torso = new THREE.Mesh(new THREE.CapsuleGeometry(0.17, 0.16, 6, 16), shirt); torso.position.y = 0.2; torso.scale.set(1, 1, 0.85); torso.castShadow = true; body.add(torso);
    // 大大的頭
    const head = new THREE.Group(); head.position.y = 0.62; body.add(head);
    const hd = new THREE.Mesh(new THREE.SphereGeometry(0.27, 32, 24), skin); hd.castShadow = true; head.add(hd);
    const hairM = mat(p.hair, { roughness: 0.75 });
    const cap = new THREE.Mesh(new THREE.SphereGeometry(0.286, 32, 20, 0, Math.PI * 2, 0, Math.PI * 0.52), hairM);
    cap.rotation.x = -0.32; cap.position.set(0, 0.015, -0.01); cap.castShadow = true; head.add(cap);
    [-0.12, 0, 0.12].forEach((x, k) => { const b = new THREE.Mesh(new THREE.SphereGeometry(0.1, 14, 10), hairM); b.scale.set(1.15, 0.55, 0.6); b.position.set(x, 0.17 - Math.abs(x) * 0.25, 0.2 - Math.abs(x) * 0.15); b.rotation.z = -x * 2; head.add(b); });
    const backHair = (y0, y1) => { const m = new THREE.Mesh(new THREE.SphereGeometry(0.29, 28, 16, Math.PI, Math.PI, y0, y1), hairM); m.castShadow = true; head.add(m); return m; };
    if (p.style === 'bun') {
      backHair(Math.PI * 0.2, Math.PI * 0.45);
      const bun = new THREE.Mesh(new THREE.SphereGeometry(0.11, 18, 14), hairM); bun.position.set(0, 0.29, -0.06); head.add(bun);
      const tie = new THREE.Mesh(new THREE.TorusGeometry(0.075, 0.018, 8, 20), mat(p.acc)); tie.rotation.x = Math.PI / 2 + 0.3; tie.position.set(0, 0.23, -0.05); head.add(tie);
    } else if (p.style === 'pigtails') {
      backHair(Math.PI * 0.2, Math.PI * 0.4);
      [-1, 1].forEach(sd => {
        const pt = new THREE.Mesh(new THREE.SphereGeometry(0.1, 16, 12), hairM); pt.position.set(sd * 0.27, 0.12, -0.06); head.add(pt);
        for (let k = 0; k < 3; k++) { const pearl = new THREE.Mesh(new THREE.SphereGeometry(0.03, 10, 8), mat(p.acc, { roughness: 0.2 })); pearl.position.set(sd * (0.33 + k * 0.012), 0.04 - k * 0.07, -0.06); head.add(pearl); }
      });
    } else if (p.style === 'bob') {
      backHair(Math.PI * 0.18, Math.PI * 0.55).scale.set(1.04, 1, 1.04);
      [-1, 1].forEach(sd => { const sh = new THREE.Mesh(new THREE.SphereGeometry(0.1, 12, 10), hairM); sh.scale.set(0.6, 1.4, 0.9); sh.position.set(sd * 0.24, -0.04, 0.05); head.add(sh); });
      const clip = box(0.1, 0.035, 0.03, mat(p.acc, { roughness: 0.3 }), 0.15, 0.2, 0.19, head); clip.rotation.z = -0.5; clip.castShadow = false;
    } else {
      backHair(Math.PI * 0.2, Math.PI * 0.3);
      const tuft = new THREE.Mesh(new THREE.ConeGeometry(0.035, 0.12, 8), hairM); tuft.position.set(0.02, 0.31, 0.02); tuft.rotation.z = -0.4; head.add(tuft);
    }
    // 閃亮亮的眼睛、腮紅、笑臉
    [-1, 1].forEach(sd => {
      const e = new THREE.Mesh(new THREE.SphereGeometry(0.042, 14, 12), eyeM); e.scale.set(0.9, 1.15, 0.55); e.position.set(sd * 0.095, 0.0, 0.248); head.add(e);
      const s1 = new THREE.Mesh(new THREE.SphereGeometry(0.014, 8, 6), shineM); s1.position.set(sd * 0.095 + 0.014, 0.018, 0.27); head.add(s1);
      const s2 = new THREE.Mesh(new THREE.SphereGeometry(0.007, 6, 6), shineM); s2.position.set(sd * 0.095 - 0.012, -0.016, 0.27); head.add(s2);
      const bl = new THREE.Mesh(new THREE.CircleGeometry(0.042, 20), blushM); bl.position.set(sd * 0.165, -0.065, 0.222); bl.rotation.y = sd * 0.62; bl.scale.set(1.2, 0.75, 1); head.add(bl);
    });
    const mouth = new THREE.Mesh(new THREE.TorusGeometry(0.032, 0.008, 6, 16, Math.PI), mat(0x9a3b3b)); mouth.rotation.z = Math.PI; mouth.position.set(0, -0.075, 0.262); head.add(mouth);
    const mouthO = new THREE.Mesh(new THREE.SphereGeometry(0.022, 10, 8), mat(0x9a3b3b)); mouthO.scale.set(1, 1.2, 0.4); mouthO.position.set(0, -0.09, 0.258); mouthO.visible = false; head.add(mouthO);
    if (p.glasses) {
      const gm = mat(0x2b2b2b, { metalness: 0.4, roughness: 0.3 });
      [-1, 1].forEach(sd => { const r = new THREE.Mesh(new THREE.TorusGeometry(0.058, 0.009, 8, 24), gm); r.position.set(sd * 0.095, 0.0, 0.275); head.add(r); });
      box(0.07, 0.01, 0.01, gm, 0, 0.012, 0.28, head).castShadow = false;
    }
    // 小短手（肩膀當轉軸）
    const arms = [];
    [-1, 1].forEach(sd => {
      const sh = new THREE.Group(); sh.position.set(sd * 0.2, 0.3, 0); body.add(sh);
      const up = new THREE.Mesh(new THREE.CapsuleGeometry(0.048, 0.1, 4, 8), shirt); up.position.y = -0.09; up.castShadow = true; sh.add(up);
      const el = new THREE.Group(); el.position.y = -0.18; sh.add(el);
      const fo = new THREE.Mesh(new THREE.CapsuleGeometry(0.042, 0.1, 4, 8), shirt); fo.position.y = -0.07; fo.castShadow = true; el.add(fo);
      const hand = new THREE.Mesh(new THREE.SphereGeometry(0.048, 12, 10), skin); hand.position.y = -0.16; el.add(hand);
      sh.rotation.x = -0.5; el.rotation.x = -1.0;
      arms.push({ sh, el, s: sd });
    });
    // 名牌
    const tagTex = canvasTex(320, 120, () => {});
    const tag = new THREE.Sprite(new THREE.SpriteMaterial({ map: tagTex, depthTest: false, transparent: true, sizeAttenuation: false }));
    tag.scale.set(0.15, 0.0563, 1); tag.position.set(p.seat[0], p.seat[1] < 0 ? 2.45 : 2.2, p.seat[1]); tag.renderOrder = 10; scene.add(tag);
    // 頭上的符號（? 或 ✓）
    const iconTex = canvasTex(128, 128, () => {});
    const icon = new THREE.Sprite(new THREE.SpriteMaterial({ map: iconTex, depthTest: false, transparent: true, sizeAttenuation: false }));
    icon.scale.set(0.042, 0.042, 1); icon.position.set(p.seat[0], 1.9, p.seat[1]); icon.visible = false; icon.renderOrder = 11; scene.add(icon);
    // 選取光圈
    const sel = new THREE.Mesh(new THREE.RingGeometry(0.42, 0.5, 40), new THREE.MeshBasicMaterial({ color: 0x2f7de1, transparent: true, opacity: 0.85 }));
    sel.rotation.x = -Math.PI / 2; sel.position.set(p.seat[0], 0.01, p.seat[1]); sel.visible = false; scene.add(sel);
    g.traverse(o => { o.userData.key = p.key; });
    people[p.key] = { ...p, g, body, head, torso, arms, legs, mouth, mouthO, tag, tagTex, icon, iconTex, sel, status: 'idle', task: '', changed: 0,
      W: { mode: 'seat', s: 0, path: [], back: false, next: performance.now() / 1000 + 6 + Math.random() * 20, spot: null, goal: { type: 'spot' }, chat: null },
      say: bubble(), sayUntil: 0 };
    drawTag(people[p.key]);
  });

  function drawTag(P) {
    const { ctx: g, canvas: c } = P.tagTex.userData, st = STATUS[P.status] || STATUS.idle;
    g.clearRect(0, 0, c.width, c.height);
    g.fillStyle = 'rgba(255,255,255,.93)'; roundRect(g, 4, 4, c.width - 8, c.height - 8, 22); g.fill();
    g.strokeStyle = st.color; g.lineWidth = 5; g.stroke();
    g.fillStyle = st.color; g.beginPath(); g.arc(34, 42, 12, 0, 7); g.fill();
    g.fillStyle = '#222'; g.font = `bold 36px ${CJK}`; g.textBaseline = 'middle'; g.fillText(P.name, 58, 43);
    g.fillStyle = '#666'; g.font = `24px ${CJK}`; g.fillText(P.role, 58 + g.measureText(P.name).width * 1.5 + 14, 45);
    g.fillStyle = st.color; g.font = `bold 24px ${CJK}`;
    const sub = P.task ? P.task.replace(/^(完成|待確認)：/, '') : st.text;
    g.fillText(fit(g, (P.task && P.status !== 'idle' ? st.text + '・' : '') + sub, c.width - 40), 22, 88);
    P.tagTex.needsUpdate = true;
  }
  function drawIcon(P, kind) {
    const { ctx: g, canvas: c } = P.iconTex.userData; g.clearRect(0, 0, c.width, c.height);
    if (!kind) { P.icon.visible = false; return; }
    const col = kind === '?' ? STATUS.waiting.color : kind === '✓' ? STATUS.done.color : STATUS.working.color;
    g.fillStyle = col; g.beginPath(); g.arc(64, 60, 50, 0, 7); g.fill();
    if (kind === '?') { g.beginPath(); g.moveTo(50, 104); g.lineTo(64, 124); g.lineTo(72, 104); g.fill(); }
    g.fillStyle = '#fff'; g.font = `bold 66px ${CJK}`; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.fillText(kind === '…' ? '···' : kind, 64, kind === '…' ? 52 : 62);
    P.iconTex.needsUpdate = true; P.icon.visible = true;
  }


  // ---------- 走路：繞過桌子的路線 ----------
  const OBST = [[-1.9, 2.7, -1.75, 1.75], [-3.45, -1.9, -1.75, 0.1], [-6.7, -4.8, 0.6, 2.6], [5.6, 7.6, -5.2, -4.2], [-7.7, -6.8, -5.8, -4.8], [6.8, 7.8, 2.1, 3.1]];
  const inObst = (x, z, pad = 0) => OBST.some(([a, b, c, d]) => x > a - pad && x < b + pad && z > c - pad && z < d + pad);
  const NODES = [];
  OBST.forEach(([a, b, c, d]) => [[a - 0.45, c - 0.45], [b + 0.45, c - 0.45], [a - 0.45, d + 0.45], [b + 0.45, d + 0.45]]
    .forEach(([x, z]) => { if (Math.abs(x) < 7.6 && Math.abs(z) < 5.6 && !inObst(x, z, 0.05)) NODES.push([x, z]); }));
  function clear(a, b) {
    const n = Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / 0.08);
    for (let i = 1; i < n; i++) { const t = i / n; if (inObst(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)) return false; }
    return true;
  }
  function route(a, b) {           // 最短的可走路線（不含起點）
    if (clear(a, b)) return [b];
    const pts = [a, b, ...NODES], N = pts.length, dist = Array(N).fill(1e9), prev = Array(N).fill(-1), done = Array(N).fill(false);
    dist[0] = 0;
    for (let it = 0; it < N; it++) {
      let u = -1; for (let i = 0; i < N; i++) if (!done[i] && (u < 0 || dist[i] < dist[u])) u = i;
      if (u < 0 || dist[u] >= 1e9) break; done[u] = true; if (u === 1) break;
      for (let v = 0; v < N; v++) if (!done[v] && clear(pts[u], pts[v])) {
        const d = dist[u] + Math.hypot(pts[v][0] - pts[u][0], pts[v][1] - pts[u][1]); if (d < dist[v]) { dist[v] = d; prev[v] = u; }
      }
    }
    if (prev[1] < 0) return [b];
    const out = []; for (let v = 1; v !== 0; v = prev[v]) out.unshift(pts[v]); return out;
  }
  function freePoint() {
    for (let k = 0; k < 50; k++) { const x = -7.2 + Math.random() * 14.4, z = -5.2 + Math.random() * 10.4; if (!inObst(x, z, 0.35)) return [x, z]; }
    return [4, 3.5];
  }
  // 員工起來走走會去的地方
  const SPOTS = [
    { p: [-6.9, -2.0], look: [-8, -2.0] }, { p: [-6.9, 3.6], look: [-8, 3.6] }, { p: [6.0, -3.7], look: [6.6, -4.6] },
    { p: [-0.6, -4.9], look: [-0.6, -6] }, { p: [1.9, -4.9], look: [1.9, -6] }, { p: [-5.1, -4.9], look: [-5.1, -6] },
    { p: [5.0, -4.9], look: [5.0, -6] }, { p: [3.4, 1.3], look: [2.25, 1.25] }, { p: [-4.4, 1.6], look: [-6.1, 1.6] },
    { p: [-6.3, -4.2], look: [-7.3, -5.3] },
  ];
  const faceTo = (from, to) => Math.atan2(to[0] - from[0], to[1] - from[1]);
  function turnToward(obj, ang, k) { let d = ang - obj.rotation.y; d = Math.atan2(Math.sin(d), Math.cos(d)); obj.rotation.y += d * Math.min(1, k); }
  function stepAlong(obj, W, speed, dt) {     // 沿路線走，走到終點回傳 true
    if (!W.path.length) return true;
    const tgt = W.path[0], dx = tgt[0] - obj.position.x, dz = tgt[1] - obj.position.z, d = Math.hypot(dx, dz);
    if (d < 0.05) { W.path.shift(); return !W.path.length; }
    const st = Math.min(d, speed * dt); obj.position.x += dx / d * st; obj.position.z += dz / d * st;
    turnToward(obj, Math.atan2(dx, dz), dt * 8);
    return false;
  }
  function seatPoints(P) {
    const f = [Math.sin(P.face), Math.cos(P.face)];
    return { seat: P.seat, stand: [P.seat[0] - f[0] * 0.55, P.seat[1] - f[1] * 0.55], aisle: [P.seat[0], P.seat[1] < 0 ? -2.25 : 2.25] };
  }
  function wander(P, now, dt, t, ph) {
    const W = P.W, sp = seatPoints(P), free = P.status === 'idle' || P.status === 'done';
    const lerpSeat = () => { P.g.position.x = sp.seat[0] + (sp.stand[0] - sp.seat[0]) * W.s; P.g.position.z = sp.seat[1] + (sp.stand[1] - sp.seat[1]) * W.s; };
    if (W.mode === 'seat') {
      W.s = 0;
      if (free && now > W.next && selected !== P.key) {
        const taken = Object.values(people).map(o => o.W.spot);
        const opts = SPOTS.filter(o => !taken.includes(o)); W.spot = opts[Math.floor(Math.random() * opts.length)];
        const partner = Object.values(people).find(o => o !== P && o.W.mode === 'dwell' && !o.W.chat);
        const petKeys = Object.keys(pets).filter(k => !pets[k].W.held);
        const r = Math.random();
        W.goal = { type: 'spot' };
        if (partner && r < 0.5) { W.goal = { type: 'chat', who: partner }; partner.W.chat = P; partner.W.until = now + 30; }
        else if (petKeys.length && r < 0.75) {
          const pk = pick1(petKeys); pets[pk].W.held = P.key; pets[pk].W.until = now + 60; W.goal = { type: 'pet', pet: pk };
        }
        W.mode = 'rise';
      }
    } else if (W.mode === 'rise') {
      W.s = Math.min(1, W.s + dt * 1.8); lerpSeat();     // 一邊站起來一邊往後退出座位
      if (W.s >= 1) {
        let goal = W.spot.p;
        const near = (x, z) => { const len = Math.hypot(x, z) || 1, cand = [x - x / len * 0.6, z - z / len * 0.6]; return inObst(cand[0], cand[1], 0.1) ? [x + 0.6, z] : cand; };
        if (W.goal.type === 'chat') { const q = W.goal.who.g.position; goal = near(q.x, q.z); }
        if (W.goal.type === 'pet') { const a = pets[W.goal.pet].root.position; goal = near(a.x, a.z); }
        W.path = [sp.aisle, ...route(sp.aisle, goal)]; W.mode = 'walk'; W.back = false;
      }
    } else if (W.mode === 'walk') {
      if (!W.back && !free) goBack(P);
      if (stepAlong(P.g, W, W.back && !free ? 1.4 : 0.8, dt)) {
        if (W.back) { W.mode = 'sit'; }
        else if (W.goal.type === 'chat' && W.goal.who.W.mode === 'dwell') {
          W.mode = 'chat'; W.until = now + 7.5; W.lineAt = 0; W.turn = 0; W.goal.who.W.until = now + 8;
        } else if (W.goal.type === 'pet') {
          W.mode = 'pet'; W.until = now + 5.5; speak(P, pick1(['好乖好乖～', '好可愛！', '摸摸頭～']));
          const A = pets[W.goal.pet]; setTimeout(() => speak(A, pick1(PET_LINES[A.kind])), 700);
        } else { W.mode = 'dwell'; W.until = now + 5 + Math.random() * 7; }
      }
    } else if (W.mode === 'dwell') {
      const lookAt = W.chat ? [W.chat.g.position.x, W.chat.g.position.z] : W.spot.look;
      turnToward(P.g, faceTo([P.g.position.x, P.g.position.z], lookAt), dt * 4);
      if (!free || now > W.until) goBack(P);
    } else if (W.mode === 'chat') {
      const q = W.goal.who, me = [P.g.position.x, P.g.position.z];
      turnToward(P.g, faceTo(me, [q.g.position.x, q.g.position.z]), dt * 4);
      if (now > W.lineAt) { const who = W.turn++ % 2 ? q : P; speak(who, pick1(LINES[who.key]), 2.1); W.lineAt = now + 2.3; }
      if (!free || now > W.until || q.W.mode !== 'dwell') { q.W.chat = null; q.W.until = Math.min(q.W.until, now + 1); goBack(P); }
    } else if (W.mode === 'pet') {
      const A = pets[W.goal.pet]; turnToward(P.g, faceTo([P.g.position.x, P.g.position.z], [A.root.position.x, A.root.position.z]), dt * 4);
      if (!free || now > W.until) { A.W.held = null; A.W.until = now + 1.5; goBack(P); }
    } else if (W.mode === 'sit') {
      turnToward(P.g, P.face, dt * 6);
      if (W.turned || Math.abs(Math.atan2(Math.sin(P.face - P.g.rotation.y), Math.cos(P.face - P.g.rotation.y))) < 0.05) {
        W.turned = true; P.g.rotation.y = P.face;
        W.s = Math.max(0, W.s - dt * 1.8); lerpSeat();   // 一邊往前一邊坐下
        if (W.s <= 0) { W.turned = false; W.mode = 'seat'; W.spot = null; W.next = now + 25 + Math.random() * 50; }
      }
    }
    P.g.position.y = 0.165 * W.s;
    return W.mode === 'walk';
  }
  function goBack(P) {
    const W = P.W, sp = seatPoints(P), cur = [P.g.position.x, P.g.position.z];
    if (W.goal && W.goal.type === 'pet' && pets[W.goal.pet].W.held === P.key) { pets[W.goal.pet].W.held = null; pets[W.goal.pet].W.until = performance.now() / 1000 + 1.5; }
    if (W.goal && W.goal.type === 'chat' && W.goal.who.W.chat === P) W.goal.who.W.chat = null;
    W.goal = { type: 'spot' }; W.chat = null;
    W.path = [...route(cur, sp.aisle), sp.stand]; W.back = true; W.mode = 'walk';
  }

  // ---------- 橘貓和黑柴 ----------
  function bubble() {
    const tx = canvasTex(512, 128, () => {});
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tx, depthTest: false, transparent: true, sizeAttenuation: false }));
    sp.scale.set(0.16, 0.04, 1); sp.renderOrder = 12; sp.visible = false; scene.add(sp);
    sp.setText = text => {
      const { ctx: g, canvas: c } = tx.userData, W = c.width, H = c.height;
      g.clearRect(0, 0, W, H); g.font = `bold 44px ${CJK}`;
      const bw = Math.min(W - 16, g.measureText(text).width + 60), x0 = (W - bw) / 2;
      g.fillStyle = '#fff'; roundRect(g, x0, 8, bw, H - 40, 30); g.fill();
      g.beginPath(); g.moveTo(W / 2 - 18, H - 33); g.lineTo(W / 2, H - 8); g.lineTo(W / 2 + 18, H - 33); g.fill();
      g.strokeStyle = '#d9cbb3'; g.lineWidth = 4; roundRect(g, x0, 8, bw, H - 40, 30); g.stroke();
      g.fillStyle = '#3a2f25'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(text, W / 2, 52);
      tx.needsUpdate = true;
    };
    return sp;
  }
  function speak(obj, text, secs = 2.2) { obj.say.setText(text); obj.sayUntil = performance.now() / 1000 + secs; }
  const LINES = {
    beike: ['這課的地圖好有趣', '板書黃色是必背的喔', '下一課要先讀課本', '這張老照片好懷念'],
    chuti: ['我想到一題超讚的！', '這題會不會太難…', '題組要找好文章', '答案位置要平均'],
    shenti: ['這個年代要再查一次。', '紅筆又沒水了…', '頁碼對過了嗎？', '這題答案只有一個嗎？'],
    paiban: ['這頁剛好排滿！', '標楷體 14 號～', '同一題不能跨頁', '印表機好像卡紙了'],
    shuxue: ['答案我算兩次了！', '分數要上下疊才清楚', '直式要留夠空間', '這題單位換算要小心'],
  };
  const pick1 = a => a[Math.floor(Math.random() * a.length)];
  const PET_LINES = { cat: ['呼嚕呼嚕♡', '喵♡', '喵～'], dog: ['汪♡', '汪汪！', '嗚～♡'], pom: ['汪♪', '嗯嗯～♡', '再摸一下♡'] };
  const PET_CLICK = { cat: ['喵～', '喵？', '呼嚕♡'], dog: ['汪！', '汪汪！', '嗚汪？'], pom: ['汪♪', '嘿嘿～', '要玩嗎？'] };
  // 頭上的小符號（像貼圖一樣）
  function emoteSprite() {
    const tx = canvasTex(128, 128, () => {});
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tx, depthTest: false, transparent: true, sizeAttenuation: false }));
    sp.scale.set(0.032, 0.032, 1); sp.renderOrder = 11; sp.visible = false; scene.add(sp);
    sp.cur = null;
    sp.setEmote = e => {
      if (sp.cur === e) return; sp.cur = e; sp.visible = !!e; if (!e) return;
      const { ctx: g } = tx.userData; g.clearRect(0, 0, 128, 128);
      const col = { '♡': '#ff5b7f', 'zZ': '#5b8def', '♪': '#f29a2e', '!': '#e8930c', '…': '#888' }[e] || '#555';
      g.font = `bold ${e === 'zZ' ? 64 : 92}px ${CJK}`; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.lineWidth = 10; g.strokeStyle = '#fff'; g.strokeText(e, 64, 68); g.fillStyle = col; g.fillText(e, 64, 68);
      tx.needsUpdate = true;
    };
    return sp;
  }
  // kind：cat 橘貓、dog 黑柴「黑糖」、pom 白博美「綿綿」
  function makePet(kind) {
    const isCat = kind === 'cat', isPom = kind === 'pom', root = new THREE.Group(); scene.add(root);
    const S = isCat ? 1 : isPom ? 0.95 : 1.25;
    const main = mat(isCat ? 0xf28a2e : isPom ? 0xfbfaf6 : 0x2a2522, { roughness: 0.9 });
    const belly = mat(isCat ? 0xfff1df : isPom ? 0xffffff : 0xe8b47a, { roughness: 0.9 });
    const dark = mat(isCat ? 0xc9631a : 0x161311);
    const body = new THREE.Group(); body.position.y = 0.2 * S; root.add(body);
    const torso = new THREE.Mesh(new THREE.SphereGeometry(0.12 * S, 20, 16), main);
    torso.scale.set(isPom ? 1.15 : 0.9, isPom ? 1.1 : 0.85, isPom ? 1.25 : 1.55); torso.castShadow = true; body.add(torso);
    const under = new THREE.Mesh(new THREE.SphereGeometry(0.11 * S, 16, 12), belly); under.scale.set(0.8, 0.6, 1.3); under.position.y = -0.04 * S; body.add(under);
    if (isCat) [-0.06, 0.02, 0.1].forEach(z => { const st = new THREE.Mesh(new THREE.TorusGeometry(0.105, 0.012, 6, 20, Math.PI), dark); st.position.set(0, 0.0, z); st.rotation.y = Math.PI / 2; st.scale.set(1, 0.95, 0.9); body.add(st); });
    if (isPom) {   // 蓬蓬的毛：一圈小毛球＋胸前一大團
      for (let k = 0; k < 14; k++) { const a = k / 14 * Math.PI * 2; const f = new THREE.Mesh(new THREE.SphereGeometry(0.05 * S, 10, 8), main); f.position.set(Math.cos(a) * 0.12 * S, Math.sin(a) * 0.1 * S + 0.02, Math.sin(a * 2) * 0.06 * S); f.castShadow = true; body.add(f); }
      const ruff = new THREE.Mesh(new THREE.SphereGeometry(0.1 * S, 16, 12), main); ruff.scale.set(1.25, 1.1, 0.8); ruff.position.set(0, 0.06 * S, 0.12 * S); body.add(ruff);
      const scarf = new THREE.Mesh(new THREE.TorusGeometry(0.075 * S, 0.016 * S, 8, 24), mat(0x7cc6e8)); scarf.rotation.x = Math.PI / 2 - 0.4; scarf.position.set(0, 0.1 * S, 0.17 * S); body.add(scarf);
    }
    // 頭
    const head = new THREE.Group(); head.position.set(0, (isPom ? 0.16 : 0.11) * S, (isPom ? 0.2 : 0.19) * S); body.add(head);
    const hd = new THREE.Mesh(new THREE.SphereGeometry((isPom ? 0.11 : 0.105) * S, 20, 16), main); hd.castShadow = true; head.add(hd);
    const muzzle = new THREE.Mesh(new THREE.SphereGeometry(0.05 * S, 12, 10), belly); muzzle.scale.set(1.2, 0.8, isCat ? 0.7 : isPom ? 0.75 : 1.1); muzzle.position.set(0, -0.03 * S, 0.085 * S); head.add(muzzle);
    const nose = new THREE.Mesh(new THREE.SphereGeometry(0.016 * S, 8, 6), mat(isCat ? 0xff8fa3 : 0x111111)); nose.position.set(0, -0.012 * S, (isCat ? 0.118 : isPom ? 0.122 : 0.135) * S); head.add(nose);
    const tongue = new THREE.Mesh(new THREE.SphereGeometry(0.015 * S, 8, 6), mat(0xff8fa3)); tongue.scale.set(1, 0.5, 1.2); tongue.position.set(0, -0.06 * S, 0.1 * S); tongue.visible = !isCat; head.add(tongue);
    const eyes = [];
    [-1, 1].forEach(sd => {
      const ear = new THREE.Mesh(new THREE.ConeGeometry((isPom ? 0.032 : 0.04) * S, (isPom ? 0.06 : 0.08) * S, 4), main);
      ear.position.set(sd * (isPom ? 0.065 : 0.06) * S, (isPom ? 0.1 : 0.095) * S, -0.005); ear.rotation.z = -sd * 0.25; head.add(ear);
      const e = new THREE.Mesh(new THREE.SphereGeometry(0.017 * S, 10, 8), eyeM); e.position.set(sd * 0.045 * S, 0.02 * S, 0.092 * S); head.add(e); eyes.push(e);
      const sh = new THREE.Mesh(new THREE.SphereGeometry(0.006 * S, 6, 6), shineM); sh.position.set(sd * 0.045 * S + 0.006, 0.027 * S, 0.105 * S); head.add(sh); eyes.push(sh);
      if (kind === 'dog') { const brow = new THREE.Mesh(new THREE.SphereGeometry(0.012 * S, 8, 6), belly); brow.position.set(sd * 0.045 * S, 0.052 * S, 0.088 * S); head.add(brow); }
      if (isPom) { const bl = new THREE.Mesh(new THREE.CircleGeometry(0.018 * S, 14), blushM); bl.position.set(sd * 0.072 * S, -0.02 * S, 0.083 * S); bl.rotation.y = sd * 0.6; head.add(bl); }
      if (isCat) for (let k = 0; k < 2; k++) { const wh = box(0.07, 0.003, 0.003, mat(0xffffff), sd * 0.07, -0.025 * S - k * 0.012, 0.09 * S, head); wh.rotation.z = sd * (k ? -0.15 : 0.15); wh.castShadow = false; }
    });
    // 腳
    const legsP = [];
    [[-1, 1], [1, 1], [-1, -1], [1, -1]].forEach(([sx, sz]) => {
      const piv = new THREE.Group(); piv.position.set(sx * 0.055 * S, -0.05 * S, sz * (isPom ? 0.08 : 0.11) * S); body.add(piv);
      cyl(0.024 * S, 0.022 * S, (isPom ? 0.1 : 0.14) * S, isCat || isPom ? main : belly, 0, -(isPom ? 0.05 : 0.07) * S, 0, piv, 8);
      const paw = new THREE.Mesh(new THREE.SphereGeometry(0.027 * S, 8, 6), belly); paw.position.y = -(isPom ? 0.1 : 0.14) * S; piv.add(paw);
      legsP.push({ piv, ph: (sx * sz > 0 ? 0 : Math.PI) });
    });
    // 尾巴
    const tail = new THREE.Group(); tail.position.set(0, 0.04 * S, (isPom ? -0.13 : -0.17) * S); body.add(tail);
    if (isCat) {
      let parent = tail;
      for (let k = 0; k < 6; k++) {
        const seg = new THREE.Group(); seg.position.set(0, k ? 0.045 : 0, k ? -0.01 : 0); seg.rotation.x = -0.28; parent.add(seg);
        const ball = new THREE.Mesh(new THREE.SphereGeometry(0.026 - k * 0.0015, 8, 6), k % 2 ? dark : main); seg.add(ball); parent = seg;
      }
    } else if (isPom) {   // 翹在背上的蓬蓬尾
      [[0, 0.06, 0.0, 0.06], [0, 0.11, 0.04, 0.055], [0, 0.13, 0.09, 0.045]].forEach(([x, y, z, r]) => { const b = new THREE.Mesh(new THREE.SphereGeometry(r * S, 10, 8), main); b.position.set(x, y * S, z * S); b.castShadow = true; tail.add(b); });
    } else {
      const curl = new THREE.Mesh(new THREE.TorusGeometry(0.055 * S, 0.026 * S, 8, 16, Math.PI * 1.6), main); curl.rotation.set(0, Math.PI / 2, 0.6); curl.position.set(0, 0.07 * S, 0.03); tail.add(curl);
    }
    // 吃飯用的碗（吃東西時才出現）
    const bowl = new THREE.Group(); bowl.position.set(0, 0, (isPom ? 0.3 : 0.34) * S); bowl.visible = false; root.add(bowl);
    cyl(0.07, 0.055, 0.04, mat(isCat ? 0xe76f51 : isPom ? 0x7cc6e8 : 0xf4a261), 0, 0.02, 0, bowl, 16);
    const kib = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.055, 0.01, 16), mat(0x9c6b3c)); kib.position.y = 0.04; bowl.add(kib);
    const key = '__' + kind;
    root.traverse(o => { o.userData.key = key; });
    const start = freePoint(); root.position.set(start[0], 0, start[1]);
    return { kind, key, root, body, head, tail, legs: legsP, eyes, bowl, S, say: bubble(), sayUntil: 0, emo: emoteSprite(),
             W: { mode: 'rest', path: [], until: performance.now() / 1000 + 2 + Math.random() * 4, pose: 0, held: null, act: 'sit', actT: 0 } };
  }
  const pets = { __cat: makePet('cat'), __dog: makePet('dog'), __pom: makePet('pom') };
  const ACTS = { cat: ['sit', 'sit', 'sleep', 'eat'], dog: ['sit', 'sleep', 'belly', 'eat', 'spin'], pom: ['sit', 'spin', 'belly', 'sleep', 'eat', 'spin'] };
  const ACT_EMOTE = { sleep: 'zZ', belly: '♡', eat: '♪', spin: '!' };
  function petTick(A, now, dt, t) {
    const W = A.W, dogLike = A.kind !== 'cat';
    if (W.held) {
      const q = people[W.held]; W.mode = 'rest'; W.path = [];
      if (dogLike && W.act !== 'belly') { W.act = 'belly'; W.actT = now; }   // 被摸就翻肚討摸
      if (!dogLike) W.act = 'sit';
      if (q && W.act !== 'belly') turnToward(A.root, faceTo([A.root.position.x, A.root.position.z], [q.g.position.x, q.g.position.z]), dt * 4);
    }
    if (W.mode === 'rest') {
      W.pose = Math.min(1, W.pose + dt * 2);
      if (now > W.until && !W.held) {
        let goal;
        const r = Math.random(), walker = Object.values(people).find(q => q.W.mode === 'walk' && !q.W.back);
        const pal = A.kind === 'dog' ? pick1([pets.__cat, pets.__pom]) : A.kind === 'pom' ? pets.__dog : null;
        if (dogLike && walker && r < 0.3) { const g = walker.g.position; goal = [g.x + 0.4, g.z + 0.4]; W.follow = walker.key; }
        else if (pal && r < 0.55) { const c = pal.root.position; goal = [c.x + 0.5, c.z + 0.4]; W.toPal = pal.key; }
        else if (r < 0.7) { const ps = Object.values(people), q = ps[Math.floor(Math.random() * ps.length)]; const sp = seatPoints(q); goal = [sp.aisle[0] + (Math.random() - 0.5), sp.aisle[1]]; }
        else goal = freePoint();
        if (inObst(goal[0], goal[1], 0.3)) goal = freePoint();
        W.path = route([A.root.position.x, A.root.position.z], goal); W.mode = 'walk'; W.act = 'walk';
      }
    } else {
      W.pose = Math.max(0, W.pose - dt * 3);
      if (W.follow && people[W.follow] && W.path.length) {     // 跟著人走：終點一直更新
        const g = people[W.follow].g.position; W.path[W.path.length - 1] = [g.x + 0.4, g.z + 0.4];
      }
      if (stepAlong(A.root, W, A.kind === 'cat' ? 0.55 : (W.follow || W.toPal ? 0.95 : A.kind === 'pom' ? 0.65 : 0.75), dt)) {
        W.mode = 'rest'; W.until = now + (A.kind === 'cat' ? 6 + Math.random() * 12 : 4 + Math.random() * 8);
        W.act = pick1(ACTS[A.kind]); W.actT = now;
        if (W.follow && people[W.follow]) speak(A, A.kind === 'pom' ? '汪♪' : '汪！');
        if (W.toPal) {
          const c = pets[W.toPal], d = Math.hypot(c.root.position.x - A.root.position.x, c.root.position.z - A.root.position.z);
          if (d < 1.0 && !c.W.held) {
            W.act = 'sit'; turnToward(A.root, faceTo([A.root.position.x, A.root.position.z], [c.root.position.x, c.root.position.z]), 1);
            speak(A, A.kind === 'pom' ? '一起玩嘛～' : '汪？');
            setTimeout(() => {
              if (c.kind === 'cat') speak(c, pick1(['喵？', '哈—！', '喵～']));
              else { speak(c, pick1(['汪♪', '來追我～', '汪！'])); if (c.W.mode === 'rest') { c.W.act = 'spin'; c.W.actT = performance.now() / 1000; } }
            }, 900);
          }
        }
        W.follow = null; W.toPal = null;
        if (W.act === 'spin') W.until = now + 2.2;
      }
    }
    // 姿勢
    const walking = W.mode === 'walk', sp = A.kind === 'cat' ? 9 : A.kind === 'pom' ? 13 : 11, act = walking ? 'walk' : W.act;
    let bodyY = 0.2 - W.pose * 0.06, rotX = A.kind === 'cat' ? -W.pose * 0.25 : 0, rotZ = 0, legScale = 1 - W.pose * 0.55, headX = 0, eyeY = 1;
    A.bowl.visible = act === 'eat';
    if (act === 'sleep') { bodyY = 0.12; rotX = 0; legScale = 0.25; headX = 0.35; eyeY = 0.15; }
    if (act === 'belly') { bodyY = 0.17; rotZ = Math.PI * 0.85; rotX = 0; legScale = 1; eyeY = 0.35; }
    if (act === 'eat') { headX = 0.55 + Math.sin(t * 10) * 0.1; }
    if (act === 'spin') A.root.rotation.y += dt * 7;
    A.legs.forEach((L, i) => {
      L.piv.rotation.x = walking ? Math.sin(t * sp + L.ph) * 0.55 : act === 'belly' ? Math.sin(t * 9 + L.ph) * 0.45 : 0;
      L.piv.scale.y = walking || act === 'belly' ? 1 : (i >= 2 || dogLike || act === 'sleep' ? legScale : 1);
    });
    A.body.position.y = A.S * bodyY + (walking ? Math.abs(Math.sin(t * sp)) * 0.01 : 0);
    A.body.rotation.x = rotX; A.body.rotation.z = rotZ;
    A.head.rotation.x = headX;
    A.eyes.forEach(e => { e.scale.y = eyeY * (e.geometry.parameters.radius > 0.01 ? 1.0 : 1); });
    if (A.kind === 'cat') { A.tail.rotation.y = Math.sin(t * (act === 'sleep' ? 0.6 : 1.8)) * 0.5; A.tail.rotation.x = act === 'sleep' ? 1.5 : 0; }
    else A.tail.rotation.z = Math.sin(t * (walking || act === 'spin' || W.held ? 20 : act === 'sleep' ? 2 : 8)) * 0.35;
    A.head.rotation.y = walking || act !== 'sit' ? 0 : Math.sin(t * 0.6 + (A.kind === 'cat' ? 0 : 2)) * 0.5;
    A.say.visible = now < A.sayUntil;
    if (A.say.visible) A.say.position.set(A.root.position.x, 0.75, A.root.position.z);
    const emote = W.held ? '♡' : walking ? (W.toPal || W.follow ? '!' : null) : ACT_EMOTE[act] || null;
    A.emo.setEmote(A.say.visible ? null : emote);
    if (A.emo.visible) A.emo.position.set(A.root.position.x + 0.12, 0.58 + Math.sin(t * 3) * 0.03 + (act === 'sleep' ? Math.sin(t) * 0.04 : 0), A.root.position.z);
  }

  // ---------- 點選 ----------
  const ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
  let hover = null, selected = null, downAt = null;
  function pick(ev) {
    const r = renderer.domElement.getBoundingClientRect();
    mouse.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(mouse, camera);
    const hits = ray.intersectObjects(scene.children, true);
    for (const h of hits) { if (h.object.userData.key) return h.object.userData.key; if (h.object === floor) return null; }
    return null;
  }
  renderer.domElement.addEventListener('pointerdown', e => { downAt = [e.clientX, e.clientY]; });
  renderer.domElement.addEventListener('pointerup', e => {
    if (!downAt || Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 5) return;
    const k = pick(e);
    if (k && pets[k]) {
      const A = pets[k]; speak(A, pick1(A.W.held ? PET_LINES[A.kind] : PET_CLICK[A.kind]));
      if (A.kind !== 'cat' && A.W.mode === 'rest' && !A.W.held) { A.W.act = pick1(['spin', 'belly']); A.W.actT = performance.now() / 1000; A.W.until = Math.max(A.W.until, A.W.actT + 2.5); }
      return;
    }
    if (k && people[k]) speak(people[k], pick1(['老師好！', '要交代什麼呢？', '我在這！', '來了來了～']), 1.8);
    if (k && onPick) onPick(k);
  });
  renderer.domElement.addEventListener('pointermove', e => {
    const k = pick(e); if (k !== hover) { hover = k; renderer.domElement.style.cursor = k ? 'pointer' : 'grab'; }
  });

  function select(key) {
    selected = key;
    Object.values(people).forEach(P => { P.sel.visible = P.key === key; });
  }

  // ---------- 狀態更新 ----------
  let lastBoard = '';
  function update(state) {
    if (!state) return;
    const st = state.staff || {};
    Object.values(people).forEach(P => {
      const s = st[P.key] || {};
      const status = STATUS[s.status] ? s.status : 'idle', task = s.task || '';
      if (status !== P.status || task !== P.task) {
        P.status = status; P.task = task; P.changed = performance.now(); drawTag(P);
        const kind = status === 'waiting' ? '?' : status === 'done' ? '✓' : status === 'working' ? '…' : null;
        drawIcon(P, kind);
        const scr = monitors[P.key];
        scr.material.emissive.set(status === 'working' ? 0x3d7bd9 : status === 'idle' ? 0x000000 : 0x1c3550);
        scr.material.emissiveIntensity = status === 'working' ? 0.9 : 0.5;
      }
    });
    const bj = JSON.stringify(state.board || {});
    if (bj !== lastBoard) { lastBoard = bj; drawBoard(state); drawClasses((state.board || {}).classes, (state.board || {}).classProgress); }
  }
  drawBoard(null);

  // ---------- 動畫 ----------
  const clk = new THREE.Clock();
  let lastSec = -1, evening = null;
  function frame() {
    const t = clk.getElapsedTime();
    controls.update();
    globe.rotation.y = t * 0.15;
    const now = performance.now() / 1000, dt = Math.min(0.05, now - (frame.last || now)); frame.last = now;
    Object.values(pets).forEach(A => petTick(A, now, dt, t));
    Object.values(people).forEach((P, i) => {
      const ph = i * 1.7;
      P.torso.scale.y = 1 + Math.sin(t * 1.6 + ph) * 0.012;
      const [L, R] = P.arms;
      const walking = wander(P, now, dt, t, ph), up = P.W.s;
      // 腿：坐著彎、站著直、走路擺
      P.legs.forEach((lg, k) => {
        const sw = walking ? Math.sin(t * 9 + k * Math.PI) * 0.5 : 0;
        lg.hip.rotation.x = -Math.PI / 2 * (1 - up) + sw;
        lg.knee.rotation.x = Math.PI / 2 * (1 - up) + (walking ? Math.max(0, Math.sin(t * 9 + k * Math.PI + 1.2)) * 0.6 : 0);
      });
      // 跟著人走的名牌、符號、光圈
      const gp = P.g.position, seated = P.W.mode === 'seat';
      P.tag.position.set(gp.x, seated ? (P.seat[1] < 0 ? 2.45 : 2.2) : 2.05, gp.z);
      P.icon.position.x = gp.x; P.icon.position.z = gp.z;
      P.sel.position.set(gp.x, 0.01, gp.z);
      P.say.visible = now < P.sayUntil;
      if (P.say.visible) { P.say.position.set(gp.x, seated ? 1.95 : 1.8, gp.z); P.tag.visible = false; } else P.tag.visible = true;
      if (up > 0.05) {
        L.sh.rotation.x = walking ? Math.sin(t * 9) * 0.5 : -0.1; R.sh.rotation.x = walking ? -Math.sin(t * 9) * 0.5 : -0.1;
        L.el.rotation.x = -0.3; R.el.rotation.x = -0.3; R.sh.rotation.z = 0; L.sh.rotation.z = 0.12; R.sh.rotation.z = -0.12;
        P.head.rotation.x = 0; P.head.rotation.y = walking ? 0 : Math.sin(t * 0.7 + ph) * 0.3; P.body.rotation.x = 0;
        if (P.W.mode === 'pet') {
          P.body.rotation.x = 0.55; P.head.rotation.x = 0.25; P.head.rotation.y = 0;
          R.sh.rotation.x = -1.1 + Math.sin(t * 6) * 0.18; R.el.rotation.x = -0.2; L.sh.rotation.x = -0.4;
        } else if (P.W.mode === 'chat' || (P.W.mode === 'dwell' && P.W.chat)) {
          P.head.rotation.y = 0; P.head.rotation.x = Math.sin(t * 3 + ph) * 0.06;
          R.sh.rotation.x = -0.6 + Math.sin(t * 4 + ph) * 0.35; R.el.rotation.x = -0.9;
        }
        P.body.position.y = 0.56 + (walking ? Math.abs(Math.sin(t * 9)) * 0.02 : 0);
        P.mouth.visible = true; P.mouthO.visible = false;
        if (P.icon.visible) P.icon.position.y = 1.75;
        P.sel.material.opacity = 0.55 + Math.sin(t * 3) * 0.3;
        return;
      }
      P.body.position.y = 0.56; L.sh.rotation.z = 0;
      P.mouth.visible = P.status !== 'waiting'; P.mouthO.visible = P.status === 'waiting';
      P.body.rotation.z = P.status === 'done' ? Math.sin(t * 2.4 + ph) * 0.06 : 0;
      if (P.status === 'working') {
        L.sh.rotation.x = -0.55; R.sh.rotation.x = -0.55; R.sh.rotation.z = 0;
        L.el.rotation.x = -1.05 + Math.sin(t * 16 + ph) * 0.12; R.el.rotation.x = -1.05 + Math.sin(t * 16 + ph + 1.6) * 0.12;
        P.head.rotation.x = 0.12 + Math.sin(t * 2 + ph) * 0.03; P.head.rotation.y = Math.sin(t * 0.7 + ph) * 0.12;
        P.body.rotation.x = 0.06;
        monitors[P.key].material.emissiveIntensity = 0.75 + Math.sin(t * 5 + ph) * 0.15;
      } else if (P.status === 'waiting') {
        L.sh.rotation.x = -0.5; L.el.rotation.x = -1.0;
        R.sh.rotation.x = -2.9 + Math.sin(t * 3 + ph) * 0.08; R.sh.rotation.z = 0.15; R.el.rotation.x = -0.25;
        P.head.rotation.x = -0.12; P.head.rotation.y = Math.sin(t * 0.8) * 0.25; P.body.rotation.x = -0.04;
      } else if (P.status === 'done') {
        L.sh.rotation.x = -0.4; R.sh.rotation.x = -0.4; L.el.rotation.x = -1.2; R.el.rotation.x = -1.2; R.sh.rotation.z = 0;
        P.head.rotation.x = -0.05; P.head.rotation.y = Math.sin(t * 0.5 + ph) * 0.2; P.body.rotation.x = -0.1;
      } else {
        L.sh.rotation.x = -0.45; R.sh.rotation.x = -0.45; L.el.rotation.x = -1.1; R.el.rotation.x = -1.1; R.sh.rotation.z = 0;
        P.head.rotation.x = Math.sin(t * 0.4 + ph) * 0.05; P.head.rotation.y = Math.sin(t * 0.3 + ph) * 0.35; P.body.rotation.x = 0;
      }
      if (P.icon.visible) {
        const since = (performance.now() - P.changed) / 1000;
        const bounce = since < 2.5 ? Math.abs(Math.sin(since * 6)) * 0.15 * (1 - since / 2.5) : 0;
        P.icon.position.y = 1.9 + Math.sin(t * 2 + ph) * 0.03 + bounce;
      }
      P.sel.material.opacity = 0.55 + Math.sin(t * 3) * 0.3;
    });
    printLed.material.color.set(people.paiban.status === 'working' && Math.sin(t * 8) > 0 ? 0xffaa00 : 0x33dd66);
    const sec = Math.floor(Date.now() / 1000);
    if (sec !== lastSec) {
      lastSec = sec; drawClock();
      const h = new Date().getHours(), ev = h >= 17 || h < 6;
      if (ev !== evening) {
        evening = ev;
        glassM.color.set(ev ? 0x4a4f7a : 0xffffff);
        sun.color.set(ev ? 0xffb37a : 0xfff1d6); sun.intensity = ev ? 0.5 : 1.6;
        fill.intensity = ev ? 14 : 6; hemi.intensity = ev ? 0.65 : 0.9;
      }
    }
    renderer.render(scene, camera);
  }
  renderer.setAnimationLoop(frame);

  function resize() {
    const w = el.clientWidth || 800, h = el.clientHeight || 600;
    renderer.setSize(w, h, false); renderer.domElement.style.width = w + 'px'; renderer.domElement.style.height = h + 'px';
    camera.aspect = w / h;
    camera.fov = w / h < 1.1 ? 55 : 42;
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(el); resize();

  return { update, select };
}
