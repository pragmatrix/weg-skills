// Nebenkostenabrechnung für den Mieter als Brief nach DIN 5008 Form B.
//
// Die Vorlage gilt für jedes Jahr und jedes Mietverhältnis. Alle Angaben kommen aus der Datenbasis
// `nebenkostenabrechnung_JJJJ_<Mieter>.json` (SKILL.md, Schritt 4). Das Skript `scripts/nebenkosten.sh` übergibt
// ihren absoluten Pfad als Eingabe `pfad`. Die Wurzel `/` erlaubt Typst, eine Datei außerhalb dieses Ordners zu lesen:
//
//   typst compile --root / --input pfad=<absoluter Pfad der Datenbasis> nebenkostenabrechnung.typ <Ziel.pdf>
//
// Die Vorlage rechnet nichts neu. Sie übernimmt Beträge und Summen aus der Datenbasis und prüft vorher die
// Mindestangaben und die Summen. Fehlt eine Angabe oder passt eine Summe nicht, bricht die Übersetzung mit einer
// Liste aller Befunde ab, und es entsteht kein PDF.

#let pfad = sys.inputs.at("pfad", default: none)
#assert(pfad != none, message: "Die Datenbasis fehlt. Aufruf mit --root / --input pfad=<absoluter Pfad>.")
#let daten = json(pfad)
#assert(type(daten) == dictionary, message: "Die Datenbasis ist kein JSON-Objekt.")

// ---------------------------------------------------------------------------------------------------------
// Formatierung
// ---------------------------------------------------------------------------------------------------------

// Wandelt ein Datum der Form JJJJ-MM-TT in TT.MM.JJJJ um.
#let datum(iso) = iso.split("-").rev().join(".")

// Rundet einen Betrag in Euro auf ganze Cent. Vergleiche von Beträgen laufen über Cent, damit Rundungsreste der
// Gleitkommazahlen keine Rolle spielen.
#let cent(betrag) = int(calc.round(betrag * 100))

// Schreibt einen Betrag im deutschen Format mit Tausenderpunkt, etwa „1.234,56 €“ oder „-12,30 €“.
#let eur(betrag) = {
  let c = cent(betrag)
  let euro = str(calc.quo(calc.abs(c), 100))
  let rest = calc.rem(calc.abs(c), 100)
  let gruppen = ()
  while euro.len() > 3 {
    gruppen.insert(0, euro.slice(euro.len() - 3))
    euro = euro.slice(0, euro.len() - 3)
  }
  gruppen.insert(0, euro)
  let vorzeichen = if c < 0 { "-" } else { "" }
  vorzeichen + gruppen.join(".") + "," + (if rest < 10 { "0" } else { "" }) + str(rest) + "\u{00A0}€"
}

// ---------------------------------------------------------------------------------------------------------
// Prüfung der Datenbasis
// ---------------------------------------------------------------------------------------------------------

// Liest einen verschachtelten Wert wie ("mieterin", "name"). Fehlt ein Glied, ist das Ergebnis none.
#let wert(pfad) = pfad.fold(daten, (d, k) => if type(d) == dictionary { d.at(k, default: none) } else { none })
#let leer(v) = v == none or v == ""
#let zahl(v) = type(v) in (int, float)
// Ein Text, der im Brief erscheint, ist eine nicht leere Zeichenkette.
#let text_ok(v) = type(v) == str and v.trim() != ""
// Ein Datum hat die Form JJJJ-MM-TT. Bei dieser Form entspricht die Reihenfolge der Zeichenketten der zeitlichen.
#let iso(v) = type(v) == str and v.match(regex("^\d{4}-\d{2}-\d{2}$")) != none

#let jahr = daten.at("jahr", default: none)
#let jahr_ok = type(jahr) == int
// Alle Positionen, auch die nicht umlagefähigen. Ein Eintrag, der kein Objekt ist, steht als Befund in `befunde`.
#let alle_positionen = {
  let liste = daten.at("positionen", default: ())
  if type(liste) == array { liste.filter(p => type(p) == dictionary) } else { () }
}
// Nur `umlagefaehig: true` kommt in den Brief. Fehlt das Feld, ist das ein Befund, damit keine Position
// stillschweigend wegfällt.
#let positionen = alle_positionen.filter(p => p.at("umlagefaehig", default: none) == true)
#let summen = {
  let s = daten.at("summen", default: (:))
  if type(s) == dictionary { s } else { (:) }
}
#let anlagen = {
  let a = daten.at("anlagen", default: ())
  if type(a) == array { a } else { () }
}

// Arten begünstigter Leistungen nach § 35a EStG, die eine Position unter `steuer_35a.art` nennen kann, mit ihrem
// Text im Brief.
#let arten_35a = (
  haushaltsnah: "haushaltsnahe Dienstleistungen nach Abs.\u{00A0}2",
  handwerker: "Handwerkerleistungen nach Abs.\u{00A0}3",
)

#let befunde = {
  let b = ()
  if not jahr_ok { b.push("jahr fehlt oder ist keine ganze Zahl") }

  // Angaben für Briefkopf und Betreff.
  for pfad in (
    ("vermieter", "name"), ("vermieter", "adresse"),
    ("mieterin", "name"), ("mieterin", "adresse"), ("mieterin", "wohnung"),
  ) {
    if not text_ok(wert(pfad)) { b.push(pfad.join(".") + " fehlt oder ist kein Text") }
  }
  let anrede = wert(("mieterin", "anrede"))
  if anrede != none and not text_ok(anrede) { b.push("mieterin.anrede ist kein Text") }
  let vertrag = wert(("mieterin", "mietvertrag_vom"))
  if vertrag != none and not iso(vertrag) { b.push("mieterin.mietvertrag_vom hat nicht die Form JJJJ-MM-TT") }

  // Der Abrechnungszeitraum liegt im Abrechnungsjahr, denn die Kosten stammen aus der Einzelabrechnung der WEG für
  // dieses Kalenderjahr. Ein Mieterwechsel ergibt einen kürzeren Zeitraum im selben Jahr.
  let von = wert(("abrechnungszeitraum", "von"))
  let bis = wert(("abrechnungszeitraum", "bis"))
  if not iso(von) or not iso(bis) {
    b.push("abrechnungszeitraum.von oder .bis fehlt oder hat nicht die Form JJJJ-MM-TT")
  } else if jahr_ok and not (str(jahr) + "-01-01" <= von and von <= bis and bis <= str(jahr) + "-12-31") {
    b.push("abrechnungszeitraum " + von + " bis " + bis + " liegt nicht im Abrechnungsjahr " + str(jahr))
  }

  // Eine Abrechnung entsteht erst nach dem Abrechnungsjahr.
  let d = daten.at("datum_abrechnung", default: none)
  if not iso(d) {
    b.push("datum_abrechnung fehlt oder hat nicht die Form JJJJ-MM-TT")
  } else if jahr_ok and d <= str(jahr) + "-12-31" {
    b.push("datum_abrechnung " + d + " liegt nicht nach dem Abrechnungsjahr " + str(jahr))
  }

  // Jede Position sagt ausdrücklich, ob sie umlagefähig ist.
  let liste = daten.at("positionen", default: none)
  if type(liste) != array { b.push("positionen fehlt oder ist keine Liste") } else {
    for (i, p) in liste.enumerate() {
      if type(p) != dictionary {
        b.push("positionen[" + str(i) + "] ist kein Objekt")
      } else if type(p.at("umlagefaehig", default: none)) != bool {
        b.push("Position „" + str(p.at("position", default: "?")) + "“ ohne umlagefaehig (true oder false)")
      }
    }
  }

  // Herkunft und Mindestangaben jeder umlagefähigen Position (SKILL.md, Gesetzliche Anforderungen).
  if positionen.len() == 0 { b.push("keine umlagefähige Position") }
  for p in positionen {
    let name = "Position „" + str(p.at("position", default: "?")) + "“"
    if not text_ok(p.at("position", default: none)) { b.push("Position ohne position (Name der Kostenart)") }
    if not zahl(p.at("betrag", default: none)) { b.push(name + " ohne betrag") }
    if leer(p.at("betrkv", default: none)) { b.push(name + " ohne betrkv") }
    if leer(p.at("fundstelle", default: none)) and leer(p.at("berechnung", default: none)) {
      b.push(name + " ohne fundstelle oder berechnung")
    }
    if not zahl(p.at("gesamtkosten", default: none)) { b.push(name + " ohne gesamtkosten") }
    if not text_ok(p.at("schluessel", default: none)) { b.push(name + " ohne schluessel") }
  }
  if not text_ok(daten.at("verteilvermerk", default: none)) {
    b.push("verteilvermerk fehlt (Erläuterung der Verteilerschlüssel für den Mieter)")
  }

  // Anlagen nennt der Brief mit ihrer Bezeichnung. Das Skript hängt die Datei an das PDF an.
  if type(daten.at("anlagen", default: ())) != array { b.push("anlagen ist keine Liste") }
  for a in anlagen {
    if type(a) != dictionary or not text_ok(a.at("bezeichnung", default: none)) {
      b.push("Anlage ohne bezeichnung")
    } else if type(a.at("datei", default: none)) != str or not lower(a.datei).ends-with(".pdf") {
      b.push("Anlage „" + a.bezeichnung + "“ ohne datei (Pfad einer PDF-Datei im Projektordner)")
    }
  }

  // Steuerermäßigung nach § 35a EStG: Art, Arbeitskostenanteil des Mieters und Herkunft. Der Arbeitskostenanteil
  // kann nicht größer sein als der Anteil des Mieters an der Position.
  for p in positionen.filter(p => "steuer_35a" in p) {
    let name = "Position „" + str(p.at("position", default: "?")) + "“: steuer_35a"
    let s = p.steuer_35a
    if type(s) != dictionary {
      b.push(name + " ist kein Objekt")
      continue
    }
    let art = s.at("art", default: none)
    if type(art) != str or art not in arten_35a {
      b.push(name + ".art ist weder „haushaltsnah“ noch „handwerker“")
    }
    let betrag = s.at("betrag", default: none)
    if not zahl(betrag) or betrag <= 0 {
      b.push(name + ".betrag fehlt oder ist nicht positiv")
    } else if zahl(p.at("betrag", default: none)) and cent(betrag) > cent(p.betrag) {
      b.push(name + ".betrag ist größer als der Anteil des Mieters")
    }
    if leer(s.at("fundstelle", default: none)) and leer(s.at("berechnung", default: none)) {
      b.push(name + " ohne fundstelle oder berechnung")
    }
  }

  // Summen: Die Positionen ergeben die Summe, Summe minus Vorauszahlung ergibt das Ergebnis.
  let fehlende_summen = ("summe_betriebskosten", "vorauszahlung", "nachzahlung").filter(k => not zahl(
    summen.at(k, default: none),
  ))
  for k in fehlende_summen { b.push("summen." + k + " fehlt") }
  if fehlende_summen.len() == 0 and positionen.all(p => zahl(p.at("betrag", default: none))) {
    let summe = positionen.map(p => cent(p.betrag)).sum(default: 0)
    if summe != cent(summen.summe_betriebskosten) {
      b.push(
        "die Positionen ergeben " + eur(summe / 100) + ", summen.summe_betriebskosten nennt "
          + eur(summen.summe_betriebskosten),
      )
    }
    if cent(summen.summe_betriebskosten) - cent(summen.vorauszahlung) != cent(summen.nachzahlung) {
      b.push("summen.summe_betriebskosten minus summen.vorauszahlung ergibt nicht summen.nachzahlung")
    }
  }
  b
}
#assert(befunde.len() == 0, message: "Die Datenbasis ist nicht vollständig:\n- " + befunde.join("\n- "))

// ---------------------------------------------------------------------------------------------------------
// Briefdaten
// ---------------------------------------------------------------------------------------------------------

#let vermieter = daten.vermieter
#let mieterin = daten.mieterin
// Anschriften stehen in der Datenbasis als „Straße Nr., PLZ Ort“. Jedes Glied wird eine Zeile.
#let vermieter_zeilen = (vermieter.name,) + vermieter.adresse.split(", ")
#let mieterin_zeilen = (mieterin.name,) + mieterin.adresse.split(", ")
// Ein Zusatz in Klammern hinter der Lage der Wohnung, etwa Einheit und Anteile, erscheint nicht im Betreff.
#let wohnung = mieterin.wohnung.split(" (").first()
#let mietvertrag = mieterin.at("mietvertrag_vom", default: none)
#let anrede = mieterin.at("anrede", default: "Sehr geehrte Damen und Herren,")

// Eine negative Nachzahlung ist ein Guthaben des Mieters. Die Zeile heißt dann „Ihr Guthaben“ und zeigt den
// Betrag positiv.
#let ergebnis_text = if summen.nachzahlung < 0 { "Ihr Guthaben" } else { "Ihre Nachzahlung" }
#metadata(ergebnis_text) <ergebnis>

// Solange eine Position einen Platzhalter mit `warnung` trägt, ist die Abrechnung nicht versandfertig.
#let entwurf = alle_positionen.any(p => not leer(p.at("warnung", default: none)))
#metadata(entwurf) <entwurf>

// Die geprüften Pfade der Anlagen, relativ zum Projektordner. `scripts/nebenkosten.sh` liest sie mit `typst eval`.
#metadata(anlagen.map(a => a.datei)) <anlagen>

// Begünstigte Arbeitskosten nach § 35a EStG je Art, mit den Positionen, aus denen sie stammen. Arten ohne
// Position fallen weg.
#let leistungen_35a = {
  let je_art = arten_35a.keys().map(art => {
    let ps = positionen.filter(p => p.at("steuer_35a", default: (:)).at("art", default: none) == art)
    (art: art, cent: ps.map(p => cent(p.steuer_35a.betrag)).sum(default: 0), positionen: ps.map(p => p.position))
  })
  je_art.filter(l => l.positionen.len() > 0)
}
#metadata(leistungen_35a.map(l => (l.art, l.cent)).to-dict()) <steuer_35a>

// ---------------------------------------------------------------------------------------------------------
// Seite und Geometrie nach DIN 5008 Form B
// ---------------------------------------------------------------------------------------------------------

// Seitenränder des Fließtexts. Links 25 mm, rechts 20 mm nach DIN 5008.
#let rand_links = 25mm
#let rand_oben = 20mm

// Setzt einen Block an eine feste Stelle des Blatts. x und y zählen von der linken oberen Ecke des Papiers,
// nicht vom Satzspiegel.
#let fest(x, y, inhalt) = place(top + left, dx: x - rand_links, dy: y - rand_oben, inhalt)

// Falzmarken bei 105 mm und 210 mm und die Lochmarke bei 148,5 mm, am linken Rand der ersten Seite.
#let marken = context if here().page() == 1 {
  for (y, laenge) in ((105mm, 5mm), (148.5mm, 8mm), (210mm, 5mm)) {
    place(top + left, dx: 4mm, dy: y, line(length: laenge, stroke: 0.4pt + gray))
  }
}

// Der Entwurfsvermerk liegt im Hintergrund, damit der Text lesbar bleibt.
#let entwurf_vermerk = if entwurf {
  place(center + horizon, rotate(-45deg, text(size: 110pt, fill: luma(238), weight: "bold", "ENTWURF")))
}

#set document(title: "Nebenkostenabrechnung " + str(jahr), author: vermieter.name)
#set page(
  paper: "a4",
  margin: (left: rand_links, right: 20mm, top: rand_oben, bottom: 20mm),
  background: { entwurf_vermerk; marken },
)
#set text(font: "Arial", size: 10pt, lang: "de")
#set par(leading: 0.6em, spacing: 1.2em)

// ---------------------------------------------------------------------------------------------------------
// Briefkopf: Absender, Anschriftfeld und Datum an festen Stellen
// ---------------------------------------------------------------------------------------------------------

// Absender oben rechts, bündig mit dem rechten Rand bei 190 mm.
#fest(115mm, 27mm, box(width: 75mm, align(right, vermieter_zeilen.join(linebreak()))))

// Anschriftfeld: 85 mm breit und 45 mm hoch, 20 mm von links und 45 mm von oben, mit 5 mm Innenabstand links.
// Die Zusatz- und Vermerkzone belegt die oberen 17,7 mm. Ihre letzte Zeile trägt die Rücksendeangabe. Darunter
// folgt die Anschriftzone mit 27,3 mm.
#fest(25mm, 45mm, box(width: 80mm, height: 17.7mm, align(bottom, text(size: 7pt, vermieter_zeilen.join(" – ")))))
#fest(25mm, 62.7mm, box(
  width: 80mm,
  height: 27.3mm,
  inset: (top: 1.5mm),
  text(size: 12pt, mieterin_zeilen.join(linebreak())),
))

// Datum rechts unter dem Anschriftfeld.
#fest(125mm, 93mm, box(width: 65mm, align(right)[Datum:#h(1.5em)*#datum(daten.datum_abrechnung)*]))

// ---------------------------------------------------------------------------------------------------------
// Brieftext
// ---------------------------------------------------------------------------------------------------------

// Der Fließtext beginnt mit dem Betreff unterhalb des Briefkopfs.
#v(105mm - rand_oben)

#text(size: 12pt, weight: "bold")[
  Nebenkostenabrechnung #jahr, Whg. #wohnung#if mietvertrag != none [, Mietvertrag vom #datum(mietvertrag)]
]

#v(0.6em)
#anrede

mit diesem Schreiben erhalten Sie die Nebenkostenabrechnung für das Jahr *#jahr*
(#datum(daten.abrechnungszeitraum.von) bis #datum(daten.abrechnungszeitraum.bis)):

#v(0.4em)

// Positionstabelle mit den formellen Mindestangaben: Kostenart, Verteilerschlüssel, Gesamtkosten und Anteil des
// Mieters. Darunter Summe, Vorauszahlung und Ergebnis.
#let linie = table.hline(stroke: 0.6pt)
#table(
  columns: (1fr, auto, 26mm, 24mm),
  align: (left, left, right, right),
  stroke: none,
  inset: (x: 0pt, y: 3.2pt),
  column-gutter: 4mm,
  table.header([*Kostenart*], [*Verteilerschlüssel*], [*Gesamtkosten*], [*Ihr Anteil*], linie),
  ..positionen.map(p => (p.position, p.schluessel, eur(p.gesamtkosten), eur(p.betrag))).flatten(),
  linie,
  table.cell(colspan: 3)[Summe], eur(summen.summe_betriebskosten),
  table.cell(colspan: 3)[Ihre Vorauszahlung], eur(summen.vorauszahlung),
  table.cell(colspan: 4, inset: 2pt)[],
  table.cell(colspan: 3)[*#ergebnis_text*], [*#eur(calc.abs(summen.nachzahlung))*],
)

#v(0.6em)
#daten.verteilvermerk

#if leistungen_35a.len() > 0 [
  Steuerermäßigung nach §~35a EStG: Ihr Anteil enthält Arbeitskosten für #{
    leistungen_35a
      .map(l => arten_35a.at(l.art) + " von " + eur(l.cent / 100) + " (" + l.positionen.join(", ") + ")")
      .join(" und für ")
  }.
]

Für Rückfragen stehe ich Ihnen gerne zur Verfügung.

#v(0.6em)
Mit freundlichen Grüßen

#v(12mm)
#vermieter.name

// Anlagenvermerk nach DIN 5008, eine Zeile je Anlage.
#if anlagen.len() > 0 {
  v(4mm)
  [*#if anlagen.len() == 1 [Anlage] else [Anlagen]*]
  linebreak()
  anlagen.map(a => a.bezeichnung).join(linebreak())
}
