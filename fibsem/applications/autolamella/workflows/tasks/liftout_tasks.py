
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
from fibsem import acquire, alignment, calibration, constants, utils
from fibsem import config as fcfg
from fibsem.applications.autolamella.protocol.constants import (
    LANDING_SITE_KEY,
    REMOVE_BLOCK_KEY,
    SLICE_BLOCK_KEY,
)
import numpy as np
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
    CopperAdapterTopEdge,
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

    for_liftout: bool = field(
        default=False,
        metadata={"help": "Whether the trench is being milled for a liftout protocol. Enabling this flag means this will run only for the lamella marked as for liftout block."},
    )

    milling_angle: float = field(
        default=90,
        metadata={
            "help": "The angle between the FIB and sample used for milling",
            "units": constants.DEGREE_SYMBOL,
        },
    )
    orientation: str = field(
        default="FIB",
        metadata={"help": "The orientation to perform undercut milling in"},
    )

    def __post_init__(self):
        if self.milling == {}:
            self.milling = deepcopy({REMOVE_BLOCK_KEY: DEFAULT_MILLING_CONFIG[REMOVE_BLOCK_KEY]})



@dataclass
class LandBlockTaskConfig(AutoLamellaTaskConfig):
    """Configuration for the LandBlockTask."""
    task_type: ClassVar[str] = "LIFTOUT_LAND_BLOCK"
    display_name: ClassVar[str] = "Land Liftout Block"

    for_liftout: bool = field(
        default=False,
        metadata={"help": "Whether the trench is being milled for a liftout protocol. Enabling this flag means this will run only for the lamella marked as for liftout block."},
    )

    def __post_init__(self):
        if self.milling == {}:
            self.milling = deepcopy({SLICE_BLOCK_KEY: DEFAULT_MILLING_CONFIG[SLICE_BLOCK_KEY]})







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
    """Task to Attach the Block to needlle/copper block and detach from the bulk for liftout."""
    config: LiftoutBlockTaskConfig
    config_cls: ClassVar[Type[LiftoutBlockTaskConfig]] = LiftoutBlockTaskConfig

    def _run(self) -> None:
        """Run the task to liftout the block from the site."""


        ## Overview of steps:
        # 1. Move to milling pose (this will be FIB Orientation rotating back from (SEM) undercut)
        # 2. Insert Needle to Park Position (The copper block should be on the needle at this point)
        # 3. Use detection to move the block to the bottom of block
            #3.1 When supervised, there should be an option to manually move the needle rather
        # 4. Once the block is attached to the needle, we can weld the block to the adaptor



        ##### Step 1: Move to milling pose (this will be FIB Orientation rotating back from (SEM) undercut) #####

        self.image_settings: ImageSettings = self.config.imaging
        self.image_settings.path = self.lamella.path

        self.checkpoint = self.config.model_checkpoint

        self._move_to_position()

        ## Detect and centre the bottom of the block

        ## use lamella or volume block feature??

        self._align_feature_with_ml(image_settings=self.image_settings,
                                    feature=LamellaBottomEdge(),
                                    checkpoint=self.checkpoint)
        
        ##### Step 2: Insert Needle to Park Position (The copper block should be on the needle at this point) #####

        self.log_status_message("INSERT_NEEDLE", "Inserting needle to park position...")

        ### needle stuff
        # self.microscope.insert_needle_to_park_position()
        
        #### Step 3: Use detection to move the copper to the bottom of block #####

        self._move_adaptor_to_block()


        ##### Step 4: Once the block is attached to the needle, we can weld the block to the adaptor and the cut#####

        det_ib = update_detection_ui(microscope=self.microscope,
                                            image_settings=self.image_settings,
                                            checkpoint=self.checkpoint,
                                            features=[LamellaCentre(), LamellaBottomEdge()],
                                            parent_ui=self.parent_ui,
                                            validate=self.validate,
                                            msg=self.lamella.status_info)


        self.log_status_message("WELD_BLOCK", "Welding block to adaptor...")
        welding_task_config = self.config.milling[REMOVE_BLOCK_KEY]
        welding_task_config.alignment.rect = self.lamella.alignment_area
        welding_task_config.acquisition.imaging.path = self.lamella.path # TODO: move into update_milling_config_ui

        # stage 1 is welding, stage 2 is cutting

        welding_point = welding_task_config.stages[0].pattern.point

        welding_point.x += det_ib.features[1].feature_m.x 
        welding_point.y += det_ib.features[1].feature_m.y

        cut_point = welding_task_config.stages[1].pattern.point
        cut_point.x += det_ib.features[0].feature_m.x
        cut_point.y += det_ib.features[0].feature_m.y

        msg=f"Press Run Milling to weld the block for {self.lamella.name}. Press Continue when done."
        welding_task_config = self.update_milling_config_ui(welding_task_config, msg=msg)


        ##### step 5: Remove the block from bulk

        ## needle stuff


    


    def _move_to_position(self) -> None:
        """Move the stage to the position for block milling."""
        # move to lamella milling position

        if self.config.orientation == "FIB":

            self.log_status_message("SELECT_POSITION", "Rotating to FIB orientation and moving to milling position...")
            # check if in the right orientation
            setup_position = self.microscope.get_target_position(self.lamella.stage_position, 
                                                                self.config.orientation)
            

            has_rotated = not np.isclose(setup_position.r, self.lamella.stage_position.r, atol=1e-2)

            self.microscope.safe_absolute_stage_movement(setup_position)

            if has_rotated:
                logging.info(f"Rotation Movement Detected. Aligning to lamella centre to correct for any misalignment from rotation.")
                ## align to lamella (coming from prev rotation)
                # align feature coincident   
                feature = LamellaCentre()
                lamella = align_feature_coincident(
                    microscope=self.microscope,
                    image_settings=self.image_settings,
                    lamella=self.lamella,
                    checkpoint=self.checkpoint,
                    parent_ui=self.parent_ui,
                    validate=self.validate,
                    feature=feature,
                    hfw=self.config.imaging.hfw
                )

        else:
                
            # check if close to tilt angle
            self.log_status_message("SELECT_POSITION", "Moving to milling position...")
            milling_angle = self.config.milling_angle
            is_close = self.microscope.is_close_to_milling_angle(milling_angle=milling_angle)

            
            if is_close:
                current_tilt_angle = self.microscope.get_microscope_state().stage_position.t
                self.lamella.milling_pose.stage_position.t = current_tilt_angle


            self._move_to_milling_pose()


            if not is_close:
                
                if self.validate:

                    current_milling_angle = self.microscope.get_current_milling_angle()
                    ret = ask_user(parent_ui=self.parent_ui,
                                msg=f"Tilt to specified milling angle ({milling_angle:.1f} {constants.DEGREE_SYMBOL})? "
                                f"Current milling angle is {current_milling_angle:.1f} {constants.DEGREE_SYMBOL}.",
                                pos="Tilt", neg="Skip")
                    if ret:
                        self.microscope.move_to_milling_angle(milling_angle=np.radians(milling_angle))
                else:
                    self.microscope.move_to_milling_angle(milling_angle=np.radians(milling_angle))



            # do detection 

            # Take Ion Image for detection, change beamtype temporarily to ION then change back
            orig_beam_type = self.image_settings.beam_type
            self.image_settings.beam_type = BeamType.ION
            

            self._align_feature_with_ml(image_settings=self.image_settings, 
                                        feature=LamellaCentre(), 
                                        checkpoint=self.checkpoint)

            
            self.image_settings.beam_type = orig_beam_type

    def _move_adaptor_to_block(self,tol: float = 1e-6) -> None:
        """Move the copper block on the needle to the bottom of the lamella block using detection."""
        self.log_status_message("ALIGN_ADAPTOR", "Aligning copper block to bottom of lamella block...")

        # image in EB

        self.image_settings.beam_type = BeamType.ELECTRON

        det_eb = update_detection_ui(microscope=self.microscope,
                                            image_settings=self.image_settings,
                                            checkpoint=self.checkpoint,
                                            features=[CopperAdapterTopEdge(), LamellaBottomEdge()],
                                            parent_ui=self.parent_ui,
                                            validate=self.validate,
                                            msg=self.lamella.status_info)

        self.image_settings.beam_type = BeamType.ION

        det_ib =update_detection_ui(microscope=self.microscope,
                                            image_settings=self.image_settings,
                                            checkpoint=self.checkpoint,
                                            features=[CopperAdapterTopEdge(), LamellaBottomEdge()],
                                            parent_ui=self.parent_ui,
                                            validate=self.validate,
                                            msg=self.lamella.status_info)

        ## move needle here based on detections

        self._acquire_reference_image(self.image_settings, field_of_view=self.config.imaging.field_of_view)
        


class LandBlockTask(AutoLamellaTask): 
    """Task to land the block after liftout."""
    config: LandBlockTaskConfig
    config_cls: ClassVar[Type[LandBlockTaskConfig]] = LandBlockTaskConfig

    def _run(self) -> None:
        """Run the task to land the block after liftout."""
        pass