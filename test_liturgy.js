// Checks the liturgical engine against the source site's own calendar
// (docs/data/cal-YYYY.json, 2018–2037) and against the Ceaslov's rubrics.
const fs = require("fs");
const path = require("path");
const L = require("./docs/js/liturgy.js");

const load = (n) => JSON.parse(fs.readFileSync(path.join(__dirname, "docs/data", n + ".json"), "utf8"));
const hymns = load("hymns");
const sinaxar = load("sinaxar");
let failed = 0, passed = 0;
function check(name, got, want) {
  const a = JSON.stringify(got), b = JSON.stringify(want);
  if (a === b) passed++;
  else { failed++; console.log(`FAIL ${name}: got ${a}, want ${b}`); }
}

// Pascha dates, independently known.
const PASCHA = { 2018: "2018-04-08", 2019: "2019-04-28", 2020: "2020-04-19", 2021: "2021-05-02", 2022: "2022-04-24",
  2023: "2023-04-16", 2024: "2024-05-05", 2025: "2025-04-20", 2026: "2026-04-12", 2027: "2027-05-02", 2028: "2028-04-16",
  2029: "2029-04-08", 2030: "2030-04-28" };
for (const [y, d] of Object.entries(PASCHA)) check(`pascha ${y}`, L.pascha(Number(y)), d);

// Tone and gospel of every Sunday the source calendar names, 2018–2037.
const cmp = { glas: [0, 0], voscr: [0, 0] };
const misses = [];
for (let y = 2018; y <= 2037; y++) {
  const cal = load(`cal-${y}`);
  for (const [m, e] of Object.entries(cal)) {
    const iso = `${y}-${m}`;
    if (e.glas == null) continue;
    if (new Date(iso + "T00:00Z").getUTCDay() !== 0) { misses.push(`${iso} not a Sunday`); continue; }
    cmp.glas[1]++; cmp.voscr[1]++;
    if (L.glasOf(iso) === e.glas) cmp.glas[0]++; else misses.push(`${iso} glas ${L.glasOf(iso)} vs ${e.glas}`);
    if (L.voscrOf(iso) === e.voscr) cmp.voscr[0]++; else misses.push(`${iso} voscr ${L.voscrOf(iso)} vs ${e.voscr}`);
  }
}
console.log(`calendar Sundays: glas ${cmp.glas[0]}/${cmp.glas[1]}, voscr ${cmp.voscr[0]}/${cmp.voscr[1]}`);
if (misses.length) console.log("  first differences:", misses.slice(0, 12).join(" | "));
check("glas agrees with source calendar", cmp.glas[0], cmp.glas[1]);
check("voscr agrees with source calendar", cmp.voscr[0], cmp.voscr[1]);

const ctx = (iso) => {
  const y = iso.slice(0, 4);
  return L.dayContext(iso, { calendar: load(`cal-${y}`), sinaxar });
};

// Periods.
check("Clean Monday 2026 is Lent", ctx("2026-02-23").L, true);
check("Cheesefare Sunday 2026 is not", ctx("2026-02-22").L, false);
check("Lent Saturday is not an ordinary Lent day", ctx("2026-03-07").L, false);
check("Holy Monday", ctx("2026-04-06").HW, true);
check("Bright Tuesday", ctx("2026-04-14").bright, true);
check("Annunciation in Lent keeps the festal order", ctx("2026-03-25").L, false);
check("Nativity Fast weekday with no rank is Aliluia", ctx("2026-11-17").A, true);
check("St Nicholas in the fast is not", ctx("2026-12-04").A, ctx("2026-12-04").rank === "" );
check("Nov 5 2026 ordinary", [ctx("2026-11-05").L, ctx("2026-11-05").A, ctx("2026-11-05").post], [false, false, false]);

// Slots that drop out.
check("Mijloceas skipped on an ordinary day", L.resolveSlug("04-mijloceasul-1", ctx("2026-11-05")), null);
check("Mijloceas read in the fast", L.resolveSlug("04-mijloceasul-1", ctx("2026-11-17")), "04-mijloceasul-1");
check("Bright Week replaces the Hours", L.resolveSlug("05-ceasul-3", ctx("2026-04-14")), "pasti");

// Hymns.
const names = (l) => l.map((x) => x.label.split(",")[0]);
check("Hour condac on Nov 5", names(L.condac(ctx("2026-11-05"), 1, hymns)), ["Condacul Sfinților Mucenici Galaction și Epistimia"]);
check("Sunday condac is the Resurrection's in the week's tone", L.condac(ctx("2026-11-01"), 1, hymns)[0].glas, ctx("2026-11-01").glas);
check("Pascha-period condac", /Condac/.test(L.condac(ctx("2026-05-13"), 1, hymns)[0].label), true);
check("Great feast: only its troparion", L.tropare(ctx("2026-12-25"), hymns).length, 1);
for (let i = 0; i < 366; i++) {
  const iso = L.addDays("2028-01-01", i);
  const c = ctx(iso);
  if (!L.tropare(c, hymns).length) { failed++; console.log("no troparion", iso); }
  if (!L.condac(c, 1, hymns).length) { failed++; console.log("no condac", iso); }
}

// Kathismata from RÂNDUIALA CITIRII PSALTIRII.
check("Lent Monday wk1 Hour 3", L.catisme(ctx("2026-02-23"), "3"), [7]);
check("Lent Monday wk1 Hour 1", L.catisme(ctx("2026-02-23"), "1"), []);
check("Lent Tuesday wk2 Hour 1", L.catisme(ctx("2026-03-03"), "1"), [13]);
check("Lent week 5 Thursday Matins", L.catisme(ctx("2026-03-26"), "u"), [8]);
check("Holy Tuesday Hour 6", L.catisme(ctx("2026-04-07"), "6"), [13]);
check("Holy Thursday none", L.catisme(ctx("2026-04-09"), "u"), []);
check("Light season Monday Matins", L.catisme(ctx("2026-07-06"), "u"), [4, 5]);
check("Autumn Monday Matins", L.catisme(ctx("2026-11-02"), "u"), [4, 5, 6]);
check("Autumn Sunday polyeleos", L.catisme(ctx("2026-11-01"), "u"), [2, 3, "polieleu"]);
const plainSunday = ["2026-07-12", "2026-07-19", "2026-08-02", "2026-08-09"].find((d) => !ctx(d).polieleu);
check("Summer Sunday with no polyeleos saint", L.catisme(ctx(plainSunday), "u"), [2, 3, 17]);
check("Summer Sunday with a polyeleos saint", L.catisme(ctx("2026-07-05"), "u")[2], ctx("2026-07-05").polieleu ? "polieleu" : 17);
check("Pascha line carries its rank", ctx("2026-04-12").rank, "(†)");

// The conditions in services.json: they must evaluate on every day of a leap year,
// and each service must show text on every day it is scheduled.
const services = load("services");
const evalCond = (expr, c) => new Function("c", `with (c) { return (${expr}); }`)(c);
const full = (iso) => L.serviceContext(iso, "x", { calendar: load(`cal-${iso.slice(0, 4)}`), sinaxar });
const visible = (slug, c) => services[slug].filter((i) => i.w == null || evalCond(i.w, c));
const slotsOf = (slug, c) => visible(slug, c).filter((i) => i.slot).map((i) => i.slot);
for (let i = 0; i < 366; i++) {
  const iso = L.addDays("2028-01-01", i);
  const c = { ...full(iso), lit: full(iso), eve: full(iso).dow };
  for (const slug of Object.keys(services)) {
    if (!visible(slug, c).length && !["01-miezonoptica"].includes(slug)) { failed++; console.log("empty", slug, iso); }
  }
}
const at = (iso) => { const c = full(iso); return { ...c, lit: c, eve: c.dow }; };
check("Lent weekday Hour: catisma, no saint troparion or condac", slotsOf("05-ceasul-3", at("2026-03-04")), ["catisma"]);
check("Ordinary Hour: troparion and condac", slotsOf("05-ceasul-3", at("2026-11-05")), ["tropar", "condac"]);
check("Lent Saturday Hour keeps them", slotsOf("05-ceasul-3", at("2026-03-07")), ["tropar", "condac"]);
check("Aliluia Hour: condac, no troparion of the saint", slotsOf("05-ceasul-3", at("2026-11-17")), ["catisma", "condac"]);
check("Exactly one Miezonoptica variant shows", ["2026-11-05", "2026-11-07", "2026-11-08"].map((d) => visible("01-miezonoptica", at(d))[0].i), [240, 306, 380]);
check("Mid-Pentecost troparion in its after-feast", /Înjumătăț|Înjumătăţ|Fiind la/.test(L.tropare(ctx("2026-05-13"), hymns)[0].label + L.tropare(ctx("2026-05-13"), hymns)[0].text) || L.tropare(ctx("2026-05-13"), hymns).length === 2, true);

// Shortened prayers are written out; pointers to a moment stay short.
const hour3 = services["05-ceasul-3"].filter((i) => i.r).map((i) => i.r.map((r) => r[0]).join(""));
const textOf = hour3.join("\n");
check("Împărate ceresc in full", textOf.includes("Vistierul bunătăților"), true);
check("Trisagion in full", /Sfinte Dumnezeule, Sfinte tare, Sfinte fără de moarte/.test(textOf), true);
check("Lord's Prayer in full", textOf.includes("Pâinea noastră"), true);
check("A count stays with its own prayer", /Doamne miluiește\s*\(de 12 ori\)/.test(textOf) && !/rău\.\s*\(de 12 ori\)/.test(textOf), true);
check("No shortened Tatăl nostru left, even in a rubric", /Tatăl nostru\s*(\.{2,}|…)/.test(textOf), false);
check("Veniți written out everywhere", /Veniți să ne închinăm\s*(\.{2,}|…)/.test(textOf), false);

check("Polieleu text is present", hymns.polieleu.startsWith("Lăudați numele Domnului"), true);
const utrenia = services["02-utrenia"].filter((i) => i.r).map((i) => i.r.map((r) => r[0]).join("")).join("\n");
check("Înviind Iisus written out", utrenia.includes("a dăruit lumii viață veșnică și mare milă"), true);

const treime = load("canon-treime");
const canonText = (g) => treime[g].filter((i) => i.r).map((i) => i.r.map((r) => r[0]).join("")).join("\n");
check("Irmos glas 3, cântarea 1", canonText(3).includes("Cela ce a împreunat apele dedemult"), true);
check("Irmos glas 3, cântarea 3", canonText(3).includes("Cela ce dintru cele ce n-a fost"), true);
check("Irmos glas 7, cântarea 5", canonText(7).includes("Mânecând Cuvântule la mărirea"), true);
check("Irmos glas 1, cântarea 5", canonText(1).includes("Cela ce ai luminat cu luminarea venirii Tale"), true);
check("Irmos glas 2, cântarea 4", canonText(2).includes("Te laud că auz am auzit"), true);
check("Glas 2 has no Theotokion in place of its irmos", canonText(2).includes("Te laud pe tine, Preacântată"), false);
check("Irmos glas 4, cântarea 4, not the doxology", canonText(4).includes("pe scaunul Dumnezeirii") && !canonText(4).includes("șade în Slavă Tatălui"), true);
check("Glas 4 does not borrow the irmos of glas 1", canonText(4).includes("bogăția sa să se laude"), false);
check("Irmos glas 5, cântarea 4", canonText(5).includes("Dumnezeiască deșertarea Ta cunoscându-o"), true);
check("Irmos glas 5, cântarea 6", canonText(5).includes("Marea patimilor cea sălbătăcită"), true);
check("Irmos glas 7, cântarea 3", canonText(7).includes("cu cuvântul Tău cel atotputernic"), true);
check("Irmos glas 8, cântarea 3", canonText(8).includes("întărește-mă pe piatra Bisericii"), true);
check("Irmos glas 8, cântarea 4", canonText(8).includes("Tu ești tăria mea Doamne"), true);
check("Saturday condac labels written out", JSON.stringify(hymns.condaceSapt[6]).includes("Slavă..."), false);
check("Palm Sunday troparion label", hymns.triod.find((e) => e.off === -7).t[0].l, "Troparul, glasul 1");

// The app names no source.
const dataText = fs.readdirSync(path.join(__dirname, "docs/data")).filter((f) => !f.startsWith("cal-")).map((f) => fs.readFileSync(path.join(__dirname, "docs/data", f), "utf8")).join("");
check("No links to the source site", /https?:\/\/|sites\.google/.test(dataText), false);
const allServices = Object.values(services).flat().filter((i) => i.r).map((i) => i.r.map((r) => r[0]).join(""));
check("No book titles left", allServices.filter((t) => /OCTOIHUL MARE|MINEIELE BISERICII|SINAXAR\b|PSALTIREA LUI DAVID/.test(t)), []);
check("No verse-count markers", allServices.filter((t) => /(^|\s)(Stih pe|Pe)\s+\d+\s*:/.test(t)), []);
check("Beatitude verse is clean", allServices.includes("Fericiți cei milostivi, că aceia se vor milui."), true);
check("Beatitude verse keeps its neighbour", allServices.includes("Fericiți făcătorii de pace, că aceia fiii lui Dumnezeu se vor chema."), true);

const midnight = services["01-miezonoptica"].map((i) => i.slot || (i.r || []).map((r) => r[0]).join(""));
const canonAt = midnight.indexOf("canonTreime");
check("Trinity canon is announced before it", midnight[canonAt - 1], "Și îndată se zice Canonul Treimii (Troisnicul), al glasului ce va fi de rând.");
check("What follows it comes after it", midnight[canonAt + 1], "Și după canon se cântă Troparele Treimice, glasul al 2-lea :");

for (const slug of ["11-vecernia", "priveghere"]) {
  const texts = services[slug].filter((i) => i.r).map((i) => i.r.map((r) => r[0]).join(""));
  check(`Entrance prayer in full, ${slug}`, texts.some((t) => t.startsWith("Seara și dimineața și la amiază, Te lăudăm")) && texts.some((t) => t.startsWith("De aceea, Stăpâne preabune")), true);
  check(`Entrance prayer not shortened, ${slug}`, texts.some((t) => /la amiaz(ă|ăzi)\s*(\.{2,}|…)/.test(t)), false);
}

for (const slug of ["11-vecernia", "priveghere"]) {
  const text = services[slug].filter((i) => i.r).map((i) => i.r.map((r) => r[0]).join("")).join("\n");
  check(`Entrance blessing in full, ${slug}`, text.includes("Binecuvântată este intrarea sfinților Tăi, totdeauna, acum și pururea și în vecii vecilor. Amin."), true);
  check(`Entrance blessing not shortened, ${slug}`, /intrarea [sS]finților Tăi, Doamne|Amin\.\s*etc\./.test(text), false);
}

// Great movable feasts keep their own hymns, not the saint of the date.
for (const [iso, off] of [["2026-04-05", -7], ["2026-05-21", 39], ["2026-05-31", 49]]) {
  const c = ctx(iso);
  const saintLabels = (c.sin?.t ?? []).map((t) => t.l);
  check(`Movable feast ${off} is not the saint's`, L.tropare(c, hymns).some((t) => saintLabels.includes(t.label)), false);
  check(`Movable feast ${off} has a troparion`, L.tropare(c, hymns).length > 0, true);
}

check("Paschal troparion is in the source data", services.pasti[0].r.map((r) => r[0]).join("").trim(), "Hristos a înviat din morți, cu moartea pe moarte călcând, și celor din morminte viață dăruindu-le. (de 3 ori).");

// Old calendar: fixed dates fall 13 days later, Pascha does not move.
const noVechi = (iso) => L.dayContext(iso, { calendar: load(`cal-${iso.slice(0, 4)}`), sinaxar, style: "vechi", fixed: load("fixed-calendar") });
const oldStyle = noVechi;
const withVechi = (iso) => L.dayContext(iso, { calendar: load(`cal-${iso.slice(0, 4)}`), sinaxar, style: "vechi", fixed: load("fixed-calendar"), vechi: load(`vechi-${iso.slice(0, 4)}`) });
check("Old style: Nativity on 7 January", oldStyle("2027-01-07").m, "12-25");
check("Old style: Nativity is the feast", [oldStyle("2027-01-07").feast, L.tropare(oldStyle("2027-01-07"), hymns).length, /Nașterii/.test(L.tropare(oldStyle("2027-01-07"), hymns)[0].label)], [true, 1, true]);
check("Old style: 25 December is ordinary", oldStyle("2026-12-25").feast, false);
check("Old style: Exaltation on 27 September", oldStyle("2026-09-27").feast, true);
check("Old style: Transfiguration on 19 August", oldStyle("2026-08-19").m, "08-06");
check("Old style: Nativity Fast begins 28 November", [oldStyle("2026-11-27").fastName === "Postul Nașterii Domnului", oldStyle("2026-11-28").fastName], [false, "Postul Nașterii Domnului"]);
check("Old style: Apostles' Fast ends 11 July", [oldStyle("2026-07-11").fastName, oldStyle("2026-07-12").fastName === "Postul Sfinților Apostoli"], ["Postul Sfinților Apostoli", false]);
check("Old style: Dormition Fast 14-27 August", [oldStyle("2026-08-13").fastName === "Postul Adormirii Maicii Domnului", oldStyle("2026-08-14").fastName, oldStyle("2026-08-27").fastName, oldStyle("2026-08-28").fastName === "Postul Adormirii Maicii Domnului"], [false, "Postul Adormirii Maicii Domnului", "Postul Adormirii Maicii Domnului", false]);
check("Old style: same Pascha, same tone", [oldStyle("2026-04-12").rank, oldStyle("2026-11-01").glas], ["(†)", ctx("2026-11-01").glas]);
check("Old style: no dispensation notes from the new calendar", noVechi("2026-12-25").cal.note, undefined);
check("Old style: kathismata follow the old date", L.catisme(oldStyle("2027-01-03"), "u"), [2, 3, 17]);
check("Old style: fixed-feast Sunday names are dropped", oldStyle("2026-12-20").cal.sunday, undefined);
check("Old style: Pascha-based Sunday names stay", /după Rusalii$/.test(oldStyle("2026-11-01").cal.sunday), true);
check("Old style: today has the calendar's saints and rank", [oldStyle("2026-11-05").cal.title, oldStyle("2026-11-05").rank], ["Sf. Ap. Iacob, ruda Domnului; Sf. Ignatie, Patr. Constantinopolului; Sf. Cuv. Petroniu", "†"]);
const fixedCal = load("fixed-calendar");
check("Fixed calendar covers every date", Object.keys(fixedCal).length, 366);
check("Fixed calendar has no movable day in it", Object.entries(fixedCal).filter(([, e]) => /Sf\. și Marea|Sf\. Paști|Înălțarea Domnului|Rusalii|Floriilor/.test(e.title)).map(([k]) => k), []);
check("Fixed calendar uses only the calendar's signs", Object.values(fixedCal).filter((e) => e.rank && !e.rank.includes("†")).length, 0);
check("Old style: fast from the old calendar", [withVechi("2026-11-04").cal.note, withVechi("2026-11-28").cal.note, withVechi("2026-04-11").cal.note, withVechi("2027-01-07").cal.note], ["Dezlegare la ulei", "Postul Crăciunului. Dezlegare la pește", "Postul Paștelui. Post negru", "Zi fără post"]);
check("Old style: saints of the day", /Averchie/.test(withVechi("2026-11-04").cal.title) && withVechi("2026-11-04").cal.saints.length > 10, true);
check("Old style: the feast is named once, without fast remarks", /Nașterea Domnului, Dumnezeului/.test(withVechi("2027-01-07").cal.saints[0]) && !/ZI FĂRĂ POST/.test(withVechi("2027-01-07").cal.saints[0]), true);
check("Old style: Pascha is not every saint of the year", [withVechi("2026-04-12").cal.title, withVechi("2026-04-12").cal.saints], ["Învierea Domnului (Sfintele Paști)", undefined]);
check("Old style: no Sunday names or readings among the saints", Array.from({ length: 12 }, (_, i) => String(2026 + i)).flatMap((y) => Object.values(load(`vechi-${y}`)).flatMap((d) => d.saints)).filter((t) => /^(Duminica|Zi |Dezlegare|S[ăa]pt[ăa]m)/.test(t) || !/\w/.test(t)), []);
check("Old style: outside the fetched years it still works", [noVechi("2030-11-05").cal.note, /Iacob/.test(noVechi("2030-11-05").cal.title)], [undefined, true]);
check("New style ignores old-style data", L.dayContext("2026-11-05", { calendar: load("cal-2026"), sinaxar, vechi: load("vechi-2026") }).cal.saints, undefined);
check("New style is unchanged by the option", ctx("2026-11-05").cal.title, load("cal-2026")["11-05"].title);

// Past the source's calendar the app still works.
const late = L.dayContext("2040-05-06", { calendar: null, sinaxar });
check("Beyond the calendar: Pascha still computed", [late.d, late.rank, late.cal.title], [0, "(†)", "Învierea Domnului (Sfintele Paști)"]);
const calFiles = fs.readdirSync(path.join(__dirname, "docs/data")).filter((f) => f.startsWith("cal-")).sort();
check("Calendar page states the real range", [calFiles[0], calFiles[calFiles.length - 1]], ["cal-2018.json", "cal-2037.json"]);
check("Old-style data covers 2026-2037", fs.readdirSync(path.join(__dirname, "docs/data")).filter((f) => f.startsWith("vechi-")).length, 12);
check("Old-style range on the calendar page", /2026–2037/.test(fs.readFileSync(path.join(__dirname, "docs/calendar.html"), "utf8")), true);
check("Calendar page text", /2018[^<]*2037/.test(fs.readFileSync(path.join(__dirname, "docs/calendar.html"), "utf8")), true);

// Arrows between services.
const slots = [{ time: "00:00", slug: "a" }, { time: "12:00", slug: "b" }, { time: "21:00", slug: "c" }];
const adj = (t) => { const r = L.adjacentSlots(slots, t); return [r.prev.slug, r.prev.dayOffset, r.next.slug, r.next.dayOffset]; };
check("Neighbours inside the day", adj("12:00"), ["a", 0, "c", 0]);
check("First service goes back to yesterday", adj("00:00"), ["c", -1, "b", 0]);
check("Last service goes on to tomorrow", adj("21:00"), ["b", 0, "a", 1]);
check("A service outside the schedule sits between", adj("12:01"), ["b", 0, "c", 0]);

console.log(`${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
