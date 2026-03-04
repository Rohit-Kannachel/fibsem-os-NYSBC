"""
Workflow Update Schema for Volume EM Tasks

This module defines the standardized dictionary schema for workflow status updates
in Volume EM acquisition and milling tasks.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Literal
from datetime import datetime


@dataclass
class VolumeEMWorkflowUpdate:
    """
    Standardized schema for Volume EM workflow status updates.

    This dataclass is emitted via workflow_update_signal to communicate
    workflow progress and status to the UI and logging systems.
    """

    # Primary identification (required)
    task: str  # Current task being executed (e.g., "milling", "acquisition", "alignment", "movement")
    msg: str   # Human-readable status message

    # Step progress (milling steps)
    current_step: int = 0       # Current milling step (0-indexed)
    total_steps: int = 0        # Total number of milling steps

    # Acquisition progress (within current step)
    current_acq: int = 0        # Current acquisition index (0-indexed)
    total_acq: int = 0          # Total number of acquisitions per step
    acq_name: str = ""          # Name of current acquisition (e.g., "EB", "IB")

    # Status and state
    status: Literal["running", "paused", "completed", "error", "idle"] = "running"
    stage: Literal["setup", "milling", "acquisition", "alignment", "saving", "complete"] = "setup"

    # Timing information
    timestamp: Optional[datetime] = None     # Timestamp of this update
    elapsed_time: float = 0.0                # Elapsed time in seconds since workflow start
    estimated_remaining: float = 0.0         # Estimated remaining time in seconds

    # Error handling
    error: Optional[str] = None       # Error message if status == "error"
    error_type: Optional[str] = None  # Type of error (e.g., "MicroscopeError", "IOError")

    # Image information (when acquiring)
    image_filename: Optional[str] = None            # Filename of current/last acquired image
    image_shape: Optional[tuple[int, int]] = None   # Shape of acquired image (height, width)
    image_metadata: Optional[dict] = None           # Additional image metadata

    # Milling information (when milling)
    milling_time: Optional[float] = None   # Time spent milling in seconds
    milling_depth: Optional[float] = None  # Current milling depth in meters
    estimated_milling_time: Optional[float] = None  # Estimated total milling time in seconds
    remaining_milling_time: Optional[float] = None  # Estimated remaining milling time in seconds

    # Additional context
    details: Optional[dict] = None  # Arbitrary additional details as nested dict

    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now()

    @property
    def step_progress(self) -> float:
        """Calculate step progress as percentage (0.0 - 100.0)."""
        if self.total_steps > 0:
            return (self.current_step / self.total_steps) * 100.0
        return 0.0

    @property
    def acq_progress(self) -> float:
        """Calculate acquisition progress as percentage (0.0 - 100.0)."""
        if self.total_acq > 0:
            return (self.current_acq / self.total_acq) * 100.0
        return 0.0

    @property
    def overall_progress(self) -> float:
        """Calculate overall workflow progress as percentage (0.0 - 100.0)."""
        if self.total_steps > 0:
            # Calculate progress including partial step progress from acquisitions
            step_fraction = self.current_step / self.total_steps
            if self.total_acq > 0:
                acq_fraction = (self.current_acq / self.total_acq) / self.total_steps
                return (step_fraction + acq_fraction) * 100.0
            return step_fraction * 100.0
        return 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return asdict(self)

    def format(self) -> str:
        """
        Format the workflow update into a human-readable string.

        Returns:
            Formatted string for display
        """
        lines = []

        # Main message
        lines.append(self.msg)

        # Progress information
        if self.total_steps > 0:
            lines.append(f"Step: {self.current_step + 1}/{self.total_steps}")

        if self.total_acq > 0:
            acq_str = f"Acquisition: {self.current_acq + 1}/{self.total_acq}"
            if self.acq_name:
                acq_str += f" ({self.acq_name})"
            lines.append(acq_str)

        if self.overall_progress > 0:
            lines.append(f"Overall: {self.overall_progress:.1f}%")

        # Timing information
        if self.elapsed_time > 0:
            elapsed = self.elapsed_time
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = int(elapsed % 60)
            lines.append(f"Elapsed: {hours:02d}:{minutes:02d}:{seconds:02d}")

        if self.estimated_remaining > 0:
            remaining = self.estimated_remaining
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            lines.append(f"Remaining: ~{hours:02d}:{minutes:02d}")

        # Error information
        if self.status == 'error' and self.error:
            lines.append(f"ERROR: {self.error}")

        return '\n'.join(lines)


# Example workflow update instances for different scenarios

EXAMPLE_MILLING_START = VolumeEMWorkflowUpdate(
    task="milling",
    msg="Starting milling step 1/100",
    current_step=0,
    total_steps=100,
    current_acq=0,
    total_acq=2,
    stage="milling",
    elapsed_time=0.0,
)

EXAMPLE_MILLING_PROGRESS = VolumeEMWorkflowUpdate(
    task="milling",
    msg="Milling step 50/100 complete",
    current_step=49,
    total_steps=100,
    stage="milling",
    milling_time=45.2,
    milling_depth=2.5e-6,  # 2.5 microns
    elapsed_time=3600.0,
    estimated_remaining=3600.0,
)

EXAMPLE_ACQUISITION_START = VolumeEMWorkflowUpdate(
    task="acquisition",
    msg="Acquiring EB image (1/2) for step 25/100",
    current_step=24,
    total_steps=100,
    current_acq=0,
    total_acq=2,
    acq_name="EB",
    stage="acquisition",
    elapsed_time=1800.0,
)

EXAMPLE_ACQUISITION_COMPLETE = VolumeEMWorkflowUpdate(
    task="acquisition",
    msg="Acquired IB image (2/2) for step 25/100",
    current_step=24,
    total_steps=100,
    current_acq=1,
    total_acq=2,
    acq_name="IB",
    stage="acquisition",
    image_filename="step_024_IB_20240124_143022.tif",
    image_shape=(2048, 3072),
    elapsed_time=1805.0,
)

EXAMPLE_ALIGNMENT = VolumeEMWorkflowUpdate(
    task="alignment",
    msg="Performing beam alignment for step 30/100",
    current_step=29,
    total_steps=100,
    stage="alignment",
    elapsed_time=2100.0,
)

EXAMPLE_COMPLETE = VolumeEMWorkflowUpdate(
    task="complete",
    msg="Volume EM workflow completed successfully",
    current_step=100,
    total_steps=100,
    current_acq=2,
    total_acq=2,
    status="completed",
    stage="complete",
    elapsed_time=7200.0,
)

EXAMPLE_ERROR = VolumeEMWorkflowUpdate(
    task="acquisition",
    msg="Error acquiring image: Microscope connection lost",
    current_step=45,
    total_steps=100,
    current_acq=0,
    total_acq=2,
    status="error",
    stage="acquisition",
    error="Microscope connection lost",
    error_type="ConnectionError",
    elapsed_time=3200.0,
)


def format_workflow_update(update: VolumeEMWorkflowUpdate) -> str:
    """
    Format a workflow update into a human-readable string.

    Args:
        update: VolumeEMWorkflowUpdate dataclass

    Returns:
        Formatted string for display
    """
    return update.format()
