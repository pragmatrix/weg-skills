---
name: etg24-portal
description: Dokumente aus dem ETG24-Portal einer Hausverwaltung sichten und herunterladen. Für neue Dokumente im Portal, einen Abgleich von Portal und Ablage oder Unterlagen zu einer Versammlung.
---

# ETG24-Portal

ETG24 ist ein Online-Portal, in dem eine Hausverwaltung die Dokumente der Gemeinschaft und je Einheit bereitstellt.
Abgelegt wird nach dem Skill `weg-eigentuemer-ablage`.

## Abgleichliste

Die **Abgleichliste** `Verwaltung/<Verwaltung>/ETG24-Abgleich.md` liegt im Ordner der Verwaltung, die das Portal
betreibt. Sie nennt jedes Dokument im Portal und sagt, wo es in der Ablage liegt oder warum es nicht abgelegt ist.
Ihr Kopf nennt die Adresse des Objekts im Portal und die **Bereiche**: „Objekt“ für die Dokumente der Gemeinschaft
und „Einheit N“ für jede Einheit des Nutzers, jeweils mit Pfad. Je Bereich folgt ein Abschnitt `## <Bereich>` mit der
Tabelle `| Kategorie | Titel im Portal | Datum | Größe | Ablage | Portal |`.

Fehlt die Abgleichliste, legst du sie in diesem Aufbau an. Die Adresse des Objekts und die IDs der Einheiten liest du
aus der Adresszeile, wenn der Nutzer angemeldet ist.

## Portal

- Pfade unter der Adresse des Objekts:
  - `/documents`: Dokumente der Gemeinschaft, in Kategorien
  - `/units/<ID der Einheit>/documents`: Dokumente einer Einheit
  - `/votings`: Versammlungen und Abstimmungen
  - `/posts`: Beiträge der Verwaltung. Die Liste zeigt nur angepinnte, nicht archivierte Beiträge.
- Die Listen laden beim Scrollen nach. `_etg.load()` scrollt bis zum Ende.
- Die Übersichtsseite einer Einheit zeigt Telefonnummer und E-Mail der Eigentümer. Öffne direkt `/documents`.
- Anmelden muss sich der Nutzer selbst. Bitte ihn, das Portal im Tab der Claude-Tabgruppe zu öffnen.

## Browser

Auf ETG24 lädt die Seite nie fertig. Screenshot, `get_page_text`, `find` und `read_page` brechen deshalb mit
Zeitüberschreitung ab. Arbeite nur mit `javascript_tool`. Seine Ausgabe wird nach etwa 1.500 Zeichen abgeschnitten.
Längere Ergebnisse schickst du mit `_etg.save()` als Datei an den Empfänger.

Ein Aufruf, der länger als etwa 10 Sekunden wartet, endet oft mit „Detached while handling command“. Die Seite
läuft dabei weiter. Lange Arbeit startest du deshalb mit `_etg.start()` im Hintergrund und fragst `_etg.res` in
einem eigenen, kurzen Aufruf ab.

Zum Wechseln zwischen Objekt und Einheiten ohne Neuladen (der Helfer bleibt geladen):

```js
history.pushState({}, '', BASIS + PFAD); window.dispatchEvent(new PopStateEvent('popstate'));
```

## Zugriff auf den Empfänger

Der Empfänger aus dem Ablauf läuft auf 127.0.0.1. Der Browser lässt app.etg24.de nur mit einer Berechtigung der
Website darauf zugreifen. Brave führt dafür zwei Einträge: „Lokales Netzwerk“ und „Apps auf diesem Gerät“. Für
127.0.0.1 zählt der zweite. Ist die Abfrage offen, hängt `fetch` ohne Fehler. Ist sie abgelehnt, meldet `fetch`
„Failed to fetch“. Den Zustand zeigt dieser Aufruf im Portal-Tab:

```js
await navigator.permissions.query({name: 'loopback-network'}).then((p) => p.state)
```

Bei `prompt` oder `denied` öffnet der Nutzer in einem beliebigen Tab desselben Browserprofils
`brave://settings/content/siteDetails?site=https%3A%2F%2Fapp.etg24.de` und stellt „Apps auf diesem Gerät“ auf
„Zulassen“. Danach lädst du den Portal-Tab neu. Seiten unter `brave://` kann die Erweiterung nicht
öffnen.

## Text lesen ohne Download

Die Vorschau eines Dokuments hat eine Ansicht „Text“ mit dem Inhalt, den das Portal aus dem PDF gelesen hat. Zum
reinen Lesen genügt sie, ganz ohne Empfänger: Zeile anklicken, in der Vorschau (`[role=dialog]`) den Knopf „Text“
klicken und `innerText` der Vorschau lesen. Für mehrere Dokumente läuft das wie `_etg.start()` im Hintergrund. Zitate
und Beträge prüfst du danach am PDF.

## Direktlinks

Ein Dokument hat eine dauerhafte Adresse: die Dokumentenliste seines Bereichs mit `?document=ID`, etwa
`…/documents?document=6258d481-…`. Sie öffnet die Vorschau des Dokuments, auch bei direktem Aufruf, wenn der Nutzer
angemeldet ist. `_etg.rows()` liefert sie je Zeile als `url`, die ID als `id`.

Die Direktlinks stehen in der letzten Spalte „Portal“ der Abgleichliste. `just etg24-link DATEI` gibt den Direktlink
zu einer Datei der Ablage aus, `just etg24-open DATEI` öffnet ihn im Browser. Ein Quellenlink auf ein Dokument im
Portal nimmt diese Adresse.

## Beiträge

Ein Beitrag hat keine eigene Adresse im Portal, und archivierte Beiträge fehlen in der Liste `/posts`. Alle
Beiträge, auch archivierte, liefert die Abfrage `content.posts`. Sie läuft im Portal-Tab mit dem Token aus
`localStorage` und dem Header `tenant`. Den Mandanten (`tenant`) und die Objekt-ID (`nodeId`) liest sie aus der
Adresse des Objekts. Die Adresse der API liest sie aus den Netzwerkanfragen, die die Seite schon gestellt hat. Findet
sie keine, bricht sie ab, bevor der Token die Seite verlässt. Dann lädst du den Portal-Tab neu. Gib den Token nie aus.

```js
const api = performance.getEntriesByType('resource').map((e) => e.name)
  .find((url) => url.includes('/api/internal/v1/query/'));
if (!api) throw new Error('API-Adresse nicht gefunden, Portal-Tab neu laden');
const [, , tenant, ...rest] = location.pathname.split('/');
const nodeId = rest[rest.indexOf('objects') + 1];
const tok = localStorage.getItem('etg24.auth.token');
const r = await fetch(new URL('/api/internal/v1/query/content.posts', api), {
  method: 'POST',
  headers: {'Content-Type': 'application/json', Authorization: 'Bearer ' + tok, tenant},
  body: JSON.stringify({nodeId, searchTerm: 'Suchwort', limit: 20}),
});
```

Die Antwort enthält je Beitrag `id`, `title`, `description` (der Text), `publishedOn`, `isArchived`, `pinnedUntil`,
`roleTypes` (Zielgruppe) und `nodeId`. Wo der Beitrag veröffentlicht ist, nennt `nodes`: das Objekt selbst oder eine
Objektgruppe der Verwaltung wie „Alle Objekte“. Einen Verfasser liefert die Abfrage nicht.

Einen Direktlink auf einen Beitrag gibt es nicht, auch `/posts?post=ID` öffnet nichts. Ein Beitrag wird deshalb
als Abschrift abgelegt (`JJJJMMTT Beitrag Titel (ETG24).md`), und Verweise zeigen auf diese Abschrift. Die Abschrift
nennt im Kopf Titel, `id`, Ort der Veröffentlichung (Objekt oder Objektgruppe), Datum mit Uhrzeit, Zielgruppe und ob
der Beitrag archiviert ist.

## Abstimmungen

Eine Versammlung steht unter `/votings` als Abstimmung mit den Reitern „Übersicht“ und „Tagesordnungspunkte“. Die
Liste der TOPs kürzt die Texte. Den vollen Wortlaut zeigt erst die Detailansicht eines TOPs. Sie öffnet sich mit einem
Klick auf die Karte des TOPs, das `div` mit `cursor: pointer` um den Titel. Den Text liest du aus `innerText` der
Vorschau (`[role=dialog]`). Einen Download gibt es dort nicht. Der Link mit dem Namen der Versammlung führt zurück zur
Liste. Für alle TOPs läuft das wie `_etg.start()` im Hintergrund.

Die Detailansicht nennt nach dem Text das Ergebnis und unter „Einstellungen“ den Stimmgewichtsmodus und den
Mehrheitsmodus. Ein TOP mit abgegebenen Stimmen hat zusätzlich den Reiter „Stimmen“.

Eine Abstimmung wird als Abschrift in `Versammlungen/` abgelegt (`JJJJMMTT Inhalt Versammlung JJJJ (ETG24).md`). Der
Kopf nennt die Quelle mit der Adresse der Abstimmung als Link, das Abrufdatum und den Stand der Abstimmung (etwa
„Gestartet“). Je TOP folgt `## TOP n. Titel` mit dem Text der Detailansicht. Ergebnis und Einstellungen stehen nicht
im Text, sondern in einer Tabelle unter dem TOP:

| Ergebnis | Stimmgewichtsmodus | Mehrheitsmodus |
|---|---|---|
| Beschluss zustande gekommen | Einheiten | Allstimmig |

Das Ergebnis lautet „Beschluss zustande gekommen“ bei einer Verkündung, „keine Beschlussfassung“ beim Vermerk „Es
erfolgte keine Beschlussfassung“, „Informationspunkt“ bei einem TOP ohne Einstellungen und sonst „kein Ergebnis“.
Was der Reiter „Stimmen“ zeigt, steht in Klammern dahinter.

## Werkzeuge

Helfer und Skripte liegen neben dieser Datei, `<Skill-Ordner>` steht unten für diesen Ordner. Die `justfile` des
Projekts bindet die Rezepte ein mit `import '.claude/skills/etg24-portal/etg24.just'`, dazu die Rezepte des Skills
`weg-eigentuemer-ablage`. Fehlt der Import, trägst du ihn ein. Ein neues Projekt richtet
der Skill `weg-eigentuemer-ablage` ein (Abschnitt Neues Projekt einrichten). Die Skripte nutzen `find_dupes.py` aus
`weg-eigentuemer-ablage`. Beide Skills müssen deshalb im selben Ordner installiert sein.

## Ablauf

1. Empfänger im Hintergrund starten, mit einem neuen, leeren Ordner im Scratchpad als Ziel:
   `just etg24-recv ZIELORDNER`. Er speichert, was die Seite schickt, und liefert den Helfer `etg24.js` aus.
2. Helfer in den Portal-Tab laden, nach jedem Neuladen der Seite erneut. Starte das Laden ohne `await` und frage
   das Ergebnis mit einem Zeitlimit ab, denn ohne Berechtigung hängt der Aufruf (siehe „Zugriff auf den
   Empfänger“):
   `window.__load = fetch('http://127.0.0.1:8765/etg24.js').then((r) => r.text()).then((t) => (0, eval)(t))`.
   Fertig ist der Schritt, wenn `window.__load` „etg24 bereit“ liefert.
3. Die Liste jedes Bereichs exportieren: `await _etg.load()` und danach
   `await _etg.save('objekt.json', JSON.stringify(_etg.rows()))`. Der Dateiname nennt den Bereich der Abgleichliste:
   `objekt.json` für „Objekt“, `einheit-4.json` für „Einheit 4“.
4. `python3 <Skill-Ordner>/etg24_abgleich.py ZIELORDNER/*.json` nennt jede Zeile, die noch nicht in der
   Abgleichliste steht, mit Kandidaten aus der Ablage gleicher Größe.
5. Dem Nutzer die neuen Dokumente vorschlagen, gruppiert nach dem Thema, zu dem sie gehören (Versammlung, TOP,
   Vorgang). Er wählt aus. Downloads brauchen seine Zustimmung.
6. In den Bereich des Dokuments wechseln, `await _etg.load()` aufrufen und den Download starten:
   `_etg.start([[titel, nr, präfix], …])`. Den Titel schreibst du so, wie `_etg.rows()` ihn
   liefert. Bei gleichem Titel wählt `nr` das wievielte Dokument, gezählt ab 0. Dann fragst du `_etg.res` ab, bis „FERTIG“ kommt.
7. `just dup ZIELORDNER/*` zeigt, welche Downloads schon in der Ablage liegen. Die neuen legst du nach dem Skill
   `weg-eigentuemer-ablage` ab.
8. `python3 <Skill-Ordner>/etg24_link.py fill ZIELORDNER/*.json` trägt die Direktlinks in die Spalte „Portal“ ein.
9. Abgeschlossen ist der Durchgang, wenn jede Zeile aus Schritt 4 in der Abgleichliste steht, mit Link oder Grund
   und mit Direktlink, und `just qa` nichts meldet. Danach den Empfänger beenden: `pkill -f etg24_recv.py`.
