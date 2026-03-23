# -*- coding: utf-8 -*-
import json
import streamlit as st
from src import (
    DatiPila, PRESET_CD, RHO_ACQUA_DEFAULT, MU_ACQUA_DEFAULT,
    valida_dati, tabella_sintesi, figura_geometria_2d, figura_geometria_3d,
    figura_forza_vs_velocita, figura_forza_vs_profondita,
    commenti_automatici, export_inputs_json,
    forza_totale_n, forza_idrodinamica_n, forza_idrostatica_n, momento_ribaltante_nm,
)

DEFAULTS = {
    'forma': 'Circolare',
    'diametro_m': 1.80,
    'larghezza_m': 2.00,
    'lunghezza_m': 4.00,
    'diametro_maggiore_m': 4.00,
    'diametro_minore_m': 2.00,
    'altezza_utile_m': 6.00,
    'profondita_corrente_m': 4.00,
    'velocita_ms': 2.00,
    'densita_kgm3': RHO_ACQUA_DEFAULT,
    'viscosita_pas': MU_ACQUA_DEFAULT,
    'angolo_attacco_deg': 0.0,
    'coeff_ostruzione': 1.00,
    'coeff_sicurezza': 1.20,
    'criterio_cd': 'preset interno',
    'cd_manuale': 1.20,
    'quota_punto_rotazione_m': 0.00,
    'delta_livello_idrostatico_m': 0.00,
    'includi_idrostatica': False,
}

st.set_page_config(page_title='Forza idrodinamica su pila da ponte', layout='wide')
st.title('ForzaIdrodinamicaPila v1.1 - Spinta idrodinamica su pila da ponte')
st.caption('Versione 1.1: rappresentazione 2D coerente della forma reale e vista 3D della pila con grafici Plotly.')

with st.sidebar:
    st.header('Import / Export input')
    up = st.file_uploader('Reimporta input JSON', type=['json'])
    defaults = DEFAULTS.copy()
    if up is not None:
        try:
            defaults.update(json.load(up))
            st.success('Input importati correttamente.')
        except Exception:
            st.error('JSON non valido.')

    st.header('Forma della pila')
    forma = st.selectbox('Forma in pianta della pila', ['Circolare', 'Rettangolare', 'Ellittica', 'Rettangolare con prua semicircolare'], index=['Circolare', 'Rettangolare', 'Ellittica', 'Rettangolare con prua semicircolare'].index(defaults['forma']))

    if forma == 'Circolare':
        diametro_m = st.number_input('Diametro [m]', 0.10, 20.0, float(defaults['diametro_m']), 0.05)
        larghezza_m = defaults['larghezza_m']
        lunghezza_m = defaults['lunghezza_m']
        diametro_maggiore_m = defaults['diametro_maggiore_m']
        diametro_minore_m = defaults['diametro_minore_m']
    elif forma in {'Rettangolare', 'Rettangolare con prua semicircolare'}:
        larghezza_m = st.number_input('Larghezza trasversale [m]', 0.10, 20.0, float(defaults['larghezza_m']), 0.05)
        lunghezza_m = st.number_input('Lunghezza longitudinale [m]', 0.10, 40.0, float(defaults['lunghezza_m']), 0.05)
        diametro_m = defaults['diametro_m']
        diametro_maggiore_m = defaults['diametro_maggiore_m']
        diametro_minore_m = defaults['diametro_minore_m']
    else:
        diametro_maggiore_m = st.number_input('Diametro / asse maggiore [m]', 0.10, 40.0, float(defaults['diametro_maggiore_m']), 0.05)
        diametro_minore_m = st.number_input('Diametro / asse minore [m]', 0.10, 20.0, float(defaults['diametro_minore_m']), 0.05)
        diametro_m = defaults['diametro_m']
        larghezza_m = defaults['larghezza_m']
        lunghezza_m = defaults['lunghezza_m']

    st.header('Parametri idraulici')
    altezza_utile_m = st.number_input('Altezza utile della pila [m]', 0.10, 100.0, float(defaults['altezza_utile_m']), 0.10)
    profondita_corrente_m = st.number_input('Profondità della corrente [m]', 0.05, 100.0, float(defaults['profondita_corrente_m']), 0.10)
    velocita_ms = st.number_input('Velocità media della corrente [m/s]', 0.0, 20.0, float(defaults['velocita_ms']), 0.10)
    densita_kgm3 = st.number_input('Densità del fluido [kg/m³]', 500.0, 1500.0, float(defaults['densita_kgm3']), 10.0)
    viscosita_pas = st.number_input('Viscosità dinamica [Pa·s]', 1e-6, 0.1, float(defaults['viscosita_pas']), 1e-4, format='%.5f')
    angolo_attacco_deg = st.number_input('Angolo di attacco del flusso [°]', 0.0, 90.0, float(defaults['angolo_attacco_deg']), 1.0)

    st.header('Coefficienti')
    criterio_cd = st.selectbox('Criterio per Cd', ['preset interno', 'manuale'], index=['preset interno', 'manuale'].index(defaults['criterio_cd']))
    if criterio_cd == 'preset interno':
        st.info(f"Preset interno Cd per {forma}: {PRESET_CD[forma]:.2f}")
        cd_manuale = defaults['cd_manuale']
    else:
        cd_manuale = st.number_input('Cd manuale [-]', 0.05, 10.0, float(defaults['cd_manuale']), 0.05)
    coeff_ostruzione = st.number_input('Coefficiente di ostruzione / debris factor [-]', 0.10, 5.0, float(defaults['coeff_ostruzione']), 0.05)
    coeff_sicurezza = st.number_input('Coefficiente di sicurezza [-]', 1.0, 5.0, float(defaults['coeff_sicurezza']), 0.05)

    st.header('Momento e idrostatica')
    quota_punto_rotazione_m = st.number_input('Quota del punto di rotazione / riferimento momento [m]', 0.0, 50.0, float(defaults['quota_punto_rotazione_m']), 0.10)
    includi_idrostatica = st.checkbox('Considera spinta idrostatica differenziale', value=bool(defaults['includi_idrostatica']))
    if includi_idrostatica:
        delta_livello_idrostatico_m = st.number_input('Differenza di livello idrico monte-valle [m]', 0.0, 20.0, float(defaults['delta_livello_idrostatico_m']), 0.05)
    else:
        delta_livello_idrostatico_m = 0.0

d = DatiPila(
    forma=forma,
    diametro_m=diametro_m,
    larghezza_m=larghezza_m,
    lunghezza_m=lunghezza_m,
    diametro_maggiore_m=diametro_maggiore_m,
    diametro_minore_m=diametro_minore_m,
    altezza_utile_m=altezza_utile_m,
    profondita_corrente_m=profondita_corrente_m,
    velocita_ms=velocita_ms,
    densita_kgm3=densita_kgm3,
    viscosita_pas=viscosita_pas,
    angolo_attacco_deg=angolo_attacco_deg,
    coeff_ostruzione=coeff_ostruzione,
    coeff_sicurezza=coeff_sicurezza,
    criterio_cd=criterio_cd,
    cd_manuale=cd_manuale,
    quota_punto_rotazione_m=quota_punto_rotazione_m,
    delta_livello_idrostatico_m=delta_livello_idrostatico_m,
    includi_idrostatica=includi_idrostatica,
)

errori = valida_dati(d)
if errori:
    for e in errori:
        st.error(e)
    st.stop()

Fid_kN = forza_idrodinamica_n(d) / 1000.0
Fidr_kN = forza_idrostatica_n(d) / 1000.0
Ftot_kN = forza_totale_n(d) / 1000.0
M_kNm = momento_ribaltante_nm(d) / 1000.0

df = tabella_sintesi(d)
note = commenti_automatici(d)

c1, c2, c3, c4 = st.columns(4)
c1.metric('Forza idrodinamica [kN]', f"{Fid_kN:.1f}")
c2.metric('Forza idrostatica [kN]', f"{Fidr_kN:.1f}")
c3.metric('Forza totale [kN]', f"{Ftot_kN:.1f}")
c4.metric('Momento ribaltante [kNm]', f"{M_kNm:.1f}")

t1, t2, t3, t4 = st.tabs(['Sintesi', 'Geometria 2D Plotly', 'Forma 3D Plotly', 'Grafici + note'])
with t1:
    st.dataframe(df, use_container_width=True)
    st.download_button('Scarica sintesi CSV', df.to_csv(index=False).encode('utf-8'), 'forza_idrodinamica_pila_sintesi.csv', 'text/csv')
    st.download_button('Salva input JSON', export_inputs_json(d), 'forza_idrodinamica_pila_input.json', 'application/json')
with t2:
    st.plotly_chart(figura_geometria_2d(d), use_container_width=True)
with t3:
    st.plotly_chart(figura_geometria_3d(d), use_container_width=True)
with t4:
    st.plotly_chart(figura_forza_vs_velocita(d), use_container_width=True)
    st.plotly_chart(figura_forza_vs_profondita(d), use_container_width=True)
    for n in note:
        st.markdown(f'- {n}')
    st.info('La v1.1 corregge la rappresentazione grafica della forma: la vista in pianta e la vista frontale sono ora coerenti con la geometria realmente selezionata e con l’angolo di attacco del flusso.')
