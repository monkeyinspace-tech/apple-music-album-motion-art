"""Valores animáveis (como expressões/keyframes do After Effects) — sempre em loop fechado.

Qualquer parâmetro numérico animável aceita:
  número                                   -> constante
  {"wave":"sin|cos|tri", "amp":A, "base":B, "cycles":n, "phase":p, "from_zero":true}
                                                                   -> B + A·onda(2π(n·t+p))   (from_zero: subtrai o valor em t=0)
  {"env":true, "amp":A, "base":B, "cycles":n}                        -> B + A·(1−cos 2πnt)/2   (0 nas pontas)
  {"wiggle":{"amp":A,"freq":n,"seed":s}}                             -> tremor suave periódico, ZERO em t=0
  {"keys":[[t,v],...], "ease":"linear|inout|in|out|hold"}           -> keyframes (t em 0..1)
  [[t,v],...]                                                        -> atalho para keys
t é normalizado: 0 = primeiro frame, 1 = fechamento do loop.
"""
import math, random

TAU = 2 * math.pi


def _ease(name, u):
    if name == 'inout': return u * u * (3 - 2 * u)
    if name == 'in': return u * u
    if name == 'out': return 1 - (1 - u) ** 2
    if name == 'hold': return 0.0
    return u


def _wiggle_terms(seed, freq):
    r = random.Random(seed)
    terms = []
    for i in (1, 2, 3):
        terms.append((max(1, int(round(freq))) * i, r.uniform(0, TAU), 1.0 / i))
    norm = sum(w for _, _, w in terms)
    return [(c, ph, w / norm) for c, ph, w in terms]


def evaluate(spec, t):
    if spec is None: return 0.0
    if isinstance(spec, bool): return float(spec)
    if isinstance(spec, (int, float)): return float(spec)
    if isinstance(spec, list): spec = {'keys': spec}
    base = spec.get('base', 0.0)
    amp = spec.get('amp', 1.0)
    if 'wave' in spec:
        n, ph = spec.get('cycles', 1), spec.get('phase', 0.0)
        x = TAU * (n * t + ph)
        w = spec['wave']
        f = lambda xx: math.sin(xx) if w == 'sin' else math.cos(xx) if w == 'cos' else (2 / math.pi) * math.asin(math.sin(xx))
        v = f(x) - (f(TAU * ph) if spec.get('from_zero') else 0.0)      # from_zero: fase livre, mas valor 0 em t=0
        return base + amp * v
    if spec.get('env'):
        n = spec.get('cycles', 1)
        return base + amp * (1 - math.cos(TAU * n * t)) / 2
    if 'wiggle' in spec:
        w = spec['wiggle']
        terms = _wiggle_terms(w.get('seed', 1), w.get('freq', 1))
        f = lambda tt: sum(wt * math.sin(TAU * c * tt + ph) for c, ph, wt in terms)
        return base + w.get('amp', 1.0) * (f(t) - f(0.0))
    if 'keys' in spec:
        keys = sorted(spec['keys'], key=lambda k: k[0])
        ease = spec.get('ease', 'inout')
        if t <= keys[0][0]: return float(keys[0][1])
        for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
            if t0 <= t <= t1:
                u = 0 if t1 == t0 else (t - t0) / (t1 - t0)
                return v0 + (v1 - v0) * _ease(ease, u)
        return float(keys[-1][1])
    raise ValueError(f'especificação de valor inválida: {spec!r}')


def is_spec(x):
    return isinstance(x, (int, float, list)) or (isinstance(x, dict) and any(k in x for k in ('wave', 'env', 'wiggle', 'keys')))


def loop_error(spec, tol=1e-6):
    """Retorna None se o valor fecha o loop (v(0)==v(1)); senão uma mensagem."""
    try:
        a, b = evaluate(spec, 0.0), evaluate(spec, 1.0)
    except Exception as e:
        return f'valor inválido ({e})'
    if abs(a - b) > tol * max(1, abs(a)):
        return f'não fecha o loop: v(0)={a:.4g} ≠ v(1)={b:.4g} (repita o primeiro keyframe em t=1)'
    return None
