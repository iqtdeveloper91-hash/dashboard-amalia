import warnings
from pathlib import Path

import dash
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html
from dash.dependencies import Input, Output

warnings.filterwarnings("ignore")

BASE_COLS = [
    "alumno_id",
    "grado_seccion",
    "grado",
    "seccion",
    "nombre_alumno",
]
BIMESTRE_FILES = {
    "II": "DASHBOARD_II_BIMESTRE.xlsx",
    "III": "DASHBOARD_III_BIMESTRE.xlsx",
}


def resolver_path(nombre_archivo: str) -> Path:
    return Path(__file__).resolve().parent / nombre_archivo


def cargar_bimestre(nombre_archivo: str) -> dict:
    path = resolver_path(nombre_archivo)
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {nombre_archivo}")

    raw = pd.read_excel(path, sheet_name="DATA", header=None)
    curso_row = raw.iloc[1]

    # La fila 3 (índice 3) contiene los encabezados reales
    df = pd.read_excel(path, sheet_name="DATA", header=3)
    df = df.rename(
        columns={
            "nro": "alumno_id",
            "GRADO/SECCION": "grado_seccion",
            "GRADO": "grado",
            "SECCION": "seccion",
            "APELLIDOS Y NOMBRES": "nombre_alumno",
        }
    )

    df = df.dropna(subset=["alumno_id"])
    df["alumno_id"] = pd.to_numeric(df["alumno_id"], errors="coerce")
    df = df.dropna(subset=["alumno_id"])
    df["alumno_id"] = df["alumno_id"].astype(int)
    df["grado"] = df["grado"].astype(str).str.strip()
    df["seccion"] = df["seccion"].astype(str).str.strip()
    df["nombre_alumno"] = df["nombre_alumno"].astype(str).str.strip()

    cols = [c for c in df.columns if c in BASE_COLS] + [c for c in df.columns if c not in BASE_COLS]
    df = df[cols]
    compet_cols = [c for c in df.columns if c not in BASE_COLS]

    mapeo_columnas = {}
    for idx, col in enumerate(df.columns):
        if col in BASE_COLS:
            continue
        curso = str(curso_row[idx]).strip() if pd.notna(curso_row[idx]) else "Sin curso"
        mapeo_columnas[idx] = {"curso": curso, "competencia": str(col).strip()}

    comp_to_curso = {info["competencia"]: info["curso"] for info in mapeo_columnas.values()}

    df_long = df.melt(
        id_vars=["grado", "seccion", "alumno_id", "nombre_alumno"],
        value_vars=compet_cols,
        var_name="Competencia",
        value_name="Nivel",
    )
    df_long["Curso"] = df_long["Competencia"].map(comp_to_curso)
    df_long["Nivel"] = df_long["Nivel"].astype(str).str.strip()
    df_long = df_long[df_long["Nivel"].notna() & (df_long["Nivel"] != "nan") & (df_long["Nivel"] != "")]
    df_long = df_long[df_long["Nivel"] != "-"]
    df_long["Grado"] = df_long["grado"]
    df_long["Seccion"] = df_long["seccion"]

    def agg(campos):
        tabla = df_long.groupby(campos + ["Nivel"]).size().reset_index(name="Cantidad")
        tabla["Total"] = tabla.groupby(campos)["Cantidad"].transform("sum")
        tabla["Porcentaje"] = (tabla["Cantidad"] / tabla["Total"] * 100).round(1)
        return tabla.drop(columns="Total")

    df_secundaria_comp = agg(["Competencia"])
    df_curso_comp = agg(["Curso", "Competencia"])
    df_curso_comp_grado = agg(["Grado", "Curso", "Competencia"])
    df_seccion_comp = agg(["Seccion", "Curso", "Competencia"])
    df_grado_comp = agg(["Grado", "Competencia"])
    df_seccion_comp_simple = agg(["Seccion", "Competencia"])

    total_evaluaciones = len(df_long)
    total_cursos = df_long["Curso"].nunique()
    total_competencias = df_long["Competencia"].nunique()
    total_grados = df["grado"].nunique()
    total_secciones = df["seccion"].nunique()
    nivel_counts = df_long["Nivel"].value_counts().to_dict()

    context = {
        "df_data": df,
        "df_secundaria_comp": df_secundaria_comp,
        "df_curso_comp": df_curso_comp,
        "df_curso_comp_grado": df_curso_comp_grado,
        "df_seccion_comp": df_seccion_comp,
        "df_grado_comp": df_grado_comp,
        "df_seccion_comp_simple": df_seccion_comp_simple,
        "df_estadisticas": df.rename(columns={"grado": "Grado", "seccion": "Seccion"}),
        "mapeo_columnas": mapeo_columnas,
        "total_evaluaciones": total_evaluaciones,
        "total_cursos": total_cursos,
        "total_competencias": total_competencias,
        "total_grados": total_grados,
        "total_secciones": total_secciones,
        "nivel_counts": nivel_counts,
    }
    return context


CONTEXTOS_BIMESTRE = {}
for clave, archivo in BIMESTRE_FILES.items():
    try:
        CONTEXTOS_BIMESTRE[clave] = cargar_bimestre(archivo)
    except FileNotFoundError:
        continue

if not CONTEXTOS_BIMESTRE:
    raise RuntimeError("No hay archivos de bimestre disponibles")

DEFAULT_BIMESTRE = "III" if "III" in CONTEXTOS_BIMESTRE else next(iter(CONTEXTOS_BIMESTRE))


def ctx_bimestre(bimestre: str) -> dict:
    return CONTEXTOS_BIMESTRE.get(bimestre, CONTEXTOS_BIMESTRE[DEFAULT_BIMESTRE])


ctx_base = ctx_bimestre(DEFAULT_BIMESTRE)

app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# Valores iniciales
cursos_base = sorted(ctx_base["df_curso_comp"]["Curso"].unique())
curso_default = cursos_base[0] if cursos_base else None
competencias_sec = sorted(ctx_base["df_secundaria_comp"]["Competencia"].unique())
comp_sec_default = competencias_sec[0] if competencias_sec else None
grado_base = sorted(ctx_base["df_curso_comp_grado"]["Grado"].unique())
seccion_base = sorted(ctx_base["df_seccion_comp"]["Seccion"].unique())
comp_grado_base = sorted(ctx_base["df_grado_comp"]["Competencia"].unique())
comp_seccion_base = sorted(ctx_base["df_seccion_comp_simple"]["Competencia"].unique())
alumno_grados = sorted(ctx_base["df_estadisticas"]["Grado"].unique())

app.layout = html.Div(
    [
        html.Div(
            [
                html.Div(html.Img(src="/assets/logo.png", style={"height": "80px", "marginRight": "20px"}),
                         style={"display": "inline-block", "verticalAlign": "middle"}),
                html.Div(
                    [
                        html.H1(
                            "I.E. Amalia del Águila Velásquez",
                            style={"margin": "0", "color": "#2c3e50", "fontWeight": "bold", "fontSize": "32px"},
                        ),
                        html.H2(
                            f"Dashboard Académico - {DEFAULT_BIMESTRE} Bimestre",
                            id="titulo-bimestre",
                            style={"margin": "5px 0 0 0", "color": "#7f8c8d", "fontWeight": "normal", "fontSize": "24px"},
                        ),
                    ],
                    style={"display": "inline-block", "verticalAlign": "middle"},
                ),
                html.Div(
                    [
                        html.Label("Bimestre", style={"color": "#ffffff", "fontWeight": "bold", "marginRight": "10px"}),
                        dcc.Dropdown(
                            id="bimestre-select",
                            options=[{"label": f"Bimestre {k}", "value": k} for k in sorted(CONTEXTOS_BIMESTRE.keys())],
                            value=DEFAULT_BIMESTRE,
                            clearable=False,
                            style={"minWidth": "200px", "color": "#000"},
                        ),
                    ],
                    style={"display": "inline-block", "verticalAlign": "middle", "marginLeft": "20px", "color": "white", "width": "220px"},
                ),
            ],
            style={
                "textAlign": "center",
                "marginBottom": 30,
                "padding": "20px",
                "backgroundColor": "white",
                "borderRadius": "10px",
                "boxShadow": "0 4px 6px rgba(0,0,0,0.1)",
            },
        ),
        html.Div(id="metricas-dinamicas", style={"display": "flex", "flexWrap": "wrap", "marginBottom": 30, "gap": "10px"}),
        dcc.Tabs(
            id="tabs-principal",
            value="tab-secundaria",
            children=[
                dcc.Tab(
                    label="📚 1. Nivel Secundaria",
                    value="tab-secundaria",
                    children=
                    html.Div([
                        html.H2("Desempeño por Competencia", style={"color": "#2c3e50", "marginTop": 20}),
                        html.Div([
                            html.Label("Competencia", style={"fontWeight": "bold"}),
                            dcc.Dropdown(id="competencia-secundaria", options=[{"label": c, "value": c} for c in competencias_sec], value=comp_sec_default),
                        ], style={"marginBottom": 20}),
                        html.Div(id="grafico-secundaria"),
                        html.Hr(),
                        html.H2("Porcentaje por Curso y Competencia", style={"color": "#2c3e50", "marginTop": 20}),
                        html.Div([
                            html.Div([
                                html.Label("Curso", style={"fontWeight": "bold"}),
                                dcc.Dropdown(id="curso-select", options=[{"label": c, "value": c} for c in cursos_base], value=curso_default),
                            ], style={"width": "48%", "display": "inline-block"}),
                            html.Div([
                                html.Label("Competencia", style={"fontWeight": "bold"}),
                                dcc.Dropdown(id="competencia-curso-select"),
                            ], style={"width": "48%", "display": "inline-block", "marginLeft": "4%"}),
                        ]),
                        html.Div(id="grafico-curso", style={"marginTop": 20}),
                    ], style={"padding": 20}),
                ),
                dcc.Tab(
                    label="🎓 2. Por Curso",
                    value="tab-curso",
                    children=
                    html.Div([
                        html.H2("Porcentaje por Grado, Curso y Competencia", style={"color": "#2c3e50", "marginTop": 20}),
                        html.Div([
                            html.Div([
                                html.Label("Grado", style={"fontWeight": "bold"}),
                                dcc.Dropdown(id="filtro-curso-grado", options=[{"label": g, "value": g} for g in grado_base], value=grado_base[0] if grado_base else None),
                            ], style={"width": "32%", "display": "inline-block"}),
                            html.Div([
                                html.Label("Curso", style={"fontWeight": "bold"}),
                                dcc.Dropdown(id="filtro-curso-curso"),
                            ], style={"width": "32%", "display": "inline-block", "marginLeft": "2%"}),
                            html.Div([
                                html.Label("Competencia", style={"fontWeight": "bold"}),
                                dcc.Dropdown(id="filtro-curso-competencia"),
                            ], style={"width": "32%", "display": "inline-block", "marginLeft": "2%"}),
                        ]),
                        html.Div(id="grafico-curso-grado", style={"marginTop": 20}),
                        html.Hr(style={"margin": "40px 0"}),
                        html.H2("Comparación entre Grados", style={"color": "#2c3e50"}),
                        html.Div([
                            html.Label("Seleccionar Competencia", style={"fontWeight": "bold"}),
                            dcc.Dropdown(id="competencia-comparacion-grado", options=[{"label": c, "value": c} for c in comp_grado_base], value=comp_grado_base[0] if comp_grado_base else None, style={"marginBottom": 20}),
                        ]),
                        html.Div(id="grafico-comparacion-grados"),
                    ], style={"padding": 20}),
                ),
                dcc.Tab(
                    label="👥 3. Por Sección",
                    value="tab-seccion",
                    children=
                    html.Div([
                        html.H2("Porcentaje por Sección, Curso y Competencia", style={"color": "#2c3e50", "marginTop": 20}),
                        html.Div([
                            html.Div([
                                html.Label("Sección", style={"fontWeight": "bold"}),
                                dcc.Dropdown(id="filtro-seccion-seccion", options=[{"label": s, "value": s} for s in seccion_base], value=seccion_base[0] if seccion_base else None),
                            ], style={"width": "32%", "display": "inline-block"}),
                            html.Div([
                                html.Label("Curso", style={"fontWeight": "bold"}),
                                dcc.Dropdown(id="filtro-seccion-curso"),
                            ], style={"width": "32%", "display": "inline-block", "marginLeft": "2%"}),
                            html.Div([
                                html.Label("Competencia", style={"fontWeight": "bold"}),
                                dcc.Dropdown(id="filtro-seccion-competencia"),
                            ], style={"width": "32%", "display": "inline-block", "marginLeft": "2%"}),
                        ]),
                        html.Div(id="grafico-seccion-filtros", style={"marginTop": 20}),
                        html.Hr(style={"margin": "40px 0"}),
                        html.H2("Comparación entre Secciones", style={"color": "#2c3e50"}),
                        html.Div([
                            html.Label("Seleccionar Competencia", style={"fontWeight": "bold"}),
                            dcc.Dropdown(id="competencia-comparacion-seccion", options=[{"label": c, "value": c} for c in comp_seccion_base], value=comp_seccion_base[0] if comp_seccion_base else None, style={"marginBottom": 20}),
                        ]),
                        html.Div(id="grafico-comparacion-secciones"),
                        html.Hr(style={"margin": "40px 0"}),
                        html.H2("Detalle por Sección", style={"color": "#2c3e50"}),
                        html.Div([
                            html.Div([
                                html.Label("Sección", style={"fontWeight": "bold"}),
                                dcc.Dropdown(id="seccion-select", options=[{"label": s, "value": s} for s in seccion_base], value=seccion_base[0] if seccion_base else None),
                            ], style={"width": "48%", "display": "inline-block"}),
                            html.Div([
                                html.Label("Competencia", style={"fontWeight": "bold"}),
                                dcc.Dropdown(id="competencia-seccion-select"),
                            ], style={"width": "48%", "display": "inline-block", "marginLeft": "4%"}),
                        ]),
                        html.Div(id="grafico-seccion", style={"marginTop": 20}),
                    ], style={"padding": 20}),
                ),
                dcc.Tab(
                    label="👤 4. Por Alumno",
                    value="tab-alumno",
                    children=
                    html.Div([
                        html.H2("Listado de Alumnos", style={"color": "#2c3e50", "marginTop": 20}),
                        html.P("Seleccione Grado, Sección y Curso para ver el listado de estudiantes y sus calificaciones", style={"color": "#7f8c8d", "marginBottom": 20}),
                        html.Div([
                            html.Div([
                                html.Label("Grado", style={"fontWeight": "bold"}),
                                dcc.Dropdown(id="alumno-grado-select", options=[{"label": g, "value": g} for g in alumno_grados], value=alumno_grados[0] if alumno_grados else None),
                            ], style={"width": "31%", "display": "inline-block"}),
                            html.Div([
                                html.Label("Sección", style={"fontWeight": "bold"}),
                                dcc.Dropdown(id="alumno-seccion-select"),
                            ], style={"width": "31%", "display": "inline-block", "marginLeft": "3%"}),
                            html.Div([
                                html.Label("Curso", style={"fontWeight": "bold"}),
                                dcc.Dropdown(id="alumno-curso-select"),
                            ], style={"width": "31%", "display": "inline-block", "marginLeft": "3%"}),
                        ]),
                        html.Div(id="tabla-alumnos", style={"marginTop": 30}),
                    ], style={"padding": 20}),
                ),
            ],
        ),
    ],
    style={"padding": 30, "fontFamily": "Arial, sans-serif", "backgroundColor": "#f5f6fa"},
)

app.index_string = """\
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Dashboard Académico - I.E. Amalia del Águila Velásquez</title>
        {%favicon%}
        {%css%}
        <link href=\"https://fonts.googleapis.com/css2?family=Segoe+UI:wght@300;400;500;600;700&display=swap\" rel=\"stylesheet\">
        <link rel=\"stylesheet\" href=\"https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css\"/>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f3f2f1; min-height: 100vh; }
            #react-entry-point > div { background: #ffffff; margin: 0; padding: 0; min-height: 100vh; }
            #react-entry-point > div > div:first-child { background: linear-gradient(90deg, #1f1f1f 0%, #2d2d2d 100%); padding: 15px 30px !important; margin: 0 !important; border-radius: 0 !important; box-shadow: 0 2px 4px rgba(0,0,0,0.2); display: flex; align-items: center; }
            #react-entry-point > div > div:first-child h1, #react-entry-point > div > div:first-child h2 { color: #ffffff !important; background: none !important; -webkit-text-fill-color: #ffffff !important; margin: 0 !important; text-shadow: 0 1px 3px rgba(0,0,0,0.3); }
            .metric-card { text-align: center; padding: 20px; background: #ffffff; border: 1px solid #e1dfdd; border-radius: 2px; flex: 1; min-width: 150px; box-shadow: 0 1.6px 3.6px rgba(0,0,0,0.13), 0 0.3px 0.9px rgba(0,0,0,0.11); transition: all 0.2s ease; position: relative; }
            .metric-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, #00bcf2 0%, #0078d4 100%); }
            .metric-card:hover { transform: translateY(-2px); box-shadow: 0 3.2px 7.2px rgba(0,0,0,0.13), 0 0.6px 1.8px rgba(0,0,0,0.11); }
            .metric-card h3 { color: #605e5c; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
            .metric-card h2 { color: #323130; font-size: 32px; font-weight: 600; margin: 5px 0; }
            .metric-card p { color: #797775; font-size: 13px; }
            ._dash-undo-redo { display: none; }
            .tab { background: transparent !important; border: none !important; border-bottom: 3px solid transparent !important; color: #605e5c !important; padding: 12px 20px !important; margin: 0 !important; transition: all 0.2s ease !important; font-weight: 600 !important; font-size: 14px !important; letter-spacing: 0.3px !important; }
            .tab:hover { background: rgba(0,120,212,0.05) !important; border-bottom: 3px solid #c7e0f4 !important; }
            .tab--selected { background: transparent !important; color: #0078d4 !important; border-bottom: 3px solid #0078d4 !important; }
            div[role='tablist'] { background: #faf9f8; border-bottom: 1px solid #edebe9; padding: 0 20px; }
            .Select-control { border: 1px solid #8a8886 !important; border-radius: 2px !important; background: #ffffff !important; transition: all 0.1s ease !important; font-size: 14px !important; }
            .Select-control:hover { border-color: #323130 !important; }
            .is-focused .Select-control { border-color: #0078d4 !important; box-shadow: 0 0 0 1px #0078d4 !important; }
            .Select-menu-outer { border: 1px solid #0078d4 !important; border-radius: 2px !important; box-shadow: 0 3.2px 7.2px rgba(0,0,0,0.13), 0 0.6px 1.8px rgba(0,0,0,0.11) !important; }
            .Select-option:hover { background-color: #f3f2f1 !important; }
            .Select-option.is-selected { background-color: #0078d4 !important; color: white !important; }
            label { color: #323130; font-size: 14px; font-weight: 600; margin-bottom: 5px; display: block; }
            h2, h3 { color: #323130 !important; font-weight: 600 !important; background: none !important; -webkit-text-fill-color: #323130 !important; letter-spacing: 0.3px; }
            .js-plotly-plot { border: 1px solid #e1dfdd; border-radius: 2px; background: #ffffff; box-shadow: 0 1.6px 3.6px rgba(0,0,0,0.13), 0 0.3px 0.9px rgba(0,0,0,0.11); margin-bottom: 20px; }
            div[role='tabpanel'] > div { padding: 20px 30px; background: #f3f2f1; }
            table { background: white; border: 1px solid #e1dfdd; border-radius: 2px; font-size: 14px; }
            thead th { background: #faf9f8 !important; color: #323130 !important; font-weight: 600 !important; border-bottom: 2px solid #e1dfdd !important; padding: 12px 10px !important; text-align: center !important; }
            tbody td { border-bottom: 1px solid #edebe9; padding: 10px; color: #323130; }
            tbody tr:hover { background: #f3f2f1; }
            hr { border: none; border-top: 1px solid #edebe9; margin: 30px 0; }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""


@app.callback(
    Output("metricas-dinamicas", "children"),
    [Input("tabs-principal", "value"), Input("bimestre-select", "value")],
)
def actualizar_metricas(tab_activa, bimestre):
    ctx = ctx_bimestre(bimestre)
    df_data = ctx["df_data"]
    total_evaluaciones = ctx["total_evaluaciones"]
    total_cursos = ctx["total_cursos"]
    total_competencias = ctx["total_competencias"]
    total_grados = ctx["total_grados"]
    total_secciones = ctx["total_secciones"]
    nivel_counts = ctx["nivel_counts"]
    df_curso_comp_grado = ctx["df_curso_comp_grado"]

    metricas = []

    if tab_activa == "tab-secundaria":
        metricas = [
            html.Div([
                html.H3("👥 Total de Estudiantes", style={"fontSize": "18px", "margin": 0}),
                html.H2(f"{len(df_data):,}", style={"color": "#3498db", "margin": "10px 0"}),
            ], className="metric-card"),
            html.Div([
                html.H3("📝 Total de Evaluaciones", style={"fontSize": "18px", "margin": 0}),
                html.H2(f"{total_evaluaciones:,}", style={"color": "#9b59b6", "margin": "10px 0"}),
            ], className="metric-card"),
            html.Div([
                html.H3("📚 Total de Cursos", style={"fontSize": "18px", "margin": 0}),
                html.H2(f"{total_cursos}", style={"color": "#3498db", "margin": "10px 0"}),
            ], className="metric-card"),
            html.Div([
                html.H3("🎯 Total de Competencias", style={"fontSize": "18px", "margin": 0}),
                html.H2(f"{total_competencias}", style={"color": "#16a085", "margin": "10px 0"}),
            ], className="metric-card"),
        ]
    elif tab_activa == "tab-curso":
        cursos_por_grado = df_curso_comp_grado.groupby("Grado")["Curso"].nunique()
        total_grados_curso = len(cursos_por_grado)
        metricas = [
            html.Div([
                html.H3("🎓 Total de Grados", style={"fontSize": "18px", "margin": 0}),
                html.H2(f"{total_grados_curso}", style={"color": "#3498db", "margin": "10px 0"}),
            ], className="metric-card"),
            html.Div([
                html.H3("📚 Total de Cursos", style={"fontSize": "18px", "margin": 0}),
                html.H2(f"{df_curso_comp_grado['Curso'].nunique()}", style={"color": "#9b59b6", "margin": "10px 0"}),
            ], className="metric-card"),
            html.Div([
                html.H3("🎯 Total de Competencias", style={"fontSize": "18px", "margin": 0}),
                html.H2(f"{df_curso_comp_grado['Competencia'].nunique()}", style={"color": "#16a085", "margin": "10px 0"}),
            ], className="metric-card"),
            html.Div([
                html.H3("👥 Promedio Evaluaciones por Grado", style={"fontSize": "18px", "margin": 0}),
                html.H2(f"{total_evaluaciones // total_grados if total_grados else 0}", style={"color": "#34495e", "margin": "10px 0"}),
            ], className="metric-card"),
        ]
    elif tab_activa == "tab-seccion":
        metricas = [
            html.Div([
                html.H3("👥 Total de Secciones", style={"fontSize": "18px", "margin": 0}),
                html.H2(f"{total_secciones}", style={"color": "#3498db", "margin": "10px 0"}),
            ], className="metric-card"),
            html.Div([
                html.H3("📚 Total de Cursos", style={"fontSize": "18px", "margin": 0}),
                html.H2(f"{total_cursos}", style={"color": "#34495e", "margin": "10px 0"}),
            ], className="metric-card"),
            html.Div([
                html.H3("🎯 Nivel AD", style={"fontSize": "18px", "margin": 0}),
                html.H2(f"{nivel_counts.get('AD', 0):,}", style={"color": "#27ae60", "margin": "10px 0"}),
                html.P(f"{(nivel_counts.get('AD', 0)/total_evaluaciones*100 if total_evaluaciones else 0):.1f}%", style={"color": "#7f8c8d", "margin": 0}),
            ], className="metric-card"),
            html.Div([
                html.H3("⭐ Nivel A", style={"fontSize": "18px", "margin": 0}),
                html.H2(f"{nivel_counts.get('A', 0):,}", style={"color": "#2ecc71", "margin": "10px 0"}),
                html.P(f"{(nivel_counts.get('A', 0)/total_evaluaciones*100 if total_evaluaciones else 0):.1f}%", style={"color": "#7f8c8d", "margin": 0}),
            ], className="metric-card"),
            html.Div([
                html.H3("📊 Nivel B", style={"fontSize": "18px", "margin": 0}),
                html.H2(f"{nivel_counts.get('B', 0):,}", style={"color": "#f39c12", "margin": "10px 0"}),
                html.P(f"{(nivel_counts.get('B', 0)/total_evaluaciones*100 if total_evaluaciones else 0):.1f}%", style={"color": "#7f8c8d", "margin": 0}),
            ], className="metric-card"),
            html.Div([
                html.H3("⚠️ Nivel C", style={"fontSize": "18px", "margin": 0}),
                html.H2(f"{nivel_counts.get('C', 0):,}", style={"color": "#e74c3c", "margin": "10px 0"}),
                html.P(f"{(nivel_counts.get('C', 0)/total_evaluaciones*100 if total_evaluaciones else 0):.1f}%", style={"color": "#7f8c8d", "margin": 0}),
            ], className="metric-card"),
        ]
    elif tab_activa == "tab-alumno":
        metricas = [
            html.Div([
                html.H3("👤 Total de Alumnos", style={"fontSize": "18px", "margin": 0}),
                html.H2(f"{len(df_data):,}", style={"color": "#2980b9", "margin": "10px 0"}),
            ], className="metric-card"),
            html.Div([
                html.H3("📚 Total de Cursos", style={"fontSize": "18px", "margin": 0}),
                html.H2(f"{total_cursos}", style={"color": "#34495e", "margin": "10px 0"}),
            ], className="metric-card"),
        ]

    return metricas


@app.callback(
    [
        Output("titulo-bimestre", "children"),
        Output("curso-select", "options"),
        Output("curso-select", "value"),
        Output("filtro-curso-grado", "options"),
        Output("filtro-curso-grado", "value"),
        Output("filtro-seccion-seccion", "options"),
        Output("filtro-seccion-seccion", "value"),
        Output("competencia-comparacion-grado", "options"),
        Output("competencia-comparacion-grado", "value"),
        Output("competencia-comparacion-seccion", "options"),
        Output("competencia-comparacion-seccion", "value"),
        Output("alumno-grado-select", "options"),
        Output("alumno-grado-select", "value"),
    ],
    Input("bimestre-select", "value"),
)
def sincronizar_bimestre(bimestre):
    ctx = ctx_bimestre(bimestre)

    df_curso_comp = ctx["df_curso_comp"]
    df_curso_comp_grado = ctx["df_curso_comp_grado"]
    df_seccion_comp = ctx["df_seccion_comp"]
    df_grado_comp = ctx["df_grado_comp"]
    df_seccion_comp_simple = ctx["df_seccion_comp_simple"]
    df_estadisticas = ctx["df_estadisticas"]

    cursos = sorted(df_curso_comp["Curso"].unique())
    curso_val = cursos[0] if cursos else None

    grados = sorted(df_curso_comp_grado["Grado"].unique())
    grado_val = grados[0] if grados else None

    secciones = sorted(df_seccion_comp["Seccion"].unique())
    seccion_val = secciones[0] if secciones else None

    comps_grado = sorted(df_grado_comp["Competencia"].unique())
    comp_grado_val = comps_grado[0] if comps_grado else None

    comps_seccion = sorted(df_seccion_comp_simple["Competencia"].unique())
    comp_sec_val = comps_seccion[0] if comps_seccion else None

    grados_alumno = sorted(df_estadisticas["Grado"].unique())
    grado_alumno_val = grados_alumno[0] if grados_alumno else None

    titulo = f"Dashboard Académico - {bimestre} Bimestre"

    return (
        titulo,
        [{"label": c, "value": c} for c in cursos],
        curso_val,
        [{"label": g, "value": g} for g in grados],
        grado_val,
        [{"label": s, "value": s} for s in secciones],
        seccion_val,
        [{"label": c, "value": c} for c in comps_grado],
        comp_grado_val,
        [{"label": c, "value": c} for c in comps_seccion],
        comp_sec_val,
        [{"label": g, "value": g} for g in grados_alumno],
        grado_alumno_val,
    )


@app.callback(
    Output("grafico-secundaria", "children"),
    [Input("competencia-secundaria", "value"), Input("bimestre-select", "value")],
)
def update_secundaria(competencia, bimestre):
    ctx = ctx_bimestre(bimestre)
    df_filt = ctx["df_secundaria_comp"][ctx["df_secundaria_comp"]["Competencia"] == competencia]
    if df_filt.empty:
        return html.Div("Sin datos", style={"padding": 20})

    fig = go.Figure(
        data=[
            go.Bar(
                x=df_filt["Nivel"],
                y=df_filt["Porcentaje"],
                text=[f"{row['Porcentaje']:.1f}% ({row['Cantidad']})" for _, row in df_filt.iterrows()],
                textposition="auto",
                marker_color=["#27ae60", "#2ecc71", "#f39c12", "#e74c3c"],
            )
        ]
    )

    fig.update_layout(title=f"{competencia}", xaxis_title="Nivel", yaxis_title="Porcentaje (%)", height=400)
    return dcc.Graph(figure=fig)


@app.callback(
    [Output("competencia-curso-select", "options"), Output("competencia-curso-select", "value")],
    [Input("curso-select", "value"), Input("bimestre-select", "value")],
)
def update_curso_comp_options(curso, bimestre):
    ctx = ctx_bimestre(bimestre)
    df_curso_comp = ctx["df_curso_comp"]
    comps = sorted(df_curso_comp[df_curso_comp["Curso"] == curso]["Competencia"].unique())
    return [{"label": c, "value": c} for c in comps], comps[0] if comps else None


@app.callback(
    Output("grafico-curso", "children"),
    [Input("curso-select", "value"), Input("competencia-curso-select", "value"), Input("bimestre-select", "value")],
)
def update_curso(curso, competencia, bimestre):
    if not competencia:
        return html.Div()
    df_curso_comp = ctx_bimestre(bimestre)["df_curso_comp"]
    df_filt = df_curso_comp[(df_curso_comp["Curso"] == curso) & (df_curso_comp["Competencia"] == competencia)]
    if df_filt.empty:
        return html.Div("Sin datos", style={"padding": 20})

    fig = go.Figure(
        data=[
            go.Bar(
                x=df_filt["Nivel"],
                y=df_filt["Porcentaje"],
                text=[f"{row['Porcentaje']:.1f}% ({row['Cantidad']})" for _, row in df_filt.iterrows()],
                textposition="auto",
                marker_color=["#27ae60", "#2ecc71", "#f39c12", "#e74c3c"],
            )
        ]
    )
    fig.update_layout(title=f"{curso} - {competencia}", xaxis_title="Nivel", yaxis_title="Porcentaje (%)", height=400)
    return dcc.Graph(figure=fig)


@app.callback(
    [Output("filtro-curso-curso", "options"), Output("filtro-curso-curso", "value")],
    [Input("filtro-curso-grado", "value"), Input("bimestre-select", "value")],
)
def update_curso_options_grado(grado, bimestre):
    df_curso_comp_grado = ctx_bimestre(bimestre)["df_curso_comp_grado"]
    cursos = sorted(df_curso_comp_grado[df_curso_comp_grado["Grado"] == grado]["Curso"].unique())
    return [{"label": c, "value": c} for c in cursos], cursos[0] if cursos else None


@app.callback(
    [Output("filtro-curso-competencia", "options"), Output("filtro-curso-competencia", "value")],
    [Input("filtro-curso-grado", "value"), Input("filtro-curso-curso", "value"), Input("bimestre-select", "value")],
)
def update_competencia_options_grado(grado, curso, bimestre):
    df_curso_comp_grado = ctx_bimestre(bimestre)["df_curso_comp_grado"]
    comps = sorted(
        df_curso_comp_grado[(df_curso_comp_grado["Grado"] == grado) & (df_curso_comp_grado["Curso"] == curso)][
            "Competencia"
        ].unique()
    )
    return [{"label": c, "value": c} for c in comps], comps[0] if comps else None


@app.callback(
    Output("grafico-curso-grado", "children"),
    [Input("filtro-curso-grado", "value"), Input("filtro-curso-curso", "value"), Input("filtro-curso-competencia", "value"), Input("bimestre-select", "value")],
)
def update_grafico_curso_grado(grado, curso, competencia, bimestre):
    if not competencia:
        return html.Div()
    df_curso_comp_grado = ctx_bimestre(bimestre)["df_curso_comp_grado"]
    df_filt = df_curso_comp_grado[
        (df_curso_comp_grado["Grado"] == grado)
        & (df_curso_comp_grado["Curso"] == curso)
        & (df_curso_comp_grado["Competencia"] == competencia)
    ]
    if df_filt.empty:
        return html.Div("Sin datos", style={"padding": 20})

    fig = go.Figure(
        data=[
            go.Bar(
                x=df_filt["Nivel"],
                y=df_filt["Porcentaje"],
                text=[f"{row['Porcentaje']:.1f}% ({row['Cantidad']})" for _, row in df_filt.iterrows()],
                textposition="auto",
                marker_color=["#27ae60", "#2ecc71", "#f39c12", "#e74c3c"],
            )
        ]
    )
    fig.update_layout(title=f"{grado} - {curso} - {competencia}", xaxis_title="Nivel", yaxis_title="Porcentaje (%)", height=400)
    return dcc.Graph(figure=fig)


@app.callback(
    [Output("filtro-seccion-curso", "options"), Output("filtro-seccion-curso", "value")],
    [Input("filtro-seccion-seccion", "value"), Input("bimestre-select", "value")],
)
def update_curso_options_seccion(seccion, bimestre):
    df_seccion_comp = ctx_bimestre(bimestre)["df_seccion_comp"]
    cursos = sorted(df_seccion_comp[df_seccion_comp["Seccion"] == seccion]["Curso"].unique())
    return [{"label": c, "value": c} for c in cursos], cursos[0] if cursos else None


@app.callback(
    [Output("filtro-seccion-competencia", "options"), Output("filtro-seccion-competencia", "value")],
    [Input("filtro-seccion-seccion", "value"), Input("filtro-seccion-curso", "value"), Input("bimestre-select", "value")],
)
def update_competencia_options_seccion(seccion, curso, bimestre):
    if not curso:
        return [], None
    df_seccion_comp = ctx_bimestre(bimestre)["df_seccion_comp"]
    comps = sorted(
        df_seccion_comp[(df_seccion_comp["Seccion"] == seccion) & (df_seccion_comp["Curso"] == curso)]["Competencia"].unique()
    )
    return [{"label": c, "value": c} for c in comps], comps[0] if comps else None


@app.callback(
    Output("grafico-seccion-filtros", "children"),
    [Input("filtro-seccion-seccion", "value"), Input("filtro-seccion-curso", "value"), Input("filtro-seccion-competencia", "value"), Input("bimestre-select", "value")],
)
def update_grafico_seccion_filtros(seccion, curso, competencia, bimestre):
    if not curso or not competencia:
        return html.Div()
    df_seccion_comp = ctx_bimestre(bimestre)["df_seccion_comp"]
    df_filt = df_seccion_comp[
        (df_seccion_comp["Seccion"] == seccion)
        & (df_seccion_comp["Curso"] == curso)
        & (df_seccion_comp["Competencia"] == competencia)
    ]
    if df_filt.empty:
        return html.Div("Sin datos", style={"padding": 20})

    fig = go.Figure(
        data=[
            go.Bar(
                x=df_filt["Nivel"],
                y=df_filt["Porcentaje"],
                text=[f"{row['Porcentaje']:.1f}% ({row['Cantidad']})" for _, row in df_filt.iterrows()],
                textposition="auto",
                marker_color=["#27ae60", "#2ecc71", "#f39c12", "#e74c3c"],
            )
        ]
    )
    fig.update_layout(title=f"{seccion} - {curso} - {competencia}", xaxis_title="Nivel", yaxis_title="Porcentaje (%)", height=400)
    return dcc.Graph(figure=fig)


@app.callback(
    Output("grafico-comparacion-grados", "children"),
    [Input("competencia-comparacion-grado", "value"), Input("bimestre-select", "value")],
)
def update_comp_grados(competencia, bimestre):
    df_grado_comp = ctx_bimestre(bimestre)["df_grado_comp"]
    df_filt = df_grado_comp[df_grado_comp["Competencia"] == competencia]
    if df_filt.empty:
        return html.Div("Sin datos", style={"padding": 20})

    fig = px.bar(
        df_filt,
        x="Grado",
        y="Porcentaje",
        color="Nivel",
        barmode="group",
        text="Cantidad",
        color_discrete_map={"AD": "#27ae60", "A": "#2ecc71", "B": "#f39c12", "C": "#e74c3c"},
    )

    fig.update_traces(texttemplate="%{y:.1f}%", textposition="outside")
    fig.update_layout(title=f"Comparación de Grados - {competencia}", height=500, xaxis_title="Grado", yaxis_title="Porcentaje (%)")

    return dcc.Graph(figure=fig)


@app.callback(
    [Output("competencia-seccion-select", "options"), Output("competencia-seccion-select", "value")],
    [Input("seccion-select", "value"), Input("bimestre-select", "value")],
)
def update_seccion_comp_options(seccion, bimestre):
    df_seccion_comp = ctx_bimestre(bimestre)["df_seccion_comp"]
    comps = sorted(df_seccion_comp[df_seccion_comp["Seccion"] == seccion]["Competencia"].unique())
    return [{"label": c, "value": c} for c in comps], comps[0] if comps else None


@app.callback(
    Output("grafico-seccion", "children"),
    [Input("seccion-select", "value"), Input("competencia-seccion-select", "value"), Input("bimestre-select", "value")],
)
def update_seccion(seccion, competencia, bimestre):
    if not competencia:
        return html.Div()
    df_seccion_comp = ctx_bimestre(bimestre)["df_seccion_comp"]
    df_filt = df_seccion_comp[(df_seccion_comp["Seccion"] == seccion) & (df_seccion_comp["Competencia"] == competencia)]
    if df_filt.empty:
        return html.Div("Sin datos", style={"padding": 20})

    fig = go.Figure(
        data=[
            go.Bar(
                x=df_filt["Nivel"],
                y=df_filt["Porcentaje"],
                text=[f"{row['Porcentaje']:.1f}% ({row['Cantidad']})" for _, row in df_filt.iterrows()],
                textposition="auto",
                marker_color=["#27ae60", "#2ecc71", "#f39c12", "#e74c3c"],
            )
        ]
    )

    fig.update_layout(title=f"{seccion} - {competencia}", xaxis_title="Nivel", yaxis_title="Porcentaje (%)", height=400)
    return dcc.Graph(figure=fig)


@app.callback(
    Output("grafico-comparacion-secciones", "children"),
    [Input("competencia-comparacion-seccion", "value"), Input("bimestre-select", "value")],
)
def update_comp_secciones(competencia, bimestre):
    df_seccion_comp_simple = ctx_bimestre(bimestre)["df_seccion_comp_simple"]
    df_filt = df_seccion_comp_simple[df_seccion_comp_simple["Competencia"] == competencia]
    if df_filt.empty:
        return html.Div("Sin datos", style={"padding": 20})

    fig = px.bar(
        df_filt,
        x="Seccion",
        y="Porcentaje",
        color="Nivel",
        barmode="group",
        text="Cantidad",
        color_discrete_map={"AD": "#27ae60", "A": "#2ecc71", "B": "#f39c12", "C": "#e74c3c"},
    )

    fig.update_traces(texttemplate="%{y:.1f}%", textposition="outside")
    fig.update_layout(title=f"Comparación de Secciones - {competencia}", height=500, xaxis_title="Sección", yaxis_title="Porcentaje (%)")

    return dcc.Graph(figure=fig)


@app.callback(
    [Output("alumno-seccion-select", "options"), Output("alumno-seccion-select", "value")],
    [Input("alumno-grado-select", "value"), Input("bimestre-select", "value")],
)
def update_alumno_seccion(grado, bimestre):
    df_estadisticas = ctx_bimestre(bimestre)["df_estadisticas"]
    secciones = sorted(df_estadisticas[df_estadisticas["Grado"] == grado]["Seccion"].unique())
    return [{"label": s, "value": s} for s in secciones], secciones[0] if secciones else None


@app.callback(
    [Output("alumno-curso-select", "options"), Output("alumno-curso-select", "value")],
    [Input("alumno-grado-select", "value"), Input("alumno-seccion-select", "value"), Input("bimestre-select", "value")],
)
def update_alumno_curso(grado, seccion, bimestre):
    if not seccion:
        return [], None
    df_estadisticas = ctx_bimestre(bimestre)["df_estadisticas"]
    df_filt = df_estadisticas[(df_estadisticas["Grado"] == grado) & (df_estadisticas["Seccion"] == seccion)]
    cursos = sorted(set(info["curso"] for info in ctx_bimestre(bimestre)["mapeo_columnas"].values()))
    cursos = sorted(cursos)
    return [{"label": c, "value": c} for c in cursos], cursos[0] if cursos else None


@app.callback(
    Output("tabla-alumnos", "children"),
    [Input("alumno-grado-select", "value"), Input("alumno-seccion-select", "value"), Input("alumno-curso-select", "value"), Input("bimestre-select", "value")],
)
def mostrar_tabla_alumnos(grado, seccion, curso, bimestre):
    if not seccion or not curso:
        return html.Div("Por favor, seleccione Grado, Sección y Curso", style={"padding": "20px", "textAlign": "center", "color": "#7f8c8d"})
    ctx = ctx_bimestre(bimestre)
    df_data = ctx["df_data"]
    mapeo_columnas = ctx["mapeo_columnas"]

    df_alumnos_filtrados = df_data[(df_data["grado"] == grado) & (df_data["seccion"] == seccion)].copy()

    if len(df_alumnos_filtrados) == 0:
        return html.Div("No hay datos disponibles para esta selección", style={"padding": "20px", "textAlign": "center", "color": "#e74c3c"})

    columnas_curso = [col_idx for col_idx, info in mapeo_columnas.items() if info["curso"] == curso]

    if len(columnas_curso) == 0:
        return html.Div(f"No hay competencias registradas para el curso {curso}", style={"padding": "20px", "textAlign": "center", "color": "#e74c3c"})

    competencias = [mapeo_columnas[col]["competencia"] for col in columnas_curso]

    alumnos_data = []
    for _, row in df_alumnos_filtrados.iterrows():
        alumno = {"Nro": int(row["alumno_id"]), "Alumno": row["nombre_alumno"]}
        for col_idx, comp in zip(columnas_curso, competencias):
            nivel = row.iloc[col_idx] if col_idx < len(row) else "-"
            if pd.isna(nivel):
                nivel = "-"
            comp_short = comp[:30] + "..." if len(comp) > 30 else comp
            alumno[comp_short] = str(nivel).strip()
        alumnos_data.append(alumno)

    headers = [
        html.Th("Nro", style={"padding": "10px", "border": "1px solid #ddd", "backgroundColor": "#3498db", "color": "white", "textAlign": "center", "position": "sticky", "left": "0", "zIndex": "10", "minWidth": "50px"}),
        html.Th("Alumno", style={"padding": "10px", "border": "1px solid #ddd", "backgroundColor": "#3498db", "color": "white", "textAlign": "left", "minWidth": "250px", "position": "sticky", "left": "50px", "zIndex": "10"}),
    ]

    for comp in competencias:
        comp_short = comp[:30] + "..." if len(comp) > 30 else comp
        headers.append(
            html.Th(
                comp_short,
                style={
                    "padding": "10px",
                    "border": "1px solid #ddd",
                    "backgroundColor": "#2c3e50",
                    "color": "white",
                    "textAlign": "center",
                    "minWidth": "100px",
                    "fontSize": "12px",
                    "writingMode": "horizontal-tb",
                },
                title=comp,
            )
        )

    def get_nivel_color(nivel):
        colors = {"AD": "#d5f4e6", "A": "#a9dfbf", "B": "#fdeaa1", "C": "#f5b7b1", "-": "#ecf0f1"}
        return colors.get(nivel, "#ecf0f1")

    filas = []
    for alumno in alumnos_data:
        celdas = [
            html.Td(alumno["Nro"], style={"padding": "8px", "border": "1px solid #ddd", "textAlign": "center", "backgroundColor": "white", "position": "sticky", "left": "0", "zIndex": "5"}),
            html.Td(alumno["Alumno"], style={"padding": "8px", "border": "1px solid #ddd", "backgroundColor": "white", "position": "sticky", "left": "50px", "zIndex": "5", "fontSize": "13px"}),
        ]
        for comp in competencias:
            comp_short = comp[:30] + "..." if len(comp) > 30 else comp
            nivel = alumno.get(comp_short, "-")
            celdas.append(
                html.Td(
                    nivel,
                    style={
                        "padding": "8px",
                        "border": "1px solid #ddd",
                        "textAlign": "center",
                        "fontWeight": "bold",
                        "backgroundColor": get_nivel_color(nivel),
                    },
                )
            )
        filas.append(html.Tr(celdas))

    tabla_html = html.Div(
        [
            html.H3(f"👥 Listado de Estudiantes: {grado} - {seccion} - {curso}", style={"color": "#2c3e50", "marginBottom": "10px"}),
            html.P(
                f"Total de estudiantes: {len(alumnos_data)} | Competencias evaluadas: {len(competencias)}",
                style={"fontSize": "14px", "color": "#7f8c8d", "marginBottom": "20px"},
            ),
            html.Div(
                [
                    html.Table([
                        html.Thead(html.Tr(headers)),
                        html.Tbody(filas),
                    ], style={"borderCollapse": "collapse", "boxShadow": "0 2px 4px rgba(0,0,0,0.1)", "fontSize": "14px"})
                ],
                style={"overflowX": "auto", "overflowY": "auto", "maxHeight": "600px", "border": "1px solid #ddd", "borderRadius": "5px"},
            ),
            html.Div(
                [
                    html.Div("AD", style={"display": "inline-block", "padding": "5px 10px", "margin": "5px", "backgroundColor": "#d5f4e6", "border": "1px solid #27ae60", "borderRadius": "3px"}),
                    html.Div("A", style={"display": "inline-block", "padding": "5px 10px", "margin": "5px", "backgroundColor": "#a9dfbf", "border": "1px solid #2ecc71", "borderRadius": "3px"}),
                    html.Div("B", style={"display": "inline-block", "padding": "5px 10px", "margin": "5px", "backgroundColor": "#fdeaa1", "border": "1px solid #f39c12", "borderRadius": "3px"}),
                    html.Div("C", style={"display": "inline-block", "padding": "5px 10px", "margin": "5px", "backgroundColor": "#f5b7b1", "border": "1px solid #e74c3c", "borderRadius": "3px"}),
                ],
                style={"marginTop": "20px", "textAlign": "center"},
            ),
        ]
    )

    return tabla_html


if __name__ == "__main__":
    print("\n[*] Iniciando Dashboard...")
    app.run(debug=False, host="0.0.0.0", port=8050)
