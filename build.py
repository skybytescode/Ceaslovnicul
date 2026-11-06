"""Build docs/data/*.json from the parsed Ceaslov pages (source/blocks/*.json).

Every source paragraph is kept. Each one may carry a `w` condition, a JavaScript
expression over the liturgical context (see docs/js/liturgy.js) deciding whether
it is shown on a given day. Paragraphs whose whole job is to say "here read the
troparion of the day" are replaced by a slot that the app fills in; the original
rubric stays in the data with w="false", so "Rânduiala completă" can show it.

The block numbers below are indexes into source/blocks/ceaslovul.json.
"""
import json
from collections import Counter
import re
import sys
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
BLOCKS = ROOT / "source" / "blocks"
OUT = ROOT / "docs" / "data"
RED = {"#ff0000", "#980000", "#660000"}
CEDILLA = str.maketrans("şţŞŢ", "șțȘȚ")
TYPOS = {"Împăeate Cerecc": "Împărate Ceresc", "miluieste": "miluiește", "Slavă Jie": "Slavă Ție", "cuvioasse": "cuvioase", "binecuvinteză": "binecuvintează", "mai cintită": "mai cinstită", "Aiiluia": "Aliluia", "Mljloceasurile": "Mijloceasurile"}


# Glas 4, cântarea 4: "Mărire..." here is part of the irmos, not the doxology. Octoih, block 5887.
IRMOS_G4C4 = ("Cela ce șade în Mărire...", "Cela ce șade în mărire pe scaunul Dumnezeirii, pe nor ușor a venit Iisus cel mai presus de Dumnezeire prin palmă curată și a mântuit pe cei ce strigă : Mărire Hristoase puterii Tale.")


def clean(text):
    text = text.replace("­", "").replace(" ", " ").translate(CEDILLA)
    for wrong, right in TYPOS.items():
        text = text.replace(wrong, right)
    return text.replace(*IRMOS_G4C4)


def load(name):
    return json.loads((BLOCKS / f"{name}.json").read_text(encoding="utf-8"))


def plain(block):
    return re.sub(r"\s+", " ", clean("".join(r["text"] for r in block.get("runs", [])))).strip()


def external(href):
    """Links inside the same page are dropped; the rest open the source site."""
    if not href or href.startswith("#"):
        return None
    m = re.search(r"[?&]q=([^&]+)", href) if "google.com/url" in href else None
    if m:
        from urllib.parse import unquote
        href = unquote(m.group(1))
    if href.startswith("/"):
        href = "https://sites.google.com" + href
    return href if href.startswith("http") else None


def compact(block, idx=None):
    """Source block → compact JSON: {t:'h'|'p', c:1 if centred, r:[[text,flags,href?]]}."""
    runs = []
    for r in block.get("runs", []):
        text = re.sub(r"[ \t\r\n]+", " ", clean(r["text"]))
        if not text:
            continue
        flags = ("r" if r.get("color") in RED else "") + ("b" if r.get("bold") else "") + ("i" if r.get("italic") else "")
        href = external(r.get("href"))
        item = [text, flags] + ([href] if href else [])
        if runs and runs[-1][1:] == item[1:]:
            runs[-1][0] += text
        else:
            runs.append(item)
    if runs:
        runs[0][0] = runs[0][0].lstrip()
    out = {"t": "h" if block.get("tag") in ("h1", "h2", "h3") else "p", "r": runs}
    if block.get("align") == "center" or block.get("tag") in ("h1", "h2", "h3"):
        out["c"] = 1
    if idx is not None:
        out["i"] = idx
    return out


def split_block(block, marker):
    """Split a compact block at the first occurrence of `marker` across runs."""
    marker = clean(marker)
    whole = "".join(r[0] for r in block["r"])
    pos = whole.find(marker)
    if pos < 0:
        raise SystemExit(f"split marker not found: {marker!r} in {whole[:80]!r}")
    left, right, seen = [], [], 0
    for run in block["r"]:
        end = seen + len(run[0])
        if end <= pos:
            left.append(run)
        elif seen >= pos:
            right.append(run)
        else:
            cut = pos - seen
            left.append([run[0][:cut]] + run[1:])
            right.append([run[0][cut:]] + run[1:])
        seen = end
    a, b = dict(block), dict(block)
    a["r"], b["r"] = left, right
    return a, b


def seq(*items):
    out = []
    for it in items:
        out.extend(it if isinstance(it, (range, list)) else [it])
    return out


def when(table, expr, *indexes):
    for i in seq(*indexes):
        table[i] = expr


# ── Prayers written only by their first words ────────────────────────────────
# The full text is taken from the source itself; the asserts stop the build if a
# source paragraph ever moves. PRAYER_LONG become paragraphs of their own;
# PRAYER_SHORT are replaced within the line.

def between(text, start, end=None):
    """The part of `text` from `start` up to and including `end`."""
    i = text.index(start)
    return text[i:text.index(end, i) + len(end)] if end else text[i:]


def load_prayers():
    c = load("ceaslovul")
    ps = load("psaltirea")
    t = lambda blocks, i: plain(blocks[i])
    veniti = t(c, 1088)
    long_ = {
        "imparate": t(ps, 229),
        "sfinte": between(t(ps, 230), "Sfinte Dumnezeule", "miluiește-ne pe noi"),
        "treime": t(ps, 232),
        "tatal": t(ps, 235),
        "ca_a_ta": between(t(c, 821), "Că a Ta este împărăția", "Amin"),
        "cinstita": t(c, 883),
        "cuvine": t(c, 514),
        "binecuvantat": between(t(c, 240), "Binecuvântat este Dumnezeul nostru", "vecilor."),
        "milostiveste": between(t(c, 884), "Dumnezeule, milostivește-Te spre noi", "miluiește"),
        "stapane_tata": t(c, 269),
        "stapane_isus": t(c, 891),
        "mila_doamne": t(c, 290),
        "doamne_mila": t(c, 292),
        "usa": t(c, 294),
        "marturisi": t(c, 561).split(" (")[0],
        "aliluia": between(t(c, 246), "Aliluia, aliluia, aliluia", "slavă Ție !"),
        "veniti": " ".join([
            between(veniti, "Veniți să ne închinăm Împăratului", "Dumnezeu") + ".",
            between(veniti, "Veniți să ne închinăm și să cădem la Hristos", "Dumnezeu") + ".",
            between(veniti, "Veniți să ne închinăm și să cădem la Însuși", "Dumnezeul nostru") + ".",
        ]),
    }
    for key, start in (("imparate", "Împărate ceresc"), ("treime", "Preasfântă Treime"), ("tatal", "Tatăl nostru"),
                       ("cinstita", "Ceea ce ești mai cinstită"), ("cuvine", "Cuvine-se"), ("stapane_tata", "Stăpâne"),
                       ("stapane_isus", "Stăpâne Doamne"), ("mila_doamne", "Miluiește-ne"), ("doamne_mila", "Doamne"),
                       ("usa", "Ușa milostivirii"), ("marturisi", "Bine este a ne mărturisi")):
        assert long_[key].startswith(start), (key, long_[key][:50])
    slava_text = plain(c[1054])
    short = {
        "slava": between(slava_text, "Slavă Tatălui", "Duh."),
        "acum": between(slava_text, "și acum și pururea", "Amin").capitalize(),
    }
    short["acum"] = short["acum"] + "."
    short["acum"] = short["acum"].replace(" amin.", " Amin.")
    short["rugaciuni"] = between(t(c, 301), "Pentru rugăciunile Sfinților", "Amin !")
    return long_, short


PRAYER_TOKENS = [
    ("imparate", r"Împărate [Cc]eresc(?: Mângâietorule)?"),
    ("sfinte", r"Sfinte Dumnezei?(?:r)?e|Sfinte Dumnezeule"),
    ("treime", r"Preasfântă [Tt]reime"),
    ("tatal", r"Tatăl nostru"),
    ("ca_a_ta", r"Că a [Tt]a este [Îî]mpărăția"),
    ("veniti", r"Veniți să ne închinăm"),
    ("cinstita", r"Ceea ce ești mai cinstită(?: decât [Hh]eruvimii)?"),
    ("cuvine", r"Cuvine-se cu adevărat(?: să te fericim)?"),
    ("binecuvantat", r"Binecuvântat este Dumnezeul nostru|Bine cuvântat este Dumnezeul nostru"),
    ("milostiveste", r"Dumnezeule,? milostivește-[Tt]e(?: spre noi)?"),
    ("stapane_tata", r"Stăpâne,? Dumnezeule,? Părinte [Aa]totputernice"),
    ("stapane_isus", r"Stăpâne,? Doamne,? Iisuse Hristoase,? Dumnezeul nostru"),
    ("mila_doamne", r"Miluiește-ne pe noi, Doamne, miluiește-ne pe noi"),
    ("doamne_mila", r"Doamne miluiește-ne pe noi"),
    ("usa", r"Ușa milostivirii deschide-o nouă"),
    ("marturisi", r"Bine este a ne mărturisi Domnului"),
    ("aliluia", r"Aliluia"),
    ("slava_acum", r"(?:Slavă|Mărire)\s*(?:\.{2,}|…)[\s,.]*(?:Și|și|Si) acum"),
    ("slava", r"Slavă|Mărire"),
    ("acum", r"Și acum|și acum|Si acum"),
    ("rugaciuni", r"Pentru rugăciunile(?: [Ss]finților(?: [Pp]ărinților noștri)?)?"),
    ("doamne", r"Doamne,? miluiește"),
]
ELLIPSIS = r"\s*(?:\.{2,}|…)[.,;]*"
PRAYER_RE = re.compile("|".join(f"(?P<{k}>{v}){ELLIPSIS}" for k, v in PRAYER_TOKENS))
COUNT = re.compile(r"\s*\(\s*[Dd]e \d+[^)]*\)[.,;]?|\s*\(\s*[Dd]e (?:două|trei) ori\)[.,;]?")


ENTRANCE_PRAYER = "\n".join([
    # Sent by the user on 2026-11-05 as the full text; capitals and two slips corrected.
    'Seara și dimineața și la amiază, Te lăudăm, Te binecuvântăm și ne închinăm Ție, Doamne Dumnezeul cel întru înălțime, Tatăl cel fără de început, rădăcina cea fără de început și pricinuitoare a odraslelor celor mai presus de ființă, a Fiului Tău celui născut dumnezeiește și a Duhului Tău celui începător de viață, Cel ce ești neînțeles și necuprins și care cuprinzi cu puterea Ta deodată toate cele ce există; Cel ce reverși din plinirea Ta lumina cea gânditoare, care strălucește mintea cea mai presus de lume și cea din lume, Cel ce la toate cele ce sunt întinzi bunătatea Ta cea dumnezeiască, celor de sus, ce nu pot ajunge la covârșirea ei și celor de jos, ce nu se lipsesc de ea; Cel ce pe noi, cei ce ne depărtăm, ne întorci către Tine, ne luminezi, ne îmbunezi, ne întărești și de-a doua oară ne înnoiești și ne chemi pe cei ce Te doresc spre viața veșnică și fericirea cea adevărată; Cel ce pe toate le înconjori și le umpli și tuturor împarți cu bunătate pe cele ale Tale, după cât primește fiecare din cei ce vor să se mântuiască, rămânând același și neîmpuținat în înălțimea cea nemărginită. Mulțumesc Ție, Stăpâne preabune, că m-ai învrednicit pe mine, păcătosul și nevrednicul robul Tău, ca în ceasul de acum să întâmpin fața Ta întru mărturisire și să-Ți aduc slavoslovia și slujba cea la bună vreme. Mulțumesc Ție că-mi dăruiești de-a pururea cele de folos și mântuitoare după mare mila Ta și după mulțimea îndurărilor Tale. Mulțumesc Ție, că-mi ajuți la arătare și în ascuns, întru cunoștință și întru necunoștință, ca unuia ce sunt cuprins de toate cele pământești, ca să mă unesc cu totul cu Tine întru pomenirea cea dătătoare de lumină și mântuitoare. Mulțumesc Ție pentru toate pe care le-ai făcut și le faci cu mine, ticălosul și netrebnicul robul Tău.',
    'De aceea, Stăpâne preabune, îndreptează rugăciunea mea ca tămâia înaintea Ta și o primește pe ea ca pe o mireasmă cu bun miros în Jertfelnicul Tău cel înțelegător și sfânt. Că iată, îmi întind către Tine ochii sufletului și ai trupului meu și-mi înalț către Tine mintea și inima mea. Primește-mă acum pe mine, cel ce laud, mulțumesc și binecuvintez slava Ta cea negrăită, curățește-mă de toată spurcăciunea sufletului și a trupului și mă fă prieten al zilei și al luminii. Să nu Te îngrețoșezi de mine, Iubitorule de suflete, care în fiecare zi Îți greșesc și Te întărât. Știu că m-am făcut vinovat cu păcatele mele, însă, deși am greșit foarte, alerg la îndurările Tale. Să nu mă părăsești pe mine, că spre Tine nădăjduiesc ochii sufletului meu. Și precum m-a acoperit darul Tău până acum, așa și până în sfârșit să mă păzească. Pentru rugăciunile Preacuratei Stăpânei noastre Născătoare de Dumnezeu și ale tuturor sfinților Tăi. Că bun și iubitor de oameni ești și Ție slavă și mulțumire și închinăciune înălțăm, împreună și Unuia-Născut Fiului Tău și Preasfântului și de viață Făcătorului Tău Duh, acum și pururea și în vecii vecilor. Amin.',
])


def expand_block(block, long_, short):
    """Return `block` with shortened prayers written out, split into paragraphs."""
    out, cur = [], []
    before = ""

    def flush():
        nonlocal cur
        if re.search(r"\w", "".join(r[0] for r in cur)):
            out.append({**{k: v for k, v in block.items() if k not in ("r", "i")}, "r": cur})
        cur = []

    def prayer(text):
        flush()
        out.append({"t": "p", "r": [[text, ""]], **({"w": block["w"]} if "w" in block else {})})

    runs = [list(r) for r in block["r"]]
    last_prayer = None   # (paragraph, key) while nothing has followed it yet

    def take_count(text):
        """A "(de N ori)" right after a prayer belongs on the prayer's line. The
        Veniți text already has its three forms, so its count is dropped; Aliluia likewise."""
        nonlocal last_prayer
        if last_prayer:
            m = COUNT.match(text)
            if m:
                if last_prayer[1] not in ("veniti", "aliluia"):
                    last_prayer[0]["r"].append([" " + m.group(0).strip(), "r"])
                text = text[m.end():].lstrip(" .,;")
            if text.strip():
                last_prayer = None
        return text

    for n, run in enumerate(runs):
        text, flags = take_count(run[0]), run[1]
        if len(run) > 2:
            if text:
                cur.append([text] + run[1:])
            before += text
            continue
        pos = 0
        tokens = list(PRAYER_RE.finditer(text))
        for m_i, m in enumerate(tokens):
            pre = text[pos:m.start()]
            if pre.strip():
                last_prayer = None
            if pre:
                cur.append([pre, flags])
            before += pre
            key = m.lastgroup
            if key not in long_:
                last_prayer = None
            if key == "slava_acum":
                cur.append([f"{short['slava']} {short['acum']} ", flags])
            elif key in ("slava", "acum", "rugaciuni"):
                cur.append([short[key] + " ", flags])
            elif key == "doamne":
                cur.append([m.group(key) + " ", flags])
            else:
                prayer(long_[key])
                last_prayer = (out[-1], key)
                after_text = text[m.end():]
                follow = tokens[m_i + 1].lastgroup if m_i + 1 < len(tokens) and not text[m.end():tokens[m_i + 1].start()].strip(" ,.;") else None
                # Block 240 spells out the full order; shorter forms imply it.
                if key == "sfinte" and not COUNT.match(after_text) and not after_text.strip(" ,.;"):
                    out[-1]["r"].append([" (de trei ori)", "r"])
                    last_prayer = None
                if key == "sfinte" and follow == "treime":
                    if not out[-1]["r"][-1][0].endswith("ori)"):
                        out[-1]["r"].append([" (de trei ori)", "r"])
                    out.append({"t": "p", "c": 1, "r": [[f"{short['slava']} {short['acum']}", ""]], **({"w": block["w"]} if "w" in block else {})})
                if key == "treime" and follow == "tatal":
                    out.append({"t": "p", "c": 1, "r": [[f"Doamne miluiește (de trei ori). {short['slava']} {short['acum']}", ""]], **({"w": block["w"]} if "w" in block else {})})
            before += m.group(0)
            pos = m.end()
        rest = text[pos:]
        if rest.strip():
            last_prayer = None
        if rest:
            cur.append([rest, flags])
        before += rest
    flush()
    if not out:
        return [block]
    if "i" in block:
        out[0]["i"] = block["i"]
    return out


# Any other shortened text: looked up in the source by its first words. A wrong
# guess would put the wrong prayer in the service, so everything this finds is
# written to source/expansions.txt for review, and OVERRIDES pin the ambiguous ones.
SEARCH_PAGES = ("ceaslovul", "rugaciuni", "psaltirea", "canon-treime", "canoane-md", "tipicul5", "triodul", "octoih")
OVERRIDES = {
    # Sent by the user on 2026-11-05.
    "Binecuvântată este intrarea sfinților Tăi, Doamne, totdeauna": "Binecuvântată este intrarea sfinților Tăi, totdeauna, acum și pururea și în vecii vecilor. Amin.",
    "Binecuvântată este intrarea Sfinților Tăi, Doamne": "Binecuvântată este intrarea sfinților Tăi, totdeauna, acum și pururea și în vecii vecilor. Amin.",
    "Seara și dimineața și la amiază": ENTRANCE_PRAYER,
    "Seara și dimineața și la amiazăzi": ENTRANCE_PRAYER,
    "Domnul a împărățit": ("ceaslovul", 1007),            # the prokeimenon, not all of Psalm 92
    "Fericit bărbatul": ("psaltirea", 248),                # Psalm 1, not 111
    "Slavă întru cei de sus lui Dumnezeu": ("ceaslovul", 1363),
    "Doamne și Stăpânul vieții mele": ("ceaslovul", 689),
    "Doamne strigat-am": ("ceaslovul", 942),
    "Plinind rânduiala": "Plinind rânduiala cea pentru noi și cele de pe pământ unindu-le cu cele cerești, Te-ai înălțat întru slavă, Hristoase Dumnezeul nostru, nicidecum despărțindu-Te, ci rămânând nedepărtat; și strigând celor ce Te iubesc pe Tine : Eu sunt cu voi și nimeni împotriva voastră.",   # site: /penticostarul, Condacul Înălțării
    # The Trinity canon quotes these irmoi loosely; same tone and ode in the Octoechos.
    "Cela ce apele dedemult": ("octoih", 3226),      # glas 3, cântarea 1
    "Cela ce din ce n-a fost": ("octoih", 3241),     # glas 3, cântarea 3
    "Mânecând cuvânt": ("octoih", 9346),             # glas 7, cântarea 5
    "Dintru început cer": ("octoih", 9087),          # glas 7, cântarea 3
    # Same tone and ode, different first words; the user approved these two on 2026-11-05.
    "Dumnezeiasca cunoștință": ("octoih", 6162),     # glas 5, cântarea 4
    "Viforul cel nesuferit": ("octoih", 6199),       # glas 5, cântarea 6
    # The search by first words found these in another tone or ode:
    "Cela ce ai luminat": ("octoih", 319),           # glas 1, cântarea 5
    "Te laud pe tine": ("canoane-md", 985),          # glas 2, cântarea 4
    "Cela ce ai întărit cerul": ("octoih", 10556),   # glas 8, cântarea 3
    "Tu ești întărirea mea": ("octoih", 10574),      # glas 8, cântarea 4
    # Glas 4, cântarea 3: the books give only "Nu întru înțelepciune și putere...".
    # The full text starting the same way is the different irmos of glas 1, so none.
    "Nu întru înțelepciune": "",
    "Lumină lină": ("ceaslovul", 982),
    # Taken from doxologia.ro (the source site gives only the first words):
    # doxologia.ro/psalmul-50-slujbele-bisericii-urcus-duhovnicesc-prin-smerenie
    "Înviind Iisus din mormânt": "Înviind Iisus din mormânt, precum a zis mai înainte, a dăruit lumii viață veșnică și mare milă.",
    "Înviind Iisus din mormânt și legăturile Iadului rupând": "Înviind Iisus din mormânt, precum a zis mai înainte, a dăruit lumii viață veșnică și mare milă.",
    # doxologia.ro/ceaslov/paraclise/paraclisul-sfantului-apostol-cleopa ("Apostolului Tău", here in the plural)
    "Pentru rugăciunile Apostolilor Tăi, Milostive": "Pentru rugăciunile Apostolilor Tăi, Milostive, curățește mulțimea greșelilor noastre.",
    "Pentru rugăciunile Născătoarei de Dumnezeu, Milostive": "Pentru rugăciunile Născătoarei de Dumnezeu, Milostive, curățește mulțimea greșelilor noastre.",
    # doxologia.ro/canon-cantari/canon-de-rugaciune-catre-sfantul-apostol-carp-unul-din-cei-saptezeci
    "Strigat-au mai-nainte": "Strigat-a mai înainte închipuind îngroparea Ta cea de trei zile, proorocul Iona în chit rugându-se: din stricăciune mă izbăvește, Iisuse, Împărate al puterilor.",
    # doxologia.ro/canon-de-rugaciune-catre-sfantul-ierarh-eutihie-patriarhul-constantinopolului
    "Din văpaia cuvioșilor": "Din văpaie cuvioșilor rouă ai izvorât și jertfa dreptului cu apă ai ars-o, că toate le faci Hristoase prin singură voirea. Pe Tine Te preaînălțăm întru toți vecii.",
    # Elsewhere in the source itself:
    "Mai luminat decât focul": ("triodul", 12909),
    "Lăuda-Te-voi pe Tine, Doamne, Doamne": ("ceaslovul", 537),
    "Pentru mărturisirea": ("sinaxar", 710),
    # Polieleul is sung from chosen verses of Psalm 134; the source has no such
    # selection, so the whole psalm is given, from the source's Psalter.
    "Robii Domnului": ("polieleu",),
    "Cel ce ai răcorit": ("from", "canoane-md", 1608, "Cel ce ai răcorit"),
    "Cela ce pentru mine": ("from", "canoane-md", 2392, "Cela ce pentru mine"),
    "Miluiește-ne pe noi, Dumnezeule": "Miluiește-ne, Dumnezeule, după mare mila Ta, rugămu-ne Ție, auzi-ne și ne miluiește !",
    "Miluiește-ne pe noi Dumnezeule": "Miluiește-ne, Dumnezeule, după mare mila Ta, rugămu-ne Ție, auzi-ne și ne miluiește !",
    "umină lină": ("from", "ceaslovul", 982, "umină lină"),    # its L is a separate run
    "Că s-a bine cuvântat numele Tău": ("from", "triodul", 11622, "Că s-a binecuvântat numele Tău"),
    "Pe cel ce înot în valul": ("canoane-md", 3320),
    "Astăzi mântuirea la toată lumea": ("ceaslovul", 552),
    "Domnului să ne rugăm": "Domnului să ne rugăm !",
    "Iară și iară, cu pace, Domnului să ne rugăm": "Iară și iară, cu pace, Domnului să ne rugăm !",
    "Și pentru ca să ne învrednicim noi a asculta Sfânta Evanghelie": ("triodul", 10818),
    "Doamne, Dumnezeul meu, măritu-Te-ai foarte": ("from", "ceaslovul", 924, "Doamne, Dumnezeul meu"),
    "Bine cuvintează suflete al meu, pe Domnul": ("ceaslovul", 924),
    "Însuți binecuvintează": ("from", "ceaslovul", 1216, "Însuți binecuvintează și pâinile"),
    "Doamne, scăpare Te-ai făcut nouă": ("ceaslovul", 1364),   # the verse, not Psalm 89
    "Învrednicește-ne Doamne": ("ceaslovul", 1040),            # evening form
    "Născătoare de Dumnezeu Fecioară": ("ceaslovul", 1215),    # Rejoice, O Virgin, not "zid nesurpat"
    "Născătoare de Dumnezeu, Fecioară": ("ceaslovul", 1215),
    "Fericiți cei fără prihană": "Fericiți cei fără prihană în cale, care umblă în legea Domnului.",
    "Fericiți cei firă prihană": "Fericiți cei fără prihană în cale, care umblă în legea Domnului.",
    "Fericiți cei fără de prihană": "Fericiți cei fără prihană în cale, care umblă în legea Domnului.",
    "Doamne, strigat-am": ("ceaslovul", 942),
}
NOT_PRAYERS = re.compile(r"^(De la|al Sfântului|a Născătoarei|cădind|Iar |iar |Sf\.|și mă mântuiește|Fiul și|Tine,|Robilor|Acum S-a|S-a preaslăvit)", re.I)
TAIL = re.compile(r"\s*\(\s*[Dd]e [^)]*\)\s*$")
_runs_cache = None
AUDIT = {}


def word_key(text):
    text = clean(text).lower().replace("â", "î").replace("dedemult", "de demult").replace("lsrail", "israil").replace("israel", "israil")
    return ["cel" if w == "cela" else w for w in re.findall(r"\w+", text)]


def clause_from(text, want):
    """From the word sequence `want` inside `text` to the end of its sentence."""
    spans = [(m.start(), m.group(0)) for m in re.finditer(r"\w+", clean(text))]
    words = word_key(text)
    # word_key can split one word in two; only trust the plain case.
    if len(words) != len(spans):
        return None
    for i in range(len(words) - len(want)):
        if words[i:i + len(want)] == want:
            rest = text[spans[i][0]:]
            m = re.search(r"[!.](?:\s|$)", rest)
            return rest[:m.end()].strip() if m else rest.strip()
    return None


def source_runs():
    """(page, index, text) for each stretch of non-rubric text in the source."""
    global _runs_cache
    if _runs_cache is None:
        _runs_cache = []
        for page in SEARCH_PAGES:
            for i, b in enumerate(load(page)):
                buf = ""
                for r in b.get("runs", []):
                    t = clean(r["text"])
                    red = r.get("color") in RED
                    if red and len(t.strip()) > 2:      # a rubric; a red initial stays in
                        if buf.strip():
                            _runs_cache.append((page, i, re.sub(r"\s+", " ", buf).strip()))
                        buf = ""
                    else:
                        buf += t
                if buf.strip():
                    _runs_cache.append((page, i, re.sub(r"\s+", " ", buf).strip()))
        _runs_cache = [(pg, i, t, word_key(t)) for pg, i, t in _runs_cache]
    return _runs_cache


def polieleu():
    """Psalm 134 from the source's Psalter, without its verse numbers."""
    ps = load("psaltirea")
    assert plain(ps[3138]) == "PSALMUL 134" and plain(ps[3161]) == "PSALMUL 135"
    return " ".join(re.sub(r"^\d+\.\s*", "", plain(ps[i])) for i in range(3140, 3161) if plain(ps[i]))


def lookup(phrase):
    """The full text a shortened phrase stands for, or None."""
    if phrase in AUDIT:
        return AUDIT[phrase][0]
    found = None
    if OVERRIDES.get(phrase) == ("polieleu",):
        found, origin = polieleu(), "psaltirea:3140-3160"
    elif isinstance(OVERRIDES.get(phrase), str):
        found, origin = OVERRIDES[phrase], "manual"
    elif phrase in OVERRIDES and OVERRIDES[phrase][0] == "from":
        _, page, where, start = OVERRIDES[phrase]
        found, origin = between(plain(load(page)[where]), start), f"{page}:{where}"
        if where != 924:                                       # a whole psalm stays whole
            m = re.search(r"[!.](?:\s|$)", found)
            found = found[:m.end()].strip() if m else found
    elif phrase in OVERRIDES:
        page, where = OVERRIDES[phrase]
        if isinstance(where, int):
            found = plain(load(page)[where])
        else:
            found = next(t for pg, _, t, _w in source_runs() if pg == page and t.startswith(where))
        origin = f"{page}:{where}"
    else:
        want = word_key(phrase)
        origin = ""
        if len(want) >= 2:
            for page, i, t, words in source_runs():
                if "..." in t[:60] or "…" in t[:60]:
                    continue
                if words[:len(want)] == want and len(words) > len(want) + 2:
                    found, origin = t, f"{page}:{i}"
                    break
            # An irmos quoted loosely: its first words, at least three.
            trimmed = want[:-1]
            if len(trimmed) >= 3:
                for page, i, t, words in source_runs():
                    if words[:len(trimmed)] == trimmed and len(words) > len(trimmed) + 4 and "..." not in t[:60] and "…" not in t[:60]:
                        found, origin = t, f"{page}:{i}~"
                        break
            # Inside a longer paragraph (an ectenia, say), only for a real phrase.
            if not found and len(want) >= 3:
                for page, i, t, words in source_runs():
                    if page not in ("ceaslovul", "rugaciuni") or want[0] not in words:
                        continue
                    clause = clause_from(t, want)
                    if clause and "..." not in clause and "…" not in clause and len(word_key(clause)) > len(want):
                        found, origin = clause, f"{page}:{i}*"
                        break
    if found:
        found = re.sub(r"^[\s:]*(?:\d+\.\s*)?", "", TAIL.sub("", found))
        found = re.sub(r"(?<![.…])\.\.(?![.…])", ".", found)
    AUDIT[phrase] = (found, origin)
    return found


SHORTENED = re.compile(r"([^.…:;!?()]{2,120}?)\s*(?:\.{2,}|…)[.,;]*")


def expand_rest(block):
    """Second pass over a block: whatever the prayer table did not cover."""
    out, cur = [], []

    def flush():
        nonlocal cur
        if re.search(r"\w", "".join(r[0] for r in cur)):
            out.append({**{k: v for k, v in block.items() if k != "r"}, "r": cur})
        cur = []

    runs = [list(r) for r in block["r"]]
    for a, b in zip(runs, runs[1:]):        # ".." split across two runs
        if a[0].endswith(".") and not a[0].endswith("..") and b[0].startswith(".") and not b[0].startswith(".."):
            b[0] = b[0][1:]
    for run in runs:
        text, flags = run[0], run[1]
        if len(run) > 2:
            cur.append(run)
            continue
        # Two dots are a typing slip, and a lone "..." stands for nothing.
        text = re.sub(r"(?<![.…])\.\.(?![.…])", ".", text)
        text = re.sub(r"(^|(?<=[\s!.]))(?:\.{3}|…)(?=\s*(?:\(|$))", "", text)
        pos = 0
        for m in SHORTENED.finditer(text):
            phrase = m.group(1)
            # Longest ending of the phrase that starts on a capital.
            starts = [w.start() for w in re.finditer(r"\b[A-ZĂÂÎȘȚ„”]", phrase)] or [0]
            hit = None
            for n_start, st in enumerate(starts):
                key = phrase[st:].strip(" ,”„")
                # A later capital is only a real start with some words behind it.
                if n_start and len(word_key(key)) < 3 and key not in OVERRIDES:
                    continue
                if NOT_PRAYERS.match(key):
                    continue
                full = lookup(key)
                if full:
                    hit = (st, full)
                    break
            if not hit:
                continue
            cur.append([text[pos:m.start()] + phrase[:hit[0]], flags])
            if len(hit[1]) > 110:
                flush()
                for part in hit[1].split("\n"):
                    out.append({"t": "p", "r": [[part, ""]], **({"w": block["w"]} if "w" in block else {})})
            else:
                cur.append([hit[1] + " ", flags.replace("r", "")])
            pos = m.end()
        if text[pos:]:
            cur.append([text[pos:], flags])
    flush()
    for item in out:
        rs = item["r"]
        for a, b in zip(rs, rs[1:]):
            if a[0].rstrip().endswith(".") and not a[0].rstrip().endswith("..") and b[0].startswith(".") and not b[0].startswith(".."):
                b[0] = b[0][1:]
        for r in rs:
            r[0] = re.sub(r"(?<![.…])\.\.(?![.…])", ".", r[0])
    return out or [block]


def expand_all(items, long_, short):
    result = []
    for item in expand_table(items, long_, short):
        if "slot" in item or "r" not in item:
            result.append(item)
        else:
            result.extend(expand_rest(item))
    return result


def expand_table(items, long_, short):
    result = []
    for item in items:
        # Block 344: the source splits the ellipsis across two runs.
        if item.get("i") == 344:
            item["r"] = [["Veniți să ne închinăm... ", ""], ["(de 3 ori)", "r"]]
        if "slot" in item or "r" not in item:
            result.append(item)
        else:
            result.extend(expand_block(item, long_, short))
    return result


# ── Services ─────────────────────────────────────────────────────────────────
# Each entry: range of source blocks, conditions, slots to add after a block,
# blocks fully replaced by a slot (kept hidden), and blocks split in two.

def rules_ceas1():
    w = {}
    when(w, "Lw", range(595, 600))
    when(w, "!Lw", 600)
    when(w, "!L", 608)
    when(w, "L", range(611, 618), 622, 623)
    when(w, "L&&(mon||tue||thu)", 612, 613)
    when(w, "L&&(wed||fri)", 614, 615)
    when(w, "false", 616, 617, 618)
    when(w, "!L&&!sat", 609, 610)
    when(w, "!L", 619, 620, 624, 625, 626)
    when(w, "post", 629)
    return dict(
        blocks=range(587, 630), w=w,
        replace={595: ("catisma", {"at": "1"}), 600: ("tropar", {"mode": "ceas"}), 608: ("condac", {"hour": 1}), 611: None},
        alt={601: ("!Lw", "Și acum...,", "al Născătoarei de Dumnezeu :")},
        split={621: ("Şi de este Postul Mare", "L")},
    )


def rules_ceas3():
    w = {}
    when(w, "Lw", range(666, 671))
    when(w, "!Lw", 671, 672)
    when(w, "!L", 677)
    when(w, "HW", 675)
    when(w, "!L&&!sat", 678, 679)
    when(w, "L", range(680, 686), 689)
    when(w, "!L", 686, 687)
    when(w, "post", 692)
    return dict(
        blocks=range(658, 693), w=w,
        replace={666: ("catisma", {"at": "3"}), 671: ("tropar", {"mode": "ceas"}), 672: None, 677: ("condac", {"hour": 3}), 680: None},
        alt={673: ("!Lw", "Și acum...,", "al Născătoarei de Dumnezeu :")},
        split={688: ("Şi de este Postul Mare", "L")},
    )


def rules_ceas6():
    w = {}
    when(w, "Lw", range(725, 730))
    when(w, "!Lw", 730)
    when(w, "!L", 736)
    when(w, "L||HW", 733)
    when(w, "!L&&!sat", 737)
    when(w, "L", range(738, 747), 750, 751)
    when(w, "L&&(mon||tue||thu)", 743, 744)
    when(w, "L&&(wed||fri)", 745, 746)
    when(w, "!L", 747, 748)
    when(w, "L||post", 752, 753, 754)
    when(w, "!L&&!post", 755, 756, 757)
    when(w, "post", 761)
    return dict(
        blocks=range(717, 762), w=w,
        replace={725: ("catisma", {"at": "6"}), 730: ("tropar", {"mode": "ceas"}), 736: ("condac", {"hour": 6}), 738: None},
        alt={731: ("!Lw", "Și acum...,", "al Născătoarei de Dumnezeu :")},
    )


def rules_obednita():
    w = {}
    when(w, "!L", range(786, 794), 833, 834)
    when(w, "L", 794, 808, 809, 810, 830, 831, 832)
    when(w, "!sat", 823, 824, 825, 826)
    when(w, "sat", 828, 829)
    return dict(blocks=seq(range(786, 815), range(815, 844)), w=w, replace={822: ("condac", {"weekly": 1})})


def rules_ceas9():
    w = {}
    when(w, "Lw", range(861, 866))
    when(w, "!Lw", 866)
    when(w, "!L", 871)
    when(w, "HW", 869)
    when(w, "!L&&!sat", 872, 873)
    when(w, "L", range(874, 880), 888, 889)
    when(w, "!L", 880, 881)
    when(w, "A", 885, 886, 887)
    when(w, "post", 894)
    return dict(
        blocks=range(849, 895), w=w,
        replace={861: ("catisma", {"at": "9"}), 866: ("tropar", {"mode": "ceas"}), 871: ("condac", {"hour": 9}), 874: None},
        alt={867: ("!Lw", "Și acum...,", "al Născătoarei de Dumnezeu :")},
    )


def rules_miezonoptica():
    w = {}
    when(w, "!sat&&!sun", range(240, 303))
    when(w, "!sat&&!sun&&Lw", 267, 268)
    when(w, "sat", range(306, 377))
    when(w, "sun", range(380, 403))
    return dict(
        blocks=seq(range(240, 303), range(306, 377), range(380, 403)), w=w,
        after={384: ("canonTreime", {"cond": "sun"})},
        split_slot={398: ("Doamne, miluieşte", ("ipacoi", {"cond": "sun"}), "sun")},
    )


def rules_utrenia():
    w = {}
    when(w, "!Lw", range(439, 444))
    when(w, "Lw", range(447, 452))
    when(w, "false", range(453, 462))
    when(w, "sun", 463, range(464, 478), 516, range(535, 538), 539, 549, 550, 581, 582, 583)
    when(w, "sat", range(478, 498))
    when(w, "sun||doxo", 518, 519, range(541, 544))
    when(w, "!sun", 520)
    when(w, "!(sun||doxo)", range(544, 549))
    when(w, "sun&&glas<=4", 551, 552)
    when(w, "sun&&glas>4", 553, 554)
    when(w, "!feast&&!sun", range(557, 561))
    when(w, "!sun", 561)
    when(w, "L", range(569, 576))
    when(w, "false", range(576, 581))
    return dict(
        blocks=range(407, 584), w=w,
        replace={
            444: ("tropar", {"mode": "ded", "cond": "!Lw"}), 445: None, 446: None,
            452: ("treimice", {"cond": "Lw"}),
            538: ("luminanda", {"cond": "true"}),
            562: ("tropar", {"mode": "end", "cond": "!sun"}),
        },
        after={462: ("catisma", {"at": "u"}), 581: ("condac", {"hour": 1, "cond": "sun"})},
    )


def rules_vecernia():
    w = {}
    when(w, "eve==6", 920, range(934, 938), 1044)
    when(w, "eve!=6", 1045)
    when(w, "L||A", 985)
    when(w, "(L||A)&&eve==1", range(986, 992))
    when(w, "(L||A)&&(eve==2||eve==4)", range(992, 998))
    when(w, "(L||A)&&(eve==3||eve==5)", range(998, 1003))
    when(w, "false", 1003)
    when(w, "!(L||A)", 1004)
    for first, last, day in ((1005, 1011, 6), (1011, 1015, 0), (1015, 1019, 1), (1019, 1023, 2), (1023, 1027, 3), (1027, 1031, 4), (1031, 1035, 5)):
        when(w, f"!(L||A)&&eve=={day}", range(first, last))
    when(w, "!L", range(1053, 1057))
    when(w, "L", range(1057, 1077))
    return dict(
        blocks=range(920, 1082), w=w,
        replace={1051: ("tropar", {"mode": "vecernie", "cond": "!L"}), 1052: None},
        after={930: ("catisma", {"at": "v"})},
    )


def rules_priveghere():
    return dict(blocks=range(1085, 1352), w={})


def rules_pavecernita():
    w = {}
    when(w, "!L", range(1355, 1411))
    when(w, "false", 1353, 1354)
    when(w, "!L&&eve!=5", range(1371, 1378))
    when(w, "!L&&eve==5", range(1378, 1384))
    when(w, "!L&&eve!=5", 1385, 1386)
    when(w, "L", range(1414, 1577))
    when(w, "L&&firstLentWeek", range(1415, 1420))
    when(w, "L&&!firstLentWeek", 1420)
    when(w, "L&&(eve==1||eve==3)", range(1495, 1501))
    when(w, "L&&(eve==2||eve==4)", range(1501, 1509))
    return dict(
        blocks=seq(range(1353, 1411), range(1414, 1577)), w=w,
        after={1368: ("canonMD", {"cond": "!L"})},
        replace={1369: ("tropar", {"mode": "pavecernita", "cond": "!L"}), 1384: ("condac", {"evening": 1, "cond": "!L"})},
    )


def rules_mijloceas(first, last):
    return dict(blocks=range(first, last), w={})


def rules_pasti():
    return dict(blocks=range(1579, 1593), w={})


SERVICES = {
    "01-miezonoptica": rules_miezonoptica,
    "02-utrenia": rules_utrenia,
    "03-ceasul-1": rules_ceas1,
    "04-mijloceasul-1": lambda: rules_mijloceas(633, 654),
    "05-ceasul-3": rules_ceas3,
    "06-mijloceasul-3": lambda: rules_mijloceas(696, 714),
    "07-ceasul-6": rules_ceas6,
    "08-mijloceasul-6": lambda: rules_mijloceas(765, 783),
    "obednita": rules_obednita,
    "09-ceasul-9": rules_ceas9,
    "10-mijloceasul-9": lambda: rules_mijloceas(898, 917),
    "11-vecernia": rules_vecernia,
    "priveghere": rules_priveghere,
    "12-pavecernita": rules_pavecernita,
    "pasti": rules_pasti,
}


def build_services():
    src = load("ceaslovul")
    out = {}
    for slug, make in SERVICES.items():
        rule = make()
        w, replace = rule["w"], rule.get("replace", {})
        after, alt = rule.get("after", {}), rule.get("alt", {})
        split, split_slot = rule.get("split", {}), rule.get("split_slot", {})
        items = []

        def base_cond(i):
            return w.get(i, "true")

        for i in rule["blocks"]:
            b = src[i]
            if b.get("tag") == "img" or not plain(b):
                continue
            block = compact(b, i)
            cond = base_cond(i)
            if i in replace:
                block["w"] = "false"
                items.append(block)
                spec = replace[i]
                if spec:
                    name, args = spec
                    args = dict(args)
                    extra = args.pop("cond", None)
                    combined = cond if not extra else (extra if cond == "true" else f"({cond})&&({extra})")
                    items.append({"slot": name, "a": args, "w": combined})
                continue
            if i in split:
                marker, expr = split[i]
                left, right = split_block(block, marker)
                left["w"] = cond
                right["w"] = expr
                items += [left, right]
                continue
            if i in split_slot:
                marker, (name, args), expr = split_slot[i]
                left, right = split_block(block, marker)
                left["w"] = right["w"] = cond
                items += [left, {"slot": name, "a": {}, "w": expr}, right]
                continue
            if i in alt:
                expr, black, red = alt[i]
                block["w"] = f"!({expr})"
                items.append(block)
                items.append({"t": "p", "c": 1, "w": expr, "r": [[black + " ", ""], [red, "r"]]})
                continue
            block["w"] = cond
            items.append(block)
            if i in after:
                name, args = after[i]
                args = dict(args)
                extra = args.pop("cond", None)
                items.append({"slot": name, "a": args, "w": extra or "true"})
        for item in items:
            if item.get("w") == "true":
                del item["w"]
        out[slug] = expand_all(items, *load_prayers())
    return out


# ── Hymn tables ──────────────────────────────────────────────────────────────

GLAS = re.compile(r"glas(?:ul)?\s*(?:al\s*)?(\d|întâi|I\b)", re.I)


def glas_of(label):
    m = GLAS.search(label)
    if not m:
        return None
    return 1 if not m.group(1).isdigit() else int(m.group(1))


def is_label(block):
    runs = [r for r in block.get("runs", []) if r["text"].strip()]
    if block.get("align") == "center":
        return True
    # A rubric line is entirely red; a hymn only has a red initial.
    return bool(runs) and all(r.get("color") in RED for r in runs) and len(plain(block)) < 120


def hymns_between(src, first, last):
    """Tropare and condace in [first, last): a label followed by its text."""
    tropare, condace, pending = [], [], None
    for i in range(first, last):
        b = src[i]
        if b.get("tag") == "img":
            continue
        text = plain(b)
        if not text:
            continue
        if b.get("tag") == "h2" or is_label(b):
            low = text.lower()
            text = re.sub(r"^Slavă\.*\s*", "", text)
            if "apoi iarăși" in low or "acum" in low[:12] or low.startswith("al născătoarei") or low.startswith("a născătoarei"):
                pending = None
            elif "troparul învierii" in low and len(text) < 60:
                pending = None
            elif "tropar" in low:
                pending = ("t", text)
            elif "condac" in low:
                pending = ("c", text)
            elif low.startswith("podobie") or low.startswith("slavă") or low.startswith("alt"):
                pass
            else:
                pending = None
            continue
        if pending:
            kind, label = pending
            # "Troparul, glasul 1 : Învierea cea de obște...": the text itself follows.
            label = re.sub(r"\s*:\s*[^:]*(?:\.{2,}|…)\s*$", "", label)
            entry = {"l": label.rstrip(" :"), "x": text, "g": glas_of(label)}
            (tropare if kind == "t" else condace).append(entry)
            pending = None
    return tropare, condace


MONTHS = dict(zip("SEPTEMBRIE OCTOMBRIE NOIEMBRIE DECEMBRIE IANUARIE FEBRUARIE MARTIE APRILIE MAI IUNIE IULIE AUGUST".split(),
                  (9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8)))
RANK = re.compile(r"\(†\)|†\)|†|\.\)")
RANK_ORDER = ["", ".", ".)", "†", "†)", "(†)"]


def best_rank(text):
    found = RANK.findall(text)
    return max(found, key=RANK_ORDER.index) if found else ""


def build_sinaxar():
    src = load("sinaxar")
    marks = []
    month = None
    day = None
    for i, b in enumerate(src):
        text = plain(b)
        if b.get("tag") == "h2":
            m = re.match(r"LUNA (\w+)", text)
            if m and m.group(1) in MONTHS:
                month, day = MONTHS[m.group(1)], 1
                marks.append((i, month, day))
                continue
            if month and re.fullmatch(r"\d+", text):
                day = int(text)
                marks.append((i, month, day))
    out = {}
    for n, (start, mo, da) in enumerate(marks):
        end = marks[n + 1][0] if n + 1 < len(marks) else len(src)
        title = ""
        for i in range(start, end):
            m = re.match(r"(\d+)\.\s*(.*)", plain(src[i]))
            if m and int(m.group(1)) == da:
                title = m.group(2)
                break
        first_sentence = re.split(r"(?<=[a-zăâîșț])\.\s", title)[0][:240]
        rank = best_rank(title[:12])
        tropare, condace = hymns_between(src, start, end)
        out[f"{mo:02d}-{da:02d}"] = {"title": RANK.sub("", first_sentence).strip(" .;"), "rank": rank, "t": tropare, "c": condace}
    # On the source page St Codratus' troparion (21 Sep) sits under the 22nd.
    moved = [t for t in out["09-22"]["t"] if "Codrat" in t["l"]]
    out["09-22"]["t"] = [t for t in out["09-22"]["t"] if "Codrat" not in t["l"]]
    out["09-21"]["t"] = moved + out["09-21"]["t"]
    # Leave-taking days say only "troparul și condacul praznicului".
    for day, feast in (("01-14", "01-06"), ("08-13", "08-06"), ("08-23", "08-15"), ("02-03", "02-02")):
        if not out[day]["t"]:
            out[day]["t"] = out[feast]["t"][:1]
        if not out[day]["c"]:
            out[day]["c"] = out[feast]["c"][:1]
    return out


# What each date keeps every year: the title and rank from the source's calendar,
# leaving out the years when a day named by Pascha falls on it. The old calendar
# needs it, because its dates and Pascha do not line up as they do in the source.
MOVABLE_IN_TITLE = re.compile(r"Sf\. și Marea|Paști|Înălțarea Domnului|Odovania praznicului (?:Învierii|Înălțării|Pogorârii)|Înjumătățirea|Rusalii|Cincizecim|Intrarea Domnului în Ier|Sf\. Treime|Izvorul Tămăduirii|Sâmbăta|Lăsat|Floriilor|Vinerea|Tuturor Sfinților", re.I)
SERVICE_NOTE = re.compile(r"\s*\([^()]*(?:aliturgic|Deni|Numai|Sâmbăta)[^()]*\)")


def build_fixed_calendar(years):
    votes = {}
    for days in years.values():
        for key, entry in days.items():
            title = SERVICE_NOTE.sub("", entry["title"]).strip(" ;")
            votes.setdefault(key, Counter())[(title, entry.get("rank", ""))] += 1
    fixed = {}
    for key, counts in sorted(votes.items()):
        ranked = counts.most_common()
        title, rank = next((t for t in ranked if not MOVABLE_IN_TITLE.search(t[0][0])), ranked[0])[0]
        fixed[key] = {"title": title, "rank": rank}
    return fixed


# Old-style days, fetched by tools/fetch_vechi.py. The lists carry notes and Sunday
# names that the app gives elsewhere, and on Pascha every saint of the year.
NOT_A_SAINT = re.compile(r"^(?:\W*$|Zi |Dezlegare|Duminica|S[ăa]pt[ăa]m[âa]na|[A-Z][a-z]+\.? [IVX]+, ?\d)")
FAST_REMARK = re.compile(r"\s*(?:ZI FĂRĂ POST|Zi f[ăa]r[ăa] post|Zi de post|Dezlegare la \w+)\.?", re.I)
MOST_SAINTS = 100


def build_old_style():
    out = {}
    for path in sorted((ROOT / "source" / "vechi").glob("*.json")):
        days = {}
        for key, day in json.loads(path.read_text(encoding="utf-8")).items():
            saints = []
            if len(day["saints"]) <= MOST_SAINTS:
                for _, text in day["saints"]:
                    text = FAST_REMARK.sub("", clean(text)).strip()
                    if text and not NOT_A_SAINT.match(text) and text not in saints:
                        saints.append(text)
            days[key] = {"post": clean(day["post"]), "saints": saints}
        out[path.stem] = days
    return out


def build_calendar():
    src = load("calendar")
    years, year, month, last_day, current = {}, None, 0, 0, None
    for b in src:
        text = plain(b)
        m = re.fullmatch(r"Anul (\d{4})", text)
        if m:
            year, month, last_day, current = m.group(1), 0, 99, None
            years[year] = {}
            continue
        if not year:
            continue
        m = re.match(r"(\d{1,2}) ([LMJVSD]) (.*)", text)
        if m:
            day = int(m.group(1))
            if day <= last_day and day == 1:
                month += 1
            last_day = day
            rest = m.group(3)
            note_re = r"\(([^()]*(?:Post|Dezlegare|Harți|Ajun)[^()]*)\)"
            notes = re.findall(note_re, rest)
            current = {"title": RANK.sub("", re.sub(note_re, "", rest)).strip(" ;"), "rank": best_rank(rest)}
            if notes:
                current["note"] = "; ".join(notes)
            years[year][f"{month:02d}-{day:02d}"] = current
            continue
        # Pascha's date line is followed by the feast on a line of its own.
        if current is not None and RANK.match(text):
            current["title"] = RANK.sub("", re.split(r";\s*(?:Ap\.|Ev\.)", text)[0]).strip(" ;")
            current["rank"] = best_rank(text)
        m = re.search(r"glas\s*(\d),\s*voscr\.?\s*(\d+)", text)
        if current is not None and text.startswith("Duminica") or (current is not None and m):
            current["sunday"] = re.split(r";\s*(?:Ap\.|Ev\.)", text)[0]
            if m:
                current["glas"], current["voscr"] = int(m.group(1)), int(m.group(2))
    return years


def section(src, title, start=0):
    for i in range(start, len(src)):
        if src[i].get("tag") == "h2" and plain(src[i]).upper().startswith(title.upper()):
            return i
    raise SystemExit(f"section not found: {title}")


def texts_between(src, a, b):
    return [plain(src[i]) for i in range(a, b) if src[i].get("tag") != "img" and plain(src[i]) and not is_label(src[i])]


# Paschal offset → entry, in rugăciuni-din-ceaslov order.
PENT = [(0, 873, 890), (5, 890, 894), (7, 894, 899), (14, 899, 908), (21, 908, 914), (24, 914, 920), (28, 920, 926),
        (35, 926, 932), (39, 932, 937), (42, 937, 943), (48, 943, 949), (49, 949, 954), (56, 954, 961)]
TRIOD = [(-70, 963, 968), (-63, 968, 973), (-57, 973, 978), (-56, 978, 983), (-50, 983, 991), (-49, 991, 1002),
         (-43, 1002, 1008), (-42, 1008, 1026), (-35, 1026, 1035), (-28, 1035, 1044), (-21, 1044, 1056),
         (-17, 1056, 1060), (-15, 1060, 1066), (-14, 1066, 1075), (-8, 1075, 1082), (-7, 1082, 1091),
         (-6, 1091, 1097), (-5, 1097, 1103), (-4, 1103, 1109), (-3, 1109, 1115), (-2, 1115, 1120), (-1, 1120, 1135)]


def build_hymns():
    r = load("rugaciuni")
    prayers_short = load_prayers()[1]
    invierii = {}
    starts = [528, 537, 546, 556, 566, 575, 584, 593, 604]
    for g in range(8):
        chunk = [i for i in range(starts[g] + 1, starts[g + 1]) if r[i].get("tag") != "img" and plain(r[i])]
        rec, key = {}, None
        for i in chunk:
            label = plain(r[i]).lower()
            if is_label(r[i]):
                key = "t" if label.startswith("tropar") else "b" if "născătoarei" in label else "i" if label.startswith("ipacoi") else "c" if label.startswith("condac") else key
            elif key and key not in rec:
                rec[key] = plain(r[i])
        invierii[str(g + 1)] = rec

    def weekly(first, last):
        out, keys = {}, []
        days = {"LUNI": [1], "MARȚI": [2], "MIERCURI ȘI VINERI": [3, 5], "JOI": [4], "SÂMBĂTĂ": [6]}
        pending = None
        for i in range(first, last):
            if r[i].get("tag") == "img" or not plain(r[i]):
                continue
            text = plain(r[i])
            if text.upper() in days:
                keys = days[text.upper()]
                continue
            if text.startswith("Iar acest"):
                break
            if is_label(r[i]):
                pending = text.rstrip(" :")
                continue
            if keys and pending:
                pending = re.sub(r"^Slavă\.*,?\s*", prayers_short["slava"] + " ", pending)
                pending = re.sub(r"^Și acum\.*,?\s*", prayers_short["acum"] + " ", pending)
                for k in keys:
                    out.setdefault(str(k), []).append({"l": pending, "x": text, "g": glas_of(pending)})
                pending = None
        return out

    bog = {}
    glas_heads = [607, 639, 677, 709, 741, 773, 805, 837, 871]
    eve_names = {"DUMINIC": 0, "LUNI": 1, "MARȚI": 2, "MIERCURI": 3, "JOI": 4, "VINERI": 5}
    for g in range(8):
        cur = None
        rec = {}
        for i in range(glas_heads[g] + 1, glas_heads[g + 1]):
            if r[i].get("tag") == "img" or not plain(r[i]):
                continue
            text = plain(r[i])
            if r[i].get("tag") == "h2":
                cur = next((v for k, v in eve_names.items() if text.upper().startswith(k)), cur)
                continue
            if cur is None or is_label(r[i]):
                continue
            rec.setdefault(str(cur), []).append(text)
        bog[str(g + 1)] = rec

    def moveable(table):
        out = []
        for off, a, b in table:
            t, c = hymns_between(r, a + 1, b)
            out.append({"off": off, "name": plain(r[a]), "t": t, "c": c})
        return out

    lum = {"v": {}, "lent": {}, "week": {}}
    heads = [1183, 1189, 1195, 1201, 1207, 1213, 1219, 1225, 1231, 1237, 1243, 1249]
    for n in range(11):
        lum["v"][str(n + 1)] = texts_between(r, heads[n] + 1, heads[n + 1])
    lum["lent"] = {str(n + 1): texts_between(r, 1257 + 2 * n, 1258 + 2 * n) for n in range(8)}
    week = [(1274, 1282, 1), (1282, 1289, 2), (1289, 1296, 3), (1296, 1305, 4), (1305, 1312, 5), (1312, 1321, 6)]
    for a, b, d in week:
        lum["week"][str(d)] = texts_between(r, a + 1, b)

    tri = load("triodul")
    heads = [i for i in range(12178, 12251) if tri[i].get("tag") == "h2"]
    assert len(heads) == 8, heads
    treimice = {"endings": {"1": plain(tri[12173]), "2": plain(tri[12175]), "3": plain(tri[12176]), "5": plain(tri[12176]), "4": plain(tri[12177])}}
    prayers_all = load_prayers()
    for n, h in enumerate(heads):
        end = heads[n + 1] - 1 if n < 7 else 12251
        rows = [compact(tri[i]) for i in range(h + 1, end) if tri[i].get("tag") != "img" and plain(tri[i]) and "În alte zile" not in plain(tri[i])]
        rows = expand_table(rows, *prayers_all)
        for row in rows:
            for run in row["r"]:
                run[0] = re.sub(r"(?<![.…])\.\.(?![.…])", ".", run[0])
        treimice[str(n + 1)] = rows

    return {
        "invierii": invierii,
        "tropareSapt": weekly(479, 498),
        "condaceSapt": weekly(501, 521),
        "bog": bog,
        "pent": moveable(PENT),
        "triod": moveable(TRIOD),
        "luminande": lum,
        "treimice": treimice,
        "prayers": load_prayers()[1],
        "polieleu": polieleu(),
    }


def build_canons():
    """Per-glas Trinity canon, and the Theotokos canon by glas + evening."""
    src = load("canon-treime")
    heads = [i for i, b in enumerate(src) if b.get("tag") == "h2" and re.match(r"GLASUL \d", plain(b))]
    treime = {}
    for n, h in enumerate(heads):
        end = heads[n + 1] if n + 1 < len(heads) else len(src)
        treime[str(n + 1)] = [compact(src[i]) for i in range(h + 1, end) if src[i].get("tag") != "img" and plain(src[i]) and plain(src[i]) != "..."]

    md = load("canoane-md")
    glas_heads = [i for i, b in enumerate(md) if b.get("tag") == "h2" and re.fullmatch(r"Glasul \d", plain(b))]
    names = {"SÂMBĂT": 6, "DUMINIC": 0, "LUNI": 1, "MARȚI": 2, "MARTI": 2, "MIERCURI": 3, "JOI": 4, "VINERI": 5}
    canon = {}
    for n, h in enumerate(glas_heads):
        end = glas_heads[n + 1] if n + 1 < len(glas_heads) else len(md)
        rec, cur = {}, None
        for i in range(h + 1, end):
            b = md[i]
            if b.get("tag") == "img" or not plain(b) or set(plain(b)) <= {"."}:
                continue
            text = plain(b)
            if b.get("tag") == "h2":
                match = next((v for k, v in names.items() if text.upper().startswith(k)), None)
                if match is not None:
                    cur = match
                    rec[str(cur)] = []
                    continue
            if cur is not None and not any(r.get("href") for r in b.get("runs", [])):
                rec[str(cur)].append(compact(b))
        canon[str(n + 1)] = rec
    prayers = load_prayers()
    treime = {k: expand_all(v, *prayers) for k, v in treime.items()}
    canon = {g: {e: expand_all(v, *prayers) for e, v in rec.items()} for g, rec in canon.items()}
    return treime, canon


def build_psalter():
    src = load("psaltirea")
    heads = [i for i, b in enumerate(src) if b.get("tag") == "h2" and plain(b).startswith("CATISMA")]
    stop = next(i for i, b in enumerate(src) if b.get("tag") == "h2" and plain(b).startswith("PSALMUL NECANONIC"))
    out = {}
    for n, h in enumerate(heads):
        end = heads[n + 1] if n + 1 < len(heads) else stop
        out[str(n + 1)] = [compact(src[i]) for i in range(h + 1, end) if src[i].get("tag") != "img" and plain(src[i]) and plain(src[i]) != "..."]
    prayers = load_prayers()
    return {k: expand_all(v, *prayers) for k, v in out.items()}


# The reader gets the text itself, so the app names no source: the source site's links
# to its other books go, and so do the markers for how many verses a hymn is sung on.
LINK_TITLE = re.compile(r"(?:T?(?:R?OPARELE|ROPARELE|CONDACELE)\b.*|OCTOIHUL MARE|MINEIELE BISERICII ORTODOXE|TRIODUL|PENTICOSTARUL|SINAXAR|CATAVASIER|PSALTIREA LUI DAVID|EVANGHELIA|APOSTOLUL|LUMINÂNDELE|CANOANELE MAICII DOMNULUI|CANONUL SFINTEI TREIMI|CÂNTĂRILE TREIMICE|SLUJBA PRIVEGHERII|PAVECERNIȚA MARE)?")
LINK_WORDS = {"CÂNTĂRILE LUI MOISE": "Cântările lui Moise", "VECERNIA MARE": "Vecernia Mare", "CANONUL CEL MARE": "Canonul cel Mare"}
SOURCE_REFS = [(re.compile(a), b) for a, b in [
    (r"Dacă suntem în perioada Penticostarului citim (?:troparul|condacull?) din\s*:?\s*(?:T?R?OPARELE ȘI CONDACELE PENTICOSTARULUI|T\b)?\s*", ""),
    (r":?\s*\bT?ROPARELE ȘI CONDACELE PENTICOSTARULUI\b", ""),
    (r"citim condacul de aici\s*:\s*", "citim condacul din Triod "),
    (r"\s*și de aici\s*:\s*", " și pe cel al Învierii "),
    (r"\s*\(Fericirile cele de la Sfânta Liturghie\)", ""),
    (r"\s*\(vezi (?:în Liturghier|Catavasierul)\)", ""),
    (r"(?:\bStih pe|\bPe)\s+\d+\s*:\s*", ""),
    (r"(intrarea sfinților Tăi, totdeauna, acum și pururea și în vecii vecilor\. Amin\.)\s*etc\.", r"\1"),
    # Sentences that leaned on a link for their last word.
    (r"Apoi :\s+și\s+\.", "Apoi : Apostolul și Evanghelia."),
    (r"Catisma de rând din\s+după care", "Catisma de rând din Psaltire, după care"),
    (r"cântăm din\s+pe glas", "cântăm din Psaltire pe glas"),
    (r"sărbătorii,\s+Doamne, miluiește", "sărbătorii. Doamne, miluiește"),
    (r"de la Triod :\s+Se cuvine", "de la Triod. Se cuvine"),
    (r"de rând :\s+Și după canon", "de rând. Și după canon"),
    (r"al Octoihului :\s+Iar noi", "al Octoihului. Iar noi"),
    (r"\s{2,}", " "),
    (r"\s+$", ""),
]]


# The reader's prayer "Pentru buna sporire..." is kept without the petitions
# for the hierarchs, the people and the rulers of the country.
COMMEMORATIONS = [(re.compile(a), b) for a, b in [
    (r"Pentru\s+Prea\s*[Ff]ericitul\s+Părintele\s+nostru\s*\(N\),\s*Patriarhul\s+Bisericii\s+Ortodoxe\s+Române\s+pentru\s+\([ÎîIi]nalt-\)\s*Prea\s*[Ss]fințitul\s+\(Arhi-\)\s*Episcopul\s+\(și\s+Mitropolitul\)\s+nostru\s*\(N\),\s*și\s+pentru", "Pentru"),
    (r"Pentru\s+binecredinciosul\s+popor\s+român\s+de\s+pretutindeni,\s*pentru\s+cârmuitorii\s+țării\s+noastre,\s*pentru\s+mai\s+marii\s+orașelor\s+și\s+ai\s+satelor\s+și\s+pentru\s+iubitoarea\s+de\s+Hristos\s+oaste\.\s*", ""),
    (r"Pentru\s+arhiereii\s+ortodocși,?\s+și\s+pentru\s+toți", "Pentru toți"),
    (r"Să\s+ne\s+rugăm\s+pentru\s+conducătorii\s+țării\.\s*", ""),
    # The litanies, without the same petitions.
    (r"Pentru\s+Prea\s*Fericitul\s+Părintele\s+nostru\s*\(N\),?\s*Patriarhul\s+Bisericii\s+Ortodoxe\s+Române\s*(?:și\s+|ș)?pentru\s+\([ÎîIi]nalt-\)\s*Prea\s*[Ss]fințitul\s+\(Arhi-\)\s*Episcopul\s+\(și\s+Mitropolitul\)\s+nostru\s*\(N\)ț?,\s*pentru\s+cinstita", "Pentru cinstita"),
    (r"Pentru\s+binecredinciosul\s+popor\s+român[^!]*?oștire,\s*Domnului\s+să\s+ne\s+rugăm\s*!\s*", ""),
    (r"(Încă\s+ne\s+rugăm\s+pentru)\s+Prea\s*Fericitul[^!]*?nostru\s*\(N\)ț?,\s*și\s+pentru\s+toți", r"\1 toți"),
    (r"Încă\s+ne\s+rugăm\s+pentru\s+Prea\s*Fericitul[^!]*?mântuirea\s+lui\s*!\s*", ""),
    (r"\s*\(Aici\s+se\s+pot\s+(?:spune|adăuga)\s+ectenii\s+pentru\s+felurite\s+cereri,[^)]*\)\.?", ""),
    (r"Încă\s+ne\s+rugăm\s+pentru\s+binecredinciosul\s+popor\s+român[^!]*?!\s*(?:Strana\s*:\s*Doamne\s+miluiește\s*!\s*\(de\s+3\s+ori[^)]*\)\.?\s*)?", ""),
]]


def sub_across_runs(runs, pattern, repl):
    """re.sub over the runs' joined text, leaving the formatting of what stays."""
    joined = "".join(r[0] for r in runs)
    for m in reversed(list(pattern.finditer(joined))):
        pos, placed = 0, False
        for run in runs:
            start, end = pos, pos + len(run[0])
            pos = end
            lo, hi = max(m.start(), start), min(m.end(), end)
            if lo < hi or (m.start() == m.end() == start):
                run[0] = run[0][:lo - start] + ("" if placed else m.expand(repl)) + run[0][hi - start:]
                placed = True
        joined = "".join(r[0] for r in runs)
    return [r for r in runs if r[0]]


def strip_refs(node):
    """Takes links and source references out of every paragraph, however deep."""
    if isinstance(node, list):
        return [x for x in (strip_refs(v) for v in node) if x is not None]
    if not isinstance(node, dict):
        return node
    node = {k: strip_refs(v) if k != "r" else v for k, v in node.items()}
    if "r" not in node:
        return node
    runs, touched = [], False
    for run in node["r"]:
        text, flags, href = (*run, None)[:3]
        if href:
            touched = True
            word = text.strip()
            if word in LINK_WORDS:
                text = text.replace(word, LINK_WORDS[word])
            elif word and LINK_TITLE.fullmatch(word):
                continue
        runs.append([text, flags])
    for pattern, repl in COMMEMORATIONS:
        runs = sub_across_runs(runs, pattern, repl)
    before = "".join(r[0] for r in runs)
    for pattern, repl in SOURCE_REFS[:-2]:
        runs = sub_across_runs(runs, pattern, repl)
    touched = touched or "".join(r[0] for r in runs) != before
    if not touched:
        return {**node, "r": runs}
    for pattern, repl in SOURCE_REFS[-2:]:
        runs = sub_across_runs(runs, pattern, repl)
    if not re.search(r"\w", "".join(r[0] for r in runs)):
        return None
    return {**node, "r": runs}


def place_after_canon(services):
    """The source announces what follows the Trinity canon before giving the canon."""
    items = services["01-miezonoptica"]
    i = next(k for k, x in enumerate(items) if "Și după canon" in "".join(r[0] for r in x.get("r", [])))
    assert items[i + 1].get("slot") == "canonTreime"
    flags = items[i]["r"][0][1]
    text = "".join(r[0] for r in items[i]["r"])
    head, tail = text.split("Și după canon")
    items[i] = {**items[i], "r": [[head.strip(), flags]]}
    items.insert(i + 2, {**items[i], "r": [["Și după canon" + tail, flags]]})
    return services



# Words that never stand without their diacritics, wherever the sources dropped
# them. Matched on whole words of the paragraph's joined text, so a red initial
# ("D" + "in") is not mistaken for a word.
DIACRITICS = [(re.compile(r"(?<![\w-])" + a + r"(?![\w-])"), b) for a, b in [
    ("si", "și"), ("Si", "Și"), ("SI", "ȘI"),
    ("Sfintii", "Sfinții"), ("Sfintilor", "Sfinților"), ("Sfintit", "Sfințit"), ("Sfințiti", "Sfințiți"),
    ("Sfantul", "Sfântul"), ("Marturisitorul", "Mărturisitorul"), ("Mart\\.", "Mărt."), ("Parinți", "Părinți"),
    ("Parintele", "Părintele"), ("Născatoare", "Născătoare"), ("Mucenite", "Mucenițe"), ("Botezatorul", "Botezătorul"),
    ("moastelor", "moaștelor"), ("fãrã", "fără"), ("fară", "fără"), ("Stefan", "Ștefan"), ("Înalțării", "Înălțării"),
    ("împreuna", "împreună"), ("Diocletian", "Dioclețian"), ("Scararul", "Scărarul"), ("împarateasa", "împărăteasa"),
    ("stati", "stați"), ("cerestilor", "cereștilor"),
]]


def fix_diacritics(node):
    if isinstance(node, list):
        return [fix_diacritics(v) for v in node]
    if isinstance(node, str):
        for pattern, repl in DIACRITICS:
            node = pattern.sub(repl, node)
        return node
    if not isinstance(node, dict):
        return node
    out = {k: fix_diacritics(v) for k, v in node.items() if k != "r"}
    if "r" in node:
        runs = [list(r) for r in node["r"]]
        for pattern, repl in DIACRITICS:
            runs = sub_across_runs(runs, pattern, repl)
        out["r"] = runs
    return {k: out[k] for k in node}


def write(name, data):
    data = fix_diacritics(strip_refs(data))
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{path.relative_to(ROOT)}: {path.stat().st_size // 1024} KB")



# ── Psalms, verse by verse ────────────────────────────────────────────────
# The Psalter numbers every verse; a psalm said inside a service gets the same
# numbers, one verse to a line, and its title where the service left it out.
PSALM_TITLE = re.compile(r"^\s*Psalmul\s+(\d+)\s*:?\s*$")


def psalm_verses(psalter):
    ps, cur = {}, None
    for blocks in psalter.values():
        for b in blocks:
            t = "".join(r[0] for r in b["r"]).strip()
            m = re.match(r"PSALMUL\s+(\d+)", t)
            if m:
                cur = int(m.group(1))
                ps[cur] = []
                continue
            m = re.match(r"(\d+)\.\s*", t)
            if m and cur:
                ps[cur].append((int(m.group(1)), t[m.end():]))
    return ps


def norm_map(text):
    out, idx = [], []
    for i, ch in enumerate(text):
        base = unicodedata.normalize("NFD", ch.lower())[0]
        if "a" <= base <= "z":
            out.append(base)
            idx.append(i)
    return "".join(out), idx


def split_runs(runs, cuts):
    """Splits the runs at character positions of their joined text."""
    parts, cur, pos, cuts = [], [], 0, sorted(cuts)
    for text, flags, *rest in runs:
        start = pos
        pos += len(text)
        while cuts and cuts[0] < pos:
            k = cuts.pop(0) - start
            if text[:k]:
                cur.append([text[:k], flags])
            parts.append(cur)
            cur, text, start = [], text[k:], start + k
        if text:
            cur.append([text, flags])
    parts.append(cur)
    return parts


def verse_walk(n, verses, vi, text, idx):
    """Where each verse from `vi` on begins in the normalized text `n`, by aligning
    it with the Psalter's wording (the services' wording differs here and there)."""
    from difflib import SequenceMatcher
    keys, offs, q = [], [], 0
    for _, v in verses[vi:]:
        k = norm_map(v)[0]
        offs.append(q)
        keys.append(k)
        q += len(k)
        if q > len(n) * 1.4 + 200:
            break
    Q = "".join(keys)
    sm = SequenceMatcher(None, n, Q, autojunk=False)
    blocks = [m for m in sm.get_matching_blocks() if m.size >= 4]
    if not blocks:
        return [(0, 0)], None, 0
    matched = sum(m.size for m in blocks)
    q_end = blocks[-1].b + blocks[-1].size
    p_end = blocks[-1].a + blocks[-1].size
    span = p_end - blocks[0].a
    if blocks[0].a > 10 or blocks[0].b > 10 or matched < 0.75 * max(span, 1):
        return [(0, 0)], None, 0

    def where(qk):
        for m in blocks:
            if m.b <= qk < m.b + m.size:
                return m.a + qk - m.b
            if m.b > qk:
                return max(0, m.a - (m.b - qk))
        return None

    def snap(p):
        # The verse begins at a word, best one after a punctuation mark.
        o = idx[min(p, len(idx) - 1)]
        best = None
        for d in range(0, 14):
            for c in (o - d, o + d):
                if 0 < c < len(text) and text[c - 1] == " " and not text[c].isspace():
                    before = text[:c].rstrip()
                    score = 0 if before and before[-1] in ".;:!?," else 1
                    if best is None or (score, d) < best[:2]:
                        best = (score, d, c)
        return best[2] if best else o

    starts = [(0, 0)]
    for k in range(1, len(keys)):
        if offs[k] >= q_end - 6:
            break
        p = where(offs[k])
        if p is None or p >= len(n) - 6:
            break
        c = snap(p)
        if c - starts[-1][0] < 12 or len(text) - c < 12:
            continue
        starts.append((c, k))
    covered = starts[-1][1] + 1
    end = None
    if len(n) - p_end > 12 and q_end >= offs[covered - 1] + len(keys[covered - 1]) - 6:
        end = idx[p_end - 1] + 1
        while end < len(text) and text[end] in ".;:!?, ":
            end += 1
    return starts, end, matched


def number_psalms(services, psalter):
    ps = psalm_verses(psalter)
    index = {}
    for num, verses in ps.items():
        for vi, (_, v) in enumerate(verses):
            index.setdefault(norm_map(v)[0][:24], []).append((num, vi))
    out = {}
    for slug, items in services.items():
        if not isinstance(items, list):
            out[slug] = items
            continue
        new, last = [], None  # last: (psalm, verse number) said just before
        for x in items:
            runs = x.get("r")
            if not runs or x.get("t") == "h":
                new.append(x)
                continue
            text = "".join(r[0] for r in runs)
            title = PSALM_TITLE.match(text)
            if title:
                new.append({**x, "pt": 1})
                last = (int(title.group(1)), 0)
                continue
            n, idx = norm_map(text)
            cands = list(index.get(n[:24], []))
            if last:
                cands = sorted(cands, key=lambda c: c[0] != last[0])
                # The verse after the last one said, where the wording differs.
                nxt = next((k for k, (vn, _) in enumerate(ps.get(last[0], [])) if vn == last[1] + 1), None)
                if nxt is not None and (last[0], nxt) not in cands:
                    cands.append((last[0], nxt))
            hit, best = None, 0
            for num, vi in cands:
                if len(n) < 20:
                    break
                starts, end, matched = verse_walk(n, ps[num], vi, text, idx)
                follows = last and last[0] == num and ps[num][vi][0] in (last[1] + 1, 1)
                score = matched / len(n)
                if score >= (0.7 if follows else 0.85) and (len(starts) >= 2 or follows) and score > best:
                    hit, best = (num, vi, starts, end), score
            if not hit:
                new.append(x)
                if re.search(r"\w{3}", "".join(r[0] for r in runs if "r" not in r[1])):
                    last = None
                continue
            num, vi, starts, end = hit
            verses = ps[num]
            if verses[vi][0] == 1 and not (new and new[-1].get("pt")):
                new.append({"t": "p", "c": 1, "pt": 1, "r": [[f"Psalmul {num}", "r"]], **({"w": x["w"]} if "w" in x else {})})
            cuts = [c for c, _ in starts[1:]] + ([end] if end is not None else [])
            parts = split_runs(runs, cuts)
            base = {k: v for k, v in x.items() if k not in ("r", "c")}
            carry = []
            for j, part in enumerate(parts):
                part = carry + part
                carry = []
                if not re.search(r"\w{3}", "".join(r[0] for r in part)):
                    carry = part
                    continue
                if j < len(starts):
                    new.append({**base, "r": part, "v": verses[vi + starts[j][1]][0]})
                else:
                    new.append({**base, "r": part})
            last = (num, verses[vi + starts[-1][1]][0])
        out[slug] = new
    return out


def number_psalter(psalter):
    """The Psalter's own "12. " prefixes become the same verse numbers."""
    out = {}
    for k, blocks in psalter.items():
        nb = []
        for b in blocks:
            t = "".join(r[0] for r in b["r"])
            m = re.match(r"\s*(\d+)\.\s*", t)
            if m and b["r"]:
                runs = [list(r) for r in b["r"]]
                cut = m.end()
                while cut and runs:
                    if len(runs[0][0]) <= cut:
                        cut -= len(runs[0][0])
                        runs.pop(0)
                    else:
                        runs[0][0] = runs[0][0][cut:]
                        cut = 0
                nb.append({**b, "r": runs, "v": int(m.group(1))})
            elif re.match(r"\s*PSALMUL\s+\d+", t):
                nb.append({**b, "pt": 1})
            else:
                nb.append(b)
        out[k] = nb
    return out


def main():
    psalter = build_psalter()
    write("services", number_psalms(place_after_canon(strip_refs(build_services())), psalter))
    write("hymns", build_hymns())
    write("sinaxar", build_sinaxar())
    for year, days in build_old_style().items():
        write(f"vechi-{year}", days)
    calendar = build_calendar()
    write("fixed-calendar", build_fixed_calendar(calendar))
    for year, days in calendar.items():
        write(f"cal-{year}", days)
    treime, canon = build_canons()
    write("canon-treime", treime)
    for glas, rec in canon.items():
        write(f"canon-md-{glas}", rec)
    write("psaltire", number_psalter(psalter))
    # Review file: every text found automatically, and what stayed short.
    lines = [f"{origin or 'NEGĂSIT':24} | {phrase} => {(full or '')[:90]}" for phrase, (full, origin) in sorted(AUDIT.items(), key=lambda kv: (bool(kv[1][0]), kv[0]))]
    (ROOT / "source" / "expansions.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"expansions: {sum(1 for v in AUDIT.values() if v[0])} found, {sum(1 for v in AUDIT.values() if not v[0])} not found")


if __name__ == "__main__":
    main()
