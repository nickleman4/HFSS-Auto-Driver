import numpy as np
import sys
import types

from src import hfss_driver


class FakeReport:
    def __init__(self, real, imag=0.0, primary_sweep_values=None, data_calls=None):
        self._real = real
        self._imag = imag
        self.primary_sweep_values = primary_sweep_values or [3.0]
        self.data_calls = data_calls

    def data_real(self, **kwargs):
        if self.data_calls is not None:
            self.data_calls.append(("real", kwargs))
        if isinstance(self._real, list):
            return self._real
        return [self._real]

    def data_imag(self, **kwargs):
        if self.data_calls is not None:
            self.data_calls.append(("imag", kwargs))
        if isinstance(self._imag, list):
            return self._imag
        return [self._imag]


class FakePost:
    def __init__(self):
        self.calls = []
        self.data_calls = []

    def get_solution_data(self, **kwargs):
        self.calls.append(kwargs)
        expression = kwargs["expressions"]
        if expression == "dB(S(1,1))":
            return FakeReport(
                [-9.5, -12.25],
                primary_sweep_values=[2.0, 2.1],
                data_calls=self.data_calls,
            )
        variations = kwargs["variations"]
        theta = variations["Theta"][0]
        phi = variations["Phi"][0]
        if expression == "rEPhi" and theta == "0deg" and phi == "0deg":
            return FakeReport(1.0, 2.0, data_calls=self.data_calls)
        if expression == "rETheta" and theta == "0deg" and phi == "0deg":
            return FakeReport(3.0, 4.0, data_calls=self.data_calls)
        return FakeReport(5.0, 6.0, data_calls=self.data_calls)


class FakeHfss:
    def __init__(self):
        self.assigned = {}
        self.analyzed = []
        self.post = FakePost()

    def __setitem__(self, name, value):
        self.assigned[name] = value

    def analyze_setup(self, setup_name):
        self.analyzed.append(setup_name)


def test_run_farfield_simulation_sets_variables_solves_and_returns_rows(monkeypatch):
    fake_hfss = FakeHfss()
    monkeypatch.setattr(hfss_driver, "hfss_app", fake_hfss)

    result = hfss_driver.run_farfield_simulation(
        x=np.array([6.0, 1.0]),
        var_names=["ld", "wd"],
        simulation_config={"setup_name": "Setup1", "sweep_name": "Sweep", "variable_unit": "mm"},
        farfield_config={
            "sphere_name": "3D",
            "frequencies": ["3GHz"],
            "theta": {"start": 0, "stop": 0, "step": 1},
            "phi": {"start": 0, "stop": 0, "step": 1},
            "components": ["rEPhi", "rETheta"],
            "parts": ["real", "imag"],
        },
    )

    assert result["status"] == "success"
    assert fake_hfss.assigned == {"ld": "6.0mm", "wd": "1.0mm"}
    assert fake_hfss.analyzed == ["Setup1"]
    assert result["rows"] == [
        {
            "freq": "3GHz",
            "theta": 0.0,
            "phi": 0.0,
            "rEPhi_re": 1.0,
            "rEPhi_im": 2.0,
            "rETheta_re": 3.0,
            "rETheta_im": 4.0,
        }
    ]
    assert fake_hfss.post.calls[0]["setup_sweep_name"] == "Setup1 : Sweep"
    assert fake_hfss.post.calls[0]["report_category"] == "Far Fields"
    assert fake_hfss.post.calls[0]["context"] == "3D"
    assert fake_hfss.post.data_calls[0] == ("real", {"convert_to_SI": False})
    assert fake_hfss.post.data_calls[1] == ("imag", {"convert_to_SI": False})


def test_run_farfield_simulation_passes_convert_to_si_true_to_report(monkeypatch):
    fake_hfss = FakeHfss()
    monkeypatch.setattr(hfss_driver, "hfss_app", fake_hfss)

    result = hfss_driver.run_farfield_simulation(
        x=np.array([6.0]),
        var_names=["ld"],
        simulation_config={"setup_name": "Setup1", "sweep_name": "Sweep", "variable_unit": "mm"},
        farfield_config={
            "sphere_name": "3D",
            "frequencies": ["3GHz"],
            "theta": {"start": 0, "stop": 0, "step": 1},
            "phi": {"start": 0, "stop": 0, "step": 1},
            "components": ["rEPhi"],
            "parts": ["real", "imag"],
            "convert_to_si": True,
        },
    )

    assert result["status"] == "success"
    assert fake_hfss.post.data_calls == [
        ("real", {"convert_to_SI": True}),
        ("imag", {"convert_to_SI": True}),
    ]


def test_run_farfield_simulation_passes_convert_to_si_false_to_report(monkeypatch):
    fake_hfss = FakeHfss()
    monkeypatch.setattr(hfss_driver, "hfss_app", fake_hfss)

    result = hfss_driver.run_farfield_simulation(
        x=np.array([6.0]),
        var_names=["ld"],
        simulation_config={"setup_name": "Setup1", "sweep_name": "Sweep", "variable_unit": "mm"},
        farfield_config={
            "sphere_name": "3D",
            "frequencies": ["3GHz"],
            "theta": {"start": 0, "stop": 0, "step": 1},
            "phi": {"start": 0, "stop": 0, "step": 1},
            "components": ["rEPhi"],
            "parts": ["real", "imag"],
            "convert_to_si": False,
        },
    )

    assert result["status"] == "success"
    assert fake_hfss.post.data_calls == [
        ("real", {"convert_to_SI": False}),
        ("imag", {"convert_to_SI": False}),
    ]


def test_run_farfield_simulation_returns_s11_rows_separately_when_enabled(monkeypatch):
    fake_hfss = FakeHfss()
    monkeypatch.setattr(hfss_driver, "hfss_app", fake_hfss)

    result = hfss_driver.run_farfield_simulation(
        x=np.array([6.0]),
        var_names=["ld"],
        simulation_config={"setup_name": "Setup1", "sweep_name": "Sweep", "variable_unit": "mm"},
        farfield_config={
            "sphere_name": "3D",
            "frequencies": ["2.1GHz"],
            "theta": {"start": 0, "stop": 0, "step": 1},
            "phi": {"start": 0, "stop": 0, "step": 1},
            "components": ["rEPhi"],
            "parts": ["real"],
        },
        s11_config={"enabled": True},
    )

    assert result["status"] == "success"
    assert result["rows"] == [
        {
            "freq": "2.1GHz",
            "theta": 0.0,
            "phi": 0.0,
            "rEPhi_re": 1.0,
        }
    ]
    assert result["s11_rows"] == [{"freq": "2.1GHz", "s11_db": -12.25}]
    assert fake_hfss.post.calls[0]["expressions"] == "dB(S(1,1))"
    assert fake_hfss.post.calls[1]["report_category"] == "Far Fields"


def test_run_farfield_simulation_reports_failure_without_zero_penalty(monkeypatch):
    fake_hfss = FakeHfss()
    fake_hfss.post.get_solution_data = lambda **kwargs: None
    monkeypatch.setattr(hfss_driver, "hfss_app", fake_hfss)

    result = hfss_driver.run_farfield_simulation(
        x=np.array([7.1]),
        var_names=["ld"],
        simulation_config={"setup_name": "Setup1", "sweep_name": "Sweep", "variable_unit": "mm"},
        farfield_config={
            "sphere_name": "3D",
            "frequencies": ["3GHz"],
            "theta": {"start": 0, "stop": 0, "step": 1},
            "phi": {"start": 0, "stop": 0, "step": 1},
            "components": ["rEPhi"],
            "parts": ["real"],
        },
    )

    assert result["status"] == "failed"
    assert result["rows"] == []
    assert "No far-field data" in result["error_message"]


def test_init_hfss_passes_design_name_to_pyaedt(monkeypatch):
    calls = []

    class FakeDesktop:
        def GetProcessID(self):
            return 12345

    class FakePyaedtModule:
        @staticmethod
        def Hfss(**kwargs):
            calls.append(kwargs)
            return types.SimpleNamespace(odesktop=FakeDesktop())

    monkeypatch.setitem(sys.modules, "pyaedt", FakePyaedtModule)

    hfss_driver.init_hfss("E:/model.aedt", design_name="Opti_Result1", version="2023.1")

    assert calls == [
        {
            "projectname": "E:/model.aedt",
            "designname": "Opti_Result1",
            "specified_version": "2023.1",
            "non_graphical": True,
            "new_desktop_session": True,
        }
    ]
    monkeypatch.setattr(hfss_driver, "hfss_app", None)
