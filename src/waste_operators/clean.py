"""Name standardisation and basic cleaning.

Apply the SAME function to EA operator names and Companies House company names,
so that equal stems become *candidate* matches. A stem match is not proof: for
example "Biffa Waste Services Ltd" and "Biffa Waste Services PLC" share a stem but
are different legal entities, which is why the legal form is returned separately.

Run the examples with:  python -m doctest -v src/waste_operators/clean.py
"""
import re
import unicodedata

# Legal-form words, removed only when they END the name
LEGAL_FORMS = {"limited", "ltd", "plc", "llp", "lp", "cic", "cio", "unlimited"}

# Spelled-out or spaced-out forms, rewritten before tokenising
_PHRASES = [
    (r"\bpublic limited company\b", " plc "),
    (r"\blimited liability partnership\b", " llp "),
    (r"\bcommunity interest company\b", " cic "),
    (r"\bl t d\b", " ltd "),
    (r"\bp l c\b", " plc "),
    (r"\bl l p\b", " llp "),
]

# "X Ltd trading as Y": the registered entity is the part before the marker
_TRADING_AS = re.compile(r"\s+(?:trading\s+as|t/as?)\s+")


def split_legal_form(name) -> tuple[str, str]:
    """Return (stem, legal_form) for a company name.

    >>> split_legal_form("VEOLIA ES (UK) LIMITED")
    ('veolia es uk', 'limited')
    >>> split_legal_form("Smith & Sons Ltd.")
    ('smith and sons', 'ltd')
    >>> split_legal_form("The Biffa Waste Services Ltd")
    ('biffa waste services', 'ltd')
    >>> split_legal_form("O'Brien Recycling")
    ('obrien recycling', '')
    >>> split_legal_form("Alchemy Metals Limited t/a Waste Mission")
    ('alchemy metals', 'limited')
    >>> split_legal_form("LONGWATER (GRAVEL) COMPANY LIMITED (THE)")
    ('longwater gravel company', 'limited')
    >>> split_legal_form("JAMES CROPPER PUBLIC LIMITED COMPANY")
    ('james cropper', 'plc')
    >>> split_legal_form("MYERS SKIP HIRE L T D")
    ('myers skip hire', 'ltd')
    >>> split_legal_form(None)
    ('', '')
    """
    if name is None or (isinstance(name, float) and name != name):  # None or NaN
        return "", ""
    text = unicodedata.normalize("NFKD", str(name))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))  # strip accents
    text = text.lower()
    text = _TRADING_AS.split(text, maxsplit=1)[0]
    text = text.replace("&", " and ")
    text = re.sub(r"['\u2019`]", "", text)   # O'Brien -> obrien
    text = re.sub(r"[^a-z0-9]+", " ", text)   # punctuation -> space
    text = f" {text.strip()} "
    for pattern, repl in _PHRASES:
        text = re.sub(pattern, repl, text)
    tokens = text.split()

    if tokens and tokens[0] == "the":
        tokens = tokens[1:]
    if tokens and tokens[-1] == "the":        # "... LIMITED (THE)"
        tokens = tokens[:-1]
    form = ""
    if tokens and tokens[-1] in LEGAL_FORMS:
        form = tokens.pop()
    return " ".join(tokens), form


def standardise_name(name) -> str:
    """Return just the stem of a company name.

    >>> standardise_name("EMR GROUP LIMITED")
    'emr group'
    >>> standardise_name("Mick George Ltd")
    'mick george'
    """
    return split_legal_form(name)[0]


# ---------------------------------------------------------------------------
# Rough classification, used to separate operators we expect to match Companies
# House from those we don't. These are heuristics: check the 'unclear' group by eye.
# ---------------------------------------------------------------------------
_PUBLIC = re.compile(
    r"\b(council|borough|county|district|metropolitan|unitary|authority|nhs|"
    r"hospital|hospitals|university|police|environment agency|highways|"
    r"network rail|ministry of defence)\b|\bm b c\b|\bmbc\b"
)
_BUSINESS_WORD = re.compile(
    r"\b(group|holdings|services|recycling|waste|skip|skips|hire|plant|environmental|"
    r"energy|power|farm|farms|estate|estates|quarry|quarries|aggregates|materials|"
    r"transport|haulage|metals|scrap|demolition|construction|contracts|contractors|"
    r"landfill|management|disposal|reclamation|centre|recovery|partnership|sons|"
    r"bros|co|company|and|trading|tyres|salvage|compost|composting|soils|soil)\b"
)
_TITLE = re.compile(r"\b(mr|mrs|ms|miss|dr)\b")


def classify_operator(name) -> str:
    """Return 'company', 'public_body', 'individual_or_unregistered' or 'unclear'.

    >>> classify_operator("VEOLIA ES (UK) LIMITED")
    'company'
    >>> classify_operator("ESSEX COUNTY COUNCIL")
    'public_body'
    >>> classify_operator("TAMESIDE M B C")
    'public_body'
    >>> classify_operator("Roland Head")
    'individual_or_unregistered'
    >>> classify_operator("Bush Haulage")
    'unclear'
    """
    stem, form = split_legal_form(name)
    if form:
        return "company"
    if _PUBLIC.search(stem):
        return "public_body"
    if _TITLE.search(stem):
        return "individual_or_unregistered"
    tokens = stem.split()
    if 2 <= len(tokens) <= 4 and not _BUSINESS_WORD.search(stem):
        return "individual_or_unregistered"
    return "unclear"
