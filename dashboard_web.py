import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import warnings
import os
warnings.filterwarnings('ignore')

print("📂 Cargando datos...")

# Detectar ruta del archivo Excel (funciona en local y en servidor)
if os.path.exists('DASHBOARD_II_BIMESTRE.xlsx'):
    file_path = 'DASHBOARD_II_BIMESTRE.xlsx'
else:
    file_path = r'c:\Users\erwin\Downloads\dashboard\DASHBOARD_II_BIMESTRE.xlsx'

df_estadisticas = pd.read_excel(file_path, sheet_name='ESTADISTICAS', engine='openpyxl')
df_data_raw = pd.read_excel(file_path, sheet_name='DATA', engine='openpyxl', header=None)

# Procesar la hoja DATA para obtener información de alumnos
df_data = df_data_raw.iloc[4:].copy()
df_data.columns = range(len(df_data.columns))

if len(df_data) > 0:
    df_data = df_data.reset_index(drop=True)
    df_data['alumno_id'] = df_data.iloc[:, 0].fillna(0).astype(int)
    df_data['nombre_alumno'] = df_data.iloc[:, 4].astype(str)
    df_data['grado'] = df_data.iloc[:, 2].astype(str)
    df_data['seccion'] = df_data.iloc[:, 3].astype(str)
    df_data = df_data[df_data['alumno_id'] > 0]

print(f"✅ Datos cargados: {len(df_estadisticas)} registros de estadísticas")
print(f"✅ Alumnos encontrados: {len(df_data)}")

cursos_row = df_data_raw.iloc[1, :].tolist()
competencias_row = df_data_raw.iloc[3, :].tolist()

mapeo_columnas = {}
curso_actual = None
for i, val in enumerate(cursos_row):
    if pd.notna(val) and val not in ['COMPETENCIAS', 'COMPETENCIA']:
        curso_actual = val
    if pd.notna(competencias_row[i]) and curso_actual:
        mapeo_columnas[i] = {
            'curso': curso_actual,
            'competencia': str(competencias_row[i])
        }

# 1. Agrupar por Competencia - Nivel Secundaria
df_secundaria_comp = df_estadisticas.groupby(['Competencia', 'Nivel']).size().reset_index(name='Cantidad')
total_por_comp = df_estadisticas.groupby('Competencia').size().reset_index(name='Total')
df_secundaria_comp = df_secundaria_comp.merge(total_por_comp, on='Competencia')
df_secundaria_comp['Porcentaje'] = (df_secundaria_comp['Cantidad'] / df_secundaria_comp['Total']) * 100

# 2. Agrupar por Curso - Competencia
df_curso_comp = df_estadisticas.groupby(['Curso', 'Competencia', 'Nivel']).size().reset_index(name='Cantidad')
total_curso_comp = df_estadisticas.groupby(['Curso', 'Competencia']).size().reset_index(name='Total')
df_curso_comp = df_curso_comp.merge(total_curso_comp, on=['Curso', 'Competencia'])
df_curso_comp['Porcentaje'] = (df_curso_comp['Cantidad'] / df_curso_comp['Total']) * 100

# 3. Agrupar por Grado - Competencia
df_grado_comp = df_estadisticas.groupby(['Grado', 'Competencia', 'Nivel']).size().reset_index(name='Cantidad')
total_grado_comp = df_estadisticas.groupby(['Grado', 'Competencia']).size().reset_index(name='Total')
df_grado_comp = df_grado_comp.merge(total_grado_comp, on=['Grado', 'Competencia'])
df_grado_comp['Porcentaje'] = (df_grado_comp['Cantidad'] / df_grado_comp['Total']) * 100

# 4. Agrupar por Sección - Competencia
df_seccion_comp = df_estadisticas.groupby(['Seccion', 'Competencia', 'Nivel']).size().reset_index(name='Cantidad')
total_seccion_comp = df_estadisticas.groupby(['Seccion', 'Competencia']).size().reset_index(name='Total')
df_seccion_comp = df_seccion_comp.merge(total_seccion_comp, on=['Seccion', 'Competencia'])
df_seccion_comp['Porcentaje'] = (df_seccion_comp['Cantidad'] / df_seccion_comp['Total']) * 100

# Métricas generales
total_evaluaciones = len(df_estadisticas)
nivel_counts = df_estadisticas['Nivel'].value_counts()

# Crear aplicación Dash
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server  # Para deployment en servidores web

app.layout = html.Div([
    # Header con logo y título
    html.Div([
        html.Div([
            html.Img(src='/assets/logo.png', style={'height': '80px', 'marginRight': '20px'}),
        ], style={'display': 'inline-block', 'verticalAlign': 'middle'}),
        html.Div([
            html.H1('I.E. Amalia del Águila Velásquez', 
                    style={'margin': '0', 'color': '#2c3e50', 'fontWeight': 'bold', 'fontSize': '32px'}),
            html.H2('Dashboard Académico - II Bimestre', 
                    style={'margin': '5px 0 0 0', 'color': '#7f8c8d', 'fontWeight': 'normal', 'fontSize': '24px'}),
        ], style={'display': 'inline-block', 'verticalAlign': 'middle'}),
    ], style={'textAlign': 'center', 'marginBottom': 30, 'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '10px', 'boxShadow': '0 4px 6px rgba(0,0,0,0.1)'}),
    
    # Tarjetas de métricas generales
    html.Div([
        html.Div([
            html.H3('📝 Total Evaluaciones', style={'fontSize': '18px', 'margin': 0}),
            html.H2(f'{total_evaluaciones:,}', style={'color': '#3498db', 'margin': '10px 0'})
        ], className='metric-card'),
        
        html.Div([
            html.H3('🎯 Nivel AD', style={'fontSize': '18px', 'margin': 0}),
            html.H2(f'{nivel_counts.get("AD", 0):,}', style={'color': '#27ae60', 'margin': '10px 0'}),
            html.P(f'{(nivel_counts.get("AD", 0)/total_evaluaciones*100):.1f}%', style={'color': '#7f8c8d', 'margin': 0})
        ], className='metric-card'),
        
        html.Div([
            html.H3('⭐ Nivel A', style={'fontSize': '18px', 'margin': 0}),
            html.H2(f'{nivel_counts.get("A", 0):,}', style={'color': '#2ecc71', 'margin': '10px 0'}),
            html.P(f'{(nivel_counts.get("A", 0)/total_evaluaciones*100):.1f}%', style={'color': '#7f8c8d', 'margin': 0})
        ], className='metric-card'),
        
        html.Div([
            html.H3('📊 Nivel B', style={'fontSize': '18px', 'margin': 0}),
            html.H2(f'{nivel_counts.get("B", 0):,}', style={'color': '#f39c12', 'margin': '10px 0'}),
            html.P(f'{(nivel_counts.get("B", 0)/total_evaluaciones*100):.1f}%', style={'color': '#7f8c8d', 'margin': 0})
        ], className='metric-card'),
        
        html.Div([
            html.H3('⚠️ Nivel C', style={'fontSize': '18px', 'margin': 0}),
            html.H2(f'{nivel_counts.get("C", 0):,}', style={'color': '#e74c3c', 'margin': '10px 0'}),
            html.P(f'{(nivel_counts.get("C", 0)/total_evaluaciones*100):.1f}%', style={'color': '#7f8c8d', 'margin': 0})
        ], className='metric-card'),
    ], style={'display': 'flex', 'flexWrap': 'wrap', 'marginBottom': 30, 'gap': '10px'}),
    
    # Tabs
    dcc.Tabs([
        # TAB 1: NIVEL SECUNDARIA
        dcc.Tab(label='📚 1. Nivel Secundaria', children=[
            html.Div([
                html.H2('Porcentaje por Nivel en cada Competencia', 
                       style={'color': '#2c3e50', 'marginTop': 20}),
                
                html.Div([
                    html.Label('Seleccionar Competencia:', style={'fontWeight': 'bold'}),
                    dcc.Dropdown(
                        id='competencia-secundaria',
                        options=[{'label': comp, 'value': comp} 
                                for comp in sorted(df_secundaria_comp['Competencia'].unique())],
                        value=sorted(df_secundaria_comp['Competencia'].unique())[0],
                        style={'marginBottom': 20}
                    )
                ]),
                
                html.Div(id='grafico-secundaria'),
                
                html.Hr(style={'margin': '40px 0'}),
                
                html.H2('Porcentaje por Curso y Competencia', 
                       style={'color': '#2c3e50'}),
                
                html.Div([
                    html.Div([
                        html.Label('Curso:', style={'fontWeight': 'bold'}),
                        dcc.Dropdown(id='curso-select', 
                                   options=[{'label': c, 'value': c} for c in sorted(df_curso_comp['Curso'].unique())],
                                   value=sorted(df_curso_comp['Curso'].unique())[0])
                    ], style={'width': '48%', 'display': 'inline-block'}),
                    
                    html.Div([
                        html.Label('Competencia:', style={'fontWeight': 'bold'}),
                        dcc.Dropdown(id='competencia-curso-select')
                    ], style={'width': '48%', 'display': 'inline-block', 'marginLeft': '4%'}),
                ]),
                
                html.Div(id='grafico-curso', style={'marginTop': 20}),
            ], style={'padding': 20})
        ]),
        
        # TAB 2: POR GRADO
        dcc.Tab(label='🎓 2. Por Grado', children=[
            html.Div([
                html.H2('Porcentaje por Grado en cada Competencia', 
                       style={'color': '#2c3e50', 'marginTop': 20}),
                
                html.Div([
                    html.Div([
                        html.Label('Grado:', style={'fontWeight': 'bold'}),
                        dcc.Dropdown(id='grado-select',
                                   options=[{'label': g, 'value': g} for g in sorted(df_grado_comp['Grado'].unique())],
                                   value=sorted(df_grado_comp['Grado'].unique())[0])
                    ], style={'width': '48%', 'display': 'inline-block'}),
                    
                    html.Div([
                        html.Label('Competencia:', style={'fontWeight': 'bold'}),
                        dcc.Dropdown(id='competencia-grado-select')
                    ], style={'width': '48%', 'display': 'inline-block', 'marginLeft': '4%'}),
                ]),
                
                html.Div(id='grafico-grado', style={'marginTop': 20}),
                
                html.Hr(style={'margin': '40px 0'}),
                
                html.H2('Comparación entre Grados', style={'color': '#2c3e50'}),
                
                html.Div([
                    html.Label('Seleccionar Competencia:', style={'fontWeight': 'bold'}),
                    dcc.Dropdown(
                        id='competencia-comparacion-grado',
                        options=[{'label': comp, 'value': comp} 
                                for comp in sorted(df_grado_comp['Competencia'].unique())],
                        value=sorted(df_grado_comp['Competencia'].unique())[0],
                        style={'marginBottom': 20}
                    )
                ]),
                
                html.Div(id='grafico-comparacion-grados'),
            ], style={'padding': 20})
        ]),
        
        # TAB 3: POR SECCIÓN
        dcc.Tab(label='👥 3. Por Sección', children=[
            html.Div([
                html.H2('Porcentaje por Sección en cada Competencia', 
                       style={'color': '#2c3e50', 'marginTop': 20}),
                
                html.Div([
                    html.Div([
                        html.Label('Sección:', style={'fontWeight': 'bold'}),
                        dcc.Dropdown(id='seccion-select',
                                   options=[{'label': s, 'value': s} for s in sorted(df_seccion_comp['Seccion'].unique())],
                                   value=sorted(df_seccion_comp['Seccion'].unique())[0])
                    ], style={'width': '48%', 'display': 'inline-block'}),
                    
                    html.Div([
                        html.Label('Competencia:', style={'fontWeight': 'bold'}),
                        dcc.Dropdown(id='competencia-seccion-select')
                    ], style={'width': '48%', 'display': 'inline-block', 'marginLeft': '4%'}),
                ]),
                
                html.Div(id='grafico-seccion', style={'marginTop': 20}),
                
                html.Hr(style={'margin': '40px 0'}),
                
                html.H2('Comparación entre Secciones', style={'color': '#2c3e50'}),
                
                html.Div([
                    html.Label('Seleccionar Competencia:', style={'fontWeight': 'bold'}),
                    dcc.Dropdown(
                        id='competencia-comparacion-seccion',
                        options=[{'label': comp, 'value': comp} 
                                for comp in sorted(df_seccion_comp['Competencia'].unique())],
                        value=sorted(df_seccion_comp['Competencia'].unique())[0],
                        style={'marginBottom': 20}
                    )
                ]),
                
                html.Div(id='grafico-comparacion-secciones'),
            ], style={'padding': 20})
        ]),
        
        # TAB 4: POR ALUMNO
        dcc.Tab(label='👤 4. Por Alumno', children=[
            html.Div([
                html.H2('Listado de Alumnos', 
                       style={'color': '#2c3e50', 'marginTop': 20}),
                html.P('Seleccione Grado, Sección y Curso para ver el listado de estudiantes y sus calificaciones',
                      style={'color': '#7f8c8d', 'marginBottom': 20}),
                
                html.Div([
                    html.Div([
                        html.Label('Grado:', style={'fontWeight': 'bold'}),
                        dcc.Dropdown(id='alumno-grado-select',
                                   options=[{'label': g, 'value': g} for g in sorted(df_estadisticas['Grado'].unique())],
                                   value=sorted(df_estadisticas['Grado'].unique())[0])
                    ], style={'width': '31%', 'display': 'inline-block'}),
                    
                    html.Div([
                        html.Label('Sección:', style={'fontWeight': 'bold'}),
                        dcc.Dropdown(id='alumno-seccion-select')
                    ], style={'width': '31%', 'display': 'inline-block', 'marginLeft': '3%'}),
                    
                    html.Div([
                        html.Label('Curso:', style={'fontWeight': 'bold'}),
                        dcc.Dropdown(id='alumno-curso-select')
                    ], style={'width': '31%', 'display': 'inline-block', 'marginLeft': '3%'}),
                ]),
                
                html.Div(id='tabla-alumnos', style={'marginTop': 30}),
            ], style={'padding': 20})
        ]),
    ]),
    
], style={'padding': 30, 'fontFamily': 'Arial, sans-serif', 'backgroundColor': '#f5f6fa'})

# Estilos CSS adicionales
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            .metric-card {
                text-align: center;
                padding: 20px;
                background-color: #ecf0f1;
                border-radius: 10px;
                flex: 1;
                min-width: 150px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
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
'''

# CALLBACKS

# 1. Nivel Secundaria - Competencia
@app.callback(
    Output('grafico-secundaria', 'children'),
    Input('competencia-secundaria', 'value')
)
def update_secundaria(competencia):
    df_filt = df_secundaria_comp[df_secundaria_comp['Competencia'] == competencia]
    
    fig = go.Figure(data=[
        go.Bar(x=df_filt['Nivel'], y=df_filt['Porcentaje'],
               text=[f"{row['Porcentaje']:.1f}% ({row['Cantidad']})" 
                     for _, row in df_filt.iterrows()],
               textposition='auto',
               marker_color=['#27ae60', '#2ecc71', '#f39c12', '#e74c3c'])
    ])
    
    fig.update_layout(title=f'{competencia}', xaxis_title='Nivel', 
                     yaxis_title='Porcentaje (%)', height=400)
    
    return dcc.Graph(figure=fig)

# 2. Actualizar competencias por curso
@app.callback(
    [Output('competencia-curso-select', 'options'),
     Output('competencia-curso-select', 'value')],
    Input('curso-select', 'value')
)
def update_curso_comp_options(curso):
    comps = sorted(df_curso_comp[df_curso_comp['Curso'] == curso]['Competencia'].unique())
    return [{'label': c, 'value': c} for c in comps], comps[0] if comps else None

# 3. Gráfico curso-competencia
@app.callback(
    Output('grafico-curso', 'children'),
    [Input('curso-select', 'value'),
     Input('competencia-curso-select', 'value')]
)
def update_curso(curso, competencia):
    if not competencia:
        return html.Div()
    
    df_filt = df_curso_comp[(df_curso_comp['Curso'] == curso) & 
                            (df_curso_comp['Competencia'] == competencia)]
    
    fig = go.Figure(data=[
        go.Bar(x=df_filt['Nivel'], y=df_filt['Porcentaje'],
               text=[f"{row['Porcentaje']:.1f}% ({row['Cantidad']})" 
                     for _, row in df_filt.iterrows()],
               textposition='auto',
               marker_color=['#27ae60', '#2ecc71', '#f39c12', '#e74c3c'])
    ])
    
    fig.update_layout(title=f'{curso} - {competencia}', xaxis_title='Nivel',
                     yaxis_title='Porcentaje (%)', height=400)
    
    return dcc.Graph(figure=fig)

# 4. Actualizar competencias por grado
@app.callback(
    [Output('competencia-grado-select', 'options'),
     Output('competencia-grado-select', 'value')],
    Input('grado-select', 'value')
)
def update_grado_comp_options(grado):
    comps = sorted(df_grado_comp[df_grado_comp['Grado'] == grado]['Competencia'].unique())
    return [{'label': c, 'value': c} for c in comps], comps[0] if comps else None

# 5. Gráfico grado-competencia
@app.callback(
    Output('grafico-grado', 'children'),
    [Input('grado-select', 'value'),
     Input('competencia-grado-select', 'value')]
)
def update_grado(grado, competencia):
    if not competencia:
        return html.Div()
    
    df_filt = df_grado_comp[(df_grado_comp['Grado'] == grado) & 
                            (df_grado_comp['Competencia'] == competencia)]
    
    fig = go.Figure(data=[
        go.Bar(x=df_filt['Nivel'], y=df_filt['Porcentaje'],
               text=[f"{row['Porcentaje']:.1f}% ({row['Cantidad']})" 
                     for _, row in df_filt.iterrows()],
               textposition='auto',
               marker_color=['#27ae60', '#2ecc71', '#f39c12', '#e74c3c'])
    ])
    
    fig.update_layout(title=f'{grado} - {competencia}', xaxis_title='Nivel',
                     yaxis_title='Porcentaje (%)', height=400)
    
    return dcc.Graph(figure=fig)

# 6. Comparación grados
@app.callback(
    Output('grafico-comparacion-grados', 'children'),
    Input('competencia-comparacion-grado', 'value')
)
def update_comp_grados(competencia):
    df_filt = df_grado_comp[df_grado_comp['Competencia'] == competencia]
    
    fig = px.bar(df_filt, x='Grado', y='Porcentaje', color='Nivel',
                 barmode='group',
                 color_discrete_map={'AD': '#27ae60', 'A': '#2ecc71', 'B': '#f39c12', 'C': '#e74c3c'},
                 title=f'Comparación de Grados - {competencia}')
    
    fig.update_layout(height=500, xaxis_title='Grado', yaxis_title='Porcentaje (%)')
    
    return dcc.Graph(figure=fig)

# 7. Actualizar competencias por sección
@app.callback(
    [Output('competencia-seccion-select', 'options'),
     Output('competencia-seccion-select', 'value')],
    Input('seccion-select', 'value')
)
def update_seccion_comp_options(seccion):
    comps = sorted(df_seccion_comp[df_seccion_comp['Seccion'] == seccion]['Competencia'].unique())
    return [{'label': c, 'value': c} for c in comps], comps[0] if comps else None

# 8. Gráfico sección-competencia
@app.callback(
    Output('grafico-seccion', 'children'),
    [Input('seccion-select', 'value'),
     Input('competencia-seccion-select', 'value')]
)
def update_seccion(seccion, competencia):
    if not competencia:
        return html.Div()
    
    df_filt = df_seccion_comp[(df_seccion_comp['Seccion'] == seccion) & 
                              (df_seccion_comp['Competencia'] == competencia)]
    
    fig = go.Figure(data=[
        go.Bar(x=df_filt['Nivel'], y=df_filt['Porcentaje'],
               text=[f"{row['Porcentaje']:.1f}% ({row['Cantidad']})" 
                     for _, row in df_filt.iterrows()],
               textposition='auto',
               marker_color=['#27ae60', '#2ecc71', '#f39c12', '#e74c3c'])
    ])
    
    fig.update_layout(title=f'{seccion} - {competencia}', xaxis_title='Nivel',
                     yaxis_title='Porcentaje (%)', height=400)
    
    return dcc.Graph(figure=fig)

# 9. Comparación secciones
@app.callback(
    Output('grafico-comparacion-secciones', 'children'),
    Input('competencia-comparacion-seccion', 'value')
)
def update_comp_secciones(competencia):
    df_filt = df_seccion_comp[df_seccion_comp['Competencia'] == competencia]
    
    fig = px.bar(df_filt, x='Seccion', y='Porcentaje', color='Nivel',
                 barmode='group',
                 color_discrete_map={'AD': '#27ae60', 'A': '#2ecc71', 'B': '#f39c12', 'C': '#e74c3c'},
                 title=f'Comparación de Secciones - {competencia}')
    
    fig.update_layout(height=500, xaxis_title='Sección', yaxis_title='Porcentaje (%)')
    
    return dcc.Graph(figure=fig)

# 10. Actualizar secciones según grado (para alumnos)
@app.callback(
    [Output('alumno-seccion-select', 'options'),
     Output('alumno-seccion-select', 'value')],
    Input('alumno-grado-select', 'value')
)
def update_alumno_seccion(grado):
    secciones = sorted(df_estadisticas[df_estadisticas['Grado'] == grado]['Seccion'].unique())
    return [{'label': s, 'value': s} for s in secciones], secciones[0] if secciones else None

# 11. Actualizar cursos según grado y sección (para alumnos)
@app.callback(
    [Output('alumno-curso-select', 'options'),
     Output('alumno-curso-select', 'value')],
    [Input('alumno-grado-select', 'value'),
     Input('alumno-seccion-select', 'value')]
)
def update_alumno_curso(grado, seccion):
    if not seccion:
        return [], None
    df_filt = df_estadisticas[(df_estadisticas['Grado'] == grado) & 
                              (df_estadisticas['Seccion'] == seccion)]
    cursos = sorted(df_filt['Curso'].unique())
    return [{'label': c, 'value': c} for c in cursos], cursos[0] if cursos else None

# 12. Mostrar tabla de alumnos
@app.callback(
    Output('tabla-alumnos', 'children'),
    [Input('alumno-grado-select', 'value'),
     Input('alumno-seccion-select', 'value'),
     Input('alumno-curso-select', 'value')]
)
def mostrar_tabla_alumnos(grado, seccion, curso):
    if not seccion or not curso:
        return html.Div('Por favor, seleccione Grado, Sección y Curso', 
                       style={'padding': '20px', 'textAlign': 'center', 'color': '#7f8c8d'})
    
    df_alumnos_filtrados = df_data[(df_data['grado'] == grado) & 
                                    (df_data['seccion'] == seccion)].copy()
    
    if len(df_alumnos_filtrados) == 0:
        return html.Div('No hay datos disponibles para esta selección', 
                       style={'padding': '20px', 'textAlign': 'center', 'color': '#e74c3c'})
    
    columnas_curso = [col_idx for col_idx, info in mapeo_columnas.items() 
                      if info['curso'] == curso]
    
    if len(columnas_curso) == 0:
        return html.Div(f'No hay competencias registradas para el curso {curso}', 
                       style={'padding': '20px', 'textAlign': 'center', 'color': '#e74c3c'})
    
    competencias = [mapeo_columnas[col]['competencia'] for col in columnas_curso]
    
    alumnos_data = []
    for idx, row in df_alumnos_filtrados.iterrows():
        alumno = {
            'Nro': int(row['alumno_id']),
            'Alumno': row['nombre_alumno']
        }
        
        for col_idx, comp in zip(columnas_curso, competencias):
            nivel = row.iloc[col_idx] if col_idx < len(row) else '-'
            if pd.isna(nivel):
                nivel = '-'
            comp_short = comp[:30] + '...' if len(comp) > 30 else comp
            alumno[comp_short] = str(nivel).strip()
        
        alumnos_data.append(alumno)
    
    headers = [
        html.Th('Nro', style={'padding': '10px', 'border': '1px solid #ddd', 'backgroundColor': '#3498db', 'color': 'white', 'textAlign': 'center', 'position': 'sticky', 'left': '0', 'zIndex': '10', 'minWidth': '50px'}),
        html.Th('Alumno', style={'padding': '10px', 'border': '1px solid #ddd', 'backgroundColor': '#3498db', 'color': 'white', 'textAlign': 'left', 'minWidth': '250px', 'position': 'sticky', 'left': '50px', 'zIndex': '10'})
    ]
    
    for comp in competencias:
        comp_short = comp[:30] + '...' if len(comp) > 30 else comp
        headers.append(
            html.Th(comp_short, style={
                'padding': '10px', 'border': '1px solid #ddd', 
                'backgroundColor': '#2c3e50', 'color': 'white', 
                'textAlign': 'center', 'minWidth': '100px', 
                'fontSize': '12px', 'writingMode': 'horizontal-tb'
            }, title=comp)
        )
    
    def get_nivel_color(nivel):
        colors = {
            'AD': '#d5f4e6',
            'A': '#a9dfbf',
            'B': '#fdeaa1',
            'C': '#f5b7b1',
            '-': '#ecf0f1'
        }
        return colors.get(nivel, '#ecf0f1')
    
    filas = []
    for alumno in alumnos_data:
        celdas = [
            html.Td(alumno['Nro'], style={'padding': '8px', 'border': '1px solid #ddd', 'textAlign': 'center', 'backgroundColor': 'white', 'position': 'sticky', 'left': '0', 'zIndex': '5'}),
            html.Td(alumno['Alumno'], style={'padding': '8px', 'border': '1px solid #ddd', 'backgroundColor': 'white', 'position': 'sticky', 'left': '50px', 'zIndex': '5', 'fontSize': '13px'})
        ]
        
        for comp in competencias:
            comp_short = comp[:30] + '...' if len(comp) > 30 else comp
            nivel = alumno.get(comp_short, '-')
            celdas.append(
                html.Td(nivel, style={
                    'padding': '8px', 'border': '1px solid #ddd', 
                    'textAlign': 'center', 'fontWeight': 'bold',
                    'backgroundColor': get_nivel_color(nivel)
                })
            )
        
        filas.append(html.Tr(celdas))
    
    tabla_html = html.Div([
        html.H3(f'👥 Listado de Estudiantes: {grado} - {seccion} - {curso}', 
               style={'color': '#2c3e50', 'marginBottom': '10px'}),
        html.P(f'Total de estudiantes: {len(alumnos_data)} | Competencias evaluadas: {len(competencias)}', 
              style={'fontSize': '14px', 'color': '#7f8c8d', 'marginBottom': '20px'}),
        
        html.Div([
            html.Table([
                html.Thead(html.Tr(headers)),
                html.Tbody(filas)
            ], style={
                'borderCollapse': 'collapse', 
                'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                'fontSize': '14px'
            })
        ], style={
            'overflowX': 'auto', 
            'overflowY': 'auto',
            'maxHeight': '600px',
            'border': '1px solid #ddd',
            'borderRadius': '5px'
        }),
        
        html.Div([
            html.Div('AD', style={'display': 'inline-block', 'padding': '5px 10px', 'margin': '5px', 'backgroundColor': '#d5f4e6', 'border': '1px solid #27ae60', 'borderRadius': '3px'}),
            html.Div('A', style={'display': 'inline-block', 'padding': '5px 10px', 'margin': '5px', 'backgroundColor': '#a9dfbf', 'border': '1px solid #2ecc71', 'borderRadius': '3px'}),
            html.Div('B', style={'display': 'inline-block', 'padding': '5px 10px', 'margin': '5px', 'backgroundColor': '#fdeaa1', 'border': '1px solid #f39c12', 'borderRadius': '3px'}),
            html.Div('C', style={'display': 'inline-block', 'padding': '5px 10px', 'margin': '5px', 'backgroundColor': '#f5b7b1', 'border': '1px solid #e74c3c', 'borderRadius': '3px'}),
        ], style={'marginTop': '20px', 'textAlign': 'center'})
    ])
    
    return tabla_html

if __name__ == '__main__':
    print("\n🚀 Iniciando Dashboard...")
    print("📍 Servidor web activo")
    app.run(debug=False, host='0.0.0.0', port=8050)
