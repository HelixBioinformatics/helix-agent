// Hélice metálica de Helix Agent: WebGL puro, sin dependencias.
// Gira sola, responde al scroll y al cursor, y sus pares de bases se encienden en verde Helix.
// Uso: HelixGL.mount(canvas, { shape: "helix" | "gfp", light: false, onHover, onFrame })
"use strict"
;(() => {
  const TAU = Math.PI * 2
  const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]]
  const addS = (a, b, s) => [a[0] + b[0] * s, a[1] + b[1] * s, a[2] + b[2] * s]
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
  const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
  const unit = (a) => {
    const l = Math.hypot(a[0], a[1], a[2]) || 1
    return [a[0] / l, a[1] / l, a[2] / l]
  }
  const toLinear = (hex) =>
    [1, 3, 5].map((i) => {
      const c = parseInt(hex.slice(i, i + 2), 16) / 255
      return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
    })

  // Una secuencia real (inicio de TP53 humano) da nombre a cada par de bases.
  const SEQUENCE = "ATGGAGGAGCCGCAGTCAGATCCTAGCGTCGAGCCCCCTCTGAGTCAGGAAACATTTTCAGACCTATGGAAACTACTTCCTGAAAACAACGTTCTG"
  const PAIR = { A: "T", T: "A", G: "C", C: "G" }

  // La hélice es una línea central con dos hebras enrolladas; la GFP es una cadena de cintas.
  const SHAPES = {
    helix: {
      closed: false,
      samples: 560,
      turns: 4.4,
      radius: 1.15,
      tube: 0.2,
      rung: 0.07,
      rungsPerTurn: 10,
      groove: 0.84,
      fov: 30,
      distance: 17,
      base: { x: 0.05, z: -0.07 },
      spinSpeed: 0.28,
      scrollSpin: 2.4,
      lift: 1.6,
      glowWidth: 0.03,
      pulseWidth: 0.022,
      pulseSpeed: 0.42,
      pulseEvery: 6.5,
      curve: (s) => {
        const y = (s - 0.5) * 17
        return [0.34 * Math.sin(y * 0.27 + 0.5), y, 0.28 * Math.cos(y * 0.21)]
      },
    },
    gfp: {
      protein: true,
      fov: 30,
      distance: 10.5,
      base: { x: 0.28, z: 0.1 },
      spinSpeed: 0.18,
      scrollSpin: 1.4,
      lift: 0,
      strandGlow: 1,
      glowWidth: 0.012,
      pulseWidth: 0.01,
      pulseSpeed: 0.08,
      pulseEvery: 14,
    },
  }

  // Marcos de transporte paralelo: el tubo avanza sin retorcerse sobre sí mismo.
  function frames(points, closed) {
    const n = points.length
    const T = points.map((_, i) => {
      const a = points[closed ? (i - 1 + n) % n : Math.max(i - 1, 0)]
      const b = points[closed ? (i + 1) % n : Math.min(i + 1, n - 1)]
      return unit(sub(b, a))
    })
    const seed = Math.abs(T[0][1]) < 0.9 ? [0, 1, 0] : [1, 0, 0]
    const N = [unit(cross(cross(T[0], seed), T[0]))]
    for (let i = 1; i < n; i++) N.push(unit(addS(N[i - 1], T[i], -dot(N[i - 1], T[i]))))
    const B = T.map((t, i) => cross(t, N[i]))
    // En una curva cerrada el marco no vuelve igual: se reparte ese giro a lo largo del recorrido.
    let twist = 0
    if (closed) {
      const back = unit(addS(N[n - 1], T[0], -dot(N[n - 1], T[0])))
      twist = Math.atan2(dot(cross(N[0], back), T[0]), dot(N[0], back))
    }
    return { N, B, twist }
  }

  function meshBuilder() {
    const pos = [],
      nor = [],
      info = [],
      index = []
    return {
      pos,
      nor,
      info,
      index,
      get count() {
        return pos.length / 3
      },
      vertex(p, n, i) {
        pos.push(p[0], p[1], p[2])
        nor.push(n[0], n[1], n[2])
        info.push(i[0], i[1], i[2], i[3])
      },
    }
  }

  function tube(mesh, pts, radius, sides, closed, infoAt) {
    const { N, B, twist } = frames(pts, closed)
    const n = pts.length
    const start = mesh.count
    for (let i = 0; i < n; i++) {
      const corr = closed ? (-twist * i) / n : 0
      for (let j = 0; j <= sides; j++) {
        const a = (TAU * j) / sides + corr
        const c = Math.cos(a),
          s = Math.sin(a)
        const nr = [N[i][0] * c + B[i][0] * s, N[i][1] * c + B[i][1] * s, N[i][2] * c + B[i][2] * s]
        mesh.vertex(addS(pts[i], nr, radius), nr, infoAt(i, nr))
      }
    }
    const segments = closed ? n : n - 1
    for (let i = 0; i < segments; i++) {
      const i2 = (i + 1) % n
      for (let j = 0; j < sides; j++) {
        const a = start + i * (sides + 1) + j
        const b = start + i2 * (sides + 1) + j
        mesh.index.push(a, b, a + 1, b, b + 1, a + 1)
      }
    }
  }

  // Barrido con sección elíptica: el lado ancho de la cinta queda perpendicular a `outAt`.
  // La elipse es simétrica, así que el ángulo se desenrolla cada media vuelta.
  function sweep(mesh, pts, sides, profileAt, outAt, infoAt) {
    const { N, B } = frames(pts, false)
    const n = pts.length
    const alpha = []
    let previous = 0
    for (let i = 0; i < n; i++) {
      const out = outAt(i)
      if (out) {
        const raw = Math.atan2(-dot(out, N[i]), dot(out, B[i]))
        const half = Math.PI / 2
        previous += ((((raw - previous + half) % Math.PI) + Math.PI) % Math.PI) - half
      }
      alpha.push(previous)
    }
    const start = mesh.count
    for (let i = 0; i < n; i++) {
      const [w, h] = profileAt(i)
      const ca = Math.cos(alpha[i]),
        sa = Math.sin(alpha[i])
      const U = addS(addS([0, 0, 0], N[i], ca), B[i], sa)
      const W = addS(addS([0, 0, 0], N[i], -sa), B[i], ca)
      for (let j = 0; j <= sides; j++) {
        const t = (TAU * j) / sides
        const c = Math.cos(t),
          sn = Math.sin(t)
        const p = addS(addS(pts[i], U, w * c), W, h * sn)
        const nr = unit(addS(addS([0, 0, 0], U, c / w), W, sn / h))
        mesh.vertex(p, nr, infoAt(i, nr))
      }
    }
    for (let i = 0; i < n - 1; i++)
      for (let j = 0; j < sides; j++) {
        const a = start + i * (sides + 1) + j
        const b = a + sides + 1
        mesh.index.push(a, b, a + 1, b, b + 1, a + 1)
      }
  }

  // Cartoon de la proteína verde fluorescente desde su modelo de AlphaFold (gfp-data.js):
  // cintas para las hélices, flechas para las hebras β, tubos para los lazos y el cromóforo
  // Ser65-Tyr66-Gly67 encendido en su sitio, dentro del barril.
  function buildProtein() {
    const data = window.HELIX_GFP
    if (!data) return null
    const scale = 1 / 12
    const { ss } = data
    const n = ss.length
    const triple = (list, i, k = 1) => [list[i * 3] * k, list[i * 3 + 1] * k, list[i * 3 + 2] * k]
    const ca = Array.from({ length: n }, (_, i) => triple(data.ca, i, scale))
    const across = Array.from({ length: n }, (_, i) => triple(data.width, i))
    const lerp = (a, b, t) => a + (b - a) * t
    const blend = (a, b, t) => addS(addS([0, 0, 0], a, 1 - t), b, t)
    const radial = (p) => {
      const l = Math.hypot(p[0], p[2])
      return l > 1e-4 ? [p[0] / l, 0, p[2] / l] : [0, 0, 1]
    }
    const catmull = (p0, p1, p2, p3, t) =>
      [0, 1, 2].map(
        (c) =>
          0.5 *
          (2 * p1[c] +
            (p2[c] - p0[c]) * t +
            (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t * t +
            (3 * p1[c] - p0[c] - 3 * p2[c] + p3[c]) * t * t * t),
      )
    // Sección en Å por tipo de estructura: [medio ancho, medio grosor].
    const PROFILE = { H: [1.5, 0.26], G: [1.5, 0.26], E: [1.35, 0.3], L: [0.38, 0.38] }
    const ARROW = 2.3
    const strandEnd = (i) => ss[i] === "E" && ss[i + 1] !== "E"
    const profileAt = (r) => {
      const i = Math.min(Math.floor(r), n - 2)
      const f = r - i
      if (strandEnd(i)) return [lerp(ARROW, 0.38, f) * scale, lerp(0.3, 0.38, f) * scale]
      const a = PROFILE[ss[i]] || PROFILE.L
      const b = PROFILE[ss[i + 1]] || PROFILE.L
      return [lerp(a[0], b[0], f) * scale, lerp(a[1], b[1], f) * scale]
    }

    const STEPS = 8
    const path = [],
      widths = [],
      place = []
    for (let i = 0; i < n - 1; i++) {
      const p0 = ca[Math.max(i - 1, 0)],
        p3 = ca[Math.min(i + 2, n - 1)]
      for (let j = 0; j < STEPS; j++) {
        const t = j / STEPS
        path.push(catmull(p0, ca[i], ca[i + 1], p3, t))
        widths.push(blend(across[i], across[i + 1], t))
        place.push(i + t)
      }
    }
    path.push(ca[n - 1])
    widths.push(across[n - 1])
    place.push(n - 1)
    const outs = path.map((p, i) => {
      const t = unit(sub(path[Math.min(i + 1, path.length - 1)], path[Math.max(i - 1, 0)]))
      return unit(cross(t, widths[i]))
    })

    const mesh = meshBuilder()
    sweep(
      mesh,
      path,
      12,
      (i) => profileAt(place[i]),
      (i) => outs[i],
      (i, nr) => [place[i] / (n - 1), 0, 0, 0.62 + 0.38 * dot(nr, radial(path[i]))],
    )

    // El cromóforo, en barras y esferas que brillan siempre: la fluorescencia que da nombre a la proteína.
    const { atoms: atomList, bonds } = data.chromophore
    const atoms = Array.from({ length: atomList.length / 3 }, (_, i) => triple(atomList, i, scale))
    const glowing = () => [0.5, 2, 0, 1]
    for (const [a, b] of bonds) {
      const pts = [0, 0.5, 1].map((t) => blend(atoms[a], atoms[b], t))
      sweep(mesh, pts, 8, () => [0.2 * scale, 0.2 * scale], () => null, glowing)
    }
    for (const atom of atoms) {
      const pts = Array.from({ length: 7 }, (_, k) => addS(atom, [0, 1, 0], ((k / 6) * 2 - 1) * 0.42 * scale))
      sweep(
        mesh,
        pts,
        10,
        (k) => {
          const r = (0.02 + 0.42 * Math.sin((Math.PI * k) / 6)) * scale
          return [r, r]
        },
        () => null,
        glowing,
      )
    }
    const core = atoms.reduce((sum, p) => addS(sum, p, 1 / atoms.length), [0, 0, 0])
    const halos = [{ mid: core, info: [0.5, 1, 0, 0] }]
    for (let i = 0; i < n; i += 2) halos.push({ mid: ca[i], info: [i / (n - 1), 0, 0, 0] })
    const probes = ca.map((mid, i) => ({ s: i / (n - 1), mid }))
    return { mesh, rungs: [], probes, halos }
  }

  function buildDNA(shape) {
    const { closed, samples, turns, radius, groove, curve } = shape
    const span = closed ? samples : samples - 1
    const center = Array.from({ length: samples }, (_, i) => curve(i / span))
    const { N, B, twist } = frames(center, closed)
    const phases = [0, Math.PI * groove]
    const strandPoint = (s, i, k) => {
      const theta = TAU * turns * s - (closed ? twist * s : 0) + phases[k]
      const c = Math.cos(theta),
        sn = Math.sin(theta)
      const dir = [N[i][0] * c + B[i][0] * sn, N[i][1] * c + B[i][1] * sn, N[i][2] * c + B[i][2] * sn]
      return { p: addS(center[i], dir, radius), dir }
    }
    const mesh = meshBuilder()
    for (const k of [0, 1]) {
      const strand = center.map((_, i) => strandPoint(i / span, i, k))
      tube(
        mesh,
        strand.map((x) => x.p),
        shape.tube,
        20,
        closed,
        (i, nr) => [i / span, 0, k, 0.5 + 0.5 * dot(nr, strand[i].dir)],
      )
    }
    const count = Math.round(turns * shape.rungsPerTurn)
    const rungs = []
    for (let r = 0; r < count; r++) {
      const s = (r + 0.5) / count
      const i = Math.min(Math.round(s * span), samples - 1)
      const a = strandPoint(i / span, i, 0).p
      const b = strandPoint(i / span, i, 1).p
      const steps = 6
      const pts = Array.from({ length: steps + 1 }, (_, j) => addS(a, sub(b, a), j / steps))
      tube(mesh, pts, shape.rung, 10, false, () => [i / span, 1, r / count, 0.78])
      const base = SEQUENCE[r % SEQUENCE.length]
      rungs.push({ s: i / span, seed: r / count, mid: addS(a, sub(b, a), 0.5), base, pair: PAIR[base] })
    }
    const halos = rungs.map((r) => ({ mid: r.mid, info: [r.s, 0, r.seed, 1] }))
    return { mesh, rungs, probes: rungs, halos }
  }

  // Matrices 4x4 en orden de columnas.
  const mat = {
    perspective(fovy, aspect, near, far) {
      const f = 1 / Math.tan(fovy / 2),
        nf = 1 / (near - far)
      return new Float32Array([f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) * nf, -1, 0, 0, 2 * far * near * nf, 0])
    },
    mul(a, b) {
      const o = new Float32Array(16)
      for (let c = 0; c < 4; c++)
        for (let r = 0; r < 4; r++) {
          let s = 0
          for (let k = 0; k < 4; k++) s += a[k * 4 + r] * b[c * 4 + k]
          o[c * 4 + r] = s
        }
      return o
    },
    translate: (x, y, z) => new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, x, y, z, 1]),
    rotX(a) {
      const c = Math.cos(a),
        s = Math.sin(a)
      return new Float32Array([1, 0, 0, 0, 0, c, s, 0, 0, -s, c, 0, 0, 0, 0, 1])
    },
    rotY(a) {
      const c = Math.cos(a),
        s = Math.sin(a)
      return new Float32Array([c, 0, -s, 0, 0, 1, 0, 0, s, 0, c, 0, 0, 0, 0, 1])
    },
    rotZ(a) {
      const c = Math.cos(a),
        s = Math.sin(a)
      return new Float32Array([c, s, 0, 0, -s, c, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])
    },
    normal: (m) => new Float32Array([m[0], m[1], m[2], m[4], m[5], m[6], m[8], m[9], m[10]]),
  }

  const COMMON = `
    uniform float uGlowS;
    uniform float uGlowAmt;
    uniform float uPulseS;
    uniform float uPulseAmt;
    uniform float uAmbient;
    uniform float uTime;
    uniform float uClosed;
    uniform float uGlowW;
    uniform float uPulseW;
    float band(float x, float c, float w) { float d = (x - c) / w; return exp(-d * d); }
    float sdist(float a, float b) { float d = a - b; return uClosed > 0.5 ? d - floor(d + 0.5) : d; }
    float glowAt(float s) {
      return band(sdist(s, uGlowS), 0.0, uGlowW) * uGlowAmt + band(sdist(s, uPulseS), 0.0, uPulseW) * uPulseAmt;
    }
    float breathe() { return 0.85 + 0.25 * sin(uTime * 1.4); }
    float flicker(float seed) { return pow(max(sin(uTime * 0.75 + seed * 97.0), 0.0), 70.0) * uAmbient; }
  `

  const MESH_VS = `
    attribute vec3 aPos;
    attribute vec3 aNor;
    attribute vec4 aInfo;
    uniform mat4 uProj;
    uniform mat4 uMV;
    uniform mat3 uNorm;
    varying vec3 vN;
    varying vec3 vP;
    varying vec4 vInfo;
    void main() {
      vec4 p = uMV * vec4(aPos, 1.0);
      vP = p.xyz;
      vN = uNorm * aNor;
      vInfo = aInfo;
      gl_Position = uProj * p;
    }
  `

  const MESH_FS = `
    precision highp float;
    varying vec3 vN;
    varying vec3 vP;
    varying vec4 vInfo;
    uniform float uLight;
    uniform vec3 uGreen;
    uniform vec3 uTint;
    uniform float uAccent;
    uniform float uStrandGlow;
    ${COMMON}

    // Estudio fotográfico oscuro: luces de tira, una caja de luz cenital y un reflejo verde Helix.
    vec3 envDark(vec3 r) {
      float az = atan(r.x, r.z);
      float up = r.y;
      vec3 c = mix(vec3(0.004, 0.005, 0.008), vec3(0.03, 0.033, 0.046), smoothstep(-0.6, 0.9, up));
      c += vec3(2.6) * smoothstep(0.55, 0.93, up);
      c += vec3(2.0, 2.05, 2.2) * band(az, -1.15, 0.14) * smoothstep(-0.7, 0.1, up);
      c += uTint * 1.9 * band(az, 1.45, 0.2) * smoothstep(-0.5, 0.3, up);
      c += vec3(0.42, 0.46, 0.62) * band(abs(az), 3.0, 0.38) * smoothstep(-0.3, 0.6, up);
      c += vec3(0.3, 0.32, 0.4) * band(up, -0.04, 0.05);
      c += uGreen * uAccent * 1.8 * band(az, 0.35, 0.16) * smoothstep(0.15, -0.6, up);
      return c;
    }
    // Estudio claro: fondo luminoso con banderas negras que dibujan el volumen.
    vec3 envLight(vec3 r) {
      float az = atan(r.x, r.z);
      float up = r.y;
      vec3 c = mix(vec3(0.12, 0.13, 0.13), vec3(0.92, 0.93, 0.92), smoothstep(-0.7, 0.6, up));
      c *= 1.0 - 0.92 * band(az, -1.05, 0.3) * smoothstep(-0.9, 0.4, up);
      c *= 1.0 - 0.85 * band(az, 1.75, 0.32);
      c += vec3(1.9) * smoothstep(0.7, 0.97, up);
      c += uGreen * uAccent * 0.9 * band(az, 0.3, 0.14) * smoothstep(0.1, -0.6, up);
      return c;
    }
    vec3 aces(vec3 x) { return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0); }

    void main() {
      vec3 N = normalize(vN);
      vec3 V = normalize(-vP);
      vec3 R = reflect(-V, N);
      float ndv = clamp(dot(N, V), 0.0, 1.0);
      vec3 F0 = vec3(0.62, 0.64, 0.68);
      vec3 F = F0 + (1.0 - F0) * pow(1.0 - ndv, 5.0);
      vec3 env = uLight > 0.5 ? envLight(R) : envDark(R);
      float ao = vInfo.w;
      vec3 col = env * F * mix(0.28, 1.0, ao);
      vec3 L = normalize(vec3(-0.45, 0.8, 0.5));
      col += vec3(4.0) * pow(max(dot(R, L), 0.0), 220.0) * ao;
      float kind = vInfo.y;
      float core = step(1.5, kind);
      float rung = step(0.5, kind) * (1.0 - core);
      float g = glowAt(vInfo.x) * mix(uStrandGlow, 1.0, rung) * (1.0 - core) + flicker(vInfo.z) * rung;
      col += uGreen * g * (uLight > 0.5 ? 1.2 : 2.6);
      col = mix(col, uGreen * 2.6 * breathe(), core * 0.85);
      col = aces(col * 1.05);
      gl_FragColor = vec4(pow(col, vec3(1.0 / 2.2)), 1.0);
    }
  `

  const HALO_VS = `
    attribute vec3 aPos;
    attribute vec4 aInfo;
    uniform mat4 uProj;
    uniform mat4 uMV;
    uniform float uPx;
    varying float vG;
    ${COMMON}
    void main() {
      vec4 p = uMV * vec4(aPos, 1.0);
      gl_Position = uProj * p;
      vG = min(glowAt(aInfo.x) + flicker(aInfo.z) * aInfo.w + aInfo.y * breathe(), 1.0);
      gl_PointSize = vG > 0.01 ? uPx / -p.z : 0.0;
    }
  `

  const HALO_FS = `
    precision mediump float;
    uniform vec3 uGreen;
    uniform float uHalo;
    varying float vG;
    void main() {
      vec2 d = gl_PointCoord - 0.5;
      float a = exp(-dot(d, d) * 14.0) * vG * uHalo;
      gl_FragColor = vec4(uGreen * a, a);
    }
  `

  function compile(gl, vs, fs) {
    const program = gl.createProgram()
    for (const [type, source] of [
      [gl.VERTEX_SHADER, vs],
      [gl.FRAGMENT_SHADER, fs],
    ]) {
      const shader = gl.createShader(type)
      gl.shaderSource(shader, source)
      gl.compileShader(shader)
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader))
      gl.attachShader(program, shader)
    }
    gl.linkProgram(program)
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program))
    const loc = {}
    const attributes = gl.getProgramParameter(program, gl.ACTIVE_ATTRIBUTES)
    for (let i = 0; i < attributes; i++) {
      const name = gl.getActiveAttrib(program, i).name
      loc[name] = gl.getAttribLocation(program, name)
    }
    const uniforms = gl.getProgramParameter(program, gl.ACTIVE_UNIFORMS)
    for (let i = 0; i < uniforms; i++) {
      const name = gl.getActiveUniform(program, i).name
      loc[name] = gl.getUniformLocation(program, name)
    }
    return { program, loc }
  }

  function buffer(gl, target, data) {
    const b = gl.createBuffer()
    gl.bindBuffer(target, b)
    gl.bufferData(target, data, gl.STATIC_DRAW)
    return b
  }

  const damp = (current, target, rate, dt) => current + (target - current) * (1 - Math.exp(-rate * dt))

  function mount(canvas, options = {}) {
    const shape = SHAPES[options.shape || "helix"]
    const light = !!options.light
    const gl = canvas.getContext("webgl", { antialias: true, alpha: true, premultipliedAlpha: true })
    if (!gl) return null
    const model = shape.protein ? buildProtein() : buildDNA(shape)
    if (!model) return null
    const { mesh, rungs, probes, halos } = model
    const wide = mesh.count > 65535
    if (wide && !gl.getExtension("OES_element_index_uint")) return null

    let meshProgram, haloProgram
    try {
      meshProgram = compile(gl, MESH_VS, MESH_FS)
      haloProgram = compile(gl, HALO_VS, HALO_FS)
    } catch (error) {
      console.warn("Helix: no se pudo compilar la hélice", error)
      return null
    }
    const buffers = {
      pos: buffer(gl, gl.ARRAY_BUFFER, new Float32Array(mesh.pos)),
      nor: buffer(gl, gl.ARRAY_BUFFER, new Float32Array(mesh.nor)),
      info: buffer(gl, gl.ARRAY_BUFFER, new Float32Array(mesh.info)),
      index: buffer(gl, gl.ELEMENT_ARRAY_BUFFER, wide ? new Uint32Array(mesh.index) : new Uint16Array(mesh.index)),
      haloPos: buffer(gl, gl.ARRAY_BUFFER, new Float32Array(halos.flatMap((h) => h.mid))),
      haloInfo: buffer(gl, gl.ARRAY_BUFFER, new Float32Array(halos.flatMap((h) => h.info))),
    }
    const indexType = wide ? gl.UNSIGNED_INT : gl.UNSIGNED_SHORT
    const green = toLinear(options.green || "#b9e27f")
    const tint = toLinear(options.tint || "#aab4ff").map((c) => c * 0.85)

    const reduced = matchMedia("(prefers-reduced-motion: reduce)")
    const flags = { auto: true, scroll: true, mouse: true, ...options.flags }
    const state = {
      spin: options.phase || 0,
      spinVel: 0,
      tiltX: 0,
      tiltY: 0,
      targetX: 0,
      targetY: 0,
      glowS: 0.5,
      glowAmt: 0,
      glowTarget: 0,
      glowSTarget: 0.5,
      pulseS: -1,
      pulseAmt: 0,
      nextPulse: 1.6,
      time: 0,
      scroll: 0,
    }
    const pointer = { x: 0, y: 0, inside: false, dragging: false, lastX: 0 }
    let width = 0,
      height = 0,
      dpr = 1,
      raf = 0,
      last = 0,
      visible = false,
      hovered = -1,
      mvp = null

    function resize() {
      const rect = canvas.getBoundingClientRect()
      dpr = Math.min(window.devicePixelRatio || 1, 2)
      width = Math.max(1, Math.round(rect.width * dpr))
      height = Math.max(1, Math.round(rect.height * dpr))
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width
        canvas.height = height
      }
    }

    function scrollProgress() {
      if (options.scrollMode === "section") {
        const rect = canvas.getBoundingClientRect()
        return (innerHeight - rect.top) / (innerHeight + rect.height)
      }
      return window.scrollY / Math.max(innerHeight, 1)
    }

    function modelView() {
      const scroll = flags.scroll && !reduced.matches ? state.scroll : 0
      const { base } = shape
      const scrollSpin = (options.scrollMode === "section" ? scroll - 0.5 : scroll) * shape.scrollSpin
      const model = mat.mul(
        mat.translate(0, scroll * shape.lift, 0),
        mat.mul(
          mat.rotZ(base.z + state.tiltY * 0.08),
          mat.mul(mat.rotX(base.x + state.tiltX), mat.rotY(state.spin + scrollSpin + state.tiltY * 0.35)),
        ),
      )
      return mat.mul(mat.translate(0, 0, -shape.distance), model)
    }

    function nearestProbe() {
      if (!mvp || !pointer.inside || pointer.dragging) return -1
      let best = -1,
        bestD = Infinity
      for (let i = 0; i < probes.length; i++) {
        const [x, y, z] = probes[i].mid
        const cx = mvp[0] * x + mvp[4] * y + mvp[8] * z + mvp[12]
        const cy = mvp[1] * x + mvp[5] * y + mvp[9] * z + mvp[13]
        const cw = mvp[3] * x + mvp[7] * y + mvp[11] * z + mvp[15]
        const sx = ((cx / cw) * 0.5 + 0.5) * width
        const sy = (0.5 - (cy / cw) * 0.5) * height
        const d = Math.hypot(sx - pointer.x * dpr, sy - pointer.y * dpr)
        if (d < bestD) {
          bestD = d
          best = i
        }
      }
      return bestD < 90 * dpr ? best : -1
    }

    function frame(now) {
      raf = 0
      const dt = Math.min((now - (last || now)) / 1000, 0.05)
      last = now
      const still = reduced.matches
      state.time += still ? 0 : dt
      state.scroll = damp(state.scroll, scrollProgress(), 8, dt || 1)

      if (!still) {
        if (flags.auto) state.spin += dt * shape.spinSpeed
        state.spin += state.spinVel * dt
        state.spinVel = damp(state.spinVel, 0, 2.2, dt)
        state.pulseS += dt * shape.pulseSpeed
        state.nextPulse -= dt
        if (state.nextPulse <= 0) {
          state.pulseS = -0.12
          state.pulseAmt = 1
          state.nextPulse = shape.pulseEvery
        }
        if (state.pulseS > 1.15) state.pulseAmt = 0
      }
      const tilt = flags.mouse && !still
      state.tiltX = damp(state.tiltX, tilt ? state.targetY * 0.16 : 0, 4, dt || 1)
      state.tiltY = damp(state.tiltY, tilt ? state.targetX : 0, 4, dt || 1)

      resize()
      const proj = mat.perspective((shape.fov * Math.PI) / 180, width / height, 0.1, 100)
      const mv = modelView()
      mvp = mat.mul(proj, mv)

      const near = nearestProbe()
      if (near >= 0) {
        state.glowSTarget = probes[near].s
        state.glowTarget = 1
      } else state.glowTarget = 0
      state.glowS = state.glowAmt < 0.02 ? state.glowSTarget : damp(state.glowS, state.glowSTarget, 14, dt || 1)
      state.glowAmt = damp(state.glowAmt, state.glowTarget, 7, dt || 1)
      if (near !== hovered) {
        hovered = near
        const rung = rungs[near]
        options.onHover?.(rung ? { index: near + 1, base: rung.base, pair: rung.pair } : null)
      }

      gl.viewport(0, 0, width, height)
      gl.clearColor(0, 0, 0, 0)
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT)
      gl.enable(gl.DEPTH_TEST)
      gl.disable(gl.CULL_FACE)

      const shared = (loc) => {
        gl.uniform1f(loc.uGlowS, state.glowS)
        gl.uniform1f(loc.uGlowAmt, state.glowAmt)
        gl.uniform1f(loc.uPulseS, state.pulseS)
        gl.uniform1f(loc.uPulseAmt, still ? 0 : state.pulseAmt)
        gl.uniform1f(loc.uAmbient, still ? 0 : (options.ambient ?? 0.7))
        gl.uniform1f(loc.uTime, state.time)
        gl.uniform1f(loc.uClosed, shape.closed ? 1 : 0)
        gl.uniform1f(loc.uGlowW, shape.glowWidth)
        gl.uniform1f(loc.uPulseW, shape.pulseWidth)
        gl.uniformMatrix4fv(loc.uProj, false, proj)
        gl.uniformMatrix4fv(loc.uMV, false, mv)
      }
      const attrib = (loc, name, buf, size) => {
        gl.bindBuffer(gl.ARRAY_BUFFER, buf)
        gl.enableVertexAttribArray(loc[name])
        gl.vertexAttribPointer(loc[name], size, gl.FLOAT, false, 0, 0)
      }

      const m = meshProgram
      gl.useProgram(m.program)
      shared(m.loc)
      gl.uniformMatrix3fv(m.loc.uNorm, false, mat.normal(mv))
      gl.uniform1f(m.loc.uLight, light ? 1 : 0)
      gl.uniform3fv(m.loc.uGreen, green)
      gl.uniform3fv(m.loc.uTint, tint)
      gl.uniform1f(m.loc.uAccent, options.accent ?? 1)
      gl.uniform1f(m.loc.uStrandGlow, shape.strandGlow ?? 0.28)
      attrib(m.loc, "aPos", buffers.pos, 3)
      attrib(m.loc, "aNor", buffers.nor, 3)
      attrib(m.loc, "aInfo", buffers.info, 4)
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, buffers.index)
      gl.disable(gl.BLEND)
      gl.depthMask(true)
      gl.drawElements(gl.TRIANGLES, mesh.index.length, indexType, 0)
      gl.disableVertexAttribArray(m.loc.aNor)

      const h = haloProgram
      gl.useProgram(h.program)
      shared(h.loc)
      gl.uniform3fv(h.loc.uGreen, green)
      gl.uniform1f(h.loc.uHalo, light ? 0.35 : 0.75)
      gl.uniform1f(h.loc.uPx, (2.1 * height) / (2 * Math.tan((shape.fov * Math.PI) / 360)))
      attrib(h.loc, "aPos", buffers.haloPos, 3)
      attrib(h.loc, "aInfo", buffers.haloInfo, 4)
      gl.enable(gl.BLEND)
      gl.blendFuncSeparate(gl.ONE, gl.ONE, gl.ONE, gl.ONE)
      gl.depthMask(false)
      gl.drawArrays(gl.POINTS, 0, halos.length)
      gl.depthMask(true)

      options.onFrame?.({ angle: (((state.spin * 180) / Math.PI) % 360 + 360) % 360 })
      if (visible) raf = requestAnimationFrame(frame)
    }

    function start() {
      if (!raf && visible) {
        last = 0
        raf = requestAnimationFrame(frame)
      }
    }

    const observer = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting && !document.hidden
      visible ? start() : (cancelAnimationFrame(raf), (raf = 0))
    })
    observer.observe(canvas)
    const onVisibility = () => {
      visible = !document.hidden && canvas.getBoundingClientRect().bottom > 0
      start()
    }
    document.addEventListener("visibilitychange", onVisibility)

    const onWindowMove = (event) => {
      state.targetX = (event.clientX / innerWidth) * 2 - 1
      state.targetY = (event.clientY / innerHeight) * 2 - 1
    }
    window.addEventListener("pointermove", onWindowMove, { passive: true })
    canvas.addEventListener("pointermove", (event) => {
      const rect = canvas.getBoundingClientRect()
      pointer.x = event.clientX - rect.left
      pointer.y = event.clientY - rect.top
      pointer.inside = true
      if (pointer.dragging) {
        state.spinVel += (event.clientX - pointer.lastX) * 0.09
        pointer.lastX = event.clientX
      }
    })
    canvas.addEventListener("pointerleave", () => (pointer.inside = false))
    canvas.addEventListener("pointerdown", (event) => {
      pointer.dragging = true
      pointer.lastX = event.clientX
      canvas.setPointerCapture(event.pointerId)
      canvas.classList.add("is-dragging")
    })
    const release = () => {
      pointer.dragging = false
      canvas.classList.remove("is-dragging")
    }
    canvas.addEventListener("pointerup", release)
    canvas.addEventListener("pointercancel", release)
    // Un clic envía un pulso de luz desde la base más cercana.
    canvas.addEventListener("click", () => {
      if (hovered < 0 || reduced.matches) return
      state.pulseS = probes[hovered].s
      state.pulseAmt = 1
      state.nextPulse = shape.pulseEvery
    })
    canvas.addEventListener("webglcontextlost", (event) => {
      event.preventDefault()
      cancelAnimationFrame(raf)
      raf = 0
      visible = false
    })

    return {
      destroy() {
        observer.disconnect()
        cancelAnimationFrame(raf)
        window.removeEventListener("pointermove", onWindowMove)
        document.removeEventListener("visibilitychange", onVisibility)
      },
    }
  }

  window.HelixGL = { mount }
})()
