import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from . import analog, dsp, simulation, spice
from .schemas import AnalysisResponse, PredictionRequest, SimulationConfig, TrainingRequest
from . import ml
from .artifacts import ROOT

PROJECT = json.loads((ROOT / "project.json").read_text(encoding="utf-8"))

app = FastAPI(title="ForearmSense AI", version="0.1.0", description="Uno/BioAmp/MPU-6050 grip-analysis project. Current runtime is educational simulation; live acquisition, recording and replay are planned.")


@app.get("/api/project")
def project():
    return PROJECT


@app.get("/api/project/report")
def project_report():
    path = ROOT / PROJECT["report"]
    if not path.is_file():
        raise HTTPException(404, "Revised project report is not installed")
    return FileResponse(path, media_type="application/pdf")


@app.get("/api/health")
def health():
    return {"status": "ok", "data_source": "synthetic", "version": "0.1.0", "capabilities": PROJECT["capabilities"]}


@app.get("/api/config")
def config():
    return {"defaults": SimulationConfig().model_dump(), "schema": SimulationConfig.model_json_schema()}


@app.post("/api/analog/analyze")
def analog_analysis(c: SimulationConfig):
    return analog.analyze(c)


@app.post("/api/analog/spice")
def spice_analysis(c: SimulationConfig):
    return spice.run(c)


@app.post("/api/simulation/imu")
def imu(c: SimulationConfig):
    return simulation.imu(c)


@app.post("/api/simulation/ppg")
def ppg(c: SimulationConfig):
    return simulation.ppg(c)


@app.post("/api/simulation/emg", response_model=AnalysisResponse)
@app.post("/api/simulation/multimodal", response_model=AnalysisResponse)
@app.post("/api/dsp/analyze", response_model=AnalysisResponse)
def run(c: SimulationConfig):
    t, clean, raw = simulation.emg(c)
    chain = analog.condition(raw, c)
    referred = (chain["adc_v"] - analog.VREF)/(analog.INA_GAIN*c.post_gain)
    warnings = ["SIMULATED DATA: illustrative model; no physiological or clinical validation.", "Analog model assumes valid input common mode and ideal input protection; not manufacturer-model SPICE.", PROJECT["educational_model"]]
    if chain["ina_clipped_samples"] or chain["clipped_samples"]:
        warnings.append("Clipping detected: reduce gain, electrode offset, or input amplitude.")
    result = {"config": c.model_dump(), "provenance": {"source": "synthetic", "seed": c.seed, "emg_unit": "V", "samples": len(t), "time_origin_s": 0, "synchronized": "independent modalities sharing trial time origin"}, "emg": {"time_s": t.tolist(), "clean_v": clean.tolist(), "raw_v": raw.tolist(), "input_referred_v": referred.tolist(), **{k: v.tolist() if hasattr(v, "tolist") else v for k, v in chain.items()}}, "analog": analog.analyze(c), "dsp": dsp.analyze(referred, c.sample_rate_hz), "imu": simulation.imu(c), "ppg": simulation.ppg(c), "warnings": warnings}
    result["provenance"].update({"project_scope": PROJECT["scope"], "model_context": PROJECT["educational_model"], "live_acquisition": "planned"})
    return result


@app.post("/api/ml/train")
def train(request: TrainingRequest):
    if not ml.LOCK.acquire(blocking=False):
        raise HTTPException(409, "Training already running")
    try:
        return ml.train(request.seed, request.trials_per_class)
    finally:
        ml.LOCK.release()


@app.get("/api/ml/metrics")
def model_metrics():
    if ml.METRICS is None:
        raise HTTPException(409, "Train models in this server session first")
    return ml.METRICS


@app.post("/api/ml/predict")
def predict(request: PredictionRequest):
    if request.model not in ml.MODELS:
        raise HTTPException(409, "Train models in this server session first")
    return ml.predict(ml.feature_trial(request.config), request.model)
