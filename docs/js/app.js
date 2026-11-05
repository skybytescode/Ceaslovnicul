// Ceaslovnicul: picks the service for the current hour in Chișinău and renders
// it for the current day, resolving the source's rubrics with Liturgy.
(function () {
  "use strict";

  const TZ = "Europe/Chisinau";
  const L = globalThis.Liturgy;
  const SCHEDULE = [
    { time: "00:00", slug: "01-miezonoptica", title: "Miezonoptica" },
    { time: "05:00", slug: "02-utrenia", title: "Utrenia" },
    { time: "06:00", slug: "03-ceasul-1", title: "Ceasul Întâi" },
    { time: "07:30", slug: "04-mijloceasul-1", title: "Mijloceasul Întâi" },
    { time: "09:00", slug: "05-ceasul-3", title: "Ceasul al treilea" },
    { time: "10:30", slug: "06-mijloceasul-3", title: "Mijloceasul al treilea" },
    { time: "12:00", slug: "07-ceasul-6", title: "Ceasul al șaselea" },
    { time: "13:30", slug: "08-mijloceasul-6", title: "Mijloceasul al șaselea" },
    { time: "15:00", slug: "09-ceasul-9", title: "Ceasul al nouălea" },
    { time: "16:30", slug: "10-mijloceasul-9", title: "Mijloceasul al nouălea" },
    { time: "18:00", slug: "11-vecernia", title: "Vecernia" },
    { time: "21:00", slug: "12-pavecernita", title: "Pavecernița" },
  ];
  const EXTRA = [
    { slug: "obednita", title: "Obednița" },
    { slug: "priveghere", title: "Rânduiala Privegherii" },
    { slug: "pasti", title: "Ceasurile Paștilor" },
  ];
  const WEEKDAYS = ["Duminică", "Luni", "Marți", "Miercuri", "Joi", "Vineri", "Sâmbătă"];
  const MONTHS = ["ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie"];
  const HOUR_OF = { "03-ceasul-1": 1, "05-ceasul-3": 3, "07-ceasul-6": 6, "09-ceasul-9": 9 };

  const $ = (id) => document.getElementById(id);
  const page = $("page");
  const reader = $("reader");

  // ── Data ─────────────────────────────────────────────────────────────────
  const cache = new Map();
  // The calendar: chosen on calendar.html, remembered on this device.
  const STYLE = (() => {
    const asked = new URLSearchParams(location.search).get("stil");
    try {
      if (asked === "vechi" || asked === "nou") localStorage.setItem("ceaslovnicul-stil", asked);
      return asked || localStorage.getItem("ceaslovnicul-stil") || "nou";
    } catch {
      return asked || "nou";
    }
  })();
  function fetchData(name) {
    if (!cache.has(name)) {
      cache.set(name, fetch(`data/${name}.json`).then((r) => (r.ok ? r.json() : null)).catch(() => null));
    }
    return cache.get(name);
  }

  async function dataFor(iso) {
    const [sinaxar, hymns, services] = await Promise.all([fetchData("sinaxar"), fetchData("hymns"), fetchData("services")]);
    const next = L.addDays(iso, 1);
    const [calendar, nextCalendar] = await Promise.all([fetchData(`cal-${iso.slice(0, 4)}`), fetchData(`cal-${next.slice(0, 4)}`)]);
    if (STYLE !== "vechi") return { sinaxar, hymns, services, calendar, next: nextCalendar, style: STYLE };
    const [fixed, vechi, nextVechi] = await Promise.all([fetchData("fixed-calendar"), fetchData(`vechi-${iso.slice(0, 4)}`), fetchData(`vechi-${next.slice(0, 4)}`)]);
    return { sinaxar, hymns, services, calendar, next: nextCalendar, style: STYLE, fixed, vechi, nextVechi };
  }

  // ── Clock ────────────────────────────────────────────────────────────────
  function nowInZone() {
    const parts = new Intl.DateTimeFormat("en-GB", {
      timeZone: TZ, hour12: false, year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", second: "2-digit",
    }).formatToParts(new Date());
    const get = (t) => parts.find((p) => p.type === t).value;
    const hour = get("hour") === "24" ? "00" : get("hour");
    return { iso: `${get("year")}-${get("month")}-${get("day")}`, hhmm: `${hour}:${get("minute")}`, label: `${hour}:${get("minute")}:${get("second")}` };
  }

  // The day's slots, without those not read that day.
  function slotsFor(iso, data) {
    const c = L.dayContext(iso, data);
    return SCHEDULE.map((s) => ({ ...s, resolved: L.resolveSlug(s.slug, c) })).filter((s) => s.resolved);
  }

  function activeSlot(slots, hhmm) {
    let chosen = slots[0];
    for (const s of slots) if (s.time <= hhmm) chosen = s;
    return chosen;
  }

  // ── Rendering ────────────────────────────────────────────────────────────
  const conditions = new Map();
  function test(expr, c) {
    if (expr == null) return true;
    if (!conditions.has(expr)) conditions.set(expr, new Function("c", `with (c) { return (${expr}); }`));
    return Boolean(conditions.get(expr)(c));
  }

  function el(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function renderBlock(b) {
    const e = el(b.t === "h" ? "h3" : "p", b.c ? "align-center" : "");
    for (const [text, flags] of b.r) {
      let node = document.createTextNode(text);
      if (flags.includes("r")) { const s = el("span", "rubric"); s.append(node); node = s; }
      if (flags.includes("i")) { const s = el("em"); s.append(node); node = s; }
      if (flags.includes("b")) { const s = el("strong"); s.append(node); node = s; }
      e.append(node);
    }
    return e;
  }

  function hymn(parent, label, text) {
    if (label) parent.append(el("p", "slot__label", label));
    parent.append(el("p", "", text));
  }

  // Say a list of troparia the way each service sets them out.
  function troparia(parent, list, { repeatFirst, slavaOnLast, end, c }) {
    const hymns = c.data.hymns;
    const lit = c.lit;
    list.forEach((t, i) => {
      const last = i === list.length - 1;
      const prefix = slavaOnLast && last && (list.length > 1 || end !== "only") ? `${hymns.prayers.slava} ` : "";
      const times = repeatFirst && i === 0 ? ` (de ${lit.feast ? 3 : 2} ori)` : "";
      hymn(parent, `${prefix}${t.label}${times} :`, t.text);
    });
    return hymns;
  }

  function renderSlot(item, c) {
    const box = el("div", "slot");
    const { hymns } = c.data;
    const lit = c.lit;
    const a = item.a || {};
    switch (item.slot) {
      case "tropar": {
        // From Pascha to Bright Saturday: "Hristos a înviat", in the source's own words.
        if (c.bright && lit.bright) {
          hymn(box, "Troparul Paștilor :", c.data.services.pasti[0].r.map((r) => r[0]).join("").trim());
          break;
        }
        const list = L.tropare(lit, hymns);
        const eveningOf = c.evening ? c.eve : (new Date(`${c.date}T00:00Z`).getUTCDay() + 6) % 7;
        const lastGlas = list[list.length - 1]?.glas || lit.glas;
        if (a.mode === "ceas") {
          // The Hours: Slavă... on the troparion; the service's own Și acum follows.
          list.forEach((t, i) => hymn(box, `${i === list.length - 1 ? `${hymns.prayers.slava} ` : ""}${t.label} :`, t.text));
        } else if (a.mode === "pavecernita") {
          const day = lit.sun ? [] : (hymns.tropareSapt[lit.dow] ?? []);
          for (const t of (lit.sin?.t ?? []).slice(0, 2)) hymn(box, `${t.l} :`, t.x);
          if (c.eve !== 5) for (const t of day) hymn(box, `${t.l} :`, t.x);
          if (lit.sun) hymn(box, `Troparul Învierii, glasul ${lit.glas} :`, hymns.invierii[lit.glas].t);
        } else {
          // Dumnezeu este Domnul (ded), end of Matins (end), Vespers (vecernie).
          const twice = a.mode === "ded";
          troparia(box, list, { repeatFirst: twice, slavaOnLast: list.length > 1, c });
          if (lit.feast && list.length === 1 && a.mode !== "end") {
            box.append(el("p", "align-center", `${hymns.prayers.slava} ${hymns.prayers.acum} Același tropar.`));
          } else {
            const text = L.bogorodicina(lastGlas, eveningOf, hymns, a.mode === "end");
            hymn(box, `${list.length > 1 ? hymns.prayers.acum : `${hymns.prayers.slava} ${hymns.prayers.acum}`} Al Născătoarei de Dumnezeu, glasul ${lastGlas} :`, text);
          }
        }
        break;
      }
      case "condac": {
        if (a.weekly) {
          const list = lit.sun ? L.condac(lit, 1, hymns) : (hymns.condaceSapt[lit.dow] ?? []).map((s) => ({ label: s.l, text: s.x }));
          const seen = new Set(list.map((x) => x.text));
          for (const x of L.condac(lit, 1, hymns)) if (!seen.has(x.text)) list.push(x);
          for (const x of list) hymn(box, `${x.label} :`, x.text);
        } else {
          const hour = a.evening ? 1 : a.hour;
          for (const x of L.condac(lit, hour, hymns)) hymn(box, `${x.label} :`, x.text);
        }
        break;
      }
      case "catisma": {
        const list = L.catisme(c, a.at);
        for (const n of list) {
          const d = el("details", "catisma");
          const s = el("summary", "", n === "polieleu" ? "Polieleul (în locul Catismei a 17-a)" : `Catisma ${n}`);
          d.append(s);
          if (n === "polieleu") {
            d.append(el("p", "note", "Polieleul se cântă din versete alese ale Psalmului 134; aici este psalmul întreg."));
            d.append(el("p", "", hymns.polieleu));
          } else {
            d.addEventListener("toggle", async () => {
              if (d.dataset.ready) return;
              d.dataset.ready = "1";
              const psalter = await fetchData("psaltire");
              for (const b of psalter?.[n] ?? []) d.append(renderBlock(b));
            });
          }
          box.append(d);
        }
        break;
      }
      case "treimice": {
        box.append(el("p", "slot__label", `Cântările Treimice, glasul ${lit.glas} :`));
        for (const row of hymns.treimice[lit.glas]) box.append(renderBlock(row));
        const ending = hymns.treimice.endings[lit.dow];
        if (ending) box.append(el("p", "", ending));
        break;
      }
      case "ipacoi":
        hymn(box, `Ipacoi, glasul ${lit.glas} :`, hymns.invierii[lit.glas].i);
        break;
      case "luminanda": {
        const lum = hymns.luminande;
        const list = lit.sun ? lum.v[lit.voscr] : c.L ? lum.lent[lit.glas] : (lum.week[lit.dow] ?? []);
        const title = lit.sun ? `Luminânda ${lit.voscr}` : "Luminânda zilei";
        (list ?? []).forEach((text, i) => hymn(box, i === 0 ? `${title} :` : "", text));
        break;
      }
      case "canonTreime": {
        box.append(el("p", "slot__label", `Canonul Sfintei Treimi, glasul ${lit.glas}`));
        const d = el("details", "catisma");
        d.append(el("summary", "", "Deschide canonul"));
        d.addEventListener("toggle", async () => {
          if (d.dataset.ready) return;
          d.dataset.ready = "1";
          const data = await fetchData("canon-treime");
          for (const b of data?.[lit.glas] ?? []) d.append(renderBlock(b));
        });
        box.append(d);
        break;
      }
      case "canonMD": {
        box.append(el("p", "slot__label", `Canonul Maicii Domnului, glasul ${lit.glas}`));
        const d = el("details", "catisma");
        d.append(el("summary", "", "Deschide canonul"));
        d.addEventListener("toggle", async () => {
          if (d.dataset.ready) return;
          d.dataset.ready = "1";
          const data = await fetchData(`canon-md-${lit.glas}`);
          for (const b of data?.[c.eve] ?? []) d.append(renderBlock(b));
        });
        box.append(d);
        break;
      }
      default:
        box.append(el("p", "note", `(${item.slot})`));
    }
    return box;
  }

  function renderItems(items, c, parent) {
    for (const item of items) {
      const show = test(item.w, c);
      if (!show && !state.full) continue;
      const node = item.slot ? renderSlot(item, c) : renderBlock(item);
      if (!show) node.classList.add("hidden-branch");
      parent.append(node);
    }
  }

  function formatDate(iso) {
    const [y, m, d] = iso.split("-").map(Number);
    const dow = new Date(Date.UTC(y, m - 1, d)).getUTCDay();
    return `${WEEKDAYS[dow]}, ${d} ${MONTHS[m - 1]} ${y}`;
  }

  // Every cross opens the page where the calendar is chosen.
  function crossLink(cls) {
    const a = el("a", cls);
    a.href = "calendar.html";
    a.setAttribute("aria-label", "Alege calendarul: stil nou sau stil vechi");
    a.title = "Alege calendarul";
    return a;
  }

  function dayHeader(parent, iso, c, title, time) {
    const lit = c.lit;
    const head = el("div", "day");
    const facts = [formatDate(iso)];
    if (c.style === "vechi") {
      const [, m, d] = L.addDays(iso, -13).split("-").map(Number);
      facts.push(`stil vechi: ${d} ${MONTHS[m - 1]}`);
    }
    if (c.fastName) facts.push(c.fastName);
    else if (c.periodName !== "Octoih") facts.push(c.periodName);
    if (!c.bright) facts.push(`glasul ${lit.glas}`);
    head.append(el("div", "", facts.join(" · ")));
    const saint = lit.cal?.title || lit.sin?.title || "";
    if (lit.cal?.sunday) head.append(el("div", "day__saint", lit.cal.sunday));
    if (saint) {
      // The crosses are the calendar's signs; the Sinaxar's dots are only for the rules.
      const sign = lit.rank.includes("†") ? `${lit.rank} ` : "";
      head.append(el("div", "day__saint", `${sign}${saint}`));
      if (lit.cal?.saints?.length > L.HEADER_SAINTS) {
        const all = el("details", "day__all");
        all.append(el("summary", "", `Toți sfinții zilei (${lit.cal.saints.length})`));
        for (const name of lit.cal.saints) all.append(el("p", "", name));
        head.append(all);
      }
    }
    if (c.evening) head.append(el("div", "day__rubric", "Seara: troparele și condacele sunt ale zilei de mâine."));
    if (lit.cal?.note) head.append(el("div", "day__rubric", lit.cal.note));
    parent.append(head);
    if (time) {
      const eyebrow = el("div", "page__eyebrow");
      eyebrow.append(el("span", "scheduled-time", `Ora ${time}`));
      parent.append(eyebrow);
    }
    parent.append(el("h1", "page__title", title));
    parent.append(crossLink("page__rule"));
  }

  const state = { iso: null, slug: null, manual: false, full: false, shown: null };

  function titleOf(slug, c) {
    const s = SCHEDULE.find((x) => x.slug === slug) || EXTRA.find((x) => x.slug === slug);
    return s ? s.title : slug;
  }

  // Arrows to the service before and after this one. Services outside the day's
  // schedule take the place in it where they are read.
  function serviceNav(iso, slug, base, data, where) {
    const extraTime = { obednita: base.Lw ? "15:01" : "12:01", priveghere: "18:01", pasti: "00:00" };
    const time = SCHEDULE.find((s) => s.slug === slug)?.time ?? extraTime[slug];
    const { prev, next } = L.adjacentSlots(slotsFor(iso, data), time);
    const nav = el("nav", `service-nav service-nav--${where}`);
    nav.setAttribute("aria-label", "Slujba precedentă și următoare");
    const link = (s, arrow, cls, hint, name) => {
      const day = s.dayOffset < 0 ? " (ieri)" : s.dayOffset > 0 ? " (mâine)" : "";
      const btn = el("button", `linkbtn service-nav__btn ${cls}`);
      btn.type = "button";
      btn.setAttribute("aria-label", `${hint}: ${s.title}${day}, ora ${s.time}`);
      const label = el("span", "service-nav__label");
      label.append(el("span", "service-nav__time", s.time), `${s.title}${day}`);
      const icon = el("span", "service-nav__arrow", arrow);
      icon.setAttribute("aria-hidden", "true");
      if (name === "prev") btn.append(icon, label); else btn.append(label, icon);
      btn.addEventListener("click", () => go(L.addDays(iso, s.dayOffset), s.slug));
      return btn;
    };
    nav.append(link(prev, "←", "service-nav__prev", "Slujba precedentă", "prev"), link(next, "→", "service-nav__next", "Slujba următoare", "next"));
    return nav;
  }

  async function show(iso, slug, { keepScroll } = {}) {
    const data = await dataFor(iso);
    if (!data.services || !data.hymns) {
      page.textContent = "";
      page.append(el("p", "note", "Textele nu s-au putut încărca. Verifică conexiunea și reîncarcă pagina."));
      return;
    }
    const base = L.dayContext(iso, data);
    const resolved = L.resolveSlug(slug, base) ?? slug;
    const c = L.serviceContext(iso, resolved, data);
    c.data = data;
    c.pav = slug.startsWith("12-");
    state.iso = iso;
    state.slug = slug;
    state.shown = `${iso}|${slug}`;

    const top = reader.scrollTop;
    page.textContent = "";
    page.append(serviceNav(iso, slug, base, data, "top"));
    const title = titleOf(slug) + (resolved === "pasti" && slug !== "pasti" ? " · Ceasurile Paștilor" : "");
    dayHeader(page, iso, c, title, SCHEDULE.find((s) => s.slug === slug)?.time);
    if (resolved === "pasti") page.append(el("p", "note", "În Săptămâna Luminată, Ceasurile, Pavecernița și Miezonoptica se citesc în acest chip."));
    if (/mijloceasul/.test(slug) && !L.resolveSlug(slug, base)) page.append(el("p", "note", "Mijloceasurile se citesc în zilele de post. Azi nu sunt rânduite."));

    const body = el("div", "page__body");
    renderItems(data.services[resolved] ?? [], c, body);
    // Obednița follows the Sixth Hour, or the Ninth on "Aliluia" days and in Lent.
    const obednitaAfter = base.Lw ? "09-ceasul-9" : "07-ceasul-6";
    if (slug === obednitaAfter && !base.bright) {
      body.append(el("h2", "align-center", "Obednița"));
      renderItems(data.services.obednita, c, body);
    }
    if (slug === "11-vecernia" && (c.eve === 6 || c.lit.polieleu)) {
      const more = el("div", "service-next");
      const btn = el("button", "linkbtn", "Rânduiala Privegherii");
      btn.addEventListener("click", () => go(iso, "priveghere"));
      more.append(btn);
      body.append(more);
    }
    page.append(body);
    page.append(serviceNav(iso, slug, base, data, "bottom"));
    page.append(crossLink("page__footer-mark"));
    document.title = `Ceaslovnicul · ${titleOf(slug)}`;
    reader.scrollTop = keepScroll ? top : 0;
    syncPickers(data);
    syncUrl();
  }

  function syncPickers(data) {
    const sel = $("pick-service");
    const slots = slotsFor(state.iso, data);
    sel.textContent = "";
    const add = (slug, label) => {
      const o = el("option", "", label);
      o.value = slug;
      sel.append(o);
    };
    for (const s of slots) add(s.slug, `${s.time} ${s.title}`);
    for (const s of EXTRA) add(s.slug, s.title);
    if (![...sel.options].some((o) => o.value === state.slug)) add(state.slug, titleOf(state.slug));
    sel.value = state.slug;
    $("pick-date").value = state.iso;
    $("now-btn").hidden = !state.manual;
  }

  function syncUrl() {
    const q = new URLSearchParams();
    if (state.manual) { q.set("d", state.iso); q.set("s", state.slug); }
    if (state.full) q.set("full", "1");
    if (STYLE === "vechi") q.set("stil", "vechi");
    const text = q.toString();
    history.replaceState(null, "", text ? `?${text}` : location.pathname);
  }

  function go(iso, slug) {
    state.manual = true;
    return show(iso, slug);
  }

  // ── Following the clock ──────────────────────────────────────────────────
  // Moves on by itself only while the reader is at the top of a page; otherwise
  // it offers the new service, so a prayer in progress is never cut off.
  async function tick() {
    const t = nowInZone();
    $("status-now").textContent = t.label;
    const data = await dataFor(t.iso);
    if (!data.services) return;
    const slots = slotsFor(t.iso, data);
    const active = activeSlot(slots, t.hhmm);
    const next = slots.find((s) => s.time > t.hhmm) ?? slotsFor(L.addDays(t.iso, 1), await dataFor(L.addDays(t.iso, 1)))[0];
    $("status-next").textContent = `Următor: ${next.time} · ${next.title}`;
    remind(next, t);

    if (state.manual) { $("banner").hidden = true; return; }
    const key = `${t.iso}|${active.slug}`;
    if (key === state.shown) { $("banner").hidden = true; return; }
    if (state.shown === null || reader.scrollTop < 40) {
      $("banner").hidden = true;
      await show(t.iso, active.slug);
    } else {
      $("banner-text").textContent = `A început: ${active.title}`;
      $("banner").hidden = false;
      $("banner-go").onclick = () => show(t.iso, active.slug);
    }
  }

  // ── Reminders ────────────────────────────────────────────────────────────
  const NOTIF_KEY = "ceaslovnicul.notify";
  const notifBtn = $("notif-btn");
  const notifOn = () => "Notification" in globalThis && Notification.permission === "granted" && store.get(NOTIF_KEY) === "1";
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch { /* private mode */ } },
  };
  function paintNotif() {
    if (!("Notification" in globalThis)) { notifBtn.hidden = true; return; }
    notifBtn.textContent = notifOn() ? "🔔" : "🔕";
    notifBtn.title = notifOn() ? "Notificările sunt active" : "Notificare cu 5 minute înainte de fiecare ceas (cât timp aplicația e deschisă)";
  }
  notifBtn.addEventListener("click", async () => {
    if (Notification.permission === "default") await Notification.requestPermission();
    store.set(NOTIF_KEY, store.get(NOTIF_KEY) === "1" ? "0" : "1");
    paintNotif();
  });
  let lastReminder = null;
  function remind(next, t) {
    if (!notifOn()) return;
    const [h, m] = next.time.split(":").map(Number);
    const [nh, nm] = t.hhmm.split(":").map(Number);
    let ahead = h * 60 + m - nh * 60 - nm;
    if (ahead < 0) ahead += 1440;
    if (ahead <= 0 || ahead > 5 || lastReminder === `${t.iso}${next.slug}`) return;
    lastReminder = `${t.iso}${next.slug}`;
    const body = `În ${ahead} min: ${next.title} (${next.time})`;
    // Android Chrome only allows notifications through the service worker.
    navigator.serviceWorker?.ready
      .then((reg) => reg.showNotification("Ceaslovnicul", { body, icon: "css/chi-rho.png", tag: "ceaslovnicul-reminder" }))
      .catch(() => { try { new Notification("Ceaslovnicul", { body, icon: "css/chi-rho.png" }); } catch { /* unsupported */ } });
  }

  // ── Controls ─────────────────────────────────────────────────────────────
  $("pick-service").addEventListener("change", (e) => go(state.iso, e.target.value));
  $("pick-date").addEventListener("change", (e) => { if (e.target.value) go(e.target.value, state.slug); });
  $("now-btn").addEventListener("click", () => { state.manual = false; state.shown = ""; reader.scrollTop = 0; tick(); });
  $("full-btn").addEventListener("click", () => {
    state.full = !state.full;
    $("full-btn").setAttribute("aria-pressed", String(state.full));
    show(state.iso, state.slug, { keepScroll: true });
  });

  const SCALE_KEY = "ceaslovnicul.textScale";
  const SCALES = [0.85, 1, 1.15, 1.3, 1.5, 1.75];
  function applyScale(s) {
    store.set(SCALE_KEY, String(s));
    document.documentElement.style.setProperty("--reader-scale", String(s));
    $("text-smaller").disabled = s === SCALES[0];
    $("text-larger").disabled = s === SCALES[SCALES.length - 1];
  }
  const storedScale = () => { const s = Number.parseFloat(store.get(SCALE_KEY)); return SCALES.includes(s) ? s : 1; };
  const stepScale = (delta) => {
    const i = SCALES.indexOf(storedScale());
    applyScale(SCALES[Math.min(SCALES.length - 1, Math.max(0, i + delta))]);
  };
  $("text-smaller").addEventListener("click", () => stepScale(-1));
  $("text-larger").addEventListener("click", () => stepScale(1));
  applyScale(storedScale());

  // Keep the screen on while a service is open.
  let wakeLock = null;
  async function requestWakeLock() {
    if (!("wakeLock" in navigator) || wakeLock || document.visibilityState !== "visible") return;
    try {
      wakeLock = await navigator.wakeLock.request("screen");
      wakeLock.addEventListener("release", () => { wakeLock = null; });
    } catch { /* needs a gesture on some browsers; retried below */ }
  }
  document.addEventListener("visibilitychange", requestWakeLock);
  document.addEventListener("pointerdown", requestWakeLock, { passive: true });

  const installBtn = $("install-btn");
  let installPrompt = null;
  globalThis.addEventListener("beforeinstallprompt", (e) => { e.preventDefault(); installPrompt = e; installBtn.hidden = false; });
  installBtn.addEventListener("click", async () => { installPrompt?.prompt(); installPrompt = null; installBtn.hidden = true; });

  if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});

  // ── Start ────────────────────────────────────────────────────────────────
  const params = new URLSearchParams(location.search);
  state.full = params.get("full") === "1";
  $("full-btn").setAttribute("aria-pressed", String(state.full));
  paintNotif();
  requestWakeLock();
  (async () => {
    if (params.get("d") && params.get("s")) await go(params.get("d"), params.get("s"));
    await tick();
    setInterval(tick, 1000);
  })();
})();
