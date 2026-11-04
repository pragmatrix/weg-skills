// Helfer für das ETG24-Portal. Der Empfänger liefert diesen Helfer unter /etg24.js aus. Die Seite lädt ihn nach
// jedem Neuladen erneut. Danach stehen unter window._etg bereit:
//   await _etg.load()                 Liste etwa 8 Sekunden lang nachladen, gibt {zeilen, fertig} zurück
//   _etg.rows()                       Zeilen der aktuellen Liste: {id, url, title, date, category, size, type}
//   await _etg.save(name, text)       Text als Datei an den Empfänger schicken (z. B. die Liste als JSON)
//   _etg.start([[titel, nr, präfix], …])   Downloads im Hintergrund starten, Ergebnis in _etg.res
// Ein Titel wird so geschrieben, wie _etg.rows() ihn liefert. Das Portal zeigt ihn per CSS in Großbuchstaben, der
// Vergleich nutzt aber die gespeicherte Schreibweise. nr wählt bei gleichem Titel das wievielte Dokument (ab 0),
// präfix kommt vor den Dateinamen, damit gleichnamige Dateien unterscheidbar bleiben.
(() => {
  const RECV = 'http://127.0.0.1:8765/';
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const button = (label) =>
    [...document.querySelectorAll('button,a')].find(
      (e) => (e.getAttribute('aria-label') || e.title || e.innerText.trim()) === label,
    );
  const titles = () => [...document.querySelectorAll('[data-qa="document-list:row:title"]')];

  // Der Download-Knopf erzeugt einen Blob und klickt einen unsichtbaren Link auf dessen Adresse. Beides wird hier
  // abgefangen, damit der Blob an den Empfänger gehen kann und Chrome keinen eigenen Download startet. Die Seite kann
  // auch für andere Zwecke Blob-Adressen erzeugen. Deshalb merkt sich der Helfer zu jeder Adresse ihren Blob und nimmt
  // nur den Blob des geklickten Links.
  const blobs = new Map();
  let clicked = null;
  const createObjectURL = URL.createObjectURL;
  URL.createObjectURL = (b) => {
    const url = createObjectURL.call(URL, b);
    blobs.set(url, b);
    return url;
  };
  const anchorClick = HTMLAnchorElement.prototype.click;
  HTMLAnchorElement.prototype.click = function () {
    if (this.href.startsWith('blob:')) {
      clicked = { blob: blobs.get(this.href), name: this.download };
      return;
    }
    return anchorClick.call(this);
  };

  const post = (fileName, body) =>
    fetch(RECV, { method: 'POST', headers: { 'X-Name': encodeURIComponent(fileName) }, body }).then((r) => r.text());

  const rows = () =>
    titles().map((t) => {
      const link = t.closest('[href]');
      const lines = link.innerText.split('\n').map((s) => s.trim()).filter(Boolean);
      // Der Link der Zeile ist die Download-Abfrage mit der Dokument-ID. Die Adresse des Dokuments im Portal ist die
      // aktuelle Liste mit `?document=ID`. Sie öffnet auch bei direktem Aufruf die Vorschau des Dokuments.
      const id = new URL(link.getAttribute('href'), location.href).searchParams.get('document');
      return {
        id,
        url: location.origin + location.pathname + '?document=' + id,
        title: t.textContent.trim(),
        date: lines[1],
        category: lines.find((s) => s.includes('›')) || '',
        size: lines.find((s) => /^\d+(\.\d+)? (kB|MB)$/.test(s)) || '',
        type: lines[lines.length - 1].toLowerCase(),
      };
    });

  // Ein Aufruf endet nach etwa 8 Sekunden, also vor dem Zeitlimit von javascript_tool. `fertig` ist wahr, wenn die
  // Zahl der Zeilen über drei Prüfungen im Abstand von einer Sekunde gleich blieb. Sonst ruft der Agent load() erneut.
  async function load() {
    const end = Date.now() + 8000;
    let before = titles().length;
    let stable = 0;
    while (Date.now() < end) {
      window.scrollTo(0, document.body.scrollHeight);
      titles().pop()?.scrollIntoView();
      await sleep(1000);
      const now = titles().length;
      stable = now === before ? stable + 1 : 0;
      before = now;
      if (stable >= 3) return { zeilen: now, fertig: true };
    }
    return { zeilen: before, fertig: false };
  }

  async function get(title, nr = 0, prefix = '') {
    const row = titles().filter((t) => t.textContent.trim() === title)[nr];
    if (!row) return 'FEHLT ' + title;
    clicked = null;
    row.closest('[href]').click();
    await sleep(2500);
    button('Herunterladen').click();
    for (let k = 0; k < 40 && !clicked; k++) await sleep(500);
    const got = clicked;
    button('Schließen')?.click();
    await sleep(800);
    if (!got?.blob || !got.name) return 'KEIN DOWNLOAD ' + title;
    return 'ok ' + (await post(prefix + got.name, got.blob)) + ' ' + got.blob.size;
  }

  window._etg = {
    load,
    rows,
    save: (fileName, text) => post(fileName, new Blob([text], { type: 'application/json' })),
    res: [],
    start(list) {
      this.res = [];
      (async () => {
        for (const [title, nr, prefix] of list) {
          try {
            this.res.push(await get(title, nr || 0, prefix || ''));
          } catch (e) {
            this.res.push('FEHLER ' + title + ' ' + e.message);
          }
        }
        this.res.push('FERTIG');
      })();
      return 'gestartet';
    },
  };
  return 'etg24 bereit';
})();
