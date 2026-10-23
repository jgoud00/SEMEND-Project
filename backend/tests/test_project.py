from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_project_contract_preserves_unknown_measurements_and_contiguous_task():
    project = client.get('/api/project').json()
    assert [item['name'] for item in project['hardware']] == [
        'Arduino Uno', 'BioAmp EXG Pill', 'MPU-6050', 'Hand gripper'
    ]
    assert all(value is None for value in project['measured_channels'].values())
    assert project['acquisition']['adc_bits'] is None
    assert project['capabilities']['live_acquisition'] == 'planned'
    phases = project['task_protocol']
    assert phases[0]['start_s'] == 0
    assert phases[-1]['end_s'] == 35
    assert sum(phase['phase'] == 'Squeeze' for phase in phases) == 3
    assert all(a['end_s'] == b['start_s'] for a, b in zip(phases, phases[1:]))
    assert client.get('/api/health').json()['data_source'] == 'synthetic'
    result = client.post('/api/simulation/multimodal', json={}).json()
    assert result['provenance']['live_acquisition'] == 'planned'
    assert 'not BioAmp/Uno calibration' in result['provenance']['model_context']


def test_report_is_served_and_missing_report_is_explicit(monkeypatch, tmp_path):
    response = client.get('/api/project/report')
    assert response.status_code == 200
    assert response.headers['content-type'] == 'application/pdf'
    assert response.content.startswith(b'%PDF-')
    monkeypatch.setattr('app.main.ROOT', tmp_path)
    assert client.get('/api/project/report').status_code == 404
