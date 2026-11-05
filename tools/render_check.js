// Dumps what the real page renders for a date and service, using headless Chrome.
const { execFileSync } = require("child_process");
const [,, url] = process.argv;
const out = execFileSync("google-chrome", ["--headless=new","--disable-gpu","--no-sandbox","--virtual-time-budget=6000","--dump-dom",url],{encoding:"utf8",maxBuffer:1<<28,stdio:["ignore","pipe","ignore"]});
const m = out.match(/<div class="page__inner" id="page">([\s\S]*?)<\/article>/);
const text = (m?m[1]:out).replace(/<\/(p|h1|h2|h3|div|summary)>/g,"\n").replace(/<[^>]+>/g,"").replace(/&nbsp;/g," ");
console.log(text);
