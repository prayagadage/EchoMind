"""AI Chat Panel View displaying natural language conversation and citations."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from ui.desktop.viewmodels.chat_viewmodel import ChatViewModel


class ChatView(QWidget):
    """View rendering AI Chat Panel RAG interface."""

    def __init__(self, viewModel: ChatViewModel) -> None:
        """Initialize ChatView.

        Args:
            viewModel: ChatViewModel instance.
        """
        super().__init__()
        self._vm = viewModel
        self._init_ui()
        self._vm.message_added.connect(self._on_message_added)
        self._vm.session_cleared.connect(self._on_session_cleared)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Header Row
        header_layout = QHBoxLayout()
        title = QLabel("AI Meeting Assistant")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        header_layout.addWidget(title)

        clear_btn = QPushButton("Clear Chat")
        clear_btn.setObjectName("secondary")
        clear_btn.clicked.connect(self._vm.clear_chat)
        header_layout.addWidget(clear_btn, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addLayout(header_layout)

        # Message List Widget
        self._chat_list = QListWidget()
        layout.addWidget(self._chat_list)

        # Input Row
        input_layout = QHBoxLayout()
        self._input_field = QLineEdit()
        self._input_field.setPlaceholderText("Ask a question about your meetings...")
        self._input_field.returnPressed.connect(self._on_send_clicked)
        input_layout.addWidget(self._input_field)

        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self._on_send_clicked)
        input_layout.addWidget(send_btn)
        layout.addLayout(input_layout)

    def _on_send_clicked(self) -> None:
        text = self._input_field.text()
        if text.strip():
            self._input_field.clear()
            self._vm.send_question(text)

    def _on_message_added(self, msg: dict) -> None:
        sender = msg.get("sender", "user").capitalize()
        text = msg.get("text", "")
        citations = msg.get("citations", [])

        display_text = f"<b>{sender}:</b> {text}"
        if citations:
            c_lines = ["<br><i>Citations:</i>"]
            for c in citations:
                c_lines.append(
                    f" • [{c['ref_id']}] {c['meeting_title']} ({c['entity_type']})"
                )
            display_text += "<br>".join(c_lines)

        lbl = QLabel(display_text)
        lbl.setWordWrap(True)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        if sender.lower() == "user":
            lbl.setStyleSheet(
                "background-color: #334155; color: white; "
                "padding: 10px; border-radius: 8px;"
            )
        else:
            lbl.setStyleSheet(
                "background-color: #1E293B; color: #F8FAFC; "
                "padding: 10px; border-radius: 8px; border: 1px solid #4F46E5;"
            )

        item = QListWidgetItem(self._chat_list)
        item.setSizeHint(lbl.sizeHint())
        self._chat_list.addItem(item)
        self._chat_list.setItemWidget(item, lbl)
        self._chat_list.scrollToBottom()

    def _on_session_cleared(self) -> None:
        self._chat_list.clear()
