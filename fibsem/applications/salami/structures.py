
import logging
import os
from dataclasses import dataclass, field

import yaml

from fibsem.milling.patterning import RectanglePattern
from fibsem.milling.tasks import (
    FibsemMillingStage,
    FibsemMillingTaskConfig,
    MillingAlignment,
)
from fibsem.structures import (
    BeamSettings,
    BeamType,
    FibsemMillingSettings,
    FibsemRectangle,
    ImageSettings,
    MicroscopeState,
)


@dataclass
class VolumeAcquisitionConfig:
    name: str = "Volume Acquisition Task"
    state: MicroscopeState = field(default_factory=MicroscopeState)
    image: ImageSettings = field(default_factory=ImageSettings)
    alignment_area: FibsemRectangle = field(default_factory=FibsemRectangle)

    def to_dict(self):
        return {
            "name": self.name,
            "state": self.state.to_dict(),
            "image": self.image.to_dict(),
            "alignment_area": self.alignment_area.to_dict()
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            name=data["name"],
            state=MicroscopeState.from_dict(data["state"]),
            image=ImageSettings.from_dict(data["image"]),
            alignment_area=FibsemRectangle(**data["alignment_area"])
        )


@dataclass
class VolumeMillingConfig:
    name: str = "Volume Milling Task"
    description: str = "Configuration for volume milling"
    n_steps: int = 50
    step_size: float = 100e-9  # 100 nm
    current_step: int = 0
    state: MicroscopeState = field(default_factory=MicroscopeState)
    config: FibsemMillingTaskConfig = field(default_factory=FibsemMillingTaskConfig)

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "n_steps": self.n_steps,
            "step_size": self.step_size,
            "current_step": self.current_step,
            "state": self.state.to_dict(),
            "config": self.config.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            name=data["name"],
            description=data["description"],
            n_steps=data["n_steps"],
            step_size=data["step_size"],
            current_step=data["current_step"],
            state=MicroscopeState.from_dict(data["state"]),
            config=FibsemMillingTaskConfig.from_dict(data["config"])
        )


@dataclass
class VolumeEMConfig:
    name: str
    description: str
    path: str
    milling: VolumeMillingConfig
    acquisitions: dict[str, VolumeAcquisitionConfig]

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "path": self.path,
            "milling": self.milling.to_dict(),
            "acquisitions": {k: v.to_dict() for k, v in self.acquisitions.items()}
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            name=data["name"],
            description=data["description"],
            path=data["path"],
            milling=VolumeMillingConfig.from_dict(data["milling"]),
            acquisitions={k: VolumeAcquisitionConfig.from_dict(v) for k, v in data["acquisitions"].items()}
        )

    def save(self) -> str:

        filename = os.path.join(self.path, "experiment.yaml")
        with open(filename, 'w') as f:
            yaml.dump(self.to_dict(), f, sort_keys=False)
        return filename
    
    @classmethod
    def load(cls, filename: str):
        with open(filename, 'r') as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)
