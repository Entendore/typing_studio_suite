import sys, os

# Get the script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))
# Get the PARENT directory (where typing_studio_lib actually lives!)
parent_dir = os.path.dirname(script_dir)

# Force Python to look in the parent directory
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Now we can import safely
import shutil, json
from typing_studio_lib import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QGroupBox, QLabel, QPushButton, QCheckBox, QComboBox, QSpinBox, 
    QDoubleSpinBox, QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, 
    QMessageBox, QProgressBar, Qt, QColor, QLineEdit,
    ExportConfigBuilder, VideoExporter, THEMES, EXT_TO_LANGUAGE, SUPPORTED_EXTENSIONS, 
    SKIP_DIRS, INPUT_DIR, OUTPUT_DIR, SETTINGS_FILE
)
from dataclasses import dataclass

@dataclass
class FileItem:
    path: str
    checked: bool = False
    status: str = "Pending"
    output_path: str = None
    error: str = None

class JrVsSrStudio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Junior vs Senior Dev — Code Typing Studio (Batch Edition)")
        self.resize(1200, 800)
        self._items = []
        self._exporter = None
        self._build_ui()
        self._scan_input_dir()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        
        left_panel = QVBoxLayout()
        grp_files = QGroupBox("📂 File Batch")
        grp_files_layout = QVBoxLayout(grp_files)
        
        btn_row = QHBoxLayout()
        self.scan_btn = QPushButton("🔄 Scan")
        self.add_btn = QPushButton("➕ Add")
        self.clear_btn = QPushButton("✖ Clear")
        self.select_all_btn = QPushButton("☑ All")
        for btn in [self.scan_btn, self.add_btn, self.clear_btn, self.select_all_btn]:
            btn_row.addWidget(btn)
        btn_row.addStretch()
        grp_files_layout.addLayout(btn_row)
        
        self.file_table = QTableWidget(0, 4)
        self.file_table.setHorizontalHeaderLabels(["", "File", "Lang", "Status"])
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.setEditTriggers(QTableWidget.NoEditTriggers)
        hdr = self.file_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Fixed); hdr.resizeSection(0, 36)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.Fixed); hdr.resizeSection(2, 70)
        hdr.setSectionResizeMode(3, QHeaderView.Fixed); hdr.resizeSection(3, 100)
        grp_files_layout.addWidget(self.file_table)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        grp_files_layout.addWidget(self.progress_bar)
        
        self.export_btn = QPushButton("🎬 Export Checked")
        self.export_btn.setStyleSheet("background: #a6e3a1; color: black; font-weight: bold; padding: 10px;")
        grp_files_layout.addWidget(self.export_btn)
        left_panel.addWidget(grp_files)
        
        right_panel = QVBoxLayout()
        grp_settings = QGroupBox("⚙ Settings")
        form = QFormLayout(grp_settings)
        
        self.theme_cb = QComboBox(); self.theme_cb.addItems(list(THEMES.keys()))
        self.export_format_cb = QComboBox(); self.export_format_cb.addItems(["YouTube (16:9)", "YouTube Shorts (9:16)"])
        self.pane_layout_cb = QComboBox(); self.pane_layout_cb.addItems(["Side by Side (50/50)", "Stacked (50/50)", "Junior Big (70/30)", "Senior Big (70/30)"])
        self.lang_cb = QComboBox(); self.lang_cb.addItems(["Auto", "Python", "JavaScript", "CFamily", "Java", "Go", "Rust", "Ruby", "PHP", "HTML", "CSS", "SQL", "Bash", "JSON", "YAML", "Markdown"])
        
        form.addRow("Theme:", self.theme_cb)
        form.addRow("Format:", self.export_format_cb)
        form.addRow("Pane Layout:", self.pane_layout_cb)
        form.addRow("Language:", self.lang_cb)
        
        j_box = QGroupBox("Junior Dev")
        j_form = QFormLayout(j_box)
        self.j_wpm = QSpinBox(); self.j_wpm.setRange(30, 300); self.j_wpm.setValue(90)
        self.j_pause = QDoubleSpinBox(); self.j_pause.setRange(0, 1); self.j_pause.setValue(0.15)
        j_form.addRow("WPM:", self.j_wpm); j_form.addRow("Pause Freq:", self.j_pause)
        form.addRow(j_box)
        
        s_box = QGroupBox("Senior Dev")
        s_form = QFormLayout(s_box)
        self.s_wpm = QSpinBox(); self.s_wpm.setRange(30, 300); self.s_wpm.setValue(130)
        self.s_pause = QDoubleSpinBox(); self.s_pause.setRange(0, 1); self.s_pause.setValue(0.05)
        s_form.addRow("WPM:", self.s_wpm); s_form.addRow("Pause Freq:", self.s_pause)
        form.addRow(s_box)
        
        self.fps_sp = QSpinBox(); self.fps_sp.setRange(10, 60); self.fps_sp.setValue(30)
        self.encoder_cb = QComboBox(); self.encoder_cb.addItems(["YouTube Pro (H.264/AAC)", "x264 (CPU, Fast)", "NVENC (NVIDIA)", "QSV (Intel)", "AMF (AMD)"])
        self.naming_edit = QLineEdit(); self.naming_edit.setText("{name}_jr_vs_sr")
        
        form.addRow("FPS:", self.fps_sp)
        form.addRow("Encoder:", self.encoder_cb)
        form.addRow("Output Name:", self.naming_edit)
        
        right_panel.addWidget(grp_settings)
        right_panel.addStretch()
        
        root.addLayout(left_panel, 1)
        root.addLayout(right_panel, 2)
        
        self.scan_btn.clicked.connect(self._scan_input_dir)
        self.add_btn.clicked.connect(self._add_files)
        self.clear_btn.clicked.connect(self._clear_list)
        self.select_all_btn.clicked.connect(self._select_all)
        self.export_btn.clicked.connect(self._start_export)

    def _scan_input_dir(self):
        self._items.clear()
        if not os.path.exists(INPUT_DIR): return
        for dirpath, dirnames, filenames in os.walk(INPUT_DIR):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fname in sorted(filenames):
                ext = os.path.splitext(fname)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    self._items.append(FileItem(path=os.path.join(dirpath, fname), checked=True))
        self._refresh_table()

    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", "Code Files (*.py *.js *.cpp *.cs *.go *.rs *.java)")
        for p in paths:
            self._items.append(FileItem(path=p, checked=True))
        self._refresh_table()

    def _clear_list(self):
        self._items.clear()
        self._refresh_table()

    def _select_all(self):
        for it in self._items: it.checked = True
        self._refresh_table()

    def _refresh_table(self):
        self.file_table.setRowCount(len(self._items))
        for i, item in enumerate(self._items):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Checked if item.checked else Qt.CheckState.Unchecked)
            self.file_table.setItem(i, 0, chk)
            self.file_table.setItem(i, 1, QTableWidgetItem(os.path.basename(item.path)))
            self.file_table.setItem(i, 2, QTableWidgetItem(EXT_TO_LANGUAGE.get(os.path.splitext(item.path)[1].lower(), "Text")))
            status_item = QTableWidgetItem(item.status)
            if "Done" in item.status: status_item.setForeground(QColor("#a6e3a1"))
            elif item.status == "Failed": status_item.setForeground(QColor("#ff5555"))
            self.file_table.setItem(i, 3, status_item)

    def _start_export(self):
        checked = [it for it in self._items if it.checked]
        if not checked:
            QMessageBox.information(self, "Nothing Selected", "Check files to export.")
            return
            
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(checked))
        self.progress_bar.setValue(0)
        self.export_btn.setEnabled(False)
        self._export_queue = checked
        self._export_next()

    def _export_next(self):
        if not self._export_queue:
            self.export_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            return
            
        item = self._export_queue.pop(0)
        item.status = "Rendering"
        self._refresh_table()
        
        with open(item.path, "r", encoding="utf-8") as f:
            code = f.read()
            
        lang_text = self.lang_cb.currentText()
        language = lang_text if lang_text != "Auto" else EXT_TO_LANGUAGE.get(os.path.splitext(item.path)[1].lower(), "Text")
        
        cfg = (ExportConfigBuilder()
               .junior_code(code)
               .senior_code(code) # Typically same code for Jr vs Sr
               .name(os.path.basename(item.path))
               .fmt(self.export_format_cb.currentText())
               .res("1920x1080")
               .theme(self.theme_cb.currentText())
               .j_font("Consolas")
               .s_font("Consolas")
               .font_size_auto(True)
               .font_size(18)
               .chrome(True)
               .ln(True)
               .cursor_glow(True)
               .watermark(False)
               .bg_image_path("")
               .show_kb(False)
               .kb_layout("QWERTY")
               .kb_pos("bottom_center")
               .kb_op(0.82)
               .j_wpm(self.j_wpm.value())
               .j_pause(self.j_pause.value())
               .s_wpm(self.s_wpm.value())
               .s_pause(self.s_pause.value())
               .start_pause(0.5)
               .end_pause(1.5)
               .lang(language)
               .pane_layout(self.pane_layout_cb.currentText())
               .pad(24)
               .gap(20)
               .build())
               
        base = os.path.splitext(os.path.basename(item.path))[0]
        out_name = self.naming_edit.text().format(name=base, lang=language)
        out_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in out_name)
        output_path = os.path.join(OUTPUT_DIR, f"{out_name}.mp4")
        
        self._exporter = VideoExporter(cfg, output_path, self.fps_sp.value(), None, 0.5, self.encoder_cb.currentText())
        self._exporter.progress.connect(lambda p: self.progress_bar.setValue(self.progress_bar.value() + 1))
        self._exporter.status.connect(lambda s: self.statusBar().showMessage(s))
        self._exporter.finished_ok.connect(lambda p: self._on_item_done(item, p))
        self._exporter.error.connect(lambda e: self._on_item_failed(item, e))
        self._exporter.start()

    def _on_item_done(self, item, path):
        item.status = "Done"; item.output_path = path
        self._refresh_table(); self._export_next()

    def _on_item_failed(self, item, err):
        item.status = "Failed"; item.error = err
        self._refresh_table(); self._export_next()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = JrVsSrStudio()
    win.show()
    sys.exit(app.exec())
