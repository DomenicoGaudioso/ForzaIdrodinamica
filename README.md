# ForzaIdrodinamicaPila v1.1
![Testo alternativo](socialFIdrPila.png)
Web app professionale in **Python + Streamlit** per il **predimensionamento della forza idrodinamica su una pila da ponte**.

## Novità della v1.1
- **vista 2D coerente** della forma della pila:
  - pianta reale della sezione;
  - vista frontale coerente con la larghezza proiettata rispetto all’angolo di attacco;
- **vista 3D Plotly** della forma della pila;
- mantenimento di tutte le funzioni della v1.0.

## Forme supportate
- Circolare
- Rettangolare
- Ellittica
- Rettangolare con prua semicircolare

## Logica di calcolo
La forza idrodinamica principale è ancora stimata con la classica formulazione di drag:
\[
F_d = \tfrac{1}{2}\rho C_d A V^2
\]
con fattori aggiuntivi per ostruzione / debris e sicurezza.

## Miglioria grafica fondamentale
La rappresentazione della geometria non usa più un rettangolo equivalente unico come sostituto della sezione reale. La v1.1 mostra invece:
- il **contorno reale in pianta** della forma selezionata;
- la **proiezione frontale reale** rispetto al flusso;
- la **forma estrusa in 3D** lungo l’altezza utile della pila.

## Avvio rapido
```bash
pip install -r requirements.txt
streamlit run app.py
```
