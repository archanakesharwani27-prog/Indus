# scripts/installer.py
# INDUS One-Click Graphical Setup & Installer Wizard
import sys
import os
import shutil
import zipfile
import subprocess
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPixmap, QIcon
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QProgressBar, QCheckBox,
    QFileDialog, QMessageBox, QFrame, QStackedWidget
)

def _get_bundle_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BUNDLE_DIR = _get_bundle_dir()
DEFAULT_INSTALL_DIR = Path.home() / 'AppData' / 'Local' / 'Programs' / 'INDUS'


class InstallWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, target_dir: Path, api_key: str, create_desktop_shortcut: bool, create_start_shortcut: bool):
        super().__init__()
        self.target_dir = target_dir
        self.api_key = api_key.strip()
        self.create_desktop_shortcut = create_desktop_shortcut
        self.create_start_shortcut = create_start_shortcut

    def run(self):
        try:
            self.progress.emit(10, "Creating installation directory...")
            self.target_dir.mkdir(parents=True, exist_ok=True)

            # Copy files from bundle
            self.progress.emit(25, "Copying INDUS system binaries & assets...")
            
            # Find payload zip or dist folder
            zip_payload = BUNDLE_DIR / "Indus_FInal_25_08_26.zip"
            if zip_payload.exists():
                with zipfile.ZipFile(zip_payload, 'r') as zf:
                    zf.extractall(self.target_dir)
            else:
                # Copy from source
                for item in ["dist", "config", "memory", "actions", "core", "agent", "scripts", "face.png", "requirements.txt"]:
                    src = BUNDLE_DIR / item
                    dst = self.target_dir / item
                    if src.is_file():
                        shutil.copy2(src, dst)
                    elif src.is_dir():
                        if dst.exists():
                            shutil.rmtree(dst)
                        shutil.copytree(src, dst)

            self.progress.emit(60, "Configuring API keys and security vault...")
            cfg_dir = self.target_dir / "config"
            cfg_dir.mkdir(parents=True, exist_ok=True)
            api_file = cfg_dir / "api_keys.json"
            
            import json
            current_cfg = {}
            if api_file.exists():
                try:
                    current_cfg = json.loads(api_file.read_text(encoding="utf-8"))
                except Exception:
                    current_cfg = {}
            
            if self.api_key:
                current_cfg["gemini_api_key"] = self.api_key
            elif "gemini_api_key" not in current_cfg:
                current_cfg["gemini_api_key"] = ""
            
            api_file.write_text(json.dumps(current_cfg, indent=4), encoding="utf-8")

            # Determine executable path
            exe_target = self.target_dir / "dist" / "Indus_FInal_25_08_26.exe"
            if not exe_target.exists():
                exe_target = self.target_dir / "Indus_FInal_25_08_26.exe"

            # Create Shortcuts
            self.progress.emit(85, "Creating Windows shortcuts...")
            if self.create_desktop_shortcut:
                self._create_shortcut(
                    shortcut_path=Path.home() / "Desktop" / "INDUS AI.lnk",
                    target_exe=exe_target,
                    work_dir=self.target_dir
                )

            if self.create_start_shortcut:
                start_dir = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "INDUS"
                start_dir.mkdir(parents=True, exist_ok=True)
                self._create_shortcut(
                    shortcut_path=start_dir / "INDUS AI.lnk",
                    target_exe=exe_target,
                    work_dir=self.target_dir
                )

            self.progress.emit(100, "Installation complete!")
            self.finished.emit(True, str(exe_target))

        except Exception as e:
            self.finished.emit(False, str(e))

    def _create_shortcut(self, shortcut_path: Path, target_exe: Path, work_dir: Path):
        try:
            ps_script = f'''
             = New-Object -ComObject WScript.Shell
             = .CreateShortcut("{str(shortcut_path)}")
            .TargetPath = "{str(target_exe)}"
            .WorkingDirectory = "{str(work_dir)}"
            .Description = "INDUS Autonomous Desktop AI Assistant"
             = "{str(work_dir / 'face.png')}"
            if (Test-Path ) {{
                .IconLocation = 
            }}
            .Save()
            '''
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, timeout=10)
        except Exception as e:
            print(f"[Installer] Shortcut error: {e}")


class InstallerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("INDUS AI Assistant — Setup Wizard")
        self.setFixedSize(580, 480)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #030810;
                color: #4ADDE8;
            }
            QLabel {
                color: #4ADDE8;
                font-family: 'Segoe UI', Arial;
            }
            QLineEdit {
                background-color: #060F1C;
                color: #FFFFFF;
                border: 1px solid #0F2A4A;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #00FFFF;
            }
            QPushButton {
                background-color: #00FFFF;
                color: #000000;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #00D5D5;
            }
            QPushButton:pressed {
                background-color: #009999;
            }
            QPushButton#secondary {
                background-color: #060F1C;
                color: #4ADDE8;
                border: 1px solid #0F2A4A;
            }
            QPushButton#secondary:hover {
                background-color: #0A1B30;
                border: 1px solid #00FFFF;
            }
            QCheckBox {
                color: #4ADDE8;
                font-size: 13px;
                spacing: 8px;
            }
            QProgressBar {
                background-color: #060F1C;
                border: 1px solid #0F2A4A;
                border-radius: 6px;
                text-align: center;
                color: #FFFFFF;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #00FFFF;
                border-radius: 5px;
            }
        """)

        self.installed_exe = ""
        self._init_ui()

    def _init_ui(self):
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Page 1: Welcome & Settings
        self.page1 = QWidget()
        l1 = QVBoxLayout(self.page1)
        l1.setContentsMargins(35, 30, 35, 30)
        l1.setSpacing(15)

        # Header
        title = QLabel("INDUS AI Assistant")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #00FFFF;")
        subtitle = QLabel("Autonomous Military-Grade Desktop AI • Setup Wizard")
        subtitle.setStyleSheet("font-size: 13px; color: #8AACC8;")
        l1.addWidget(title)
        l1.addWidget(subtitle)
        l1.addSpacing(10)

        # Install Directory
        l1.addWidget(QLabel("Installation Directory:"))
        dir_layout = QHBoxLayout()
        self.txt_dir = QLineEdit(str(DEFAULT_INSTALL_DIR))
        btn_browse = QPushButton("Browse...")
        btn_browse.setObjectName("secondary")
        btn_browse.setFixedWidth(90)
        btn_browse.clicked.connect(self._browse_dir)
        dir_layout.addWidget(self.txt_dir)
        dir_layout.addWidget(btn_browse)
        l1.addLayout(dir_layout)

        # API Key
        l1.addWidget(QLabel("Gemini API Key (Optional — can be set later):"))
        self.txt_key = QLineEdit()
        self.txt_key.setPlaceholderText("Paste your Gemini API key (AIzaSy...)")
        l1.addWidget(self.txt_key)

        # Shortcuts Checkboxes
        self.chk_desktop = QCheckBox("Create Desktop Shortcut")
        self.chk_desktop.setChecked(True)
        self.chk_start = QCheckBox("Create Start Menu Shortcut")
        self.chk_start.setChecked(True)
        l1.addWidget(self.chk_desktop)
        l1.addWidget(self.chk_start)

        l1.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("secondary")
        btn_cancel.clicked.connect(self.close)
        btn_install = QPushButton("Install INDUS Now")
        btn_install.clicked.connect(self._start_install)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_install)
        l1.addLayout(btn_layout)

        self.stack.addWidget(self.page1)

        # Page 2: Progress
        self.page2 = QWidget()
        l2 = QVBoxLayout(self.page2)
        l2.setContentsMargins(35, 40, 35, 40)
        l2.setSpacing(20)

        p_title = QLabel("Installing INDUS...")
        p_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #00FFFF;")
        self.lbl_status = QLabel("Extracting components...")
        self.lbl_status.setStyleSheet("font-size: 13px; color: #8AACC8;")
        self.pbar = QProgressBar()
        self.pbar.setValue(0)
        self.pbar.setFixedHeight(26)

        l2.addWidget(p_title)
        l2.addWidget(self.lbl_status)
        l2.addWidget(self.pbar)
        l2.addStretch()
        self.stack.addWidget(self.page2)

        # Page 3: Success Finish
        self.page3 = QWidget()
        l3 = QVBoxLayout(self.page3)
        l3.setContentsMargins(35, 40, 35, 40)
        l3.setSpacing(20)

        s_title = QLabel("🎉 Installation Complete!")
        s_title.setStyleSheet("font-size: 22px; font-weight: bold; color: #00FFFF;")
        s_desc = QLabel("INDUS has been successfully installed on your computer.\nYou can launch it anytime from your Desktop shortcut or Start Menu.")
        s_desc.setStyleSheet("font-size: 13px; color: #8AACC8; line-height: 1.4;")
        
        self.chk_launch = QCheckBox("Launch INDUS AI Assistant immediately")
        self.chk_launch.setChecked(True)

        l3.addWidget(s_title)
        l3.addWidget(s_desc)
        l3.addWidget(self.chk_launch)
        l3.addStretch()

        btn_finish = QPushButton("Finish")
        btn_finish.clicked.connect(self._finish)
        l3.addWidget(btn_finish)
        self.stack.addWidget(self.page3)

    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select Installation Folder", str(DEFAULT_INSTALL_DIR))
        if d:
            self.txt_dir.setText(d)

    def _start_install(self):
        target = Path(self.txt_dir.text().strip())
        if not target:
            QMessageBox.warning(self, "Invalid Path", "Please select a valid installation folder.")
            return

        self.stack.setCurrentIndex(1)
        self.worker = InstallWorker(
            target_dir=target,
            api_key=self.txt_key.text().strip(),
            create_desktop_shortcut=self.chk_desktop.isChecked(),
            create_start_shortcut=self.chk_start.isChecked()
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, val: int, msg: str):
        self.pbar.setValue(val)
        self.lbl_status.setText(msg)

    def _on_finished(self, success: bool, result_or_err: str):
        if success:
            self.installed_exe = result_or_err
            self.stack.setCurrentIndex(2)
        else:
            QMessageBox.critical(self, "Installation Failed", f"An error occurred during installation:\n{result_or_err}")
            self.stack.setCurrentIndex(0)

    def _finish(self):
        if self.chk_launch.isChecked() and self.installed_exe and Path(self.installed_exe).exists():
            subprocess.Popen([self.installed_exe], cwd=str(Path(self.installed_exe).parent))
        self.close()


def main():
    app = QApplication(sys.argv)
    win = InstallerWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
