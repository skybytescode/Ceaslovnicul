# Ceaslovnicul

Ceaslovul cel Mare ca aplicație web (PWA): deschide singur slujba ceasului după ora
Atenei și o rânduiește pentru ziua de azi (zi a săptămânii, Post Mare, posturi,
Penticostar, Triod, Săptămâna Luminată, sfinții zilei, glasul de rând).

Sursa textelor: <https://sites.google.com/site/ortodox007/> (ediția din 2003).
Câteva texte pe care site-ul le dă doar prescurtat sunt de pe <https://doxologia.ro/>;
sunt notate în `build.py`, iar `source/expansions.txt` arată sursa fiecărui text completat.
Câteva rugăciuni și irmoase au fost completate de autorul aplicației; sunt notate tot acolo.
Pe stil vechi, sfinții zilei și postul vin de pe <https://calendar.ortodox.md/> (`tools/fetch_vechi.py`, `source/vechi/`).
Permisiunea de republicare a textelor de pe aceste site-uri nu a fost verificată.

Aplicația: <https://skybytescode.github.io/Ceaslovnicul/>

## Cum funcționează

- `docs/data/services.json`: fiecare paragraf din sursă, cu o condiție `w`.
  Ce nu se citește azi rămâne în date și se vede cu butonul ☰ (Rânduiala completă).
- `docs/js/liturgy.js`: Paștele, glasul, evanghelia, perioadele, troparele,
  condacele și catismele zilei.
- `docs/js/app.js`: urmează ceasul și afișează slujba.

Seara (Vecernia, Pavecernița) troparele sunt ale zilei următoare, ca în sursă.

## Reconstruire și teste

```sh
tools/fetch_source.sh   # sursa → source/blocks/
python3 build.py        # source/blocks/ + regulile → docs/data/
node test_liturgy.js    # verifică motorul față de calendarul site-ului, 2018–2037
```

## Rulare locală

```sh
cd docs && python3 -m http.server 8010
```

Altă zi sau altă slujbă: <http://localhost:8010/?d=2027-03-22&s=05-ceasul-3>
