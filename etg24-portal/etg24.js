// Helfer für das ETG24-Portal. Den ganzen Text mit javascript_tool in den Portal-Tab geben, nach jedem Neuladen
// der Seite erneut. Danach stehen unter window._etg bereit:
//   await _etg.load()                 Liste bis zum Ende nachladen, gibt die Zahl der Zeilen zurück
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

  // Der Download-Knopf erzeugt einen Blob und klickt einen unsichtbaren Link. Beides wird hier abgefangen, damit der
  // Blob an den Empfänger gehen kann und Chrome keinen eigenen Download startet.
  let blob = null;
  let name = null;
  const createObjectURL = URL.createObjectURL;
  URL.createObjectURL = (b) => {
    blob = b;
    return createObjectURL.call(URL, b);
  };
  const anchorClick = HTMLAnchorElement.prototype.click;
  HTMLAnchorElement.prototype.click = function () {
    if (this.href.startsWith('blob:')) {
      name = this.download;
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

  async function load() {
    let before = -1;
    for (let n = 0; n < 40 && titles().length !== before; n++) {
      before = titles().length;
      window.scrollTo(0, document.body.scrollHeight);
      titles().pop()?.scrollIntoView();
      await sleep(1500);
    }
    return titles().length;
  }

  async function get(title, nr = 0, prefix = '') {
    const row = titles().filter((t) => t.textContent.trim() === title)[nr];
    if (!row) return 'FEHLT ' + title;
    blob = null;
    name = null;
    row.closest('[href]').click();
    await sleep(2500);
    button('Herunterladen').click();
    for (let k = 0; k < 40 && !(blob && name); k++) await sleep(500);
    const got = blob;
    const fileName = prefix + name;
    button('Schließen')?.click();
    await sleep(800);
    if (!got) return 'KEIN DOWNLOAD ' + title;
    return 'ok ' + (await post(fileName, got)) + ' ' + got.size;
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
