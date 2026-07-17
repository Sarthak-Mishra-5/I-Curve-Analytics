"""Configuration: contracts, fields, Lightstreamer endpoints, analytics windows."""
from __future__ import annotations

import calendar
from datetime import date, datetime, timezone
from pathlib import Path

SERVER_URL = "https://ls-md.corp.hertshtengroup.com/"
ADAPTER_SET = "TTsdkLSAdapter"
DATA_ADAPTER = "HGL1_Adapter"

FIELD_NAMES = [
    "command",
    "Exchange",
    "Contract",
    "Product",
    "InstrumentId",
    "ClientRecvTime",
    "ExchangeRecvTime",
    "ServerRecvTime",
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
    "Last",
    "LastQty",
    "SeriesStatus",
    "Settle",
    "PrevSettle",
    "BestAsk",
    "BestAskQty",
    "BestBid",
    "BestBidQty",
    "IndSettle",
    "Price",
    "AdminPrice",
    "Admin",
    "Direction",
]

SUBSCRIBED_CONTRACTS_SA3 = [
    ("SA3 Jun26", "6777292727603905167"),
    ("SA3 Sep26", "10152022727750786343"),
    ("SA3 Dec26", "6914531881671971328"),
    ("SA3 Mar27", "5619891302845554146"),
    ("SA3 Jun27", "11935287284762367596"),
    ("SA3 Sep27", "3973483485124835681"),
    ("SA3 Dec27", "12146542221589140494"),
    ("SA3 Mar28", "6314259765637387886"),
    ("SA3 Jun28", "12197960486633385234"),
    ("SA3 Sep28", "12203053644589187435"),
    ("SA3 Dec28", "14401575330262518877"),
    ("SA3 Mar29", "6504067269185906303"),
    ("SA3 Jun29", "15117311257991458693"),
    ("SA3 Sep29", "6558853516677562258"),
    ("SA3 Dec29", "18071176284543341830"),
]

SUBSCRIBED_CONTRACTS_ER3 = [
    ("ER3 JUN26", "17887834827094596965"),
    ("ER3 SEP26", "13942165873650377178"),
    ("ER3 DEC26", "4095991086729837254"),
    ("ER3 MAR27", "6978109625607659725"),
    ("ER3 JUN27", "1617737763414000389"),
    ("ER3 SEP27", "12062554666991936143"),
    ("ER3 DEC27", "10640221686516715116"),
    ("ER3 MAR28", "12215144550695335695"),
    ("ER3 JUN28", "7543045276132469533"),
    ("ER3 SEP28", "978230606953087791"),
    ("ER3 DEC28", "3161274050251907543"),
    ("ER3 MAR29", "4293326410978229541"),
    ("ER3 JUN29", "17711323309675939815"),
    ("ER3 SEP29", "4020974588637570309"),
    ("ER3 DEC29", "3779534020756663275"),
]

SUBSCRIBED_CONTRACTS_I = [
    ("I Jun26", "5444827104880269937"),
    ("I Sep26", "6628990053936569924"),
    ("I Dec26", "196073038322495181"),
    ("I Mar27", "6532810731306051149"),
    ("I Jun27", "10290150595504250421"),
    ("I Sep27", "18341350720628559368"),
    ("I Dec27", "17244622560953637946"),
    ("I Mar28", "6159411209048528655"),
    ("I Jun28", "16203147123713749534"),
    ("I Sep28", "13181973989553924789"),
    ("I Dec28", "6189133329181631919"),
    ("I Mar29", "1972877616990500330"),
    ("I Jun29", "5829843526467061673"),
    ("I Sep29", "17983703097809095440"),
    ("I Dec29", "18370117369950377328"),
    ("I Sep26-Dec26", "1311068273505625388"),
    ("I Dec26-Mar27", "16718227565601251613"),
    ("I Mar27-Jun27", "1767469478377361142"),
    ("I Jun27-Sep27", "18058480039346735234"),
    ("I Sep27-Dec27", "14681154602997790890"),
    ("I Dec27-Mar28", "13030605258118569052"),
    ("I Mar28-Jun28", "1157860809804392967"),
    ("I Jun28-Sep28", "11148007141172160632"),
    ("I Sep28-Dec28", "4060413914256790782"),
    ("I Dec28-Mar29", "6052216482589083108"),
    ("I Mar29-Jun29", "1149284821042178103"),
    ("I Sep26-Mar27", "5095276832087724662"),
    ("I Dec26-Jun27", "9786540273641429331"),
    ("I Mar27-Sep27", "5376365224130369800"),
    ("I Jun27-Dec27", "18266552713857873693"),
    ("I Sep27-Mar28", "14639056438856399301"),
    ("I Dec27-Jun28", "6249447006615112440"),
    ("I Mar28-Sep28", "2008292388024126264"),
    ("I Jun28-Dec28", "12451747188123896583"),
    ("I Sep28-Mar29", "3300259466889622117"),
    ("I Dec28-Jun29", "16485150609240682923"),
    ("I Sep26 3MF", "5455585003313830833"),
    ("I Dec26 3MF", "506849390470211885"),
    ("I Mar27 3MF", "2402332155024113565"),
    ("I Jun27 3MF", "14845139698021760722"),
    ("I Sep27 3MF", "449477163040795145"),
    ("I Dec27 3MF", "13799494491971916490"),
    ("I Mar28 3MF", "507859596072904008"),
    ("I Jun28 3MF", "2278492407074804159"),
    ("I Sep28 3MF", "14364857017175468665"),
    ("I Dec28 3MF", "3223910060297845133"),
    ("I Mar29 3MF", "8249884473220438753"),
    ("I Jun29 3MF", "17041841442998138260"),
    ("I Sep29 3MF", "7167285452380657429"),
    ("I Dec29 3MF", "13954489903467424437"),  
]

ALL_CONTRACTS = SUBSCRIBED_CONTRACTS_SA3 + SUBSCRIBED_CONTRACTS_ER3 + SUBSCRIBED_CONTRACTS_I

# Tenor ordering. Quarter codes H/M/U/Z = Mar/Jun/Sep/Dec.
TENOR_ORDER = [
    "Jun26", "Sep26", "Dec26",
    "Mar27", "Jun27", "Sep27", "Dec27",
    "Mar28", "Jun28", "Sep28", "Dec28",
    "Mar29", "Jun29", "Sep29", "Dec29",
]

# Map raw InstrumentId → canonical display name (e.g. "SA3 Jun26").
INSTRUMENT_ID_TO_NAME: dict[str, str] = {iid: name for name, iid in ALL_CONTRACTS}
NAME_TO_INSTRUMENT_ID: dict[str, str] = {name: iid for name, iid in ALL_CONTRACTS}

# Product → ordered list of contract names.
def _tenor_key(name: str) -> int:
    suffix = name.split()[-1].title()  # "Jun26"
    return TENOR_ORDER.index(suffix) if suffix in TENOR_ORDER else 999

SA3_NAMES = sorted([n for n, _ in SUBSCRIBED_CONTRACTS_SA3], key=_tenor_key)
ER3_NAMES = sorted([n for n, _ in SUBSCRIBED_CONTRACTS_ER3], key=_tenor_key)

# --- "I" curve name lists ---------------------------------------------------
# SUBSCRIBED_CONTRACTS_I is already laid out in chronological blocks:
# outrights, then 3-month spreads, then 6-month spreads, then 3-month flies.
# Derive ordered name lists generically (by structure, not by hardcoding) so
# this same derivation pattern can be reused for future STIR curves.
def _spread_width(name: str) -> int | None:
    """Index distance (in TENOR_ORDER) between the two legs of a calendar
    spread name like 'I Sep26-Dec26'. Returns None if not a spread name."""
    body = name.split(" ", 1)[1]
    if "-" not in body:
        return None
    near, far = body.split("-")
    if near not in TENOR_ORDER or far not in TENOR_ORDER:
        return None
    return TENOR_ORDER.index(far) - TENOR_ORDER.index(near)

_QUARTER_MONTH_NUM = {"Mar": 3, "Jun": 6, "Sep": 9, "Dec": 12}


def _tenor_expiry_date(tenor: str) -> date:
    """3rd-Wednesday-of-contract-month IMM expiry date for a quarterly tenor
    like 'Sep26' (standard STIR futures convention)."""
    month, year = _QUARTER_MONTH_NUM[tenor[:3]], 2000 + int(tenor[3:])
    first_weekday, _ = calendar.monthrange(year, month)  # 0=Mon..6=Sun
    first_wednesday = 1 + (2 - first_weekday) % 7
    return date(year, month, first_wednesday + 14)


def _front_tenor(name: str) -> str:
    """The tenor governing a name's expiry: the outright's own tenor, a
    spread's near leg, or a fly's front leg."""
    body = name.split(" ", 1)[1]
    return body.split("-")[0] if "-" in body else body.split()[0]


def _is_expired(name: str, as_of: date) -> bool:
    return _tenor_expiry_date(_front_tenor(name)) < as_of


# Evaluated once at process start — correct as of today, and self-corrects on
# each restart as more quarterly contracts expire. Scoped to the "I" curve
# only; SA3/ER3 use the same static-list pattern but aren't filtered here.
_TODAY = datetime.now(timezone.utc).date()

I_OUTRIGHT_NAMES = [n for n, _ in SUBSCRIBED_CONTRACTS_I if "-" not in n and "3MF" not in n and not _is_expired(n, _TODAY)]
I_3MS_NAMES = [n for n, _ in SUBSCRIBED_CONTRACTS_I if _spread_width(n) == 1 and not _is_expired(n, _TODAY)]
I_6MS_NAMES = [n for n, _ in SUBSCRIBED_CONTRACTS_I if _spread_width(n) == 2 and not _is_expired(n, _TODAY)]
I_3MF_NAMES = [n for n, _ in SUBSCRIBED_CONTRACTS_I if "3MF" in n and not _is_expired(n, _TODAY)]

# Rolling calendar-time curve-history store + stats scheduler settings.
CURVE_HISTORY_BAR_SEC = 60             # bar resolution for the persistent history store
CURVE_HISTORY_WINDOW_DAYS = 30         # rolling window used by the stats tables
CURVE_STATS_INTERVAL_SEC = 60.0        # how often the curve stats scheduler recomputes
CURVE_HISTORY_DIR = Path(__file__).parent.parent / "data_cache" / "curve_history"
CURVE_CORRELATION_HISTORY_DIR = Path(__file__).parent.parent / "data_cache" / "curve_correlation"
CURVE_CORRELATION_HISTORY_DAYS = 180   # trailing window shown in every correlation chart (~6 months)

# Analytics windows (number of observations / ticks). In-memory only.
ROLLING_BUFFER_SIZE = 5000          # per-instrument tick buffer cap
ROLLING_WINDOW_SHORT = 60           # short window (e.g. spread z-score)
ROLLING_WINDOW_MEDIUM = 300         # medium
ROLLING_WINDOW_LONG = 1200          # long
ANALYTICS_INTERVAL_SEC = 1.0        # how often the analytics scheduler runs

# Alert thresholds.
ALERT_SPREAD_Z = 2.5
ALERT_FLY_Z = 2.5
ALERT_RESID_Z = 2.5
ALERT_CORR_DROP = 0.3               # corr regime shift threshold (delta)
ALERT_VOL_SPIKE = 2.0               # realized vol / ewma vol ratio

# DV01 per tick — placeholder; real values depend on contract specs.
# SA3 (SARON 3M, CHF, 0.5bp ticks typical): ~CHF12.50/tick (approx)
# ER3 (€STR 3M, EUR, 0.5bp ticks typical): ~EUR12.50/tick (approx)
# These are placeholders — overrideable via env later.
DV01_PER_TICK = {
    "SA3": 12.50,
    "ER3": 7,
    "I": 14,
}
TICK_SIZE = {
    "SA3": 0.005,
    "ER3": 0.0025,
    "I": 0.005,
}
