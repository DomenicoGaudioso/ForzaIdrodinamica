# ForzaIdrodinamicaPila v1.0

Web app professionale in **Python + Streamlit** per il **predimensionamento della forza idrodinamica su una pila da ponte**.

## Obiettivo dell'app
L'app consente di stimare la forza idrodinamica principale su una pila di ponte investita da una corrente, con possibilità di scegliere la forma in pianta della pila e valutare il momento ribaltante associato.

## Forme supportate
- **Circolare**
- **Rettangolare**
- **Ellittica**
- **Rettangolare con prua semicircolare**

## Impostazione fisica adottata
La forza idrodinamica principale è stimata con la classica formulazione di drag:

\[
F_d = \tfrac{1}{2}\,\rho\,C_d\,A\,V^2
\]

corretta da:
- coefficiente di ostruzione / debris factor;
- coefficiente di sicurezza.

L'app può inoltre considerare, in modo opzionale, una **componente idrostatica differenziale** dovuta a un dislivello idrico tra monte e valle della pila.

## Input principali
- forma della pila;
- dimensioni geometriche;
- altezza utile della pila;
- profondità della corrente;
- velocità media della corrente;
- densità e viscosità del fluido;
- angolo di attacco del flusso;
- criterio per il coefficiente `Cd` (preset interno oppure manuale);
- coefficiente di ostruzione;
- coefficiente di sicurezza;
- quota del punto di riferimento per il momento;
- dislivello idrostatico opzionale.

## Output principali
- larghezza proiettata;
- area proiettata immersa;
- pressione dinamica;
- numero di Reynolds;
- numero di Froude;
- forza idrodinamica;
- forza idrostatica differenziale opzionale;
- forza totale;
- momento ribaltante.

## Grafici Plotly
- geometria idraulicamente efficace della pila;
- forza totale in funzione della velocità;
- forza totale in funzione della profondità della corrente.

## Struttura del progetto
```text
ForzaIdrodinamicaPila/
├── app.py
├── src.py
├── requirements.txt
├── README.md
└── prompt.txt
```

## Avvio rapido
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Nota importante
La v1.0 è pensata per il **predimensionamento tecnico**. Il coefficiente di drag può dipendere in modo sensibile da forma, Reynolds, rugosità, debris, interazione con il pelo libero e dettagli geometrici locali. Per verifiche definitive si raccomandano riferimenti progettuali specifici, bibliografia tecnica coerente con il caso di studio e, se necessario, modellazioni idrauliche più raffinate.
