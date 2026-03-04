
import logging
import os
from typing import Optional, TYPE_CHECKING
import time
from fibsem import acquire
from fibsem.applications.volume_em.structures import (
    VolumeAcquisitionConfig,
    VolumeEMConfig,
    VolumeMillingConfig,
)
from fibsem.applications.volume_em.workflow_update_schema import VolumeEMWorkflowUpdate
from fibsem.microscope import FibsemMicroscope
from fibsem.milling.tasks import run_milling_task

if TYPE_CHECKING:
    from fibsem.applications.volume_em.ui.volume_em_widget import VolumeEMWidget

class VolumeEMTask:
    def __init__(self, microscope: FibsemMicroscope,
                 config: VolumeEMConfig,
                 parent_ui: Optional['VolumeEMWidget'] = None):
        self.microscope = microscope
        self.config = config
        self.parent_ui = parent_ui
        self._start_time = 0.0

        self._configure_directories()

    def _configure_directories(self):
        """Configure directories for acquisition and milling tasks"""

        # make sure output path exists
        os.makedirs(self.config.path, exist_ok=True)

        # remap the acquisition paths
        for name, acq in self.config.acquisitions.items():
            acq.image.path = os.path.join(self.config.path, name)
            os.makedirs(acq.image.path, exist_ok=True)

        # remap the milling imaging path
        self.config.milling.config.acquisition.imaging.path = self.config.path
        os.makedirs(self.config.milling.config.acquisition.imaging.path, exist_ok=True)

    @property
    def current_step(self) -> int:
        return self.config.milling.current_step
    
    @current_step.setter
    def current_step(self, value):
        self.config.milling.current_step = value

    @property
    def total_steps(self) -> int:
        return self.config.milling.n_steps

    def update_status(self, update: VolumeEMWorkflowUpdate):
        """Send a workflow status update."""
        if self.parent_ui:
            self.parent_ui.workflow_update_signal.emit(update)
        logging.info(f"Volume EM workflow update: {update.task} - {update.msg}")

    def check_stop_requested(self) -> bool:
        if self.parent_ui is not None:
            return self.parent_ui._workflow_stop_event.is_set()
        return False

    def run(self):

        self._start_time = time.time()

        # Send workflow start update
        self.update_status(VolumeEMWorkflowUpdate(
            task="setup",
            msg=f"Starting Volume EM workflow: {self.config.name}",
            current_step=self.current_step,
            total_steps=self.total_steps,
            stage="setup",
        ))

        while self.current_step < self.total_steps:

            print("-"*80)

            logging.info(f"Starting step {self.current_step + 1} of {self.total_steps}")

            # Send step start update
            elapsed = time.time() - self._start_time
            self.update_status(VolumeEMWorkflowUpdate(
                task="milling",
                msg=f"Step {self.current_step + 1}/{self.total_steps}: Starting milling",
                current_step=self.current_step,
                total_steps=self.total_steps,
                stage="milling",
                elapsed_time=elapsed,
            ))

            # milling
            self._milling_task()

            # acquisitions
            for j, (name, acq) in enumerate(self.config.acquisitions.items()):
                if self.check_stop_requested():
                    logging.info("Stop requested. Exiting Volume EM workflow.")
                    return

                # Send acquisition update
                elapsed = time.time() - self._start_time
                update = VolumeEMWorkflowUpdate(
                    task="acquisition",
                    msg=f"Starting acquisition {j + 1} of {len(self.config.acquisitions)}: {name}",
                    current_step=self.current_step,
                    total_steps=self.total_steps,
                    current_acq=j,
                    total_acq=len(self.config.acquisitions),
                    acq_name=name,
                    stage="acquisition",
                    elapsed_time=elapsed,
                )
                self.update_status(update)
                self._acquisition_task(acq, acq_index=j)

            # adjust milling position by step size
            self.config.milling.config.stages[0].pattern.point.y += self.config.milling.step_size

            # we need to beam shift the imaging state as the image 'moves' up
            for name, acq in self.config.acquisitions.items():
                acq.state.electron_beam.shift.y += self.config.milling.step_size # type: ignore

            # increase current step
            self.current_step += 1

            # save config
            self.config.save()

        # Send workflow completion update
        elapsed = time.time() - self._start_time
        self.update_status(VolumeEMWorkflowUpdate(
            task="complete",
            msg=f"Volume EM workflow completed: {self.total_steps} steps processed",
            current_step=self.total_steps,
            total_steps=self.total_steps,
            status="completed",
            stage="complete",
            elapsed_time=elapsed,
        ))

    def _milling_task(self):

        # Send milling start update
        elapsed = time.time() - self._start_time
        self.update_status(VolumeEMWorkflowUpdate(
            task="milling",
            msg=f"Milling step {self.current_step + 1}/{self.total_steps}",
            current_step=self.current_step,
            total_steps=self.total_steps,
            stage="milling",
            elapsed_time=elapsed,
        ))

        # return  # TODO: Uncomment when milling is disabled

        # set microscope state
        self.microscope.set_microscope_state(self.config.milling.state)

        # run milling task
        self.config.milling.config.acquisition.imaging.path = self.config.path # reset
        milling_start_time = time.time()
        run_milling_task(microscope=self.microscope, 
                         config=self.config.milling.config, 
                         parent_ui=self.parent_ui)
        milling_duration = time.time() - milling_start_time

        # Send milling complete update
        elapsed = time.time() - self._start_time
        milling_depth = self.config.milling.step_size * (self.current_step + 1)
        self.update_status(VolumeEMWorkflowUpdate(
            task="milling",
            msg=f"Completed milling step {self.current_step + 1}/{self.total_steps}",
            current_step=self.current_step,
            total_steps=self.total_steps,
            stage="milling",
            milling_time=milling_duration,
            milling_depth=milling_depth,
            elapsed_time=elapsed,
        ))
        # QUERY: do we want to change the current at all?

    def _acquisition_task(self, acq: VolumeAcquisitionConfig, acq_index: int = 0):

        # set microscope state
        self.microscope.set_microscope_state(acq.state)

        # alignment - send update
        elapsed = time.time() - self._start_time
        self.update_status(VolumeEMWorkflowUpdate(
            task="alignment",
            msg=f"Aligning beam for {acq.name} acquisition",
            current_step=self.current_step,
            total_steps=self.total_steps,
            current_acq=acq_index,
            total_acq=len(self.config.acquisitions),
            acq_name=acq.name,
            stage="alignment",
            elapsed_time=elapsed,
        ))

        # auto-focus
        self.microscope.auto_focus(acq.image.beam_type, acq.alignment_area)

        # auto-contrast
        self.microscope.autocontrast(acq.image.beam_type, acq.alignment_area)

        # acquisition - send update
        elapsed = time.time() - self._start_time
        self.update_status(VolumeEMWorkflowUpdate(
            task="acquisition",
            msg=f"Acquiring {acq.name} image for step {self.current_step + 1}/{self.total_steps}",
            current_step=self.current_step,
            total_steps=self.total_steps,
            current_acq=acq_index,
            total_acq=len(self.config.acquisitions),
            acq_name=acq.name,
            stage="acquisition",
            elapsed_time=elapsed,
        ))

        # set image settings
        acq.image.save = True
        acq.image.autocontrast = False
        acq.image.autogamma = False
        acq.image.filename = f"{acq.name}-Image-{self.config.milling.current_step:03d}"
        image = self.microscope.acquire_image(acq.image)
        image.save(os.path.join(acq.image.path, acq.image.filename)) # type: ignore

        # snap shot of microscope state
        acq.state = self.microscope.get_microscope_state(acq.image.beam_type)

        if self.parent_ui:
            self.microscope.sem_acquisition_signal.emit(image)

        # Send acquisition complete update
        elapsed = time.time() - self._start_time
        self.update_status(VolumeEMWorkflowUpdate(
            task="acquisition",
            msg=f"Completed {acq.name} acquisition",
            current_step=self.current_step,
            total_steps=self.total_steps,
            current_acq=acq_index,
            total_acq=len(self.config.acquisitions),
            acq_name=acq.name,
            stage="acquisition",
            image_filename=acq.image.filename,
            image_shape=(image.data.shape[0], image.data.shape[1]) if image.data is not None else None,
            elapsed_time=elapsed,
        ))

        time.sleep(2)


def run_volume_em_task(microscope: FibsemMicroscope,
                       config: VolumeEMConfig, 
                       parent_ui: Optional['VolumeEMUI'] = None) -> None:

    task = VolumeEMTask(microscope=microscope, 
                        config=config, 
                        parent_ui=parent_ui)
    task.run()