# actions/autonomous_watcher.py
# INDUS JARVIS AUTONOMOUS WATCHER & PC CONTROLLER

import os
import sys
import time
import threading
from datetime import datetime
from pathlib import Path

from memory.db_engine import (
    db_get_fact, db_set_fact, db_get_frequent_apps,
    db_log_autonomous_action, db_get_active_rules,
    db_set_rule, db_record_app_launch
)
from actions.computer_settings import get_theme_mode, set_theme_mode
from actions.open_app import open_app


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


class AutonomousWatcher:
    def __init__(self, player_ui=None):
        self.ui = player_ui
        self._running = False
        self._thread = None
        self._last_theme_enforced = None
        self._startup_executed = False

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        print("[AutonomousWatcher] Jarvis Autonomous Watcher daemon started.")

    def stop(self):
        self._running = False

    def _log(self, text: str):
        print(f"[JarvisAutonomous] {text}")
        if self.ui:
            try:
                self.ui.write_log(f"[AUTO] {text}")
            except Exception:
                pass

    def check_and_enforce_theme(self):
        pref = db_get_fact("theme") or db_get_fact("theme_preference")
        if not pref:
            return

        pref_clean = pref.strip().lower()
        target_theme = None
        if "dark" in pref_clean:
            target_theme = "dark"
        elif "light" in pref_clean:
            target_theme = "light"

        if not target_theme:
            return

        try:
            current_theme = get_theme_mode()
            if current_theme != target_theme:
                res = set_theme_mode(target_theme)
                msg = f"Detected {current_theme.upper()} mode on Windows. Autonomously switched to {target_theme.upper()} mode as preferred by user."
                self._log(msg)
                db_log_autonomous_action("theme_auto_switch", f"{current_theme} -> {target_theme}", "success")
                self._last_theme_enforced = target_theme
        except Exception as e:
            print(f"[AutonomousWatcher] Theme check error: {e}")

    def execute_startup_routine(self) -> list:
        pref_apps = db_get_fact("startup_apps")
        apps_to_launch = []

        if pref_apps:
            apps_to_launch = [a.strip() for a in pref_apps.replace(";", ",").split(",") if a.strip()]
        else:
            frequent = db_get_frequent_apps(min_count=3)
            if frequent:
                apps_to_launch = frequent[:4]

        launched = []
        for app in apps_to_launch:
            self._log(f"Proactively opening workspace app: {app}")
            try:
                res = open_app(parameters={"app_name": app}, player=self.ui)
                launched.append(app)
                db_log_autonomous_action("auto_launch_app", f"App: {app}", "success")
                time.sleep(1.2)
            except Exception as e:
                print(f"[AutonomousWatcher] Failed to launch {app}: {e}")

        return launched

    def _watch_loop(self):
        time.sleep(4)
        self.check_and_enforce_theme()
        check_interval = 15
        while self._running:
            try:
                self.check_and_enforce_theme()
            except Exception as e:
                print(f"[AutonomousWatcher] Error in watch loop: {e}")
            time.sleep(check_interval)


_watcher_instance = None

def get_autonomous_watcher(player_ui=None) -> AutonomousWatcher:
    global _watcher_instance
    if _watcher_instance is None:
        _watcher_instance = AutonomousWatcher(player_ui=player_ui)
    elif player_ui and not _watcher_instance.ui:
        _watcher_instance.ui = player_ui
    return _watcher_instance

def start_autonomous_watcher(player_ui=None) -> AutonomousWatcher:
    watcher = get_autonomous_watcher(player_ui=player_ui)
    watcher.start()
    return watcher
