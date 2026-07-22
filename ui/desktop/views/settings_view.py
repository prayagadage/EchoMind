"""Settings View providing configuration options for Audio, AI, Search, and Privacy."""

from core.settings_service import EchoMindUserSettings
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from ui.desktop.viewmodels.settings_viewmodel import SettingsViewModel


class SettingsView(QWidget):
    """View rendering tabbed settings preferences."""

    def __init__(self, viewModel: SettingsViewModel) -> None:
        """Initialize SettingsView.

        Args:
            viewModel: SettingsViewModel instance.
        """
        super().__init__()
        self._vm = viewModel
        self._init_ui()
        self._load_from_settings(self._vm.settings)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Settings & Preferences")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 12px;")
        layout.addWidget(title)

        tabs = QTabWidget()

        # 1. Audio Tab
        audio_tab = QWidget()
        a_form = QFormLayout(audio_tab)
        self._audio_device = QComboBox()
        self._audio_device.addItems(
            ["default", "MacBook Air Microphone", "External Mic"]
        )
        self._vad_threshold = QLineEdit("0.002")
        a_form.addRow("Input Device:", self._audio_device)
        a_form.addRow("VAD Energy Threshold:", self._vad_threshold)
        tabs.addTab(audio_tab, "Audio")

        # 2. AI Model Tab
        ai_tab = QWidget()
        ai_form = QFormLayout(ai_tab)
        self._whisper_model = QLineEdit("mlx-community/whisper-small-mlx")
        self._llm_model = QLineEdit("mlx-community/Qwen3-4B-4bit")
        ai_form.addRow("Whisper STT Model:", self._whisper_model)
        ai_form.addRow("LLM Provider Model:", self._llm_model)
        tabs.addTab(ai_tab, "AI Models")

        # 3. Search Tab
        search_tab = QWidget()
        s_form = QFormLayout(search_tab)
        self._top_k = QSpinBox()
        self._top_k.setRange(1, 20)
        self._top_k.setValue(5)
        s_form.addRow("Vector Search Top-K Hits:", self._top_k)
        tabs.addTab(search_tab, "Search")

        # 4. Appearance Tab
        app_tab = QWidget()
        app_form = QFormLayout(app_tab)
        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["dark", "light", "system"])
        app_form.addRow("UI Theme Mode:", self._theme_combo)
        tabs.addTab(app_tab, "Appearance")

        # 5. Privacy Tab
        priv_tab = QWidget()
        p_form = QFormLayout(priv_tab)
        self._auto_delete_audio = QCheckBox(
            "Auto-purge raw PCM audio after transcription"
        )
        self._auto_delete_audio.setChecked(True)
        p_form.addRow("Audio Storage:", self._auto_delete_audio)
        tabs.addTab(priv_tab, "Privacy")

        layout.addWidget(tabs)

        # Save Button
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self._on_save_clicked)
        layout.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _load_from_settings(self, s: EchoMindUserSettings) -> None:
        self._audio_device.setCurrentText(s.audio.input_device)
        self._vad_threshold.setText(str(s.audio.vad_energy_threshold))
        self._whisper_model.setText(s.ai_model.whisper_model)
        self._llm_model.setText(s.ai_model.llm_model)
        self._top_k.setValue(s.search.top_k)
        self._theme_combo.setCurrentText(s.appearance.theme)
        self._auto_delete_audio.setChecked(s.privacy.auto_delete_audio)

    def _on_save_clicked(self) -> None:
        current = self._vm.settings
        current.audio.input_device = self._audio_device.currentText()
        current.ai_model.whisper_model = self._whisper_model.text()
        current.ai_model.llm_model = self._llm_model.text()
        current.search.top_k = self._top_k.value()
        current.appearance.theme = self._theme_combo.currentText()
        current.privacy.auto_delete_audio = self._auto_delete_audio.isChecked()

        self._vm.save_settings(current)
