# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple
import json
import math
import numpy as np
import pandas as pd
import plotly.graph_objects as go

RHO_ACQUA_DEFAULT = 1000.0  # kg/m3
MU_ACQUA_DEFAULT = 1.00e-3  # Pa*s
G = 9.81

# Preset interni di Cd (orientativi e modificabili dall'utente)
# NOTA: sono valori interni di predimensionamento, non da intendersi come valori normativi.
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
    larghezza_m: float
    lunghezza_m: float
    diametro_maggiore_m: float
    diametro_minore_m: float
    altezza_utile_m: float
    profondita_corrente_m: float
    velocita_ms: float
    densita_kgm3: float
    viscosita_pas: float
    angolo_attacco_deg: float
    coeff_ostruzione: float
    coeff_sicurezza: float
    criterio_cd: str                  # 'preset interno' o 'manuale'
    cd_manuale: float
    quota_punto_rotazione_m: float
    delta_livello_idrostatico_m: float
    includi_idrostatica: bool = False


# =============================================================================
# Validazione
# =============================================================================

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


# =============================================================================
# Geometria e idrodinamica
# =============================================================================

def altezza_immersa(d: DatiPila) -> float:
    return min(d.altezza_utile_m, d.profondita_corrente_m)


def coeff_drag(d: DatiPila) -> float:
    if d.criterio_cd == 'manuale':
        return d.cd_manuale
    return PRESET_CD[d.forma]


def larghezza_proiettata(d: DatiPila) -> float:
    theta = math.radians(d.angolo_attacco_deg)
    if d.forma == 'Circolare':
        return d.diametro_m
    if d.forma in {'Rettangolare', 'Rettangolare con prua semicircolare'}:
        # proiezione del rettangolo sul piano normale al flusso
        return abs(d.larghezza_m * math.cos(theta)) + abs(d.lunghezza_m * math.sin(theta))
    # Ellittica: proiezione del diametro equivalente sul piano normale al flusso
    a = d.diametro_maggiore_m / 2.0   # asse maggiore lungo flusso nominale
    b = d.diametro_minore_m / 2.0     # asse minore trasversale
    return 2.0 * math.sqrt((a * math.sin(theta))**2 + (b * math.cos(theta))**2)


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
    Lc = lunghezza_caratteristica_reynolds(d)
    return d.densita_kgm3 * d.velocita_ms * Lc / d.viscosita_pas


def froude(d: DatiPila) -> float:
    h = max(altezza_immersa(d), 1e-9)
    return d.velocita_ms / math.sqrt(G * h)


def forza_idrodinamica_n(d: DatiPila) -> float:
    Cd = coeff_drag(d)
    A = area_proiettata_immersa(d)
    q = pressione_dinamica_pa(d)
    return Cd * q * A * d.coeff_ostruzione * d.coeff_sicurezza


def forza_idrostatica_n(d: DatiPila) -> float:
    if (not d.includi_idrostatica) or d.delta_livello_idrostatico_m <= 0:
        return 0.0
    h = altezza_immersa(d)
    b = larghezza_proiettata(d)
    # risultante differenziale idrostatica su piastra verticale equivalente
    # F = rho*g*b*h*delta_h, interpretata come pressione differenziale uniforme media
    return d.densita_kgm3 * G * b * h * d.delta_livello_idrostatico_m


def forza_totale_n(d: DatiPila) -> float:
    return forza_idrodinamica_n(d) + forza_idrostatica_n(d)


def braccio_risultante_idrodinamica_m(d: DatiPila) -> float:
    # distribuzione uniforme rispetto all'altezza immersa -> baricentro a h/2
    return altezza_immersa(d) / 2.0 + d.quota_punto_rotazione_m


def momento_ribaltante_nm(d: DatiPila) -> float:
    return forza_totale_n(d) * braccio_risultante_idrodinamica_m(d)


# =============================================================================
# Tabelle e commenti
# =============================================================================

def tabella_sintesi(d: DatiPila) -> pd.DataFrame:
    rows = [
        ('Forma', d.forma),
        ('Cd utilizzato [-]', coeff_drag(d)),
        ('Altezza immersa [m]', altezza_immersa(d)),
        ('Larghezza proiettata [m]', larghezza_proiettata(d)),
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
        note.append('Il coefficiente Cd è stato assunto tramite preset interno orientativo. Per verifiche definitive si raccomanda la calibrazione con bibliografia, prove o linee guida adottate nel progetto.')
    if Re < 1e4:
        note.append('Il numero di Reynolds risulta relativamente basso rispetto a casi tipici di piena su pile da ponte. Verificare la coerenza dei parametri di input.')
    elif Re > 1e6:
        note.append('Il numero di Reynolds è elevato: il valore di Cd può risultare sensibile a forma, rugosità e dettagli geometrici locali.')
    if Fr > 1.0:
        note.append('Il numero di Froude supera l’unità: il moto può essere prossimo o oltre il regime critico/supercritico, quindi l’azione idrodinamica potrebbe richiedere valutazioni più raffinate.')
    if d.coeff_ostruzione > 1.2:
        note.append('È stato considerato un coefficiente di ostruzione/debris significativo: la presenza di materiale flottante può governare il risultato.')
    if d.includi_idrostatica and d.delta_livello_idrostatico_m > 0:
        note.append('È stata considerata anche una componente idrostatica differenziale tra monte e valle della pila.')
    if d.forma == 'Rettangolare':
        note.append('Le pile rettangolari sono in genere più sfavorevoli dal punto di vista del drag rispetto a forme più aerodinamiche/idrodinamiche.')
    if d.forma == 'Ellittica':
        note.append('La forma ellittica riduce in genere la larghezza proiettata efficace per certi angoli di attacco e può risultare più efficiente dal punto di vista idrodinamico.')
    if d.forma == 'Rettangolare con prua semicircolare':
        note.append('La forma con prua arrotondata consente in genere un comportamento più favorevole rispetto alla sezione rettangolare pura; il Cd resta comunque fortemente dipendente dai dettagli di progetto.')
    return note


# =============================================================================
# Grafici Plotly
# =============================================================================

def figura_geometria(d: DatiPila) -> go.Figure:
    fig = go.Figure()
    h = altezza_immersa(d)

    # Vista semplificata frontale + linea di pelo libero
    b = larghezza_proiettata(d)
    fig.add_trace(go.Scatter(
        x=[-b/2, b/2, b/2, -b/2, -b/2],
        y=[0, 0, h, h, 0],
        fill='toself', mode='lines', name='Area immersa equivalente',
        line=dict(color='darkslategray', width=3), fillcolor='rgba(80,120,150,0.35)'
    ))
    fig.add_hline(y=h, line_dash='dash', line_color='royalblue', annotation_text='Pelo libero / altezza immersa')
    fig.add_annotation(x=0, y=h/2, text=f'{d.forma}<br>b = {b:.2f} m', showarrow=False, font=dict(size=12))
    fig.update_layout(
        title='Geometria idraulicamente efficace della pila',
        xaxis_title='Larghezza proiettata [m]', yaxis_title='Altezza immersa [m]',
        template='plotly_white', height=430
    )
    fig.update_yaxes(scaleanchor='x', scaleratio=1)
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
    fig.update_layout(title='Forza totale in funzione della velocità', xaxis_title='Velocità [m/s]', yaxis_title='Forza [kN]', template='plotly_white', height=400)
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
    fig.update_layout(title='Forza totale in funzione della profondità della corrente', xaxis_title='Profondità corrente [m]', yaxis_title='Forza [kN]', template='plotly_white', height=400)
    return fig


def export_inputs_json(d: DatiPila) -> bytes:
    return json.dumps(asdict(d), ensure_ascii=False, indent=2).encode('utf-8')
