"""Widget helpers for editing the liftout options associated with a lamella."""

from __future__ import annotations

from typing import Optional

from PyQt5 import QtCore, QtWidgets

from fibsem.ui import stylesheets


class AutoLamellaLiftoutOptionsWidget(QtWidgets.QGroupBox):
    """Provide simple controls to edit a lamella's liftout options."""

    liftout_options_changed = QtCore.pyqtSignal(bool)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self._for_liftout: bool = False
        self._updating: bool = False

        self.setTitle("Liftout Options")
        self._setup_ui()
        self._connect_signals()
        self._update_inputs()
        self.setEnabled(True)

    # --------------------------------------------------------------------- #
    # UI helpers
    def _setup_ui(self) -> None:
        layout = QtWidgets.QGridLayout(self)

        self.checkbox_for_liftout = QtWidgets.QCheckBox("Lamella is used as liftout block")
        self.checkbox_for_liftout.setStyleSheet(stylesheets.CHECKBOX_STYLE)

        layout.addWidget(self.checkbox_for_liftout, 0, 0)
        layout.setColumnStretch(1, 1)

    def _connect_signals(self) -> None:
        self.checkbox_for_liftout.toggled.connect(self._handle_input_changed)

    # --------------------------------------------------------------------- #
    # Public API
    def set_for_liftout(self, enabled: Optional[bool]) -> None:
        """Update the widget to reflect a new liftout enabled state."""
        self._for_liftout = enabled if enabled is not None else False
        self._update_inputs()

    def get_for_liftout(self) -> bool:
        """Return the currently bound liftout enabled state."""
        return self._for_liftout

    # --------------------------------------------------------------------- #
    # Internal helpers
    def _handle_input_changed(self) -> None:
        if self._updating:
            return

        self._for_liftout = self.checkbox_for_liftout.isChecked()

        self._update_inputs()
        self.liftout_options_changed.emit(self._for_liftout)

    def _update_inputs(self) -> None:
        self._updating = True
        self.checkbox_for_liftout.setChecked(self._for_liftout)
        self._updating = False


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    widget = AutoLamellaLiftoutOptionsWidget()
    widget.set_liftout_enabled(False)

    def _on_liftout_options_changed(enabled: bool) -> None:
        print("Liftout options changed:", enabled)

    widget.liftout_options_changed.connect(_on_liftout_options_changed)

    widget.show()
    sys.exit(app.exec_())