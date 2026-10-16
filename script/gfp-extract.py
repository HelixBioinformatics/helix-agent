"""Convierte el modelo de AlphaFold de la GFP en datos compactos para el cartoon WebGL.

Uso: python3 -I script/gfp-extract.py AF-P42212-F1-model_v6.pdb www/gfp-data.js

Asigna la estructura secundaria con la energía de puentes de hidrógeno de DSSP, alisa el
plisado de las hebras, alinea el eje del barril con Y y guarda, por residuo, la posición del
carbono alfa, la dirección del ancho de la cinta (desde el C=O) y el tipo de estructura.
"""
import json
import math
import sys


def vec(a, b):
    return [b[0] - a[0], b[1] - a[1], b[2] - a[2]]


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def norm(a):
    return math.sqrt(dot(a, a))


def unit(a):
    n = norm(a) or 1.0
    return [a[0] / n, a[1] / n, a[2] / n]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def dist(a, b):
    return norm(vec(a, b))


def parse(path):
    residues = {}
    order = []
    for line in open(path):
        if not line.startswith("ATOM"):
            continue
        name = line[12:16].strip()
        resname = line[17:20]
        seq = int(line[22:26])
        xyz = [float(line[30:38]), float(line[38:46]), float(line[46:54])]
        element = line[76:78].strip() or name[0]
        if seq not in residues:
            residues[seq] = {"name": resname, "atoms": {}, "elements": {}}
            order.append(seq)
        residues[seq]["atoms"][name] = xyz
        residues[seq]["elements"][name] = element
    return [dict(seq=s, **residues[s]) for s in order]


def assign(res):
    n = len(res)
    N = [r["atoms"]["N"] for r in res]
    C = [r["atoms"]["C"] for r in res]
    O = [r["atoms"]["O"] for r in res]
    H = [None] * n
    for i in range(1, n):
        if res[i]["name"] == "PRO":
            continue
        co = unit(vec(O[i - 1], C[i - 1]))
        H[i] = [N[i][k] + co[k] for k in range(3)]

    def hbond(i, j):
        # C=O de i con N-H de j (DSSP: E < -0.5 kcal/mol).
        if not (0 <= i < n and 0 <= j < n) or abs(i - j) < 2 or H[j] is None:
            return False
        r_on, r_ch = dist(O[i], N[j]), dist(C[i], H[j])
        r_oh, r_cn = dist(O[i], H[j]), dist(C[i], N[j])
        energy = 0.084 * 332 * (1 / r_on + 1 / r_ch - 1 / r_oh - 1 / r_cn)
        return energy < -0.5

    ss = ["L"] * n
    turn4 = [hbond(i, i + 4) for i in range(n)]
    for i in range(1, n - 4):
        if turn4[i - 1] and turn4[i]:
            for k in range(i, i + 4):
                ss[k] = "H"
    # Hélices 3-10: aparecen en la hélice central distorsionada, junto al cromóforo.
    turn3 = [hbond(i, i + 3) for i in range(n)]
    for i in range(1, n - 3):
        if turn3[i - 1] and turn3[i]:
            for k in range(i, i + 3):
                if ss[k] == "L":
                    ss[k] = "G"
    bridge = [False] * n
    for i in range(1, n - 1):
        for j in range(1, n - 1):
            if abs(i - j) < 3:
                continue
            parallel = (hbond(i - 1, j) and hbond(j, i + 1)) or (hbond(j - 1, i) and hbond(i, j + 1))
            anti = (hbond(i, j) and hbond(j, i)) or (hbond(i - 1, j + 1) and hbond(j - 1, i + 1))
            if parallel or anti:
                bridge[i] = True
    for i in range(n):
        if bridge[i] and ss[i] != "H":
            ss[i] = "E"
    # Rellena abultamientos de un residuo y quita fragmentos demasiado cortos para dibujarse.
    for i in range(1, n - 1):
        if ss[i] == "L" and ss[i - 1] == "E" and ss[i + 1] == "E":
            ss[i] = "E"
    i = 0
    while i < n:
        j = i
        while j < n and ss[j] == ss[i]:
            j += 1
        minimum = {"H": 4, "G": 3, "E": 3}.get(ss[i], 0)
        if j - i < minimum:
            for k in range(i, j):
                ss[k] = "L"
        i = j
    return "".join(ss)


def barrel_axis(ca, ss):
    # Las hebras de un barril β se inclinan alrededor del eje: al sumarlas con el mismo
    # sentido, las componentes tangenciales se cancelan y queda la dirección del eje.
    runs, i = [], 0
    while i < len(ss):
        j = i
        while j < len(ss) and ss[j] == ss[i]:
            j += 1
        if ss[i] == "E":
            runs.append(unit(vec(ca[i], ca[j - 1])))
        i = j
    total = [0.0, 0.0, 0.0]
    for d in runs:
        sign = 1 if dot(d, runs[0]) >= 0 else -1
        total = [total[k] + sign * d[k] for k in range(3)]
    return unit(total)


def main(src, out):
    res = parse(src)
    ss = assign(res)
    ca = [r["atoms"]["CA"] for r in res]
    # El centro y el eje se toman del barril, es decir, de las hebras.
    strands = [p for p, s in zip(ca, ss) if s == "E"]
    center = [sum(p[k] for p in strands) / len(strands) for k in range(3)]
    ca = [vec(center, p) for p in ca]
    axis = barrel_axis(ca, ss)
    ref = [1.0, 0.0, 0.0] if abs(axis[0]) < 0.9 else [0.0, 0.0, 1.0]
    ex = unit(cross(axis, ref))
    ez = cross(ex, axis)

    def frame(p):
        return [dot(p, ex), dot(p, axis), dot(p, ez)]

    ca = [frame(p) for p in ca]
    # Alisa el plisado de las hebras para que la cinta corra recta.
    smooth = [p[:] for p in ca]
    for i in range(1, len(ca) - 1):
        if ss[i] == "E":
            smooth[i] = [(ca[i - 1][k] + 2 * ca[i][k] + ca[i + 1][k]) / 4 for k in range(3)]
    widths = []
    previous = None
    for i, r in enumerate(res):
        o = frame(vec(r["atoms"]["C"], r["atoms"]["O"]))
        a = smooth[max(i - 1, 0)]
        b = smooth[min(i + 1, len(smooth) - 1)]
        t = unit(vec(a, b))
        w = unit([o[k] - dot(o, t) * t[k] for k in range(3)])
        if previous is not None and dot(w, previous) < 0:
            w = [-x for x in w]
        widths.append(w)
        previous = w

    # Cromóforo: Ser65-Tyr66-Gly67, con sus enlaces por distancia.
    atoms, index = [], {}
    for r in res:
        if r["seq"] in (65, 66, 67):
            for name, xyz in r["atoms"].items():
                if r["elements"][name] == "H":
                    continue
                index[(r["seq"], name)] = len(atoms)
                atoms.append(frame(vec(center, xyz)))
    keys = list(index)
    bonds = []
    for a in range(len(keys)):
        for b in range(a + 1, len(keys)):
            if dist(atoms[index[keys[a]]], atoms[index[keys[b]]]) < 1.9:
                bonds.append([index[keys[a]], index[keys[b]]])

    r2 = lambda xs: [round(x, 2) for p in xs for x in p]
    r3 = lambda xs: [round(x, 3) for p in xs for x in p]
    data = {
        "source": "AlphaFold DB AF-P42212-F1 (v6), CC BY 4.0",
        "ca": r2(smooth),
        "width": r3(widths),
        "ss": ss,
        "chromophore": {"atoms": r2(atoms), "bonds": bonds},
    }
    with open(out, "w") as f:
        f.write("// Generado desde AlphaFold DB AF-P42212-F1 (v6), CC BY 4.0. No editar a mano.\n")
        f.write("window.HELIX_GFP = " + json.dumps(data, separators=(",", ":")) + "\n")
    runs, i = [], 0
    while i < len(ss):
        j = i
        while j < len(ss) and ss[j] == ss[i]:
            j += 1
        if ss[i] != "L":
            runs.append(f"{ss[i]}{res[i]['seq']}-{res[j - 1]['seq']}")
        i = j
    print(len(res), "residuos;", ss.count("E"), "en hebra,", ss.count("H") + ss.count("G"), "en hélice")
    print(" ".join(runs))
    print("cromóforo:", len(atoms), "átomos,", len(bonds), "enlaces")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
