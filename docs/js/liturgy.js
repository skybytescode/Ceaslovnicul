// The liturgical day: everything the Ceaslov's rubrics ask about a date, and
// which hymns and kathismata they select. Pure functions, shared by the browser
// and the Node tests. Dates are "YYYY-MM-DD" strings in the new calendar, which
// is what the source site's calendar uses.
(function (root) {
  "use strict";

  const DAY = 86400000;
  const toUTC = (iso) => { const [y, m, d] = iso.split("-").map(Number); return Date.UTC(y, m - 1, d); };
  const fromUTC = (t) => new Date(t).toISOString().slice(0, 10);
  const addDays = (iso, n) => fromUTC(toUTC(iso) + n * DAY);
  const diffDays = (a, b) => Math.round((toUTC(a) - toUTC(b)) / DAY);
  const mmdd = (iso) => iso.slice(5);

  // Orthodox Pascha: Julian computus, shifted to the new calendar (+13 days,
  // valid 1900–2099).
  function pascha(year) {
    const a = year % 4, b = year % 7, c = year % 19;
    const d = (19 * c + 15) % 30;
    const e = (2 * a + 4 * b - d + 34) % 7;
    const month = Math.floor((d + e + 114) / 31);
    const day = ((d + e + 114) % 31) + 1;
    return addDays(fromUTC(Date.UTC(year, month - 1, day)), 13);
  }

  function paschaOffset(iso) {
    const y = Number(iso.slice(0, 4));
    const p = pascha(y);
    return { offset: diffDays(iso, p), pascha: p, previous: pascha(y - 1) };
  }

  // Tone of the week: an 8-week cycle from Thomas Sunday, running through
  // Holy Week until the next Thomas Sunday.
  function glasOf(iso) {
    const { offset, pascha: p, previous } = paschaOffset(iso);
    const start = addDays(offset >= 7 ? p : previous, 7);
    const weeks = Math.floor(diffDays(iso, start) / 7);
    return (weeks % 8) + 1;
  }

  // Sunday matins gospel: an 11-week cycle from All Saints Sunday.
  function voscrOf(iso) {
    const { offset, pascha: p, previous } = paschaOffset(iso);
    // Between Thomas and All Saints the Sundays have their own fixed gospels.
    const fixed = { 7: 1, 14: 4, 21: 5, 28: 7, 35: 8, 42: 10 }[offset];
    if (fixed) return fixed;
    const start = addDays(offset >= 56 ? p : previous, 56);
    const weeks = Math.floor(diffDays(iso, start) / 7);
    return (weeks % 11) + 1;
  }

  const inRange = (m, from, to) => m >= from && m <= to;
  const RANKS = ["", ".", ".)", "†", "†)", "(†)"];

  // Days named by Pascha rather than by the date. The great feasts among them
  // outrank the saint of the date, on either calendar.
  const MOVABLE_FEASTS = {
    "-7": "Intrarea Domnului în Ierusalim (Duminica Floriilor)", 0: "Învierea Domnului (Sfintele Paști)",
    1: "A doua zi de Paști", 2: "A treia zi de Paști", 39: "Înălțarea Domnului",
    49: "Pogorârea Sfântului Duh (Cincizecimea)", 50: "Sfânta Treime",
  };
  const HOLY_WEEK = { "-6": "Sfânta și Marea Luni", "-5": "Sfânta și Marea Marți", "-4": "Sfânta și Marea Miercuri",
    "-3": "Sfânta și Marea Joi", "-2": "Sfânta și Marea Vineri", "-1": "Sfânta și Marea Sâmbătă" };

  // The Sunday's name survives the change of calendar only as far as it hangs on
  // Pascha: the parts that follow fixed feasts or the Lukan jump are dropped.
  function oldStyleSunday(name) {
    if (!name) return undefined;
    if (/după Paști|din Post|Lăsatului|Zaheu|Vameș|Fiului Risipitor|Tuturor Sfinților/.test(name)) return name;
    return /după Rusalii/.test(name) ? name.replace(/\s*\(.*$/, "") : undefined;
  }

  const HEADER_SAINTS = 3;

  // A day's entry where the source's calendar cannot give it: on the old calendar,
  // whose saints fall 13 days later, and in years beyond the source's calendar.
  function computedDay(d, day, civil, old, vechi) {
    const great = MOVABLE_FEASTS[d];
    const saints = vechi?.saints.length ? vechi.saints : null;
    const named = saints ? saints.slice(0, HEADER_SAINTS).join(" ") : day?.title;
    return {
      title: great ?? [HOLY_WEEK[d], named].filter(Boolean).join("; "),
      rank: great ? "(†)" : day?.rank ?? "",
      sunday: old ? oldStyleSunday(civil?.sunday) : civil?.sunday,
      note: vechi?.post || undefined,
      saints: saints ?? undefined,
    };
  }

  // What the rubrics ask about one civil date. With `data.style` "vechi" the saints
  // and fixed feasts are those of the date 13 days earlier; Pascha does not move.
  function dayContext(iso, data) {
    const { offset: d, pascha: p } = paschaOffset(iso);
    const dow = new Date(toUTC(iso)).getUTCDay();
    const old = data?.style === "vechi";
    const m = mmdd(old ? addDays(iso, -13) : iso);
    const civil = data?.calendar?.[mmdd(iso)];
    const sin = data?.sinaxar?.[m];
    const cal = civil && !old ? civil : computedDay(d, data?.fixed?.[m] ?? sin, civil, old, old ? data?.vechi?.[mmdd(iso)] : null);
    const rank = cal.rank;
    const rankN = RANKS.indexOf(rank);

    const lentPeriod = d >= -48 && d <= -1;
    const HW = d >= -6 && d <= -1;
    const feast = rank === "(†)";
    const weekday = dow >= 1 && dow <= 5;
    // Ordinary weekday of Great Lent: the source's "zi obișnuită". Annunciation
    // and other great feasts keep the festal order.
    const L = d >= -48 && d <= -9 && weekday && !feast;
    const apostles = d >= 57 && m <= "06-28";
    const nativity = inRange(m, "11-15", "12-24");
    const dormition = inRange(m, "08-01", "08-14");
    // "Aliluia" instead of "Dumnezeu este Domnul": weekdays of the other fasts
    // when no saint with doxology or polyeleos is kept.
    const A = !lentPeriod && (apostles || nativity || dormition) && weekday && rankN < RANKS.indexOf(".)");
    const bright = d >= 0 && d <= 6;
    const pent = d >= 0 && d <= 56;
    const triod = d >= -70 && d <= -1;

    return {
      date: iso, m, dow, pascha: p, d, rank, cal, sin, style: old ? "vechi" : "nou",
      movableFeast: d in MOVABLE_FEASTS,
      sun: dow === 0, mon: dow === 1, tue: dow === 2, wed: dow === 3, thu: dow === 4, fri: dow === 5, sat: dow === 6,
      L, HW, A, Lw: L || HW || A, post: L || A,
      lentPeriod, firstLentWeek: d >= -48 && d <= -44,
      lentWeek: lentPeriod ? Math.floor((d + 48) / 7) + 1 : 0,
      bright, pent, triod, feast,
      doxo: rankN >= RANKS.indexOf(".)"),
      polieleu: rankN >= RANKS.indexOf("†"),
      glas: glasOf(iso), voscr: voscrOf(iso),
      fastName: lentPeriod ? "Postul Mare" : apostles ? "Postul Sfinților Apostoli" : nativity ? "Postul Nașterii Domnului" : dormition ? "Postul Adormirii Maicii Domnului" : "",
      periodName: bright ? "Săptămâna Luminată" : HW ? "Săptămâna Patimilor" : lentPeriod ? "Postul Mare" : pent ? "Penticostar" : triod ? "Triod" : "Octoih",
    };
  }

  // Evening services are read on `iso` but belong to the next liturgical day:
  // the rubrics' day-of-week tests use the evening, the hymns use the morrow.
  const EVENING = new Set(["11-vecernia", "12-pavecernita", "priveghere"]);

  function serviceContext(iso, slug, data) {
    const c = dayContext(iso, data);
    const evening = EVENING.has(slug);
    const lit = evening ? dayContext(addDays(iso, 1), data.next ? { ...data, calendar: data.next, vechi: data.nextVechi } : data) : c;
    return { ...c, lit, eve: c.dow, evening };
  }

  // Which service a schedule slot resolves to on a day. Null means the slot is
  // not read that day (the Mijloceasuri are only for fast days).
  function resolveSlug(slug, c) {
    if (c.bright && /^(01-|03-|05-|07-|09-|12-)/.test(slug)) return "pasti";
    if (c.bright && /mijloceasul/.test(slug)) return null;
    if (/mijloceasul/.test(slug) && !c.post) return null;
    return slug;
  }

  // The services before and after a time of day. `slots` are the day's services in
  // order; past either end, the neighbour is the first or last of the next or previous day.
  function adjacentSlots(slots, time) {
    const earlier = slots.filter((s) => s.time < time);
    const later = slots.filter((s) => s.time > time);
    return {
      prev: earlier.length ? { ...earlier[earlier.length - 1], dayOffset: 0 } : { ...slots[slots.length - 1], dayOffset: -1 },
      next: later.length ? { ...later[0], dayOffset: 0 } : { ...slots[0], dayOffset: 1 },
    };
  }

  // ── Hymns ─────────────────────────────────────────────────────────────────
  const latest = (table, d) => {
    let found = null;
    for (const e of table) if (e.off <= d) found = e;
    return found;
  };

  // The moveable entry in force, per the source: "troparul Praznicului (cel din
  // Duminica ce a trecut)". Holy Week days have their own entries.
  function moveableEntry(lit, hymns) {
    if (lit.pent) return latest(hymns.pent, lit.d);
    if (lit.triod) return latest(hymns.triod, lit.d);
    return null;
  }

  const saintTropare = (lit) => lit.sin?.t ?? [];
  const saintCondace = (lit) => lit.sin?.c ?? [];

  // The troparia said in place of "Dumnezeu este Domnul" at the hours, and at
  // Vespers and Matins. Returns [{label, text, glas, prefix}].
  function tropare(lit, hymns) {
    const out = [];
    const saints = saintTropare(lit);
    const entry = moveableEntry(lit, hymns);
    if (lit.movableFeast && entry?.t.length) return entry.t.map((t) => ({ label: t.l, text: t.x, glas: t.g }));
    if (lit.feast && !lit.movableFeast && saints.length) return saints.slice(0, 1).map((s) => ({ label: s.l, text: s.x, glas: s.g }));
    // A Pentecostarion feast keeps its troparion through its week of after-feast
    // (Mid-Pentecost, for instance, until its leave-taking seven days on).
    const festal = lit.pent && !entry?.t.length && !lit.sun
      ? [...hymns.pent].reverse().find((e) => e.off <= lit.d && lit.d - e.off <= 7 && e.t.length)
      : null;
    if (entry?.t.length || festal) {
      for (const t of (entry?.t.length ? entry : festal).t) out.push({ label: t.l, text: t.x, glas: t.g });
    } else if (lit.sun) {
      const inv = hymns.invierii[lit.glas];
      out.push({ label: `Troparul Învierii, glasul ${lit.glas}`, text: inv.t, glas: lit.glas });
    }
    const list = saints.length ? saints : (out.length ? [] : hymns.tropareSapt[lit.dow] ?? []);
    for (const s of list) out.push({ label: s.l, text: s.x, glas: s.g });
    if (!out.length) for (const t of hymns.tropareSapt[lit.dow] ?? []) out.push({ label: t.l, text: t.x, glas: t.g });
    return out;
  }

  // The kontakion of an hour. With two saints the hours alternate between them
  // ("le zicem schimbându-le"): Hour 1 and 6 the first, Hour 3 and 9 the second.
  function condac(lit, hour, hymns) {
    const entry = moveableEntry(lit, hymns);
    const saints = saintCondace(lit);
    if (lit.movableFeast && entry?.c.length) return entry.c.map(hymnOf);
    if (lit.feast && !lit.movableFeast && saints.length) return [hymnOf(saints[0])];
    if (lit.pent && entry?.c.length) return entry.c.map(hymnOf);
    if (lit.triod && entry?.c.length && (lit.sun || lit.sat || lit.HW || !lit.lentPeriod)) return entry.c.map(hymnOf);
    if (lit.sun) {
      const inv = hymns.invierii[lit.glas];
      return [{ label: `Condacul Învierii, glasul ${lit.glas}`, text: inv.c, glas: lit.glas }];
    }
    if (saints.length) {
      const pick = saints.length > 1 && (hour === 3 || hour === 9) ? saints[1] : saints[0];
      return [hymnOf(pick)];
    }
    return (hymns.condaceSapt[lit.dow] ?? []).map(hymnOf);
  }

  const hymnOf = (s) => ({ label: s.l, text: s.x, glas: s.g });

  // Theotokion of the tone and the evening; [0] after "Dumnezeu este Domnul",
  // [1] at the end of Matins. Saturday evening takes the Resurrection one.
  function bogorodicina(glas, evening, hymns, end) {
    const g = glas || 1;
    if (evening === 6) return hymns.invierii[g].b;
    const list = hymns.bog[g]?.[evening];
    return list ? list[end ? 1 : 0] ?? list[0] : hymns.invierii[g].b;
  }

  // ── Kathismata (RÂNDUIALA CITIRII PSALTIRII) ──────────────────────────────
  const LENT_NORMAL = {
    1: { u: [4, 5, 6], 3: 7, 6: 8, 9: 9, v: 18 },
    2: { u: [10, 11, 12], 1: 13, 3: 14, 6: 15, 9: 16, v: 18 },
    3: { u: [19, 20, 1], 1: 2, 3: 3, 6: 4, 9: 5, v: 18 },
    4: { u: [6, 7, 8], 1: 9, 3: 10, 6: 11, 9: 12, v: 18 },
    5: { u: [13, 14, 15], 3: 19, 6: 20, v: 18 },
  };
  const LENT_WEEK5 = {
    1: { u: [4, 5, 6], 3: 7, 6: 8, 9: 9, v: 10 },
    2: { u: [11, 12, 13], 1: 14, 3: 15, 6: 16, 9: 18, v: 7 },
    3: { u: [20, 1, 2], 1: 3, 3: 4, 6: 5, 9: 6, v: 7 },
    4: { u: [8], 3: 9, 6: 10, 9: 11, v: 12 },
    5: { u: [13, 14, 15], 3: 19, 6: 20, v: 18 },
  };
  const HOLY = {
    1: { u: [4, 5, 6], 3: 7, 6: 8, v: 18 },
    2: { u: [9, 10, 11], 3: 12, 6: 13, v: 18 },
    3: { u: [14, 15, 16], 3: 19, 6: 20, v: 18 },
  };
  const LIGHT = { // Thomas Sunday – 21 Sep, 21 Dec – 14 Jan, and the two weeks before Lent
    1: { u: [4, 5], v: 6 }, 2: { u: [7, 8], v: 9 }, 3: { u: [10, 11], v: 12 },
    4: { u: [13, 14], v: 15 }, 5: { u: [19, 20], v: 18 }, 6: { u: [16, 17], v: 1 },
  };
  const FULL = { // 22 Sep – 20 Dec, 15 Jan – the Saturday before the Prodigal Son
    1: { u: [4, 5, 6], v: 18 }, 2: { u: [7, 8, 9], v: 18 }, 3: { u: [10, 11, 12], v: 18 },
    4: { u: [13, 14, 15], v: 18 }, 5: { u: [19, 20], v: 18 }, 6: { u: [16, 17], v: 1 },
  };

  // Kathismata for `at` ("u" Matins, "v" Vespers, "1"/"3"/"6"/"9" the Hours).
  // Returns a list of numbers, possibly with "polieleu" as the last Sunday item.
  function catisme(c, at) {
    const { dow, d, m } = c;
    if (d >= -2 && d <= 6) return [];       // none from Holy Thursday until Thomas Saturday
    if (d === -3) return [];
    if (dow === 0) {
      if (at !== "u") return [];
      if (c.lentPeriod) return d === -7 ? [2, 3, "polieleu"] : [2, 3, 17];
      const full = inRange(m, "09-22", "12-20") || m >= "01-15" && m < "09-22" && d < -63;
      const third = c.feast || c.polieleu || full || d === -63 || d === -56 || d === 7 ? "polieleu" : 17;
      return [2, 3, third];
    }
    let table;
    if (c.HW) table = HOLY;
    else if (d >= -48 && d <= -9) table = d >= -20 && d <= -15 ? LENT_WEEK5 : LENT_NORMAL;
    if (table) {
      const row = table[dow];
      if (dow === 6 || !row) return at === "u" ? [16, 17] : at === "v" ? [1] : [];
      const v = row[at];
      return v == null ? [] : Array.isArray(v) ? v : [v];
    }
    if (at !== "u" && at !== "v") return [];
    const isFull = inRange(m, "09-22", "12-20") || (m >= "01-15" && d < -63 && m < "09-22");
    const row = (isFull ? FULL : LIGHT)[dow];
    const v = row?.[at];
    return v == null ? [] : Array.isArray(v) ? v : [v];
  }

  const api = {
    pascha, addDays, diffDays, glasOf, voscrOf, dayContext, serviceContext, resolveSlug, adjacentSlots,
    tropare, condac, bogorodicina, catisme, moveableEntry, HEADER_SAINTS,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Liturgy = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
