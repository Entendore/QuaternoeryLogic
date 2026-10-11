"""
Quaternary Logic System — PySide6 GUI
Wraps the Prolog backend for interactive use cases.
"""

import sys
import os
from typing import List, Optional, Tuple
from pyswip import Prolog, PrologError

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QHBoxLayout, QGridLayout, QLabel, QPushButton, QLineEdit,
    QTextEdit, QSpinBox, QComboBox, QGroupBox, QFormLayout,
    QFrame, QMessageBox, QSplitter, QSlider, QCheckBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QFont, QPalette

try:
    import matplotlib
    matplotlib.use('QtAgg')
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


# ═══════════════════════════════════════════════════════════════════
# PROLOG BRIDGE
# ═══════════════════════════════════════════════════════════════════

class PrologEngine:
    """Singleton Prolog engine that loads the quaternary.pl file."""
    _instance = None
    _prolog = None

    @classmethod
    def get(cls) -> 'PrologEngine':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._prolog = Prolog()
        pl_file = os.path.join(os.path.dirname(__file__), 'quaternary.pl')
        if not os.path.exists(pl_file):
            raise FileNotFoundError(f"quaternary.pl not found at {pl_file}")
        self._prolog.consult(pl_file)

    def query(self, q: str) -> List[dict]:
        """Run a Prolog query and return all solutions as list of dicts."""
        try:
            return list(self._prolog.query(q))
        except PrologError as e:
            return [{"_error": str(e)}]

    def query_once(self, q: str) -> Optional[dict]:
        """Return first solution or None."""
        results = self.query(q)
        return results[0] if results else None

    def raw_query(self, q: str) -> str:
        """Run query and format results as string."""
        results = self.query(q)
        if not results:
            return "false."
        lines = []
        for r in results:
            if "_error" in r:
                return f"ERROR: {r['_error']}"
            if not r:
                lines.append("true.")
            else:
                pairs = [f"{k} = {v}" for k, v in r.items()]
                lines.append(", ".join(pairs))
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# BASE TAB
# ═══════════════════════════════════════════════════════════════════

class BaseTab(QWidget):
    """Base class for all use-case tabs."""

    def __init__(self, title: str):
        super().__init__()
        self.engine = PrologEngine.get()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 12, 12, 12)

        title_label = QLabel(f"<h2>{title}</h2>")
        title_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(title_label)

    def add_output(self, readonly: bool = True) -> QTextEdit:
        out = QTextEdit()
        out.setReadOnly(readonly)
        out.setFont(QFont("Consolas", 10))
        self.layout.addWidget(out)
        return out


# ═══════════════════════════════════════════════════════════════════
# TAB 1: PROLOG CONSOLE
# ═══════════════════════════════════════════════════════════════════

class PrologConsoleTab(BaseTab):
    def __init__(self):
        super().__init__("Prolog Console")

        hint = QLabel("Enter Prolog queries. End with a period. Example: <code>qxor(2, 3, X).</code>")
        hint.setWordWrap(True)
        self.layout.addWidget(hint)

        self.input = QLineEdit()
        self.input.setPlaceholderText("qxor(2, 3, X).")
        self.input.returnPressed.connect(self.run_query)
        self.input.setFont(QFont("Consolas", 11))
        self.layout.addWidget(self.input)

        btn_row = QHBoxLayout()
        run_btn = QPushButton("▶ Run Query")
        run_btn.clicked.connect(self.run_query)
        clear_btn = QPushButton("🗑 Clear")
        clear_btn.clicked.connect(lambda: self.output.clear())
        examples_btn = QPushButton("💡 Examples")
        examples_btn.clicked.connect(self.show_examples)
        btn_row.addWidget(run_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addWidget(examples_btn)
        self.layout.addLayout(btn_row)

        self.output = self.add_output()

    def run_query(self):
        q = self.input.text().strip()
        if not q:
            return
        self.output.append(f"?- {q}")
        result = self.engine.raw_query(q)
        self.output.append(result)
        self.output.append("")

    def show_examples(self):
        examples = [
            "qxor(2, 3, X).",
            "notq(1, X).",
            "qand(2, 3, X).",
            "dna_to_q(['A','T','G','C'], Q).",
            "qpsk_modulate(2, I, Qc).",
            "seg7(3, Segs).",
            "traffic_step(2, timer, Next, Duration).",
            "findall(X, between(0,3,X), Ls).",
        ]
        self.output.append("─── Example Queries ───")
        for e in examples:
            self.output.append(f"  {e}")
        self.output.append("")


# ═══════════════════════════════════════════════════════════════════
# TAB 2: DNA ANALYZER
# ═══════════════════════════════════════════════════════════════════

NUC_COLORS = {'A': '#4CAF50', 'C': '#2196F3', 'G': '#FFC107', 'T': '#F44336'}

class DNATab(BaseTab):
    def __init__(self):
        super().__init__("🧬 DNA Sequence Analyzer")

        form = QFormLayout()
        self.seq_input = QLineEdit("ATGCCATG")
        self.seq_input.setPlaceholderText("e.g. ATGCCATG")
        form.addRow("DNA Sequence:", self.seq_input)
        self.layout.addLayout(form)

        btn_row = QHBoxLayout()
        for label, fn in [
            ("Encode → Q", self.encode),
            ("Complement", self.complement),
            ("Rev. Complement", self.rev_comp),
            ("GC Content", self.gc_content),
        ]:
            b = QPushButton(label)
            b.clicked.connect(fn)
            btn_row.addWidget(b)
        self.layout.addLayout(btn_row)

        self.output = self.add_output()
        self.viz = QLabel()
        self.viz.setAlignment(Qt.AlignCenter)
        self.viz.setMinimumHeight(60)
        self.layout.addWidget(self.viz)

    def _parse_seq(self) -> List[str]:
        return [c.upper() for c in self.seq_input.text() if c.upper() in 'ACGT']

    def _render_dna(self, seq: List[str]):
        html = "".join(f'<span style="background:{NUC_COLORS[c]};color:white;'
                       f'padding:2px 6px;margin:1px;font-weight:bold;">{c}</span>'
                       for c in seq)
        self.viz.setText(html)

    def encode(self):
        seq = self._parse_seq()
        if not seq:
            return
        prolog_list = "[" + ",".join(f"'{c}'" for c in seq) + "]"
        res = self.engine.query_once(f"dna_to_q({prolog_list}, Q)")
        if res:
            self.output.append(f"DNA:      {''.join(seq)}")
            self.output.append(f"Quaternary: {res['Q']}")
            self._render_dna(seq)
            self.output.append("")

    def complement(self):
        seq = self._parse_seq()
        if not seq:
            return
        prolog_list = "[" + ",".join(f"'{c}'" for c in seq) + "]"
        res = self.engine.query_once(f"dna_to_q({prolog_list}, Q), dna_complement(Q, C), q_to_dna(C, DNA)")
        if res:
            comp = [str(x).strip("'") for x in res['DNA']]
            self.output.append(f"Original:    {''.join(seq)}")
            self.output.append(f"Complement:  {''.join(comp)}")
            self._render_dna(comp)
            self.output.append("")

    def rev_comp(self):
        seq = self._parse_seq()
        if not seq:
            return
        prolog_list = "[" + ",".join(f"'{c}'" for c in seq) + "]"
        res = self.engine.query_once(f"dna_to_q({prolog_list}, Q), dna_rev_comp(Q, RC), q_to_dna(RC, DNA)")
        if res:
            rc = [str(x).strip("'") for x in res['DNA']]
            self.output.append(f"Original:         {''.join(seq)}")
            self.output.append(f"Rev. Complement:  {''.join(rc)}")
            self._render_dna(rc)
            self.output.append("")

    def gc_content(self):
        seq = self._parse_seq()
        if not seq:
            return
        prolog_list = "[" + ",".join(f"'{c}'" for c in seq) + "]"
        res = self.engine.query_once(f"dna_to_q({prolog_list}, Q), gc_content(Q, GC, Total)")
        if res:
            gc, total = int(res['GC']), int(res['Total'])
            pct = gc * 100 / total if total else 0
            self.output.append(f"Sequence: {''.join(seq)}")
            self.output.append(f"GC content: {gc}/{total} = {pct:.1f}%")
            self.output.append("")


# ═══════════════════════════════════════════════════════════════════
# TAB 3: 7-SEGMENT CALCULATOR
# ═══════════════════════════════════════════════════════════════════

class Seg7Widget(QFrame):
    """Custom-painted 7-segment display."""
    def __init__(self, value: int = 0, parent=None):
        super().__init__(parent)
        self.value = value
        self.setFixedSize(80, 140)
        self.setStyleSheet("background-color: #1a1a1a; border: 2px solid #333; border-radius: 6px;")

    def set_value(self, v: int):
        self.value = v
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        res = self.engine.query_once(f"seg7({self.value}, S)") if hasattr(self, 'engine') else None
        if not res:
            p.end(); return

        segs = [int(x) for x in res['S']]
        on_color = QColor('#ff3030')
        off_color = QColor('#3a1010')

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        thick = 8
        length = w - 30

        def seg_rect(x, y, horizontal):
            if horizontal:
                return (x, y, length, thick)
            return (x, y, thick, length)

        # Segment positions: a=top, b=top-right, c=bot-right, d=bottom, e=bot-left, f=top-left, g=middle
        positions = [
            seg_rect(15, 10, True),            # a
            seg_rect(w - 15 - thick, 14, False), # b
            seg_rect(w - 15 - thick, cy + 4, False), # c
            seg_rect(15, h - 10 - thick, True), # d
            seg_rect(15, cy + 4, False),       # e
            seg_rect(15, 14, False),           # f
            seg_rect(15, cy - thick // 2, True), # g
        ]

        for i, (x, y, sw, sh) in enumerate(positions):
            color = on_color if segs[i] else off_color
            p.setBrush(color)
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(x, y, sw, sh, 3, 3)

        p.end()


class CalculatorTab(BaseTab):
    def __init__(self):
        super().__init__("🔢 Quaternary Calculator")

        row = QHBoxLayout()
        self.a_spin = QSpinBox(); self.a_spin.setRange(0, 3); self.a_spin.setValue(2)
        self.op_combo = QComboBox()
        self.op_combo.addItems(["add (+)", "sub (−)", "mul (×)", "AND", "OR", "XOR"])
        self.b_spin = QSpinBox(); self.b_spin.setRange(0, 3); self.b_spin.setValue(3)
        row.addWidget(QLabel("A:")); row.addWidget(self.a_spin)
        row.addWidget(self.op_combo)
        row.addWidget(QLabel("B:")); row.addWidget(self.b_spin)
        calc_btn = QPushButton("="); calc_btn.clicked.connect(self.calculate)
        row.addWidget(calc_btn)
        self.layout.addLayout(row)

        self.display = Seg7Widget(0)
        self.display.engine = self.engine
        self.result_label = QLabel("Result: ?")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setFont(QFont("Consolas", 14, QFont.Bold))

        disp_row = QHBoxLayout()
        disp_row.addStretch(); disp_row.addWidget(self.display); disp_row.addStretch()
        self.layout.addLayout(disp_row)
        self.layout.addWidget(self.result_label)

        self.output = self.add_output()

        # Truth table
        self.truth_table = QTextEdit()
        self.truth_table.setReadOnly(True)
        self.truth_table.setFont(QFont("Consolas", 10))
        self.layout.addWidget(QLabel("<b>Full Truth Table (QXOR):</b>"))
        self.layout.addWidget(self.truth_table)
        self._show_truth_table()

    def calculate(self):
        a, b = self.a_spin.value(), self.b_spin.value()
        op_idx = self.op_combo.currentIndex()
        op_map = {0: 'qfa', 1: 'qfs', 2: 'qmul1', 3: 'qand', 4: 'qor', 5: 'qxor'}
        op_name = op_map[op_idx]
        op_symbol = ["+", "−", "×", "AND", "OR", "XOR"][op_idx]

        if op_idx in (0, 1):
            cin = '0' if op_idx == 0 else '0'
            q = f"{op_name}({a}, {b}, {cin}, Sum, Cout)"
            res = self.engine.query_once(q)
            if res:
                s, c = int(res['Sum']), int(res['Cout'])
                self.display.set_value(s)
                self.result_label.setText(f"{a} {op_symbol} {b} = {s}  (carry/borrow: {c})")
                self.output.append(f"{a} {op_symbol} {b} = {s} (C={c})")
        elif op_idx == 2:
            q = f"qmul1({a}, {b}, Hi, Lo)"
            res = self.engine.query_once(q)
            if res:
                hi, lo = int(res['Hi']), int(res['Lo'])
                self.display.set_value(lo)
                self.result_label.setText(f"{a} × {b} = {hi}{lo}₄  (={a*b} in decimal)")
                self.output.append(f"{a} × {b} = {hi}{lo}₄")
        else:
            q = f"{op_name}({a}, {b}, R)"
            res = self.engine.query_once(q)
            if res:
                r = int(res['R'])
                self.display.set_value(r)
                self.result_label.setText(f"{a} {op_symbol} {b} = {r}")
                self.output.append(f"{a} {op_symbol} {b} = {r}")

    def _show_truth_table(self):
        lines = ["A B | A⊕B", "---------"]
        for a in range(4):
            for b in range(4):
                res = self.engine.query_once(f"qxor({a}, {b}, R)")
                r = int(res['R']) if res else '?'
                lines.append(f"{a} {b} |  {r}")
        self.truth_table.setPlainText("\n".join(lines))


# ═══════════════════════════════════════════════════════════════════
# TAB 4: TRAFFIC LIGHT
# ═══════════════════════════════════════════════════════════════════

class TrafficLightWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 300)
        self.setStyleSheet("background-color: #2b2b2b; border-radius: 12px; border: 2px solid #444;")
        self.state = 0  # 0=red, 1=yellow, 2=green, 3=off

    def set_state(self, s: int):
        self.state = s
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        radius = 35
        colors = [QColor('#ff2020'), QColor('#ffcc00'), QColor('#20dd40'), QColor('#444')]
        dim_colors = [QColor('#4a0808'), QColor('#4a3a00'), QColor('#084a10'), QColor('#222')]

        y_positions = [40, 40 + 2*radius + 20, 40 + 4*radius + 40]
        for i, y in enumerate(y_positions):
            color = colors[i] if self.state == i else dim_colors[i]
            p.setBrush(color)
            p.setPen(QColor('#111'))
            p.drawEllipse(w // 2 - radius, y, 2 * radius, 2 * radius)
        p.end()


class TrafficTab(BaseTab):
    def __init__(self):
        super().__init__("🚦 Traffic Light Controller")

        main_row = QHBoxLayout()

        # Controls
        controls = QVBoxLayout()
        self.state_label = QLabel("State: RED")
        self.state_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.state_label.setAlignment(Qt.AlignCenter)
        controls.addWidget(self.state_label)

        self.duration_label = QLabel("Duration: 30s")
        self.duration_label.setAlignment(Qt.AlignCenter)
        controls.addWidget(self.duration_label)

        for text, evt in [("⏱ Timer", "timer"), ("🚑 Emergency", "emergency"),
                          ("🔧 Maintenance", "maintenance")]:
            b = QPushButton(text)
            b.clicked.connect(lambda _, e=evt: self.step(e))
            controls.addWidget(b)

        self.log = QTextEdit(); self.log.setReadOnly(); self.log.setMaximumHeight(150)
        controls.addWidget(QLabel("<b>Event Log:</b>"))
        controls.addWidget(self.log)

        # Light
        self.light = TrafficLightWidget()

        main_row.addLayout(controls)
        main_row.addWidget(self.light)
        self.layout.addLayout(main_row)

        self.current_state = 0
        self._update_display()

    def step(self, event: str):
        res = self.engine.query_once(
            f"traffic_step({self.current_state}, {event}, Next, Duration)"
        )
        if res:
            next_state = int(res['Next'])
            duration = int(res['Duration'])
            name_res = self.engine.query_once(f"state_name({next_state}, Name)")
            name = str(name_res['Name']) if name_res else "?"
            self.current_state = next_state
            self._update_display(name, duration)
            self.log.append(f"[{event}] → {name.upper()} ({duration}s)")

    def _update_display(self, name: str = "RED", duration: int = 30):
        self.light.set_state(self.current_state)
        self.state_label.setText(f"State: {name.upper()}")
        self.duration_label.setText(f"Duration: {duration}s")
        colors = {'RED': '#ff2020', 'YELLOW': '#ffcc00', 'GREEN': '#20dd40', 'OFF': '#888'}
        self.state_label.setStyleSheet(f"color: {colors.get(name, 'white')};")


# ═══════════════════════════════════════════════════════════════════
# TAB 5: COLOR MIXER
# ═══════════════════════════════════════════════════════════════════

class ColorPreview(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 120)
        self.color = QColor('#000000')
        self._update_style()

    def set_rgb(self, r: int, g: int, b: int):
        # Scale 0-3 → 0-255
        self.color = QColor(r * 85, g * 85, b * 85)
        self._update_style()

    def _update_style(self):
        self.setStyleSheet(f"background-color: {self.color.name()}; border: 2px solid #555; border-radius: 8px;")


class ColorTab(BaseTab):
    def __init__(self):
        super().__init__("🎨 Quaternary Color Mixer")

        grid = QGridLayout()
        self.sliders = {}
        for i, (name, color) in enumerate([("FG Red", 'red'), ("FG Green", 'green'), ("FG Blue", 'blue'),
                                            ("BG Red", 'red'), ("BG Green", 'green'), ("BG Blue", 'blue')]):
            label = QLabel(name)
            slider = QSlider(Qt.Horizontal); slider.setRange(0, 3); slider.setValue(0)
            slider.valueChanged.connect(self._update)
            val = QLabel("0")
            slider.valueChanged.connect(lambda v, lbl=val: lbl.setText(str(v)))
            grid.addWidget(label, i, 0)
            grid.addWidget(slider, i, 1)
            grid.addWidget(val, i, 2)
            self.sliders[name] = slider

        self.alpha_slider = QSlider(Qt.Horizontal); self.alpha_slider.setRange(0, 3); self.alpha_slider.setValue(3)
        self.alpha_slider.valueChanged.connect(self._update)
        grid.addWidget(QLabel("Alpha (blend):"), 6, 0)
        grid.addWidget(self.alpha_slider, 6, 1)

        self.layout.addLayout(grid)

        # Preview row
        preview_row = QHBoxLayout()
        self.fg_preview = ColorPreview()
        self.bg_preview = ColorPreview()
        self.result_preview = ColorPreview()
        for lbl, w in [("Foreground", self.fg_preview), ("Background", self.bg_preview),
                       ("Result", self.result_preview)]:
            col = QVBoxLayout()
            col.addWidget(QLabel(f"<b>{lbl}</b>", alignment=Qt.AlignCenter))
            col.addWidget(w, alignment=Qt.AlignCenter)
            preview_row.addLayout(col)
        self.layout.addLayout(preview_row)

        self.output = self.add_output()
        self._update()

    def _update(self):
        fg = (self.sliders["FG Red"].value(), self.sliders["FG Green"].value(), self.sliders["FG Blue"].value())
        bg = (self.sliders["BG Red"].value(), self.sliders["BG Green"].value(), self.sliders["BG Blue"].value())
        alpha = self.alpha_slider.value()

        self.fg_preview.set_rgb(*fg)
        self.bg_preview.set_rgb(*bg)

        # Blend via Prolog
        q = (f"blend_channel({fg[0]}, {bg[0]}, {alpha}, R), "
             f"blend_channel({fg[1]}, {bg[1]}, {alpha}, G), "
             f"blend_channel({fg[2]}, {bg[2]}, {alpha}, B)")
        res = self.engine.query_once(q)
        if res:
            r, g, b = int(res['R']), int(res['G']), int(res['B'])
            self.result_preview.set_rgb(r, g, b)
            self.output.setPlainText(
                f"FG: rgb({fg[0]},{fg[1]},{fg[2]})\n"
                f"BG: rgb({bg[0]},{bg[1]},{bg[2]})\n"
                f"Alpha: {alpha}\n"
                f"Result: rgb({r},{g},{b}) = #{r*85:02x}{g*85:02x}{b*85:02x}"
            )


# ═══════════════════════════════════════════════════════════════════
# TAB 6: QPSK CONSTELLATION
# ═══════════════════════════════════════════════════════════════════

class QPSKTab(BaseTab):
    def __init__(self):
        super().__init__("📡 QPSK Modulator")

        if not HAS_MPL:
            self.layout.addWidget(QLabel("⚠ matplotlib not installed — plot disabled"))
            self.output = self.add_output()
            return

        # Constellation diagram
        self.figure = Figure(figsize=(5, 5))
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.layout.addWidget(self.canvas)
        self._draw_constellation()

        # Bit input
        row = QHBoxLayout()
        row.addWidget(QLabel("Bit stream (e.g. 10110001):"))
        self.bits_input = QLineEdit("10110001")
        row.addWidget(self.bits_input)
        mod_btn = QPushButton("Modulate"); mod_btn.clicked.connect(self.modulate)
        row.addWidget(mod_btn)
        self.layout.addLayout(row)

        self.output = self.add_output()

    def _draw_constellation(self, highlighted: Optional[int] = None):
        self.ax.clear()
        for s in range(4):
            res = self.engine.query_once(f"qpsk_constellation({s}, Phase, I, Qc)")
            if res:
                I, Qc, phase = float(res['I']), float(res['Qc']), int(res['Phase'])
                color = 'red' if highlighted == s else 'blue'
                size = 200 if highlighted == s else 100
                self.ax.scatter(I, Qc, s=size, c=color, zorder=5)
                self.ax.annotate(f"  {s} ({phase}°)", (I, Qc), fontsize=11, fontweight='bold')
        self.ax.axhline(0, color='gray', linewidth=0.5)
        self.ax.axvline(0, color='gray', linewidth=0.5)
        self.ax.set_xlim(-1.3, 1.3); self.ax.set_ylim(-1.3, 1.3)
        self.ax.set_xlabel("In-Phase (I)")
        self.ax.set_ylabel("Quadrature (Q)")
        self.ax.set_title("QPSK Constellation Diagram")
        self.ax.grid(True, alpha=0.3)
        self.ax.set_aspect('equal')
        self.canvas.draw()

    def modulate(self):
        bits_str = self.bits_input.text().strip()
        bits = [int(b) for b in bits_str if b in '01']
        if len(bits) % 2 != 0:
            self.output.append("⚠ Bit stream must have even length")
            return

        self.output.clear()
        self.output.append(f"Bits: {bits_str}")
        self.output.append("Symbols:")
        for i in range(0, len(bits), 2):
            sym = bits[i] * 2 + bits[i+1]
            res = self.engine.query_once(f"qpsk_modulate({sym}, I, Qc)")
            if res:
                self.output.append(f"  {bits[i]}{bits[i+1]} → Symbol {sym}: I={float(res['I']):+.3f}, Q={float(res['Qc']):+.3f}")
        self._draw_constellation(sym)


# ═══════════════════════════════════════════════════════════════════
# TAB 7: COMBINATION LOCK
# ═══════════════════════════════════════════════════════════════════

class LockTab(BaseTab):
    def __init__(self):
        super().__init__("🔐 Quaternary Combination Lock")

        # Secret combo (hidden from user)
        self.secret = [1, 3, 0, 2]
        self.attempts = 0
        self.locked_out = False

        info = QLabel(f"<i>(Secret combination is {self.secret} — try to crack it!)</i>")
        info.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(info)

        # Digit spinners
        row = QHBoxLayout()
        self.digits = []
        for i in range(4):
            s = QSpinBox(); s.setRange(0, 3); s.setValue(0)
            s.setFixedWidth(60)
            self.digits.append(s)
            row.addWidget(s)
        self.layout.addLayout(row)

        btn_row = QHBoxLayout()
        try_btn = QPushButton("🔑 Try Combination"); try_btn.clicked.connect(self.try_combo)
        reset_btn = QPushButton("🔄 Reset Lock"); reset_btn.clicked.connect(self.reset)
        btn_row.addWidget(try_btn); btn_row.addWidget(reset_btn)
        self.layout.addLayout(btn_row)

        self.status = QLabel("Attempts: 0 / 3")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setFont(QFont("Arial", 12))
        self.layout.addWidget(self.status)

        self.output = self.add_output()

    def try_combo(self):
        if self.locked_out:
            self.output.append("⛔ Lock is locked out. Reset to try again.")
            return

        guess = [s.value() for s in self.digits]
        prolog_guess = "[" + ",".join(map(str, guess)) + "]"
        prolog_secret = "[" + ",".join(map(str, self.secret)) + "]"

        res = self.engine.query_once(f"combo_distance({prolog_secret}, {prolog_guess}, D)")
        if res:
            dist = int(res['D'])
            hint_res = self.engine.query_once(f"hint_from_distance({dist}, Hint)")
            hint = str(hint_res['Hint']) if hint_res else "?"
            self.attempts += 1

            if dist == 0:
                self.status.setText("🎉 UNLOCKED!")
                self.status.setStyleSheet("color: green; font-weight: bold;")
                self.output.append(f"✓ Guess {guess} — EXACT MATCH! Unlocked in {self.attempts} attempts.")
            elif self.attempts >= 3:
                self.locked_out = True
                self.status.setText("⛔ LOCKED OUT")
                self.status.setStyleSheet("color: red; font-weight: bold;")
                self.output.append(f"✗ Guess {guess} (distance {dist}, {hint}) — LOCKED OUT!")
            else:
                self.status.setText(f"Attempts: {self.attempts} / 3  |  Hint: {hint}")
                self.output.append(f"✗ Guess {guess} — distance {dist} ({hint})")

    def reset(self):
        self.attempts = 0
        self.locked_out = False
        self.status.setText("Attempts: 0 / 3")
        self.status.setStyleSheet("")
        self.output.append("── Lock reset ──")


# ═══════════════════════════════════════════════════════════════════
# TAB 8: FLASH MEMORY
# ═══════════════════════════════════════════════════════════════════

class FlashTab(BaseTab):
    def __init__(self):
        super().__init__("💾 Multi-Level Flash Memory")

        form = QFormLayout()
        self.level_spin = QSpinBox(); self.level_spin.setRange(0, 3); self.level_spin.setValue(2)
        form.addRow("Program Level (0-3):", self.level_spin)
        self.time_spin = QSpinBox(); self.time_spin.setRange(0, 500); self.time_spin.setValue(100)
        form.addRow("Time elapsed (cycles):", self.time_spin)
        self.layout.addLayout(form)

        sim_btn = QPushButton("⚡ Simulate Aging"); sim_btn.clicked.connect(self.simulate)
        self.layout.addWidget(sim_btn)

        self.output = self.add_output()

        # Voltage table
        self.layout.addWidget(QLabel("<b>Voltage Level Reference:</b>"))
        table = QTextEdit(); table.setReadOnly()
        table.setPlainText(
            "Level 0 (erased):  0.5V\n"
            "Level 1:           1.5V\n"
            "Level 2:           2.5V\n"
            "Level 3 (full):    3.5V\n\n"
            "Thresholds: 1.0V, 2.0V, 3.0V"
        )
        self.layout.addWidget(table)

    def simulate(self):
        level = self.level_spin.value()
        time = self.time_spin.value()

        res_v = self.engine.query_once(f"voltage_level({level}, V)")
        if not res_v: return
        v0 = float(res_v['V'])

        res_drift = self.engine.query_once(f"voltage_drift({v0}, {time}, Vd)")
        if not res_drift: return
        vd = float(res_drift['Vd'])

        res_read = self.engine.query_once(f"read_cell({vd}, ReadBack)")
        read_back = int(res_read['ReadBack']) if res_read else '?'

        self.output.clear()
        self.output.append(f"Programmed level: {level}")
        self.output.append(f"Initial voltage:  {v0:.2f}V")
        self.output.append(f"After {time} cycles: {vd:.2f}V")
        self.output.append(f"Read back as:     level {read_back}")
        if read_back != level:
            self.output.append(f"⚠ DATA CORRUPTION! Lost level due to charge leakage.")
        else:
            self.output.append(f"✓ Data intact.")

        # Gray code info
        res_gray = self.engine.query_once(f"gray_encode({level}, G)")
        if res_gray:
            gray = [int(x) for x in res_gray['G']]
            self.output.append(f"Gray code for level {level}: {gray}")


# ═══════════════════════════════════════════════════════════════════
# TAB 9: ELEVATOR
# ═══════════════════════════════════════════════════════════════════

class ElevatorTab(BaseTab):
    def __init__(self):
        super().__init__("🛗 4-Floor Elevator Controller")

        form = QFormLayout()
        self.current_spin = QSpinBox(); self.current_spin.setRange(0, 3); self.current_spin.setValue(1)
        form.addRow("Current Floor:", self.current_spin)
        self.target_spin = QSpinBox(); self.target_spin.setRange(0, 3); self.target_spin.setValue(3)
        form.addRow("Target Floor:", self.target_spin)
        self.layout.addLayout(form)

        go_btn = QPushButton("🚀 Go!"); go_btn.clicked.connect(self.go)
        self.layout.addWidget(go_btn)

        self.output = self.add_output()

        # Floor diagram
        self.floor_display = QLabel()
        self.floor_display.setAlignment(Qt.AlignCenter)
        self.floor_display.setFont(QFont("Consolas", 12))
        self.layout.addWidget(self.floor_display)
        self._update_diagram(1, None)

    def go(self):
        current = self.current_spin.value()
        target = self.target_spin.value()

        res_dist = self.engine.query_once(f"floor_distance({current}, {target}, D)")
        dist = int(res_dist['D']) if res_dist else 0

        res_moves = self.engine.query_once(f"elevator_moves({current}, {target}, Moves)")
        moves = [int(x) for x in res_moves['Moves']] if res_moves else []

        self.output.clear()
        cur_name = self._floor_name(current)
        tgt_name = self._floor_name(target)
        self.output.append(f"Traveling from {cur_name} to {tgt_name}")
        self.output.append(f"Distance: {dist} floor(s)")
        if moves:
            self.output.append(f"Stops: {['→ ' + self._floor_name(m) for m in moves]}")
        else:
            self.output.append("Already there!")

        self._update_diagram(target, moves)

    def _floor_name(self, f: int) -> str:
        res = self.engine.query_once(f"floor_name({f}, Name)")
        return str(res['Name']).title() if res else f"F{f}"

    def _update_diagram(self, current: int, moves: Optional[List[int]]):
        lines = []
        for f in [3, 2, 1, 0]:
            name = self._floor_name(f)
            marker = " 🛗 " if f == current else "    "
            lines.append(f"  {f} │ {name:10s} │{marker}│")
        self.floor_display.setText("\n".join(lines))


# ═══════════════════════════════════════════════════════════════════
# TAB 10: VOTING
# ═══════════════════════════════════════════════════════════════════

class VotingTab(BaseTab):
    def __init__(self):
        super().__init__("🗳️ Quaternary Voting System")

        self.layout.addWidget(QLabel("Ratings: 0=Strong No, 1=No, 2=Yes, 3=Strong Yes"))

        form = QFormLayout()
        self.votes_input = QLineEdit("3, 2, 3, 1, 2, 3, 2")
        self.votes_input.setPlaceholderText("e.g. 3, 2, 3, 1, 2")
        form.addRow("Votes (comma-separated):", self.votes_input)
        self.layout.addLayout(form)

        btn_row = QHBoxLayout()
        for label, fn in [("Tally", self.tally), ("Consensus", self.consensus),
                          ("Check Veto", self.veto)]:
            b = QPushButton(label); b.clicked.connect(fn)
            btn_row.addWidget(b)
        self.layout.addLayout(btn_row)

        self.output = self.add_output()

    def _parse_votes(self) -> List[int]:
        try:
            return [int(x.strip()) for x in self.votes_input.text().split(",") if x.strip()]
        except ValueError:
            return []

    def tally(self):
        votes = self._parse_votes()
        if not votes: return
        prolog_list = "[" + ",".join(map(str, votes)) + "]"
        res = self.engine.query_once(f"tally_votes({prolog_list}, Total, Average)")
        if res:
            self.output.append(f"Votes: {votes}")
            self.output.append(f"Total: {int(res['Total'])}")
            self.output.append(f"Average: {float(res['Average']):.2f}")
            self.output.append("")

    def consensus(self):
        votes = self._parse_votes()
        if not votes: return
        prolog_list = "[" + ",".join(map(str, votes)) + "]"
        res = self.engine.query_once(f"consensus({prolog_list}, Level)")
        if res:
            level = str(res['Level'])
            self.output.append(f"Votes: {votes}")
            self.output.append(f"Consensus: {level.upper()}")
            self.output.append("")

    def veto(self):
        votes = self._parse_votes()
        if not votes: return
        prolog_list = "[" + ",".join(map(str, votes)) + "]"
        res = self.engine.query(f"has_veto({prolog_list})")
        if res:
            self.output.append(f"Votes: {votes}")
            self.output.append("⛔ VETO DETECTED — at least one Strong No (0) present")
        else:
            self.output.append(f"Votes: {votes}")
            self.output.append("✓ No veto")
        self.output.append("")


# ═══════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ═══════════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quaternary Logic System — Prolog + PySide6")
        self.resize(1000, 750)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Initialize Prolog engine (show error if it fails)
        try:
            PrologEngine.get()
        except Exception as e:
            QMessageBox.critical(self, "Prolog Error",
                f"Failed to initialize Prolog engine:\n\n{e}\n\n"
                "Make sure SWI-Prolog is installed and quaternary.pl is in the same directory.")
            sys.exit(1)

        # Add all tabs
        self.tabs.addTab(PrologConsoleTab(), "🖥️ Console")
        self.tabs.addTab(DNATab(), "🧬 DNA")
        self.tabs.addTab(CalculatorTab(), "🔢 Calculator")
        self.tabs.addTab(TrafficTab(), "🚦 Traffic")
        self.tabs.addTab(ColorTab(), "🎨 Colors")
        self.tabs.addTab(QPSKTab(), "📡 QPSK")
        self.tabs.addTab(LockTab(), "🔐 Lock")
        self.tabs.addTab(FlashTab(), "💾 Flash")
        self.tabs.addTab(ElevatorTab(), "🛗 Elevator")
        self.tabs.addTab(VotingTab(), "🗳️ Voting")

        # Status bar
        self.statusBar().showMessage("Ready — Prolog engine loaded")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Dark theme
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()