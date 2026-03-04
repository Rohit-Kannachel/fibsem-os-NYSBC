import logging
from pathlib import Path
from typing import Optional

import napari
import numpy as np
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal

from fibsem.microscope import FibsemMicroscope
from fibsem.structures import FibsemImage
from fibsem.ui import utils as ui_utils


class VolumeEMViewerWidget(QtWidgets.QWidget):
    """
    Volume EM Viewer Widget for napari.

    Provides a file picker to select a directory containing .tif files,
    loads all .tif files as a single 3D volume layer in napari.
    """

    # Signals
    volume_loaded_signal = pyqtSignal(str, int)  # directory path, number of slices
    loading_error_signal = pyqtSignal(str)  # error message

    def __init__(self, microscope: Optional[FibsemMicroscope] = None,
                 viewer: Optional[napari.Viewer] = None,
                 parent=None):
        super().__init__(parent=parent)

        self.microscope = microscope

        # Get viewer from parent or use provided viewer
        if viewer is not None:
            self.viewer = viewer
        elif hasattr(parent, 'viewer'):
            self.viewer = parent.viewer
        else:
            raise ValueError("Parent must have 'viewer' attribute of type napari.Viewer, "
                           "or viewer must be provided directly")

        self.experiment_directory = None
        self.current_subdirectory = None
        self.current_layer_name = "Volume EM"
        self.slice_metadata_list = []  # Store metadata for each slice

        self.viewer.scale_bar.visible = True
        self.viewer.scale_bar.unit = "m"

        self._setup_ui()
        self._setup_connections()

        logging.info("VolumeEMViewerWidget initialized")

    def _setup_ui(self):
        """Setup the user interface."""
        # Main layout
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # Title
        title_label = QtWidgets.QLabel("Volume EM Viewer")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)

        # Directory selection group
        dir_group = QtWidgets.QGroupBox("Experiment Data")
        dir_layout = QtWidgets.QVBoxLayout()
        dir_group.setLayout(dir_layout)

        # Experiment directory path display
        exp_dir_path_layout = QtWidgets.QHBoxLayout()
        exp_dir_path_label = QtWidgets.QLabel("Experiment:")
        self.exp_dir_path_lineedit = QtWidgets.QLineEdit()
        self.exp_dir_path_lineedit.setReadOnly(True)
        self.exp_dir_path_lineedit.setPlaceholderText("No experiment selected")
        exp_dir_path_layout.addWidget(exp_dir_path_label)
        exp_dir_path_layout.addWidget(self.exp_dir_path_lineedit)
        dir_layout.addLayout(exp_dir_path_layout)

        # Browse experiment button
        self.browse_button = QtWidgets.QPushButton("Browse Experiment Directory...")
        dir_layout.addWidget(self.browse_button)

        # Subdirectory selection
        subdir_layout = QtWidgets.QHBoxLayout()
        subdir_label = QtWidgets.QLabel("Acquisition:")
        self.subdir_combobox = QtWidgets.QComboBox()
        self.subdir_combobox.setEnabled(False)
        self.subdir_combobox.setPlaceholderText("Select acquisition...")
        subdir_layout.addWidget(subdir_label)
        subdir_layout.addWidget(self.subdir_combobox)
        dir_layout.addLayout(subdir_layout)

        # Load button
        self.load_button = QtWidgets.QPushButton("Load Volume")
        self.load_button.setEnabled(False)
        dir_layout.addWidget(self.load_button)

        layout.addWidget(dir_group)

        # Volume info group
        info_group = QtWidgets.QGroupBox("Volume Information")
        info_layout = QtWidgets.QFormLayout()
        info_group.setLayout(info_layout)

        self.slice_count_label = QtWidgets.QLabel("-")
        self.volume_shape_label = QtWidgets.QLabel("-")
        self.file_pattern_label = QtWidgets.QLabel("-")

        info_layout.addRow("Number of slices:", self.slice_count_label)
        info_layout.addRow("Volume shape:", self.volume_shape_label)
        info_layout.addRow("File pattern:", self.file_pattern_label)

        layout.addWidget(info_group)

        # Image metadata group
        metadata_group = QtWidgets.QGroupBox("Image Metadata")
        metadata_layout = QtWidgets.QFormLayout()
        metadata_group.setLayout(metadata_layout)

        self.filename_label = QtWidgets.QLabel("-")
        self.filename_label.setWordWrap(True)
        self.acquisition_date_label = QtWidgets.QLabel("-")
        self.pixel_size_label = QtWidgets.QLabel("-")
        self.field_of_view_label = QtWidgets.QLabel("-")

        metadata_layout.addRow("First image:", self.filename_label)
        metadata_layout.addRow("Acquisition date:", self.acquisition_date_label)
        metadata_layout.addRow("Pixel size (x, y):", self.pixel_size_label)
        metadata_layout.addRow("Field of view:", self.field_of_view_label)

        layout.addWidget(metadata_group)

        # Current slice metadata group
        current_slice_group = QtWidgets.QGroupBox("Current Slice")
        current_slice_layout = QtWidgets.QFormLayout()
        current_slice_group.setLayout(current_slice_layout)

        self.current_slice_index_label = QtWidgets.QLabel("-")
        self.current_slice_filename_label = QtWidgets.QLabel("-")
        self.current_slice_filename_label.setWordWrap(True)
        self.current_slice_date_label = QtWidgets.QLabel("-")

        current_slice_layout.addRow("Slice index:", self.current_slice_index_label)
        current_slice_layout.addRow("Filename:", self.current_slice_filename_label)
        current_slice_layout.addRow("Acquired:", self.current_slice_date_label)

        layout.addWidget(current_slice_group)

        # Layer controls group
        layer_group = QtWidgets.QGroupBox("Layer Controls")
        layer_layout = QtWidgets.QVBoxLayout()
        layer_group.setLayout(layer_layout)

        # Layer name
        layer_name_layout = QtWidgets.QHBoxLayout()
        layer_name_label = QtWidgets.QLabel("Layer name:")
        self.layer_name_lineedit = QtWidgets.QLineEdit(self.current_layer_name)
        layer_name_layout.addWidget(layer_name_label)
        layer_name_layout.addWidget(self.layer_name_lineedit)
        layer_layout.addLayout(layer_name_layout)

        # Clear button
        self.clear_button = QtWidgets.QPushButton("Clear Volume")
        self.clear_button.setEnabled(False)
        layer_layout.addWidget(self.clear_button)

        layout.addWidget(layer_group)

        # Status label
        self.status_label = QtWidgets.QLabel("Ready")
        self.status_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.status_label)

        # Add stretch to push everything to the top
        layout.addStretch()

    def _setup_connections(self):
        """Setup signal/slot connections."""
        self.browse_button.clicked.connect(self._on_browse_clicked)
        self.subdir_combobox.currentTextChanged.connect(self._on_subdirectory_changed)
        self.load_button.clicked.connect(self._on_load_clicked)
        self.clear_button.clicked.connect(self._on_clear_clicked)
        self.layer_name_lineedit.textChanged.connect(self._on_layer_name_changed)

        # Connect internal signals
        self.volume_loaded_signal.connect(self._on_volume_loaded)
        self.loading_error_signal.connect(self._on_loading_error)

    def _on_browse_clicked(self):
        """Handle browse experiment directory button click."""
        directory = ui_utils.open_existing_directory_dialog(
            msg="Select experiment directory",
            path=str(Path.home()),
            parent=self
        )

        if directory:
            self.experiment_directory = directory
            self.exp_dir_path_lineedit.setText(directory)

            # Scan for subdirectories containing .tif files
            subdirs = self._get_acquisition_subdirectories(directory)

            # Update combobox
            self.subdir_combobox.clear()
            if len(subdirs) == 0:
                self.status_label.setText("Warning: No acquisition subdirectories found")
                self.status_label.setStyleSheet("color: orange; font-style: italic;")
                self.subdir_combobox.setEnabled(False)
                self.load_button.setEnabled(False)
            else:
                self.subdir_combobox.addItems([d.name for d in subdirs])
                self.subdir_combobox.setEnabled(True)
                self.status_label.setText(f"Found {len(subdirs)} acquisition(s)")
                self.status_label.setStyleSheet("color: green; font-style: italic;")

    def _on_subdirectory_changed(self, subdir_name: str):
        """Handle subdirectory selection change."""
        if not subdir_name or not self.experiment_directory:
            self.load_button.setEnabled(False)
            return

        # Update current subdirectory
        self.current_subdirectory = Path(self.experiment_directory) / subdir_name

        # Scan subdirectory for .tif files
        tif_files = self._get_tif_files(str(self.current_subdirectory))
        self.file_pattern_label.setText(f"*.tif ({len(tif_files)} files)")

        if len(tif_files) == 0:
            self.status_label.setText(f"Warning: No .tif files found in {subdir_name}")
            self.status_label.setStyleSheet("color: orange; font-style: italic;")
            self.load_button.setEnabled(False)
        else:
            self.status_label.setText(f"Ready to load {len(tif_files)} .tif files from {subdir_name}")
            self.status_label.setStyleSheet("color: green; font-style: italic;")
            self.load_button.setEnabled(True)

    def _on_load_clicked(self):
        """Handle load button click."""
        if not self.current_subdirectory:
            return

        # Disable controls during loading
        self.browse_button.setEnabled(False)
        self.subdir_combobox.setEnabled(False)
        self.load_button.setEnabled(False)
        self.status_label.setText("Loading volume...")
        self.status_label.setStyleSheet("color: blue; font-style: italic;")

        try:
            # Load volume directly
            volume, num_slices, scale, metadata, slice_metadata_list = self._load_volume(str(self.current_subdirectory))

            # Store slice metadata for later use
            self.slice_metadata_list = slice_metadata_list

            # Add or update layer in napari
            if self.current_layer_name in self.viewer.layers:
                self.viewer.layers[self.current_layer_name].data = volume
                self.viewer.layers[self.current_layer_name].scale = np.array(scale)
            else:
                self.viewer.add_image(
                    volume,
                    name=self.current_layer_name,
                    colormap='gray',
                    scale=np.array(scale),
                )

            # Update volume info UI
            self.slice_count_label.setText(str(num_slices))
            self.volume_shape_label.setText(f"{volume.shape}")
            self.clear_button.setEnabled(True)

            # Update metadata UI
            self._update_metadata_display(metadata)

            # Connect to napari dimension slider to update current slice info
            self._connect_slice_updates()

            # Update current slice display with first slice
            self._update_current_slice_display(0)

            # Emit signal
            self.volume_loaded_signal.emit(str(self.current_subdirectory), num_slices)

            self.status_label.setText(f"Volume loaded successfully ({num_slices} slices)")
            self.status_label.setStyleSheet("color: green; font-style: italic;")

            logging.info(f"Volume loaded into napari layer '{self.current_layer_name}'")

        except Exception as e:
            error_msg = f"Error loading volume: {str(e)}"
            logging.error(error_msg)

            self.loading_error_signal.emit(error_msg)
            self.status_label.setText(error_msg)
            self.status_label.setStyleSheet("color: red; font-style: italic;")

        finally:
            # Re-enable controls
            self.browse_button.setEnabled(True)
            self.subdir_combobox.setEnabled(True)
            self.load_button.setEnabled(True)

    def _on_clear_clicked(self):
        """Handle clear button click."""
        if self.current_layer_name in self.viewer.layers:
            self.viewer.layers.remove(self.current_layer_name)
            self.clear_button.setEnabled(False)
            self.status_label.setText("Volume cleared")
            self.status_label.setStyleSheet("color: gray; font-style: italic;")

            # Reset info labels
            self.slice_count_label.setText("-")
            self.volume_shape_label.setText("-")

            # Reset metadata labels
            self.filename_label.setText("-")
            self.acquisition_date_label.setText("-")
            self.pixel_size_label.setText("-")
            self.field_of_view_label.setText("-")

            # Reset current slice labels
            self.current_slice_index_label.setText("-")
            self.current_slice_filename_label.setText("-")
            self.current_slice_date_label.setText("-")

            # Clear slice metadata list
            self.slice_metadata_list = []

    def _on_layer_name_changed(self, text: str):
        """Handle layer name change."""
        self.current_layer_name = text

    def _update_metadata_display(self, metadata: dict):
        """
        Update the metadata display labels.

        Args:
            metadata: Dictionary containing filename, acquisition_date, pixel_size_x, pixel_size_y, hfw
        """
        # Filename
        filename = metadata.get('filename', '-')
        self.filename_label.setText(str(filename))

        # Acquisition date
        acq_date = metadata.get('acquisition_date')
        if acq_date:
            # Format datetime nicely
            date_str = acq_date.strftime("%Y-%m-%d %H:%M:%S")
            self.acquisition_date_label.setText(date_str)
        else:
            self.acquisition_date_label.setText("-")

        # Pixel size
        px_x = metadata.get('pixel_size_x')
        px_y = metadata.get('pixel_size_y')
        if px_x is not None and px_y is not None:
            # Convert to nanometers for display
            px_x_nm = px_x * 1e9
            px_y_nm = px_y * 1e9
            self.pixel_size_label.setText(f"{px_x_nm:.2f} nm, {px_y_nm:.2f} nm")
        else:
            self.pixel_size_label.setText("-")

        # Field of view (HFW)
        hfw = metadata.get('hfw')
        if hfw is not None:
            # Convert to micrometers for display
            hfw_um = hfw * 1e6
            self.field_of_view_label.setText(f"{hfw_um:.2f} µm")
        else:
            self.field_of_view_label.setText("-")

    def _connect_slice_updates(self):
        """Connect to napari dimension slider to update current slice display."""
        # Disconnect any previous connections to avoid duplicates
        try:
            self.viewer.dims.events.current_step.disconnect(self._on_slice_changed)
        except Exception:
            pass  # No previous connection

        # Connect to dimension change event
        self.viewer.dims.events.current_step.connect(self._on_slice_changed)

    def _on_slice_changed(self, event):
        """Handle napari dimension slider change."""
        if len(self.slice_metadata_list) == 0:
            return

        # Get current z-slice index (first dimension)
        current_z = event.value[0] if len(event.value) > 0 else 0

        # Update display
        self._update_current_slice_display(current_z)

    def _update_current_slice_display(self, slice_index: int):
        """
        Update the current slice display labels.

        Args:
            slice_index: Index of the current slice
        """
        if slice_index >= len(self.slice_metadata_list) or slice_index < 0:
            return

        slice_info = self.slice_metadata_list[slice_index]

        # Update labels
        self.current_slice_index_label.setText(f"{slice_index} / {len(self.slice_metadata_list) - 1}")
        self.current_slice_filename_label.setText(slice_info['filename'])

        # Format acquisition date
        acq_date = slice_info.get('acquisition_date')
        if acq_date:
            date_str = acq_date.strftime("%Y-%m-%d %H:%M:%S")
            self.current_slice_date_label.setText(date_str)
        else:
            self.current_slice_date_label.setText("-")

    @staticmethod
    def _get_tif_files(directory: str) -> list[Path]:
        """
        Get all .tif and .tiff files in directory, sorted by name.

        Args:
            directory: Path to directory

        Returns:
            List of Path objects for .tif files, sorted by name
        """
        dir_path = Path(directory)
        tif_files = sorted(list(dir_path.glob("*.tif")) + list(dir_path.glob("*.tiff")))
        return tif_files

    @staticmethod
    def _get_acquisition_subdirectories(experiment_dir: str) -> list[Path]:
        """
        Get all subdirectories in experiment directory that contain .tif files.

        Args:
            experiment_dir: Path to experiment directory

        Returns:
            List of Path objects for subdirectories containing .tif files, sorted by name
        """
        exp_path = Path(experiment_dir)
        subdirs = []

        # Find all subdirectories
        for item in exp_path.iterdir():
            if item.is_dir():
                # Check if subdirectory contains .tif files
                tif_files = list(item.glob("*.tif")) + list(item.glob("*.tiff"))
                if len(tif_files) > 0:
                    subdirs.append(item)

        # Sort by name
        subdirs.sort(key=lambda x: x.name)

        return subdirs

    def _load_volume(self, directory: str) -> tuple[np.ndarray, int, tuple[float, float, float], dict, list]:
        """
        Load volume data from directory containing .tif files using FibsemImage.load().

        Args:
            directory: Path to directory containing .tif files

        Returns:
            Tuple of (volume data, number of slices, scale (z, y, x), metadata_dict, slice_metadata_list)
            metadata_dict contains: filename, acquisition_date, pixel_size_x, pixel_size_y, hfw
            slice_metadata_list: List of dicts with filename and acquisition_date for each slice
        """
        tif_files = self._get_tif_files(directory)

        logging.info(f"Loading volume from {len(tif_files)} .tif files in {directory}")
        if len(tif_files) == 0:
            raise ValueError("No .tif files found in directory")

        # Load all images into a list using FibsemImage.load
        slices = []
        slice_metadata_list = []  # Store metadata for each slice
        pixel_size_x = None
        pixel_size_y = None
        first_metadata = None
        first_filename = None

        for tif_file in tif_files:
            fibsem_img = FibsemImage.load(str(tif_file))
            slices.append(fibsem_img.data)

            # Store metadata for this slice
            slice_info = {
                'filename': tif_file.name,
                'acquisition_date': fibsem_img.metadata.acquisition_date if fibsem_img.metadata else None,
            }
            slice_metadata_list.append(slice_info)

            # Get metadata from first image with valid metadata
            if first_metadata is None and fibsem_img.metadata is not None:
                first_metadata = fibsem_img.metadata
                first_filename = tif_file.name

                if fibsem_img.metadata.pixel_size is not None:
                    pixel_size_x = fibsem_img.metadata.pixel_size.x
                    pixel_size_y = fibsem_img.metadata.pixel_size.y
                    logging.info(f"Using pixel size from metadata: x={pixel_size_x:.2e}m, y={pixel_size_y:.2e}m")

        # Stack into 3D volume
        volume = np.stack(slices, axis=0)

        # Set default scale if no metadata found
        if pixel_size_x is None or pixel_size_y is None:
            logging.warning("No pixel size metadata found, using default scale (1, 1, 1)")
            scale = (1.0, 1.0, 1.0)
        else:
            # napari scale is (z, y, x) - use pixel size for x and y, assume 1.0 for z
            scale = (1.0, pixel_size_y, pixel_size_x)

        # Build metadata dictionary
        metadata_dict = {
            'filename': first_filename if first_filename else tif_files[0].name,
            'acquisition_date': first_metadata.acquisition_date if first_metadata else None,
            'pixel_size_x': pixel_size_x,
            'pixel_size_y': pixel_size_y,
            'hfw': first_metadata.image_settings.hfw if first_metadata else None,
        }

        logging.info(f"Loaded volume with shape {volume.shape} from {len(tif_files)} files")
        logging.info(f"Volume scale (z, y, x): {scale}")

        return volume, len(tif_files), scale, metadata_dict, slice_metadata_list

    def _on_volume_loaded(self, directory: str, num_slices: int):
        """Handle volume loaded signal."""
        logging.info(f"Volume loaded from {directory} with {num_slices} slices")
        self.viewer.reset_view()

    def _on_loading_error(self, error_msg: str):
        """Handle loading error signal."""
        QtWidgets.QMessageBox.warning(
            self,
            "Loading Error",
            error_msg
        )


def create_volume_em_viewer_widget(
    viewer: napari.Viewer,
    microscope: Optional[FibsemMicroscope] = None,
) -> VolumeEMViewerWidget:
    """
    Create and dock a Volume EM viewer widget to a napari viewer.

    Args:
        viewer: napari Viewer instance
        microscope: Optional FibsemMicroscope instance

    Returns:
        VolumeEMViewerWidget instance
    """
    widget = VolumeEMViewerWidget(microscope=microscope, viewer=viewer)

    viewer.window.add_dock_widget(
        widget=widget,
        area="right",
        add_vertical_stretch=True,
        name="Volume EM Viewer"
    )

    logging.info("Volume EM Viewer widget docked to napari")

    return widget
