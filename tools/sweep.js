// Opens many date/service pairs in headless Chrome; reports JS errors and empty pages.
const { spawnSync } = require("child_process");
const dates = ["2026-02-23","2026-03-07","2026-03-08","2026-03-26","2026-04-04","2026-04-05","2026-04-09","2026-04-11","2026-04-12","2026-04-18","2026-04-19","2026-05-21","2026-05-31","2026-06-10","2026-08-05","2026-08-15","2026-09-14","2026-12-24","2026-12-31","2027-01-06","2028-02-29"];
const slugs = ["01-miezonoptica","02-utrenia","03-ceasul-1","07-ceasul-6","09-ceasul-9","11-vecernia","12-pavecernita"];
let bad = 0, n = 0;
for (const d of dates) for (const s of slugs) {
  n++;
  const r = spawnSync("google-chrome", ["--headless=new","--disable-gpu","--no-sandbox","--enable-logging=stderr","--virtual-time-budget=2500","--dump-dom",`http://localhost:8010/?d=${d}&s=${s}`],{encoding:"utf8",maxBuffer:1<<28});
  const err = (r.stderr.match(/Uncaught[^"]*/g)||[]);
  const len = (r.stdout.match(/page__body[\s\S]*<\/article>/)||[""])[0].replace(/<[^>]+>/g,"").length;
  if (err.length || len < 300) { bad++; console.log("BAD", d, s, len, err[0]||""); }
}
console.log(`${n} pages, ${bad} bad`);
