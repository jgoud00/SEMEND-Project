from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SimulationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    duration_s: float = Field(default=2, ge=1, le=10)
    sample_rate_hz: Literal[2000, 4000, 8000] = 4000
    gesture: Literal["Rest", "Grip", "Wrist flexion", "Wrist extension", "Forearm rotation"] = "Grip"
    intensity: float = Field(default=0.65, ge=0, le=1)
    mains_mv: float = Field(default=0.25, ge=0, le=2)
    noise_mv: float = Field(default=0.05, ge=0, le=0.5)
    offset_mv: float = Field(default=0, ge=-50, le=50)
    motion_mv: float = Field(default=0.15, ge=0, le=2)
    fatigue: float = Field(default=0, ge=0, le=1)
    post_gain: float = Field(default=50, ge=1, le=100)
    highpass_hz: float = Field(default=20, ge=5, le=100)
    lowpass_hz: float = Field(default=450, ge=150, le=700)
    notch: bool = True
    heart_rate_bpm: float = Field(default=72, ge=40, le=180)
    motion_scenario: Literal["Gesture", "Stationary", "Repetitive", "Tremor", "Sudden motion"] = "Gesture"
    tremor_hz: float = Field(default=6, ge=3, le=12)
    motion_scale: float = Field(default=1, ge=0, le=2)
    ppg_scenario: Literal["Clean", "Motion artifact", "Low perfusion", "Dropout"] = "Clean"
    ppg_noise_au: float = Field(default=0.035, ge=0, le=0.5)
    ppg_motion_au: float = Field(default=0.5, ge=0, le=2)
    resistor_tolerance_pct: float = Field(default=1, ge=0, le=5)
    capacitor_tolerance_pct: float = Field(default=5, ge=0, le=10)
    electrode_resistance_ohm: float = Field(default=10000, ge=0, le=100000)
    temperature_c: float = Field(default=25, ge=0, le=50)

    @model_validator(mode="after")
    def bandwidth(self):
        if self.lowpass_hz >= self.sample_rate_hz / 2:
            raise ValueError("Low-pass cutoff must be below Nyquist")
        return self


class AnalysisResponse(BaseModel):
    config: SimulationConfig
    provenance: dict
    emg: dict
    analog: dict
    dsp: dict
    imu: dict
    ppg: dict
    warnings: list[str]


class TrainingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seed: int = Field(default=1000, ge=0, le=2**31-1)
    trials_per_class: int = Field(default=6, ge=6, le=12)


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    config: SimulationConfig = Field(default_factory=SimulationConfig)
    model: Literal["Logistic Regression", "SVM", "Decision Tree", "Random Forest", "Gradient Boosting"] = "Random Forest"
