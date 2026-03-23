# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple
import json
import math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

RHO_ACQUA_DEFAULT = 1000.0  # kg/m3
MU_ACQUA_DEFAULT = 1.00e-3  # Pa*s
G = 9.81

PRESET_CD = {
    'Circolare': 1.20,
    'Rettangolare': 2.00,
    'Ellittica': 0.70,
    'Rettangolare con prua semicircolare': 1.10,
}

@dataclass(frozen=True)
class DatiPila:
    forma: str
    diametro_m: float
    larghezza_m: float          # trasversale
    lunghezza_m: float          # longitudinale
    diametro_maggiore_m: float  # asse lungo nominale
    diametro_minore_m: float    # asse trasversale nominale
    altezza_utile_m: float
    profondita_corrente_m: float
    velocita_ms: float
    densita_kgm3: float
    viscosita_pas: float
    angolo_attacco_deg: float
    coeff_ostruzione: float
    coeff_sicurezza: float
    criterio_cd: str
    cd_manuale: float
    quota_punto_rotazione_m: float
    delta_livello_idrostatico_m: float
    includi_idrostatica: bool = False


def valida_dati(d: DatiPila) -> List[str]:
    err: List[str] = []
    if d.forma not in {'Circolare', 'Rettangolare', 'Ellittica', 'Rettangolare con prua semicircolare'}:
        err.append('La forma selezionata non è supportata.')
    if d.altezza_utile_m <= 0:
        err.append('L’altezza utile della pila deve essere positiva.')
    if d.profondita_corrente_m <= 0:
        err.append('La profondità della corrente deve essere positiva.')
    if d.velocita_ms < 0:
        err.append('La velocità non può essere negativa.')
    if d.densita_kgm3 <= 0:
        err.append('La densità del fluido deve essere positiva.')
    if d.viscosita_pas <= 0:
        err.append('La viscosità dinamica deve essere positiva.')
    if d.coeff_ostruzione <= 0:
        err.append('Il coefficiente di ostruzione / debris factor deve essere positivo.')
    if d.coeff_sicurezza < 1.0:
        err.append('Il coefficiente di sicurezza deve essere almeno pari a 1.0.')
    if d.criterio_cd not in {'preset interno', 'manuale'}:
        err.append('Il criterio del coefficiente Cd non è supportato.')
    if d.criterio_cd == 'manuale' and d.cd_manuale <= 0:
        err.append('Il coefficiente Cd manuale deve essere positivo.')
    if d.quota_punto_rotazione_m < 0:
        err.append('La quota del punto di rotazione non può essere negativa.')
    if d.forma == 'Circolare' and d.diametro_m <= 0:
        err.append('Per la forma circolare il diametro deve essere positivo.')
    if d.forma in {'Rettangolare', 'Rettangolare con prua semicircolare'}:
        if d.larghezza_m <= 0 or d.lunghezza_m <= 0:
            err.append('Per la forma rettangolare larghezza e lunghezza devono essere positive.')
    if d.forma == 'Ellittica':
        if d.diametro_maggiore_m <= 0 or d.diametro_minore_m <= 0:
            err.append('Per la forma ellittica i due diametri devono essere positivi.')
    return err


def altezza_immersa(d: DatiPila) -> float:
    return min(d.altezza_utile_m, d.profondita_corrente_m)


def coeff_drag(d: DatiPila) -> float:
    return d.cd_manuale if d.criterio_cd == 'manuale' else PRESET_CD[d.forma]


def _rotation(theta_deg: float):
    t = math.radians(theta_deg)
    c, s = math.cos(t), math.sin(t)
    return np.array([[c, -s], [s, c]])


def plan_polygon(d: DatiPila, n=120) -> np.ndarray:
    """Restituisce il contorno 2D in pianta della forma reale, centrata in (0,0), prima o dopo rotazione."""
    if d.forma == 'Circolare':
        r = d.diametro_m / 2.0
        ang = np.linspace(0, 2*np.pi, n)
        pts = np.column_stack([r*np.cos(ang), r*np.sin(ang)])
    elif d.forma == 'Rettangolare':
        L = d.lunghezza_m / 2.0
        B = d.larghezza_m / 2.0
        pts = np.array([[-L,-B],[L,-B],[L,B],[-L,B],[-L,-B]], dtype=float)
    elif d.forma == 'Ellittica':
        a = d.diametro_maggiore_m / 2.0
        b = d.diametro_minore_m / 2.0
        ang = np.linspace(0, 2*np.pi, n)
        pts = np.column_stack([a*np.cos(ang), b*np.sin(ang)])
    else:  # Rettangolare con prua semicircolare
        L = d.lunghezza_m
        B = d.larghezza_m
        r = B/2.0
        # asse x = longitudinale, prua verso +x
        x_back = -L/2.0
        x_center_nose = L/2.0 - r
        y_top, y_bot = B/2.0, -B/2.0
        arc = np.linspace(-np.pi/2, np.pi/2, max(40, n//3))
        nose = np.column_stack([x_center_nose + r*np.cos(arc), r*np.sin(arc)])
        pts = np.vstack([
            [x_back, y_bot],
            [x_center_nose, y_bot],
            nose,
            [x_center_nose, y_top],
            [x_back, y_top],
            [x_back, y_bot],
        ]).astype(float)
    rot = _rotation(d.angolo_attacco_deg)
    return pts @ rot.T


def larghezza_proiettata(d: DatiPila) -> float:
    pts = plan_polygon(d)
    # flusso lungo asse x globale; larghezza proiettata sulla normale al flusso = range coordinata y
    return float(np.max(pts[:,1]) - np.min(pts[:,1]))


def lunghezza_caratteristica_reynolds(d: DatiPila) -> float:
    if d.forma == 'Circolare':
        return d.diametro_m
    if d.forma in {'Rettangolare', 'Rettangolare con prua semicircolare'}:
        return max(d.larghezza_m, d.lunghezza_m)
    return max(d.diametro_maggiore_m, d.diametro_minore_m)


def area_proiettata_immersa(d: DatiPila) -> float:
    return larghezza_proiettata(d) * altezza_immersa(d)


def pressione_dinamica_pa(d: DatiPila) -> float:
    return 0.5 * d.densita_kgm3 * d.velocita_ms**2


def reynolds(d: DatiPila) -> float:
    return d.densita_kgm3 * d.velocita_ms * lunghezza_caratteristica_reynolds(d) / d.viscosita_pas


def froude(d: DatiPila) -> float:
    h = max(altezza_immersa(d), 1e-9)
    return d.velocita_ms / math.sqrt(G * h)


def forza_idrodinamica_n(d: DatiPila) -> float:
    return coeff_drag(d) * pressione_dinamica_pa(d) * area_proiettata_immersa(d) * d.coeff_ostruzione * d.coeff_sicurezza


def forza_idrostatica_n(d: DatiPila) -> float:
    if (not d.includi_idrostatica) or d.delta_livello_idrostatico_m <= 0:
        return 0.0
    return d.densita_kgm3 * G * larghezza_proiettata(d) * altezza_immersa(d) * d.delta_livello_idrostatico_m


def forza_totale_n(d: DatiPila) -> float:
    return forza_idrodinamica_n(d) + forza_idrostatica_n(d)


def braccio_risultante_m(d: DatiPila) -> float:
    return altezza_immersa(d) / 2.0 + d.quota_punto_rotazione_m


def momento_ribaltante_nm(d: DatiPila) -> float:
    return forza_totale_n(d) * braccio_risultante_m(d)


def tabella_sintesi(d: DatiPila) -> pd.DataFrame:
    rows = [
        ('Forma', d.forma),
        ('Cd utilizzato [-]', coeff_drag(d)),
        ('Angolo di attacco [°]', d.angolo_attacco_deg),
        ('Altezza immersa [m]', altezza_immersa(d)),
        ('Larghezza proiettata reale [m]', larghezza_proiettata(d)),
        ('Area proiettata immersa [m²]', area_proiettata_immersa(d)),
        ('Pressione dinamica [Pa]', pressione_dinamica_pa(d)),
        ('Numero di Reynolds [-]', reynolds(d)),
        ('Numero di Froude [-]', froude(d)),
        ('Forza idrodinamica [kN]', forza_idrodinamica_n(d) / 1000.0),
        ('Forza idrostatica differenziale [kN]', forza_idrostatica_n(d) / 1000.0),
        ('Forza totale [kN]', forza_totale_n(d) / 1000.0),
        ('Momento ribaltante [kNm]', momento_ribaltante_nm(d) / 1000.0),
    ]
    return pd.DataFrame(rows, columns=['Parametro', 'Valore'])


def commenti_automatici(d: DatiPila) -> List[str]:
    note: List[str] = []
    Re = reynolds(d)
    Fr = froude(d)
    if d.criterio_cd == 'preset interno':
        note.append('Il coefficiente Cd è assunto tramite preset interno orientativo. Per verifiche definitive si raccomanda la calibrazione con bibliografia, prove o linee guida del progetto.')
    note.append('Il grafico della geometria ora mostra la forma reale della sezione in pianta e una vista frontale coerente con la larghezza proiettata rispetto all’angolo di attacco.')
    if Re < 1e4:
        note.append('Il numero di Reynolds risulta relativamente basso rispetto a casi tipici di piena su pile da ponte: verificare la coerenza dei parametri di input.')
    elif Re > 1e6:
        note.append('Il numero di Reynolds è elevato: il valore di Cd può risultare sensibile a forma, rugosità e dettagli geometrici locali.')
    if Fr > 1.0:
        note.append('Il numero di Froude supera l’unità: il moto può essere prossimo o oltre il regime critico/supercritico, quindi l’azione idrodinamica potrebbe richiedere valutazioni più raffinate.')
    if d.coeff_ostruzione > 1.2:
        note.append('È stato considerato un coefficiente di ostruzione/debris significativo: la presenza di materiale flottante può governare il risultato.')
    if d.includi_idrostatica and d.delta_livello_idrostatico_m > 0:
        note.append('È stata considerata anche una componente idrostatica differenziale tra monte e valle della pila.')
    return note


def figura_geometria_2d(d: DatiPila) -> go.Figure:
    pts = plan_polygon(d)
    b = larghezza_proiettata(d)
    h = altezza_immersa(d)
    fig = make_subplots(rows=1, cols=2, subplot_titles=('Vista in pianta della forma reale', 'Vista frontale idraulica'))

    # Pianta reale
    fig.add_trace(go.Scatter(x=pts[:,0], y=pts[:,1], fill='toself', mode='lines', name='Pianta reale', line=dict(color='black', width=2), fillcolor='rgba(120,160,200,0.35)'), row=1, col=1)
    # asse flusso
    xspan = max(np.ptp(pts[:,0]), 1.0)
    yspan = max(np.ptp(pts[:,1]), 1.0)
    fig.add_annotation(x=-xspan*0.6, y=max(pts[:,1])+0.15*yspan, ax=xspan*0.2, ay=max(pts[:,1])+0.15*yspan, xref='x1', yref='y1', axref='x1', ayref='y1', showarrow=True, arrowhead=3, arrowsize=1.2, arrowwidth=2, text='Direzione del flusso')

    # Vista frontale coerente con proiezione
    fig.add_trace(go.Scatter(x=[-b/2, b/2, b/2, -b/2, -b/2], y=[0,0,h,h,0], fill='toself', mode='lines', name='Proiezione frontale', line=dict(color='darkslategray', width=2), fillcolor='rgba(70,130,180,0.35)'), row=1, col=2)
    fig.add_hline(y=h, line_dash='dash', line_color='royalblue', row=1, col=2)
    fig.add_annotation(x=0, y=h/2, xref='x2', yref='y2', text=f'b = {b:.2f} m<br>h = {h:.2f} m', showarrow=False)

    fig.update_xaxes(title_text='x longitudinale [m]', row=1, col=1)
    fig.update_yaxes(title_text='y trasversale [m]', row=1, col=1, scaleanchor='x', scaleratio=1)
    fig.update_xaxes(title_text='Larghezza proiettata [m]', row=1, col=2)
    fig.update_yaxes(title_text='Altezza immersa [m]', row=1, col=2, scaleanchor='x2', scaleratio=1)
    fig.update_layout(title='Geometria della pila - rappresentazione coerente', template='plotly_white', height=480, showlegend=False)
    return fig


def figura_geometria_3d(d: DatiPila) -> go.Figure:
    pts = plan_polygon(d, n=160)
    z_bottom = 0.0
    z_top = d.altezza_utile_m
    h_imm = altezza_immersa(d)

    x = pts[:,0]
    y = pts[:,1]
    z0 = np.full_like(x, z_bottom, dtype=float)
    z1 = np.full_like(x, z_top, dtype=float)

    fig = go.Figure()
    # base e top come linee chiuse
    fig.add_trace(go.Scatter3d(x=x, y=y, z=z0, mode='lines', line=dict(color='dimgray', width=6), name='Base'))
    fig.add_trace(go.Scatter3d(x=x, y=y, z=z1, mode='lines', line=dict(color='black', width=6), name='Sommità'))

    # generatrici verticali campionate
    sample_idx = np.linspace(0, len(x)-1, 28, dtype=int)
    for i in sample_idx:
        fig.add_trace(go.Scatter3d(x=[x[i], x[i]], y=[y[i], y[i]], z=[z_bottom, z_top], mode='lines', line=dict(color='gray', width=3), showlegend=False))

    # pelo libero
    xx = np.linspace(np.min(x)-0.3*np.ptp(x)-0.2, np.max(x)+0.3*np.ptp(x)+0.2, 2)
    yy = np.linspace(np.min(y)-0.3*np.ptp(y)-0.2, np.max(y)+0.3*np.ptp(y)+0.2, 2)
    XX, YY = np.meshgrid(xx, yy)
    ZZ = np.full_like(XX, h_imm)
    fig.add_trace(go.Surface(x=XX, y=YY, z=ZZ, opacity=0.35, showscale=False, colorscale=[[0,'rgba(65,105,225,0.4)'],[1,'rgba(65,105,225,0.4)']], name='Pelo libero'))

    # freccia flusso semplificata con segmento e cono
    span = max(np.ptp(x), np.ptp(y), 1.0)
    x0 = np.min(x) - 0.8*span
    x1 = x0 + 0.6*span
    y0 = 0.0
    zflow = h_imm*0.7
    fig.add_trace(go.Scatter3d(x=[x0, x1], y=[y0, y0], z=[zflow, zflow], mode='lines', line=dict(color='firebrick', width=10), name='Flusso'))
    fig.add_trace(go.Cone(x=[x1], y=[y0], z=[zflow], u=[0.25*span], v=[0], w=[0], sizemode='absolute', sizeref=0.18*span, colorscale=[[0,'firebrick'],[1,'firebrick']], showscale=False, name='Direzione flusso'))

    fig.update_layout(
        title='Forma 3D della pila',
        template='plotly_white',
        height=560,
        scene=dict(
            xaxis_title='x longitudinale [m]',
            yaxis_title='y trasversale [m]',
            zaxis_title='z verticale [m]',
            aspectmode='data',
            camera=dict(eye=dict(x=1.6, y=1.4, z=1.1))
        ),
        showlegend=False
    )
    return fig


def figura_forza_vs_velocita(d: DatiPila) -> go.Figure:
    v = np.linspace(0.0, max(d.velocita_ms * 1.6, 0.5), 80)
    F = []
    for vv in v:
        dd = DatiPila(**{**asdict(d), 'velocita_ms': float(vv)})
        F.append(forza_totale_n(dd) / 1000.0)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=v, y=F, mode='lines', name='Forza totale [kN]'))
    fig.add_vline(x=d.velocita_ms, line_dash='dot', line_color='firebrick', annotation_text='Velocità di progetto')
    fig.update_layout(title='Forza totale in funzione della velocità', xaxis_title='Velocità [m/s]', yaxis_title='Forza [kN]', template='plotly_white', height=380)
    return fig


def figura_forza_vs_profondita(d: DatiPila) -> go.Figure:
    hh = np.linspace(0.0, max(d.altezza_utile_m * 1.1, d.profondita_corrente_m * 1.1, 0.5), 80)
    F = []
    for h in hh:
        dd = DatiPila(**{**asdict(d), 'profondita_corrente_m': float(h)})
        F.append(forza_totale_n(dd) / 1000.0)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hh, y=F, mode='lines', name='Forza totale [kN]'))
    fig.add_vline(x=d.profondita_corrente_m, line_dash='dot', line_color='firebrick', annotation_text='Profondità di progetto')
    fig.update_layout(title='Forza totale in funzione della profondità della corrente', xaxis_title='Profondità corrente [m]', yaxis_title='Forza [kN]', template='plotly_white', height=380)
    return fig


def export_inputs_json(d: DatiPila) -> bytes:
    return json.dumps(asdict(d), ensure_ascii=False, indent=2).encode('utf-8')
