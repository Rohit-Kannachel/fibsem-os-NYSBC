import logging
from typing import Optional

from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal
import napari

from fibsem.microscope import FibsemMicroscope
from fibsem.applications.volume_em.structures import VolumeEMConfig
from fibsem.applications.volume_em.workflow_update_schema import (
    VolumeEMWorkflowUpdate,
    format_workflow_update,
)
from fibsem.structures import FibsemImage
from fibsem.ui import stylesheets
import threading
from fibsem.applications.volume_em.tasks import run_volume_em_task
from pprint import pprint

from superqt import ensure_main_thread

from fibsem.utils import format_duration

class VolumeEMWidget(QtWidgets.QWidget):
    """
    Volume EM Workflow Control Widget.

    Main widget for controlling Volume EM acquisition and milling workflows.
    """

    # Signals
    workflow_started_signal = pyqtSignal()
    workflow_finished_signal = pyqtSignal()
    workflow_update_signal = pyqtSignal(object)  # VolumeEMWorkflowUpdate (use object for PyQt compatibility)

    def __init__(self,
                 microscope: FibsemMicroscope,
                 parent=None):
        super().__init__(parent=parent)

        self.microscope = microscope
        self.config: Optional[VolumeEMConfig] = None

        self._workflow_thread: Optional[threading.Thread] = None
        self._workflow_stop_event = threading.Event()

        # Store persistent workflow state
        self._workflow_state: Optional[VolumeEMWorkflowUpdate] = None

        self._setup_ui()
        self._setup_connections()

        logging.info("VolumeEMWidget initialized")

    def _setup_ui(self):
        """Setup the user interface."""
        # Main layout
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # Title
        title_label = QtWidgets.QLabel("Volume EM Workflow")
        title_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        layout.addWidget(title_label)

        # Experiment info group
        exp_info_group = QtWidgets.QGroupBox("Experiment Information")
        exp_info_layout = QtWidgets.QVBoxLayout()
        exp_info_group.setLayout(exp_info_layout)

        # Experiment name
        name_layout = QtWidgets.QHBoxLayout()
        name_label = QtWidgets.QLabel("Name:")
        name_label.setFixedWidth(100)
        self.experiment_name_label = QtWidgets.QLabel("-")
        self.experiment_name_label.setStyleSheet("font-weight: bold;")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.experiment_name_label)
        name_layout.addStretch()
        exp_info_layout.addLayout(name_layout)

        # Experiment description
        desc_layout = QtWidgets.QVBoxLayout()
        desc_label = QtWidgets.QLabel("Description:")
        self.experiment_description_label = QtWidgets.QLabel("-")
        self.experiment_description_label.setWordWrap(True)
        self.experiment_description_label.setStyleSheet("padding: 5px; border-radius: 3px;")
        desc_layout.addWidget(desc_label)
        desc_layout.addWidget(self.experiment_description_label)
        exp_info_layout.addLayout(desc_layout)

        # Experiment path
        path_layout = QtWidgets.QHBoxLayout()
        path_label = QtWidgets.QLabel("Path:")
        path_label.setFixedWidth(100)
        self.experiment_path_label = QtWidgets.QLabel("-")
        self.experiment_path_label.setWordWrap(True)
        self.experiment_path_label.setStyleSheet("color: #666;")
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.experiment_path_label)
        path_layout.addStretch()
        exp_info_layout.addLayout(path_layout)

        # Number of acquisitions
        acq_layout = QtWidgets.QHBoxLayout()
        acq_label = QtWidgets.QLabel("Acquisitions:")
        acq_label.setFixedWidth(100)
        self.acquisitions_count_label = QtWidgets.QLabel("-")
        acq_layout.addWidget(acq_label)
        acq_layout.addWidget(self.acquisitions_count_label)
        acq_layout.addStretch()
        exp_info_layout.addLayout(acq_layout)

        # Milling steps
        steps_layout = QtWidgets.QHBoxLayout()
        steps_label = QtWidgets.QLabel("Milling steps:")
        steps_label.setFixedWidth(100)
        self.milling_steps_label = QtWidgets.QLabel("-")
        steps_layout.addWidget(steps_label)
        steps_layout.addWidget(self.milling_steps_label)
        steps_layout.addStretch()
        exp_info_layout.addLayout(steps_layout)

        layout.addWidget(exp_info_group)

        # Workflow controls group
        workflow_group = QtWidgets.QGroupBox("Workflow Control")
        workflow_layout = QtWidgets.QVBoxLayout()
        workflow_group.setLayout(workflow_layout)

        # Run workflow button
        self.run_workflow_button = QtWidgets.QPushButton("Run Workflow")
        self.run_workflow_button.setStyleSheet(stylesheets.GREEN_PUSHBUTTON_STYLE)
        self.run_workflow_button.setMinimumHeight(40)
        workflow_layout.addWidget(self.run_workflow_button)

        # Stop workflow button
        self.stop_workflow_button = QtWidgets.QPushButton("Stop Workflow")
        self.stop_workflow_button.setStyleSheet(stylesheets.RED_PUSHBUTTON_STYLE)
        self.stop_workflow_button.setMinimumHeight(40)
        self.stop_workflow_button.setEnabled(False)
        workflow_layout.addWidget(self.stop_workflow_button)

        layout.addWidget(workflow_group)

        # Status group
        status_group = QtWidgets.QGroupBox("Status")
        status_layout = QtWidgets.QVBoxLayout()
        status_group.setLayout(status_layout)

        self.status_label = QtWidgets.QLabel("Ready")
        self.status_label.setStyleSheet("color: gray; font-style: italic;")
        status_layout.addWidget(self.status_label)

        # Workflow status info label
        workflow_status_label = QtWidgets.QLabel("Workflow Info:")
        workflow_status_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        status_layout.addWidget(workflow_status_label)

        self.workflow_status_info_label = QtWidgets.QLabel("-")
        self.workflow_status_info_label.setWordWrap(True)
        self.workflow_status_info_label.setStyleSheet(
            "padding: 8px; "
            # "background-color: #f5f5f5; "
            "border: 1px solid #ddd; "
            "border-radius: 4px; "
            "font-family: monospace; "
            "font-size: 10px;"
        )
        self.workflow_status_info_label.setMinimumHeight(60)
        status_layout.addWidget(self.workflow_status_info_label)

        # Progress bars
        progress_label = QtWidgets.QLabel("Progress:")
        progress_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        status_layout.addWidget(progress_label)

        # Step progress bar
        step_progress_layout = QtWidgets.QHBoxLayout()
        step_progress_label = QtWidgets.QLabel("Step:")
        step_progress_label.setFixedWidth(80)
        self.step_progress_bar = QtWidgets.QProgressBar()
        self.step_progress_bar.setMinimum(0)
        self.step_progress_bar.setMaximum(100)
        self.step_progress_bar.setValue(0)
        self.step_progress_bar.setTextVisible(True)
        self.step_progress_bar.setFormat("%p% (%v/%m)")
        step_progress_layout.addWidget(step_progress_label)
        step_progress_layout.addWidget(self.step_progress_bar)
        status_layout.addLayout(step_progress_layout)

        milling_progress_layout = QtWidgets.QHBoxLayout()
        milling_progress_label = QtWidgets.QLabel("Milling:")
        milling_progress_label.setFixedWidth(80)
        self.milling_progress_bar = QtWidgets.QProgressBar()
        self.milling_progress_bar.setMinimum(0)
        self.milling_progress_bar.setMaximum(100)
        self.milling_progress_bar.setValue(0)
        self.milling_progress_bar.setTextVisible(True)
        self.milling_progress_bar.setFormat("%p% (%v/%m)")
        milling_progress_layout.addWidget(milling_progress_label)
        milling_progress_layout.addWidget(self.milling_progress_bar)
        status_layout.addLayout(milling_progress_layout)

        # Acquisition progress bar
        acq_progress_layout = QtWidgets.QHBoxLayout()
        acq_progress_label = QtWidgets.QLabel("Acquisition:")
        acq_progress_label.setFixedWidth(80)
        self.acq_progress_bar = QtWidgets.QProgressBar()
        self.acq_progress_bar.setMinimum(0)
        self.acq_progress_bar.setMaximum(100)
        self.acq_progress_bar.setValue(0)
        self.acq_progress_bar.setTextVisible(True)
        self.acq_progress_bar.setFormat("%p% (%v/%m)")
        acq_progress_layout.addWidget(acq_progress_label)
        acq_progress_layout.addWidget(self.acq_progress_bar)
        status_layout.addLayout(acq_progress_layout)

        layout.addWidget(status_group)

        # Add stretch to push everything to the top
        layout.addStretch()

        self.viewer = napari.current_viewer()
        if self.viewer is None:
            raise RuntimeError("No active Napari viewer found. Please start Napari before creating the VolumeEMWidget.")
        
        self.microscope.sem_acquisition_signal.connect(self._on_image_acquired)
        # self.microscope.milling_progress_signal.connect(self._on_milling_progress)

    def _setup_connections(self):
        """Setup signal/slot connections."""
        self.run_workflow_button.clicked.connect(self._on_run_workflow_clicked)
        self.stop_workflow_button.clicked.connect(self._on_stop_workflow_clicked)

        # Connect internal signals
        self.workflow_started_signal.connect(self._on_workflow_started)
        self.workflow_finished_signal.connect(self._on_workflow_stopped)
        self.workflow_update_signal.connect(self._on_workflow_update)

    @ensure_main_thread
    def _on_image_acquired(self, image: FibsemImage):
        """Handle image acquisition signal."""
        logging.info(f"Image acquired: {image.metadata.acquisition_date}")

        name = "SEM Image"
        if name in self.viewer.layers:
            self.viewer.layers[name].data = image.data
        else:
            self.viewer.add_image(image.data, name=name)

        self.viewer.reset_view()

    def _on_run_workflow_clicked(self):
        """Handle run workflow button click."""
        logging.info("Run workflow button clicked")
        if self.config is None:
            logging.error("No Volume EM configuration loaded. Cannot start workflow.")
            return

        # Disable run button, enable stop button
        self.run_workflow_button.setEnabled(False)
        self.stop_workflow_button.setEnabled(True)

        self.status_label.setText("Workflow running...")
        self.status_label.setStyleSheet("color: blue; font-style: italic;")

        # Emit signal
        self.workflow_started_signal.emit()

        self._workflow_thread = threading.Thread(target=self._workflow_worker, daemon=True)
        self._workflow_thread.start()

    def _workflow_worker(self):

        try:
            logging.info("Starting Volume EM workflow task...")
            if self.config is None:
                raise ValueError("No Volume EM configuration loaded.")

            self.config.milling.current_step = 0  # Reset current step before running
            self.config.milling.n_steps = 10
            run_volume_em_task(microscope=self.microscope,
                               config=self.config,
                               parent_ui=self)
            logging.info("Volume EM workflow task completed successfully")
            self.status_label.setText("Workflow completed successfully")
        except Exception as e:
            logging.error(f"Error during Volume EM workflow: {e}")
            self.status_label.setText(f"Error: {e}")
            self.status_label.setStyleSheet("color: red; font-style: italic;")
        finally:
            # Re-enable run button, disable stop button
            self.run_workflow_button.setEnabled(True)
            self.stop_workflow_button.setEnabled(False)

            # Emit stopped signal
            self.workflow_finished_signal.emit()

    def _on_stop_workflow_clicked(self):
        """Handle stop workflow button click."""
        if self.is_workflow_running:
            self._workflow_stop_event.set()

    @property
    def is_workflow_running(self) -> bool:
        """Check if the workflow is currently running."""
        return self._workflow_thread is not None and self._workflow_thread.is_alive()

    def _on_workflow_started(self):
        """Handle workflow started signal."""
        logging.info("Volume EM workflow started")
        # Reset workflow state when starting a new workflow
        self._workflow_state = None

    def _on_workflow_stopped(self):
        """Handle workflow stopped signal."""
        logging.info("Volume EM workflow stopped")

    def _on_workflow_update(self, update: VolumeEMWorkflowUpdate):
        """Handle workflow update signal with incremental state updates."""
        logging.info(f"Volume EM workflow update: {update.task} - {update.msg}")

        # Initialize workflow state if it doesn't exist
        if self._workflow_state is None:
            self._workflow_state = VolumeEMWorkflowUpdate(
                task="idle",
                msg="",
                current_step=0,
                total_steps=0,
                current_acq=0,
                total_acq=0,
                acq_name="",
                status="idle",
                stage="setup",
            )

        # Incrementally update the stored state with new values
        # Only update fields that are provided in the new update
        if update.task:
            self._workflow_state.task = update.task
        if update.msg:
            self._workflow_state.msg = update.msg

        # Update progress tracking
        if update.total_steps > 0:
            self._workflow_state.total_steps = update.total_steps
        if update.current_step >= 0:
            self._workflow_state.current_step = update.current_step

        if update.total_acq > 0:
            self._workflow_state.total_acq = update.total_acq
        if update.current_acq >= 0:
            self._workflow_state.current_acq = update.current_acq
        if update.acq_name:
            self._workflow_state.acq_name = update.acq_name

        # Update status and stage
        if update.status:
            self._workflow_state.status = update.status
        if update.stage:
            self._workflow_state.stage = update.stage

        # Update timing
        if update.timestamp:
            self._workflow_state.timestamp = update.timestamp
        if update.elapsed_time > 0:
            self._workflow_state.elapsed_time = update.elapsed_time
        if update.estimated_remaining > 0:
            self._workflow_state.estimated_remaining = update.estimated_remaining

        # Update optional fields
        if update.error:
            self._workflow_state.error = update.error
        if update.error_type:
            self._workflow_state.error_type = update.error_type
        if update.image_filename:
            self._workflow_state.image_filename = update.image_filename
        if update.image_shape:
            self._workflow_state.image_shape = update.image_shape
        if update.milling_time is not None:
            self._workflow_state.milling_time = update.milling_time
        if update.milling_depth is not None:
            self._workflow_state.milling_depth = update.milling_depth
        if update.details:
            self._workflow_state.details = update.details

        # Format the complete workflow state for display
        formatted_msg = format_workflow_update(self._workflow_state)

        # Update the workflow status info label
        self.workflow_status_info_label.setText(formatted_msg)

        # Update step progress bar using stored state
        if self._workflow_state.total_steps > 0:
            self.step_progress_bar.setMaximum(self._workflow_state.total_steps)
            self.step_progress_bar.setValue(self._workflow_state.current_step)
            self.step_progress_bar.setFormat(f"{self._workflow_state.step_progress:.1f}% ({self._workflow_state.current_step}/{self._workflow_state.total_steps})")
        else:
            self.step_progress_bar.setValue(0)
            self.step_progress_bar.setFormat("0% (0/0)")

        # Update acquisition progress bar using stored state
        if self._workflow_state.total_acq > 0:
            self.acq_progress_bar.setMaximum(self._workflow_state.total_acq)
            self.acq_progress_bar.setValue(self._workflow_state.current_acq)
            acq_name_str = f" - {self._workflow_state.acq_name}" if self._workflow_state.acq_name else ""
            # Display 1-based index for user-friendly display
            current_acq_display = self._workflow_state.current_acq + 1
            self.acq_progress_bar.setFormat(f"{self._workflow_state.acq_progress:.1f}% ({current_acq_display}/{self._workflow_state.total_acq}){acq_name_str}")
        else:
            self.acq_progress_bar.setValue(0)
            self.acq_progress_bar.setFormat("0% (0/0)")


    @ensure_main_thread
    def _on_milling_progress(self, progress: dict):
        logging.info(f"Milling progress: {progress}")

        progress_info: dict = progress.get("progress", None)  # type: ignore
        if progress_info is None:
            logging.warning("No progress information provided.")
            return

        state = progress_info.get("state", None)

        # update
        if state == "update":
            logging.debug(progress_info)

            estimated_time = progress_info.get("estimated_time", None)
            remaining_time = progress_info.get("remaining_time", None)
            start_time = progress_info.get("start_time", None)

            if remaining_time is None or estimated_time is None:
                logging.warning(
                    "Remaining time or estimated time not provided in progress info."
                )
                return

            # calculate the percent complete
            percent_complete = int((1 - (remaining_time / estimated_time)) * 100)
            self.milling_progress_bar.setValue(percent_complete)
            self.milling_progress_bar.setFormat(f"{format_duration(remaining_time)} remaining...")

        if state == "finished":
            self.milling_progress_bar.setValue(100)
            self.milling_progress_bar.setFormat("Milling finished.")

    def load_config(self, config: VolumeEMConfig):
        """
        Load a VolumeEMConfig and update the display.

        Args:
            config: VolumeEMConfig instance
        """
        self.config = config

        # Update name
        self.experiment_name_label.setText(config.name if config.name else "-")

        # Update description
        self.experiment_description_label.setText(config.description if config.description else "-")

        # Update path
        self.experiment_path_label.setText(config.path if config.path else "-")

        # Update acquisitions count
        num_acquisitions = len(config.acquisitions) if config.acquisitions else 0
        acq_names = ", ".join(config.acquisitions.keys()) if config.acquisitions else "None"
        self.acquisitions_count_label.setText(f"{num_acquisitions} ({acq_names})")

        # Update milling steps
        if config.milling:
            current_step = config.milling.current_step
            total_steps = config.milling.n_steps
            step_size_nm = config.milling.step_size * 1e9  # Convert to nm
            self.milling_steps_label.setText(
                f"{total_steps} steps × {step_size_nm:.1f} nm (current: {current_step})"
            )
        else:
            self.milling_steps_label.setText("-")

        logging.info(f"Config loaded: {config.name}")

    def set_experiment_info(self, name: str, description: str):
        """
        Set the experiment information display (legacy method).

        Args:
            name: Experiment name
            description: Experiment description
        """
        self.experiment_name_label.setText(name if name else "-")
        self.experiment_description_label.setText(description if description else "-")

        logging.info(f"Experiment info set: {name}")


def create_volume_em_widget(
    microscope: FibsemMicroscope,
    config: Optional[VolumeEMConfig] = None
) -> VolumeEMWidget:
    """
    Create a Volume EM workflow control widget.

    Args:
        microscope: Optional FibsemMicroscope instance
        config: Optional VolumeEMConfig instance

    Returns:
        VolumeEMWidget instance
    """
    widget = VolumeEMWidget(microscope=microscope)
    if config is not None:
        widget.load_config(config)

    logging.info("Volume EM widget created")

    return widget


def main():
    """Create Qt application and show Volume EM widget."""

    import napari
    import os
    from fibsem import utils
    viewer = napari.Viewer()

    PATH = r"C:\Users\rohit\Documents\Code\newFIBSEM\fibsem-os-NYSBC\fibsem\applications\volume_em\test-volume-em-experiment"
    config = VolumeEMConfig.load(os.path.join(PATH, "experiment.yaml"))

    microscope, settings = utils.setup_session()

    # Create the Volume EM widget
    widget = create_volume_em_widget(microscope=microscope, config=config)

    # Set example experiment information
    widget.set_experiment_info(
        name="Example Volume EM Experiment",
        description="This is a demonstration of the Volume EM workflow widget. "
                   "Configure your experiment parameters and click 'Run Workflow' to start."
    )

    viewer.window.add_dock_widget(widget, area='right')

    print("Volume EM Widget demo started")
    print("Set experiment info and use the controls to test the workflow")

    # Run the application
    # sys.exit(app.exec_())

    napari.run()


if __name__ == "__main__":
    main()