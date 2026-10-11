import sys, os, json
from typing_studio_lib import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QGroupBox, QLabel, QPushButton, QCheckBox, QComboBox, QSpinBox, QDoubleSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox, QProgressBar,
    Qt, QColor, THEMES, EXT_TO_LANGUAGE, SUPPORTED_EXTENSIONS, SKIP_DIRS,
    EXPORT_FORMATS, INPUT_DIR, OUTPUT_DIR, SETTINGS_FILE,
    CodeRenderer, TypingAnimator, TypingProfile, MultiPaneRenderer, KeyboardOverlay,
    SimpleSoundGen, VideoExporter, ExportConfigBuilder
)
from dataclasses import dataclass

@dataclass
class FileItem:
    path: str
    checked: bool = False
    status: str = "Pending"
    output_path: str = None

class MultiWindowStudio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MultiWindow Code Typing Studio")
        self.resize(1000, 800)
        self._items = []
        self._exporter = None
        self._build_ui()
        self._scan_input_dir()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        
        left = QVBoxLayout()
        grp_files = QGroupBox("Programs")
        fl = QVBoxLayout(grp_files)
        
        btn_row = QHBoxLayout()
        self.scan_btn = QPushButton("Scan input/")
        self.add_btn = QPushButton("Add files...")
        for b in [self.scan_btn, self.add_btn]: btn_row.addWidget(b)
        btn_row.addStretch()
        fl.addLayout(btn_row)
        
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Export", "Path", "Language", "Status"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Fixed); hdr.resizeSection(0, 60)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.Fixed); hdr.resizeSection(2, 90)
        hdr.setSectionResizeMode(3, QHeaderView.Stretch)
        fl.addWidget(self.table)
        left.addWidget(grp_files)
        
        self.progress_bar = QProgressBar(); left.addWidget(self.progress_bar)
        
        self.export_btn = QPushButton("Export Checked")
        self.export_btn.setStyleSheet("background: #89b4fa; color: black; font-weight: bold; padding: 10px;")
        left.addWidget(self.export_btn)
        
        right = QVBoxLayout()
        grp_settings = QGroupBox("Visual & Layout")
        form = QFormLayout(grp_settings)
        
        self.theme_cb = QComboBox(); self.theme_cb.addItems(list(THEMES.keys()))
        self.export_format_cb = QComboBox(); self.export_format_cb.addItems(list(EXPORT_FORMATS.keys()))
        self.layout_cb = QComboBox(); self.layout_cb.addItems(["1 Window (Single)", "2 Windows (Split)", "4 Windows (Grid)"])
        self.font_family_cb = QComboBox(); self.font_family_cb.addItems(["Consolas", "JetBrains Mono", "DejaVu Sans Mono", "monospace"])
        self.font_size_sp = QSpinBox(); self.font_size_sp.setRange(8, 72); self.font_size_sp.setValue(22)
        
        form.addRow("Theme:", self.theme_cb)
        form.addRow("Format:", self.export_format_cb)
        form.addRow("Layout:", self.layout_cb)
        form.addRow("Font:", self.font_family_cb)
        form.addRow("Font Size:", self.font_size_sp)
        
        self.kb_chk = QCheckBox("Show Keyboard Overlay")
        form.addRow(self.kb_chk)
        self.kb_layout_cb = QComboBox(); self.kb_layout_cb.addItems(["QWERTY", "Dvorak", "Colemak"])
        form.addRow("KB Layout:", self.kb_layout_cb)
        
        self.wpm_sp = QSpinBox(); self.wpm_sp.setRange(30, 300); self.wpm_sp.setValue(100)
        self.fps_sp = QSpinBox(); self.fps_sp.setRange(10, 60); self.fps_sp.setValue(30)
        form.addRow("WPM:", self.wpm_sp)
        form.addRow("FPS:", self.fps_sp)
        
        right.addWidget(grp_settings)
        right.addStretch()
        
        root.addLayout(left, 1)
        root.addLayout(right, 2)
        
        self.scan_btn.clicked.connect(self._scan_input_dir)
        self.add_btn.clicked.connect(self._add_files)
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

    def _refresh_table(self):
        self.table.setRowCount(len(self._items))
        for i, item in enumerate(self._items):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Checked if item.checked else Qt.CheckState.Unchecked)
            self.table.setItem(i, 0, chk)
            self.table.setItem(i, 1, QTableWidgetItem(os.path.basename(item.path)))
            self.table.setItem(i, 2, QTableWidgetItem(EXT_TO_LANGUAGE.get(os.path.splitext(item.path)[1].lower(), "Python")))
            self.table.setItem(i, 3, QTableWidgetItem(item.status))

    def _start_export(self):
        checked = [it for it in self._items if it.checked]
        if not checked:
            QMessageBox.information(self, "Nothing Selected", "Check files to export.")
            return
            
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(checked))
        self.progress_bar.setValue(0)
        self._export_queue = checked
        self._export_next()

    def _export_next(self):
        if not self._export_queue:
            self.progress_bar.setVisible(False)
            return
            
        item = self._export_queue.pop(0)
        item.status = "Rendering"
        self._refresh_table()
        
        with open(item.path, "r", encoding="utf-8") as f:
            code = f.read()
            
        lang = EXT_TO_LANGUAGE.get(os.path.splitext(item.path)[1].lower(), "Python")
        fmt = self.export_format_cb.currentText()
        res = "1920x1080" if "16:9" in fmt else "1080x1920"
        w, h = EXPORT_FORMATS[fmt]["resolutions"][res]
        
        layout_name = self.layout_cb.currentText()
        num_panes = 1 if "1 Window" in layout_name else 2 if "2 Windows" in layout_name else 4
        code_files = [(code, os.path.basename(item.path)) for _ in range(num_panes)]
        
        cfg = (ExportConfigBuilder()
               .junior_code(code).senior_code(code)
               .name(os.path.basename(item.path)).fmt(fmt).res(res)
               .theme(self.theme_cb.currentText())
               .j_font(self.font_family_cb.currentText()).s_font(self.font_family_cb.currentText())
               .font_size_auto(False).font_size(self.font_size_sp.value())
               .chrome(True).ln(True).cursor_glow(True).watermark(False).bg_image_path("")
               .show_kb(self.kb_chk.isChecked()).kb_layout(self.kb_layout_cb.currentText())
               .kb_pos("bottom_center").kb_op(0.82)
               .j_wpm(self.wpm_sp.value()).j_pause(0.1)
               .s_wpm(self.wpm_sp.value()).s_pause(0.1)
               .start_pause(0.5).end_pause(1.5).lang(lang)
               .pane_layout("Side by Side (50/50)" if num_panes == 2 else "Stacked (50/50)")
               .pad(24).gap(20).build())
        
        output = os.path.join(OUTPUT_DIR, f"{os.path.splitext(os.path.basename(item.path))[0]}_multi.mp4")
        
        self._exporter = VideoExporter(cfg, output, self.fps_sp.value(), None, 0.5, "YouTube Pro (H.264/AAC)")
        self._exporter.progress.connect(lambda p: self.progress_bar.setValue(self.progress_bar.value() + 1))
        self._exporter.finished_ok.connect(lambda p: self._on_item_done(item, p))
        self._exporter.error.connect(lambda e: self._on_item_failed(item, e))
        self._exporter.start()

    def _on_item_done(self, item, path):
        item.status = "Done"; item.output_path = path
        self._refresh_table(); self._export_next()

    def _on_item_failed(self, item, err):
        item.status = "Failed"
        self._refresh_table(); self._export_next()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MultiWindowStudio()
    win.show()
    sys.exit(app.exec())
