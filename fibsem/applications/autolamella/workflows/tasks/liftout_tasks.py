
import logging
import os
from copy import deepcopy
from dataclasses import asdict, dataclass, field, fields


from fibsem.applications.autolamella.workflows._default_milling_config import DEFAULT_MILLING_CONFIG
from fibsem.applications.autolamella.workflows.tasks.base_task import AutoLamellaTask
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from fibsem.applications.autolamella.protocol.constants import (
    LANDING_SITE_KEY,
    REMOVE_BLOCK_KEY,
    SLICE_BLOCK_KEY,
)

from fibsem.applications.autolamella.structures import (
    AutoLamellaTaskConfig,
    AutoLamellaTaskState,
    AutoLamellaTaskStatus,
    Experiment,
    Lamella,
)
from fibsem.applications.autolamella.workflows.core import (
    align_feature_coincident,
    ask_user,
    set_images_ui,
    update_alignment_area_ui,
    update_detection_ui,
    update_status_ui,
)
from fibsem.detection.detection import (
    Feature,
    LamellaBottomEdge,
    LamellaCentre,
    LamellaTopEdge,
    VolumeBlockCentre,
)

from fibsem.microscope import FibsemMicroscope
from fibsem.milling.patterning.utils import get_pattern_reduced_area
from fibsem.milling.tasks import FibsemMillingTaskConfig, run_milling_task
from fibsem.structures import (
    BeamType,
    FibsemImage,
    FibsemRectangle,
    FibsemStagePosition,
    ImageSettings,
    Point,
    DEFAULT_ALIGNMENT_AREA,
)

if TYPE_CHECKING:
    from fibsem.applications.autolamella.ui import AutoLamellaUI

TAutoLamellaTaskConfig = TypeVar(
    "TAutoLamellaTaskConfig", bound="AutoLamellaTaskConfig"
)









@dataclass
class MillLandingSiteTaskConfig(AutoLamellaTaskConfig):

    """Configuration for the MillLandingSiteTask."""
    task_type: ClassVar[str] = "LIFTOUT_MILL_LANDING_SITE"
    display_name: ClassVar[str] = "Mill Landing Site"

    def __post_init__(self):
        if self.milling == {}:
            self.milling = deepcopy({"milling": DEFAULT_MILLING_CONFIG[LANDING_SITE_KEY]})


@dataclass
class LiftoutBlockTaskConfig(AutoLamellaTaskConfig):
    """Configuration for the LiftoutBlockTask."""
    task_type: ClassVar[str] = "LIFTOUT_BLOCK_MILLING"
    display_name: ClassVar[str] = "Mill Block for Liftout"

    def __post_init__(self):
        if self.milling == {}:
            self.milling = deepcopy({"milling": DEFAULT_MILLING_CONFIG[REMOVE_BLOCK_KEY]})

@dataclass
class LandBlockTaskConfig(AutoLamellaTaskConfig):
    """Configuration for the LandBlockTask."""
    task_type: ClassVar[str] = "LIFTOUT_LAND_BLOCK"
    display_name: ClassVar[str] = "Land Liftout Block"

    def __post_init__(self):
        if self.milling == {}:
            self.milling = deepcopy({"milling": DEFAULT_MILLING_CONFIG[SLICE_BLOCK_KEY]})







class MillLandingSiteTask(AutoLamellaTask):
    """Task to mill the landing site for a lamella."""
    config: MillLandingSiteTaskConfig
    config_cls: ClassVar[Type[MillLandingSiteTaskConfig]] = MillLandingSiteTaskConfig

    # TODO: Implement this task and change references from lamella to landing site where appropriate
    # probably the easiest way to do this
    # includes: move_to_milling_pose: This should change to landing site from experiment?
    # logging: where ever it says lamella.etc change to get info or do something else?

    def _run(self) -> None:
        """Run the task to mill the landing site for a lamella."""



class LiftoutBlockTask(AutoLamellaTask):
    """Task to mill the block for liftout."""
    config: LiftoutBlockTaskConfig
    config_cls: ClassVar[Type[LiftoutBlockTaskConfig]] = LiftoutBlockTaskConfig

    def _run(self) -> None:
        """Run the task to mill the block for liftout."""
        pass


class LandBlockTask(AutoLamellaTask): 
    """Task to land the block after liftout."""
    config: LandBlockTaskConfig
    config_cls: ClassVar[Type[LandBlockTaskConfig]] = LandBlockTaskConfig

    def _run(self) -> None:
        """Run the task to land the block after liftout."""
        pass