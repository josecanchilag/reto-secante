"""
🎯 Reto de la Secante — juego interactivo para aprender el método de la secante.

Ejecutar:  streamlit run app.py
"""
import html
import os
import sqlite3
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Reto de la Secante", page_icon="🎯", layout="centered")

# ───────────────────────── Configuración ─────────────────────────
DB_PATH = os.environ.get("RANKING_DB", "ranking.db")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "secante")  # cámbiala al desplegar
TIME_LIMIT = 600  # 10 minutos (el bono de tiempo llega a 0 en este punto)
MEDALS = ["🥇", "🥈", "🥉"]

# ───────────────────────── Ranking (SQLite) ─────────────────────────
def run_sql(sql, params=(), fetch=False):
    con = sqlite3.connect(DB_PATH)
    try:
        con.execute(
            "CREATE TABLE IF NOT EXISTS scores ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, "
            "points INTEGER NOT NULL, seconds INTEGER NOT NULL, "
            "ts TEXT DEFAULT CURRENT_TIMESTAMP)"
        )
        cur = con.execute(sql, params)
        rows = cur.fetchall() if fetch else None
        con.commit()
        return rows
    finally:
        con.close()


def save_score(name, points, seconds):
    run_sql("INSERT INTO scores (name, points, seconds) VALUES (?, ?, ?)", (name, points, seconds))


def top_scores(limit=10):
    """Mejor intento de cada jugador, ordenado por puntos (y menor tiempo en empate)."""
    return run_sql(
        """
        SELECT name, points, seconds FROM scores s
        WHERE id = (SELECT id FROM scores WHERE lower(name) = lower(s.name)
                    ORDER BY points DESC, seconds ASC LIMIT 1)
        ORDER BY points DESC, seconds ASC LIMIT ?
        """,
        (limit,),
        fetch=True,
    )


def reset_ranking():
    run_sql("DELETE FROM scores")


# ───────────────────────── Matemática ─────────────────────────
def secant_step(f, a, b):
    """Un paso de la secante a partir de x_{n-1}=a y x_n=b."""
    return b - f(b) * (b - a) / (f(b) - f(a))


def secant_run(f, x0, x1, tol=1e-6, max_iter=30):
    """Devuelve (lista de x, convergió?, mensaje)."""
    xs = [x0, x1]
    for _ in range(max_iter):
        if abs(f(xs[-1])) < tol:
            return xs, True, ""
        if f(xs[-1]) == f(xs[-2]):
            return xs, False, "Se anuló el denominador (f(xₙ) = f(xₙ₋₁))."
        xs.append(secant_step(f, xs[-2], xs[-1]))
        if abs(xs[-1]) > 1e6:
            return xs, False, "El método se salió de control (divergió)."
    return xs, abs(f(xs[-1])) < tol, "" if abs(f(xs[-1])) < tol else "No convergió en 30 iteraciones."


F = lambda x: x**2 - 2          # niveles de cálculo
G = lambda x: x**3 - x - 2      # laboratorio (raíz ≈ 1.5214)

X0, X1 = 1.0, 2.0
X2 = secant_step(F, X0, X1)                 # 1.3333
X3 = secant_step(F, X1, X2)                 # 1.4000
ERR = abs((X3 - X2) / X3) * 100             # 4.76 %

# ───────────────────────── Contenido del juego ─────────────────────────
QUIZ = [
    {
        "q": "**¿Qué necesita el método de la secante para arrancar?**",
        "opts": [
            "Un solo valor inicial y la derivada $f'(x)$",
            "Dos valores iniciales, $x_0$ y $x_1$",
            "Un intervalo $[a,b]$ donde $f$ cambie de signo, siempre",
            "Ningún valor inicial",
        ],
        "ans": 1,
        "expl": "La derivada se aproxima con la pendiente de la recta que pasa por **dos** puntos, así que hacen falta $x_0$ y $x_1$.",
    },
    {
        "q": "**¿Cuál es la fórmula de iteración de la secante?**",
        "opts": [
            r"$x_{n+1}=x_n-\dfrac{f(x_n)}{f'(x_n)}$",
            r"$x_{n+1}=\dfrac{x_n+x_{n-1}}{2}$",
            r"$x_{n+1}=x_n-\dfrac{f(x_n)\,(x_n-x_{n-1})}{f(x_n)-f(x_{n-1})}$",
            r"$x_{n+1}=x_n+f(x_n)$",
        ],
        "ans": 2,
        "expl": "La primera es Newton-Raphson, la segunda es bisección. La secante usa la pendiente entre $x_{n-1}$ y $x_n$ en lugar de $f'(x_n)$.",
    },
    {
        "q": "**¿Cuál es la ventaja principal de la secante frente a Newton-Raphson?**",
        "opts": [
            "No necesita calcular la derivada $f'(x)$",
            "Siempre converge",
            "Converge más rápido que Newton en todos los casos",
            "No necesita valores iniciales",
        ],
        "ans": 0,
        "expl": "No hay que derivar: solo se evalúa $f$ una vez por iteración. A cambio converge un poco más lento (orden ≈ 1.618) y **no** está garantizada la convergencia.",
    },
]

CALC = {
    "calc1": {
        "title": "Reto 4 · Tu primera iteración",
        "prompt": (
            "Función: $f(x)=x^2-2$ (su raíz es $\\sqrt{2}\\approx 1.4142$).\n\n"
            "Con $x_0=1$ y $x_1=2$, calcula **$x_2$**. Responde con 4 decimales."
        ),
        "answer": X2,
        "tol": 0.0005,
        "hint": "Primero calcula $f(x_0)=-1$ y $f(x_1)=2$. Luego sustituye en la fórmula con $x_n=x_1$ y $x_{n-1}=x_0$.",
        "expl": r"$x_2 = 2-\dfrac{2\cdot(2-1)}{2-(-1)} = 2-\dfrac{2}{3}=\mathbf{1.3333}$",
    },
    "calc2": {
        "title": "Reto 5 · Segunda iteración",
        "prompt": (
            "Ahora usa $x_1=2$ y $x_2=1.3333$ (¡el viejo $x_0$ se descarta!).\n\n"
            "Calcula **$x_3$** con 4 decimales."
        ),
        "answer": X3,
        "tol": 0.0005,
        "hint": "$f(x_2)=1.3333^2-2\\approx-0.2222$ y $f(x_1)=2$.",
        "expl": r"$x_3 = 1.3333-\dfrac{(-0.2222)(1.3333-2)}{-0.2222-2}=\mathbf{1.4000}$",
    },
    "calc3": {
        "title": "Reto 6 · ¿Cuánto error llevamos?",
        "prompt": (
            "El error relativo aproximado entre dos iteraciones es\n\n"
            r"$\varepsilon_a=\left|\dfrac{x_3-x_2}{x_3}\right|\cdot 100\%$" "\n\n"
            "Con $x_2=1.3333$ y $x_3=1.4000$, calcula **$\\varepsilon_a$ en %** (2 decimales)."
        ),
        "answer": ERR,
        "tol": 0.05,
        "hint": "$x_3-x_2 = 0.0667$. Divídelo entre $x_3=1.4$ y multiplica por 100.",
        "expl": r"$\varepsilon_a=\left|\dfrac{1.4000-1.3333}{1.4000}\right|\cdot100=\mathbf{4.76\%}$",
    },
}

ORDER = ["intro", "quiz0", "quiz1", "quiz2", "calc1", "calc2", "calc3", "lab", "final"]
N_CHALLENGES = len(ORDER) - 2  # sin intro ni final


# ───────────────────────── Estado ─────────────────────────
def init_state():
    st.session_state.setdefault("step_idx", 0)
    st.session_state.setdefault("stepstate", {})
    st.session_state.setdefault("t0", None)
    st.session_state.setdefault("player", "")
    st.session_state.setdefault("result", None)


def ss(step_id):
    return st.session_state.stepstate.setdefault(
        step_id, {"attempts": 0, "hint": False, "done": False, "points": 0, "correct": None, "msg": None}
    )


def go_next():
    st.session_state.step_idx += 1
    st.rerun()


def current_points():
    return sum(s["points"] for s in st.session_state.stepstate.values())


def fmt_time(sec):
    return f"{sec // 60}:{sec % 60:02d}"


def parse_num(text):
    try:
        return float(text.strip().replace(",", "."))
    except ValueError:
        return None


# ───────────────────────── Gráficas ─────────────────────────
def draw_secant(ax, f, a, b, xmin, xmax, **kw):
    """Dibuja la recta que pasa por (a,f(a)) y (b,f(b))."""
    xs = np.array([xmin, xmax])
    slope = (f(b) - f(a)) / (b - a)
    ax.plot(xs, f(a) + slope * (xs - a), **kw)


def plot_intro():
    f = lambda x: x**2 - 9
    x0, x1 = 2.0, 4.0
    x2 = secant_step(f, x0, x1)
    xx = np.linspace(1.5, 4.5, 200)
    fig, ax = plt.subplots(figsize=(6.2, 3.3))
    ax.plot(xx, f(xx), lw=2, label="f(x)")
    ax.axhline(0, color="gray", lw=0.8)
    draw_secant(ax, f, x0, x1, 1.5, 4.5, ls="--", color="tab:orange", label="recta secante")
    ax.scatter([x0, x1], [f(x0), f(x1)], color="tab:red", zorder=5)
    ax.scatter([x2], [0], color="tab:green", zorder=5)
    for x, y, t in [(x0, f(x0), "x₀"), (x1, f(x1), "x₁")]:
        ax.annotate(t, (x, y), textcoords="offset points", xytext=(-14, 6))
    ax.annotate("x₂ (nuevo punto)", (x2, 0), textcoords="offset points", xytext=(6, -16))
    ax.set_xlim(1.5, 4.5)
    ax.set_ylim(-8, 12)
    ax.set_title("f(x)=x²−9 · x₀=2, x₁=4  →  x₂≈2.8333", fontsize=10)
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.25)
    st.pyplot(fig)
    plt.close(fig)


def plot_lab(xs):
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    xx = np.linspace(0, 4, 300)
    ax.plot(xx, G(xx), lw=2, label="g(x)=x³−x−2")
    ax.axhline(0, color="gray", lw=0.8)
    for k in range(min(4, len(xs) - 2)):
        draw_secant(ax, G, xs[k], xs[k + 1], 0, 4, ls="--", lw=1, alpha=0.7)
    visible = [(i, x) for i, x in enumerate(xs[:8]) if 0 <= x <= 4]
    ax.scatter([x for _, x in visible], [0] * len(visible), color="tab:red", zorder=5)
    for i, x in visible:
        ax.annotate(f"x{i}", (x, 0), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8)
    ax.set_xlim(0, 4)
    ax.set_ylim(-6, 20)
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.25)
    st.pyplot(fig)
    plt.close(fig)


# ───────────────────────── Podio ─────────────────────────
def podium_html(rows):
    heights = [150, 115, 90]
    cells = []
    for pos in [1, 0, 2]:  # 2º, 1º, 3º
        if pos < len(rows):
            name, pts, secs = rows[pos]
            cells.append(
                f"""<div style="flex:1;max-width:190px;text-align:center;min-width:0">
                <div style="font-size:2rem">{MEDALS[pos]}</div>
                <div style="font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{html.escape(name)}</div>
                <div style="opacity:.75;font-size:.85rem">{pts} pts · {fmt_time(secs)}</div>
                <div style="height:{heights[pos]}px;margin-top:6px;border-radius:10px 10px 0 0;
                background:rgba(128,128,128,.25);display:flex;justify-content:center;
                font-size:2rem;font-weight:700;padding-top:8px">{pos + 1}</div></div>"""
            )
        else:
            cells.append('<div style="flex:1;max-width:190px"></div>')
    return (
        '<div style="display:flex;align-items:flex-end;justify-content:center;gap:12px;margin:1rem 0">'
        + "".join(cells)
        + "</div>"
    )


def ranking_table(rows):
    df = pd.DataFrame(
        [(i + 1, n, p, fmt_time(s)) for i, (n, p, s) in enumerate(rows)],
        columns=["Puesto", "Jugador", "Puntos", "Tiempo"],
    )
    st.dataframe(df, hide_index=True)


# ───────────────────────── Pantallas ─────────────────────────
def render_intro():
    st.title("🎯 Reto de la Secante")
    st.caption("⏱️ ~8 minutos · 7 retos · suma puntos y sube al podio")

    t1, t2, t3 = st.tabs(["1️⃣ La idea", "2️⃣ Cómo se juega", "3️⃣ Puntos"])
    with t1:
        st.markdown(
            "Queremos encontrar la raíz de una función, es decir, el $x$ donde $f(x)=0$.\n\n"
            "Newton-Raphson necesita la derivada $f'(x)$. **La secante la evita**: usa la pendiente de la "
            "recta que une los dos últimos puntos."
        )
        st.latex(r"x_{n+1}=x_n-\frac{f(x_n)\,(x_n-x_{n-1})}{f(x_n)-f(x_{n-1})}")
        st.markdown(
            "**Paso a paso:**\n"
            "1. Elige dos puntos iniciales $x_0$ y $x_1$.\n"
            "2. Traza la recta que pasa por $(x_0,f(x_0))$ y $(x_1,f(x_1))$.\n"
            "3. Donde esa recta corta el eje $x$ está el nuevo punto $x_2$.\n"
            "4. Descarta el más viejo ($x_0$) y repite con $x_1$ y $x_2$ hasta que el error sea pequeño."
        )
        plot_intro()
        st.markdown(
            "**Ejemplo rápido:** $f(x)=x^2-9$, $x_0=2$, $x_1=4$ → "
            r"$x_2=4-\dfrac{7\cdot(4-2)}{7-(-5)}\approx 2.8333$ (la raíz real es 3)."
        )
    with t2:
        st.markdown(
            "**Nivel 1 · Teoría** (3 preguntas de opción múltiple)\n\n"
            "**Nivel 2 · Calcula a mano** (3 retos: $x_2$, $x_3$ y el error). Puedes usar calculadora.\n\n"
            "**Nivel 3 · Laboratorio** (1 reto): elige $x_0$ y $x_1$ y mira cómo la secante llega a la raíz.\n\n"
            "**Reglas**\n"
            "- Cada cálculo tiene **3 intentos** y cada pregunta de teoría **2**.\n"
            "- Puedes usar punto o coma decimal (`1.3333` o `1,3333`).\n"
            "- Hay **pistas**, pero cuestan puntos.\n"
            "- El reloj corre desde que presionas *Empezar*; terminar rápido da bono."
        )
    with t3:
        st.table(
            pd.DataFrame(
                {
                    "Reto": ["Teoría (×3)", "Cálculos (×3)", "Laboratorio", "Bono de tiempo"],
                    "Máximo": ["50 c/u", "100 c/u", "100", "hasta 100"],
                    "Cómo se pierde": [
                        "2º intento vale 25",
                        "intentos: 100 → 70 → 40 · pista: −15",
                        "más iteraciones = menos puntos",
                        "baja a 0 a los 10 min",
                    ],
                }
            )
        )
        st.caption("Puntaje máximo: 650.")

    st.divider()
    name = st.text_input("Tu nombre para el podio", max_chars=24, key="name_input", placeholder="Ej. Camila")
    if st.button("🚀 Empezar", type="primary", disabled=not name.strip()):
        st.session_state.player = name.strip()
        st.session_state.t0 = time.time()
        go_next()

    rows = top_scores(3)
    if rows:
        st.subheader("🏆 Podio actual")
        st.markdown(podium_html(rows), unsafe_allow_html=True)


def render_quiz(i):
    q = QUIZ[i]
    sid = f"quiz{i}"
    s = ss(sid)
    st.subheader(f"Nivel 1 · Teoría — Reto {i + 1}")
    st.markdown(q["q"])
    choice = st.radio(
        "Opciones", q["opts"], index=None, key=f"radio_{sid}", disabled=s["done"], label_visibility="collapsed"
    )
    if not s["done"]:
        if st.button("Responder", key=f"btn_{sid}", disabled=choice is None):
            s["attempts"] += 1
            if q["opts"].index(choice) == q["ans"]:
                s.update(done=True, correct=True, points=50 if s["attempts"] == 1 else 25)
            elif s["attempts"] >= 2:
                s.update(done=True, correct=False, points=0)
            st.rerun()
        if s["attempts"] == 1:
            st.warning("Casi. Tienes un intento más (vale 25 pts).")
    else:
        if s["correct"]:
            st.success(f"¡Correcto! +{s['points']} pts")
        else:
            st.error("No era esa. La respuesta correcta está marcada abajo.")
            st.markdown("✅ " + q["opts"][q["ans"]])
        st.markdown(q["expl"])
        if st.button("Siguiente ➜", key=f"next_{sid}", type="primary"):
            go_next()


def render_calc(sid):
    c = CALC[sid]
    s = ss(sid)
    st.subheader(c["title"])
    st.markdown(c["prompt"])
    with st.expander("📖 Fórmula"):
        st.latex(r"x_{n+1}=x_n-\frac{f(x_n)\,(x_n-x_{n-1})}{f(x_n)-f(x_{n-1})}")

    if not s["done"]:
        val = st.text_input("Tu respuesta", key=f"in_{sid}", placeholder="Ej. 1.2345")
        c1, c2 = st.columns(2)
        if c1.button("Comprobar", key=f"chk_{sid}", type="primary"):
            x = parse_num(val)
            if x is None:
                s["msg"] = ("warning", "Escribe un número válido (ej. 1.2345).")
            else:
                s["attempts"] += 1
                if abs(x - c["answer"]) <= c["tol"]:
                    base = [100, 70, 40][s["attempts"] - 1]
                    s.update(done=True, correct=True, points=max(0, base - (15 if s["hint"] else 0)), msg=None)
                elif s["attempts"] >= 3:
                    s.update(done=True, correct=False, points=0, msg=None)
                else:
                    s["msg"] = ("error", f"No coincide. Te quedan {3 - s['attempts']} intento(s).")
            st.rerun()
        if c2.button("💡 Pista (−15 pts)", key=f"hint_{sid}", disabled=s["hint"]):
            s["hint"] = True
            st.rerun()
        if s["hint"]:
            st.info(c["hint"])
        if s["msg"]:
            getattr(st, s["msg"][0])(s["msg"][1])
    else:
        if s["correct"]:
            st.success(f"¡Correcto! +{s['points']} pts")
        else:
            st.error(f"Se acabaron los intentos. La respuesta era {c['answer']:.4f}." if sid != "calc3" else
                     f"Se acabaron los intentos. La respuesta era {c['answer']:.2f} %.")
        st.markdown(c["expl"])
        if st.button("Siguiente ➜", key=f"next_{sid}", type="primary"):
            go_next()


def lab_points(iters):
    if iters <= 4:
        return 100
    return {5: 80, 6: 60}.get(iters, 30)


def render_lab():
    s = ss("lab")
    s.setdefault("runs", [])
    st.subheader("Nivel 3 · Laboratorio — Reto 7")
    st.markdown(
        "Función: $g(x)=x^3-x-2$ (tiene una sola raíz real, cerca de $1.52$).\n\n"
        "**Misión:** elige $x_0$ y $x_1$ para que el método llegue a $|g(x)|<10^{-6}$ en la menor cantidad "
        "de iteraciones. Tienes **3 lanzamientos** y cuenta el mejor.\n\n"
        "`≤4 iter → 100 pts` · `5 → 80` · `6 → 60` · `más → 30`"
    )
    c1, c2 = st.columns(2)
    x0 = c1.slider("x₀", 0.0, 4.0, 1.0, 0.1, key="lab_x0")
    x1 = c2.slider("x₁", 0.0, 4.0, 2.0, 0.1, key="lab_x1")

    left = 3 - s["attempts"]
    if st.button(f"▶ Lanzar la secante ({left} restantes)", disabled=left <= 0, type="primary"):
        if x0 == x1:
            s["msg"] = ("warning", "x₀ y x₁ deben ser distintos (si no, la recta secante no existe).")
        else:
            xs, ok, why = secant_run(G, x0, x1)
            iters = len(xs) - 2
            pts = lab_points(iters) if ok else 0
            s["attempts"] += 1
            s["points"] = max(s["points"], pts)
            s["runs"].append({"x0": x0, "x1": x1, "xs": xs, "ok": ok, "why": why, "iters": iters, "pts": pts})
            s["msg"] = None
        st.rerun()

    if s.get("msg"):
        getattr(st, s["msg"][0])(s["msg"][1])

    if s["runs"]:
        run = s["runs"][-1]
        plot_lab(run["xs"])
        if run["ok"]:
            st.success(
                f"Convergió en **{run['iters']} iteraciones** → {run['pts']} pts "
                f"(mejor puntaje: {s['points']})"
            )
        else:
            st.error(run["why"] or "No convergió.")
        table = pd.DataFrame(
            {"n": range(len(run["xs"])), "xₙ": run["xs"], "g(xₙ)": [G(x) for x in run["xs"]]}
        ).head(10)
        st.dataframe(table, hide_index=True)

        if st.button("Terminar y ver resultados ➜", disabled=(s["attempts"] == 0)):
            s["done"] = True
            go_next()


def render_final():
    if st.session_state.result is None:
        elapsed = int(time.time() - st.session_state.t0)
        bonus = max(0, round(100 * (1 - elapsed / TIME_LIMIT)))
        base = current_points()
        total = base + bonus
        save_score(st.session_state.player, total, elapsed)
        st.session_state.result = {"elapsed": elapsed, "bonus": bonus, "base": base, "total": total}
        st.balloons()
    r = st.session_state.result

    st.title(f"🏁 ¡Listo, {st.session_state.player}!")
    m1, m2, m3 = st.columns(3)
    m1.metric("Puntos totales", r["total"])
    m2.metric("Tiempo", fmt_time(r["elapsed"]))
    m3.metric("Bono de tiempo", f"+{r['bonus']}")

    rows_all = top_scores(1000)
    pos = next((i + 1 for i, (n, _, _) in enumerate(rows_all) if n.lower() == st.session_state.player.lower()), None)
    if pos:
        st.caption(f"Tu mejor resultado está en el puesto #{pos} de {len(rows_all)}.")

    st.subheader("🏆 Podio")
    st.markdown(podium_html(rows_all[:3]), unsafe_allow_html=True)
    ranking_table(rows_all[:10])

    st.subheader("📌 Lo que te llevas")
    st.markdown(
        "- La secante necesita **dos** puntos iniciales y **no** usa derivadas.\n"
        "- Cada iteración usa los **dos últimos** puntos y descarta el más viejo.\n"
        "- Se detiene cuando el error aproximado (o $|f(x)|$) es suficientemente pequeño.\n"
        "- Una mala elección de $x_0$ y $x_1$ puede hacerla lenta o divergir."
    )
    if st.button("🔄 Jugar de nuevo"):
        name = st.session_state.player
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.session_state["name_input"] = name
        st.rerun()


# ───────────────────────── Barra lateral ─────────────────────────
def render_sidebar():
    with st.sidebar:
        step = ORDER[st.session_state.step_idx]
        if step not in ("intro", "final"):
            st.metric("Puntos", current_points())
            elapsed = int(time.time() - st.session_state.t0)
            st.metric("Tiempo", fmt_time(elapsed))
            if elapsed > TIME_LIMIT:
                st.caption("Pasaste los 10 min: ya no hay bono de tiempo.")
            st.divider()
        st.subheader("🏆 Podio en vivo")
        rows = top_scores(3)
        if rows:
            for i, (n, p, _) in enumerate(rows):
                st.write(f"{MEDALS[i]} **{n}** — {p}")
        else:
            st.caption("Aún nadie ha terminado. ¡Sé el primero!")
        with st.expander("Admin"):
            pwd = st.text_input("Contraseña", type="password", key="admin_pwd")
            if st.button("Reiniciar ranking"):
                if pwd == ADMIN_PASSWORD:
                    reset_ranking()
                    st.success("Ranking reiniciado.")
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta.")


# ───────────────────────── Main ─────────────────────────
def main():
    init_state()
    render_sidebar()
    step = ORDER[st.session_state.step_idx]

    if step not in ("intro", "final"):
        idx = st.session_state.step_idx
        st.progress((idx - 1) / N_CHALLENGES, text=f"Reto {idx} de {N_CHALLENGES}")

    if step == "intro":
        render_intro()
    elif step.startswith("quiz"):
        render_quiz(int(step[-1]))
    elif step.startswith("calc"):
        render_calc(step)
    elif step == "lab":
        render_lab()
    else:
        render_final()


main()
