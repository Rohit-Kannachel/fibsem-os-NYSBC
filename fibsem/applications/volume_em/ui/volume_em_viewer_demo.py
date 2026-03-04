"""
Demo script for Volume EM Viewer Widget

This script demonstrates how to use the VolumeEMViewerWidget with napari.
It creates a napari viewer and docks the Volume EM viewer widget.

Usage:
    python example/volume_em_viewer_demo.py
"""

import napari
from fibsem.applications.volume_em.ui import create_volume_em_viewer_widget


def main():
    """Create napari viewer and add Volume EM viewer widget."""

    # Create napari viewer
    viewer = napari.Viewer()

    # Create and dock the Volume EM viewer widget
    widget = create_volume_em_viewer_widget(viewer=viewer)

    print("Volume EM Viewer widget created and docked to napari")
    print("Use the 'Browse Directory...' button to select a directory containing .tif files")
    print("Then click 'Load Volume' to load the images as a 3D volume")

    # Start napari event loop
    napari.run()


if __name__ == "__main__":
    main()
