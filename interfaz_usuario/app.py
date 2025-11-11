"""Aplicacion web para interactuar con el simulador de la celda H.

Requisitos:
    pip install -r interfaz_usuario/requirements.txt

Ejecucion:
    python interfaz_usuario/app.py
"""

from __future__ import annotations

from dataclasses import replace
from typing import List, Tuple

import dash
import dash_bootstrap_components as dbc
import numpy as np
from dash import Dash, Input, Output, State, dcc, html

import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from simulador import data, simulation


def _build_config(temperature: float, pH: float) -> simulation.ElectrolyzerSimulator:
    """Crea un simulador con las condiciones indicadas (temperatura en Kelvin)."""

    conditions = replace(data.DEFAULT_CONFIG.conditions, temperature=temperature, pH=pH)
    config = replace(data.DEFAULT_CONFIG, conditions=conditions)
    return simulation.ElectrolyzerSimulator(config)


def _polarization(
    sim: simulation.ElectrolyzerSimulator,
    current_range: Tuple[float, float],
    num_points: int,
) -> Tuple[np.ndarray, List[float]]:
    currents = np.linspace(current_range[0], current_range[1], num_points)
    voltages = np.array(sim.polarization_curve(currents))
    return currents, voltages.tolist()


def _activity_profile(
    catalyst_name: str, temperature: float, pH: float, potentials: np.ndarray
) -> List[float]:
    analyzer = simulation.CatalystAnalyzer(
        catalyst=data.CATALYSTS[catalyst_name], temperature=temperature, pH=pH
    )
    return analyzer.activity_profile(potentials.tolist())


def _blank_figure(x_title: str, y_title: str, message: str) -> dict:
    return {
        "data": [],
        "layout": {
            "xaxis": {"title": x_title},
            "yaxis": {"title": y_title},
            "template": "plotly_white",
            "margin": {"l": 50, "r": 10, "t": 10, "b": 40},
            "annotations": [
                {
                    "text": message,
                    "xref": "paper",
                    "yref": "paper",
                    "showarrow": False,
                    "font": {"color": "#888"},
                }
            ],
        },
    }


CATALYST_OPTIONS = [
    {"label": data.CATALYSTS[name].name, "value": name} for name in data.CATALYSTS
]

app: Dash = dash.Dash(
    __name__,
    title="Simulador Celda H",
    external_stylesheets=[dbc.themes.SANDSTONE],
    suppress_callback_exceptions=True,
)


def _hero_section() -> dbc.Container:
    return dbc.Container(
        [
            html.H1("Simulador interactivo de celda H", className="display-5"),
            html.P(
                "Explora la curva de polarizacion y la actividad catalitica derivadas del nucleo "
                "teorico basado en DFT. Ajusta condiciones y catalizadores para obtener de inmediato "
                "nuevos estimados de desempeño.",
                className="lead",
            ),
        ],
        className="py-4",
    )


def _control_panel() -> dbc.Card:
    return dbc.Card(
        dbc.CardBody(
            [
                html.H5("Condiciones de operacion", className="card-title"),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Temperatura (K)"),
                                dcc.Slider(
                                    id="temperature-slider",
                                    min=313,
                                    max=373,
                                    step=1,
                                    value=353,
                                    marks=None,
                                    tooltip={"placement": "bottom"},
                                ),
                                html.Div(id="temperature-display", className="slider-value"),
                            ],
                            md=6,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("pH"),
                                dcc.Slider(
                                    id="ph-slider",
                                    min=0,
                                    max=14,
                                    step=0.1,
                                    value=0.0,
                                    marks={0: "0", 7: "7", 14: "14"},
                                    tooltip={"placement": "bottom"},
                                ),
                                html.Div(id="ph-display", className="slider-value"),
                            ],
                            md=6,
                        ),
                    ],
                    className="gy-3",
                ),
                html.Hr(),
                html.H5("Configuracion de corriente"),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Corriente minima (A/cm^2)"),
                                dbc.Input(id="current-min", type="number", value=0.2, step=0.1, min=0.01),
                            ],
                            md=4,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Corriente maxima (A/cm^2)"),
                                dbc.Input(id="current-max", type="number", value=2.0, step=0.1, min=0.2),
                            ],
                            md=4,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Muestras en curva"),
                                dcc.Slider(
                                    id="samples-slider",
                                    min=10,
                                    max=60,
                                    step=5,
                                    value=30,
                                    tooltip={"placement": "bottom"},
                                ),
                                html.Div(id="samples-display", className="slider-value"),
                            ],
                            md=4,
                        ),
                    ],
                    className="gy-3",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Corriente para desglose (A/cm^2)"),
                                dbc.Input(id="focus-current", type="number", value=1.0, step=0.1, min=0.1),
                            ],
                            md=6,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Catalizador"),
                                dcc.Dropdown(
                                    id="catalyst-dropdown",
                                    options=CATALYST_OPTIONS,
                                    value="Pt",
                                    clearable=False,
                                ),
                            ],
                            md=6,
                        ),
                    ],
                    className="gy-3",
                ),
            ]
        ),
        className="shadow-sm",
    )


def _cards_section() -> dbc.Row:
    cards = [
        dbc.Col(dbc.Card([dbc.CardHeader("Voltaje ideal"), html.H3(id="card-videal")]), md=3),
        dbc.Col(dbc.Card([dbc.CardHeader("Perdida activacion"), html.H3(id="card-eta-act")]), md=3),
        dbc.Col(dbc.Card([dbc.CardHeader("Perdida ohmica"), html.H3(id="card-eta-ohm")]), md=3),
        dbc.Col(dbc.Card([dbc.CardHeader("Perdida concentracion"), html.H3(id="card-eta-conc")]), md=3),
    ]
    return dbc.Row(cards, className="gy-3")


def _graphs_section() -> dbc.Row:
    return dbc.Row(
        [
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader("Curva de polarizacion"),
                        dcc.Graph(id="polarization-graph"),
                    ]
                ),
                md=7,
            ),
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader("Actividad catalitica"),
                        dcc.Graph(id="activity-graph"),
                    ]
                ),
                md=5,
            ),
        ],
        className="gy-3",
    )


app.layout = dbc.Container(
    [
        _hero_section(),
        dbc.Row(
            [
                dbc.Col(_control_panel(), md=5),
                dbc.Col(
                    [
                        html.Div(id="alert-placeholder"),
                        _cards_section(),
                        html.Div(className="my-3"),
                        _graphs_section(),
                    ],
                    md=7,
                ),
            ],
            className="gy-4",
        ),
    ],
    fluid=True,
    className="pb-4",
)


@app.callback(
    Output("temperature-display", "children"),
    Input("temperature-slider", "value"),
)
def update_temperature_display(value: float) -> str:
    return f"{value:.1f} K"


@app.callback(Output("ph-display", "children"), Input("ph-slider", "value"))
def update_ph_display(value: float) -> str:
    return f"pH {value:.1f}"


@app.callback(Output("samples-display", "children"), Input("samples-slider", "value"))
def update_samples_display(value: int) -> str:
    return f"{value} puntos"


@app.callback(
    [
        Output("polarization-graph", "figure"),
        Output("activity-graph", "figure"),
        Output("card-videal", "children"),
        Output("card-eta-act", "children"),
        Output("card-eta-ohm", "children"),
        Output("card-eta-conc", "children"),
        Output("alert-placeholder", "children"),
    ],
    [
        Input("temperature-slider", "value"),
        Input("ph-slider", "value"),
        Input("current-min", "value"),
        Input("current-max", "value"),
        Input("samples-slider", "value"),
        Input("focus-current", "value"),
        Input("catalyst-dropdown", "value"),
    ],
)
def update_outputs(
    temperature: float,
    pH: float,
    current_min: float,
    current_max: float,
    samples: int,
    focus_current: float,
    catalyst: str,
):
    error = None
    if current_min is None or current_max is None or focus_current is None:
        error = "Completa los valores de corriente para generar la simulacion."
    elif current_min <= 0 or current_max <= 0:
        error = "Las corrientes deben ser mayores que cero."
    elif current_min >= current_max:
        error = "La corriente minima debe ser menor que la maxima."
    elif focus_current <= 0:
        error = "La corriente de referencia debe ser mayor que cero."

    if error:
        alert = dbc.Alert(error, color="danger", dismissable=True)
        placeholder = (
            _blank_figure("Corriente (A/cm^2)", "Voltaje (V)", "Ajusta los valores para simular."),
            _blank_figure("Potencial (V vs SHE)", "Actividad relativa", "Ajusta los valores para simular."),
            "--",
            "--",
            "--",
            "--",
            alert,
        )
        return placeholder

    sim = _build_config(temperature, pH)
    currents, voltages = _polarization(sim, (current_min, current_max), samples)

    breakdown = sim.voltage_breakdown(focus_current)
    cards = (
        f"{breakdown['V_ideal']:.3f} V",
        f"{breakdown['eta_activacion']:.3f} V",
        f"{breakdown['eta_ohmico']:.3f} V",
        f"{breakdown['eta_concentracion']:.3f} V",
    )

    pol_fig = {
        "data": [
            {
                "x": currents.tolist(),
                "y": voltages,
                "mode": "lines+markers",
                "name": "V celda",
                "line": {"color": "#006D77", "width": 3},
            }
        ],
        "layout": {
            "xaxis": {"title": "Corriente (A/cm^2)"},
            "yaxis": {"title": "Voltaje (V)"},
            "template": "plotly_white",
            "margin": {"l": 40, "r": 10, "t": 10, "b": 40},
        },
    }

    potentials = np.linspace(0.6, 1.3, 60)
    activities = _activity_profile(catalyst, temperature, pH, potentials)
    act_fig = {
        "data": [
            {
                "x": potentials.tolist(),
                "y": activities,
                "mode": "lines",
                "line": {"color": "#FF8C42", "width": 3},
                "fill": "tozeroy",
            }
        ],
        "layout": {
            "xaxis": {"title": "Potencial (V vs SHE)"},
            "yaxis": {"title": "Actividad relativa", "type": "log", "rangemode": "tozero"},
            "template": "plotly_white",
            "margin": {"l": 50, "r": 10, "t": 10, "b": 40},
        },
    }

    return pol_fig, act_fig, *cards, None


if __name__ == "__main__":
    app.run_server(debug=True)
