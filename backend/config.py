"""Configuration: contracts, fields, Lightstreamer endpoints, analytics windows."""
from __future__ import annotations

import calendar
from datetime import date, datetime, timezone
from pathlib import Path

SERVER_URL = "https://ls-md.corp.hertshtengroup.com/"
ADAPTER_SET = "TTsdkLSAdapter"
DATA_ADAPTER = "HGL1_Adapter"

OHLC_API_URL = "https://qh-api.corp.hertshtengroup.com/api/v2/ohlc"
# Vendor limits. The row cap is per REQUEST and counted across every
# instrument in it (4 instruments x count=3000 = 12000 rows is rejected), so
# batch size has to be derived from the requested bar count — see
# data/ohlc_api.max_batch_size.
OHLC_API_RATE_LIMIT_PER_MINUTE = 10
OHLC_API_MAX_ROW = 10000

BEARER_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoyMDg4NjkzNzM1LCJpYXQiOjE3NzMzMzM3MzUsImp0aSI6ImM1N2EzZjhiNTgwYjRjOGFhYjM4Yzg4MGU5ZjcwY2UyIiwidXNlcl9pZCI6MzgzfQ.TRJ6ept6qPf2iCZucURSzUKSJbYCrNYGdHsPa8aYZGc"

def get_auth_headers():
    return {
        "Authorization": f"Bearer {BEARER_TOKEN}",
        "Accept": "application/json"
    }

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
    ("SA3 Jun26-Sep26", "15283921549582549418"),
    ("SA3 Sep26-Dec26", "13131760473352420914"),
    ("SA3 Dec26-Mar27", "16259004007279004825"),
    ("SA3 Mar27-Jun27", "10670967411415013508"),
    ("SA3 Jun27-Sep27", "8481006698682872844"),
    ("SA3 Sep27-Dec27", "13994529427492477618"),
    ("SA3 Dec27-Mar28", "3043002966821789637"),
    ("SA3 Mar28-Jun28", "13713228640041917354"),
    ("SA3 Jun28-Sep28", "11660090515889192293"),
    ("SA3 Sep28-Dec28", "18011047185126124299"),
    ("SA3 Dec28-Mar29", "6640022503720765124"),
    ("SA3 Mar29-Jun29", "8070827777609927931"),
    ("SA3 Jun29-Sep29", "2803926872344659289"),
    
    ("SA3 Jun26 3MF", "17750884815534850050"),
    ("SA3 Sep26 3MF", "9203369517049151626"),
    ("SA3 Dec26 3MF", "1264552906206314163"),
    ("SA3 Mar27 3MF", "8145974784807434202"),
    ("SA3 Jun27 3MF", "15767186777862059219"),
    ("SA3 Sep27 3MF", "14583120225367159191"),
    ("SA3 Dec27 3MF", "18363959007972907935"),
    ("SA3 Mar28 3MF", "13244091675404167818"),
    ("SA3 Jun28 3MF", "12675321651830767337"),
    ("SA3 Sep28 3MF", "11714159330713063611"),
    ("SA3 Dec28 3MF", "10865780625514236831"),
    
    
    ("SA3 Jun26-Dec26", "929766345680495730"),
    ("SA3 Dec26-Jun27", "544031855385962372"),
    ("SA3 Jun27-Dec27", "15460592429251930449"),
    ("SA3 Dec26-Dec27", "6170461984881950814"),
    ("SA3 Dec27-Dec28", "10025362995233882825"),
   
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
    ("I Mar30", "6488806392486217148"),
    ("I Jun30", "1727586975590923283"),
    ("I Sep30", "7297840225510912048"),
    ("I Dec30", "9275986266275574972"),
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

SUBSCRIBED_CONTRACTS_SO3 = [
    ("SO3 Jun26", "17388498933531365606"),
    ("SO3 Sep26", "14330867541177216896"),
    ("SO3 Dec26", "2929215027186538641"),
    ("SO3 Mar27", "12777480240935901350"),
    ("SO3 Jun27", "17489439929274896309"),
    ("SO3 Sep27", "13124315370012665646"),
    ("SO3 Dec27", "6883681751251454284"),
    ("SO3 Mar28", "4771138968527992296"),
    ("SO3 Jun28", "1778338967582843813"),
    ("SO3 Sep28", "13553073652848841644"),
    ("SO3 Dec28", "12802673068039550141"),
    ("SO3 Mar29", "14192579889497853292"),
    ("SO3 Jun29", "13656323332417174028"),
    ("SO3 Sep29", "15474919503937410045"),
    ("SO3 Dec29", "16444027228601244617"),
    ("SO3 Sep26-Dec26", "7303136447654813042"),
    ("SO3 Dec26-Mar27", "12309733990612520016"),
    ("SO3 Mar27-Jun27", "15544382300253741038"),
    ("SO3 Jun27-Sep27", "11299061421331401466"),
    ("SO3 Sep27-Dec27", "9155336585209401751"),
    ("SO3 Dec27-Mar28", "16970928175331468341"),
    ("SO3 Mar28-Jun28", "2382996932605719455"),
    ("SO3 Jun28-Sep28", "16233147676670141758"),
    ("SO3 Sep28-Dec28", "5371142640950304887"),
    ("SO3 Dec28-Mar29", "17931114822400781230"),
    ("SO3 Mar29-Jun29", "5724848222879140096"),
    ("SO3 Jun29-Sep29", "970533405473342638"),
    ("SO3 Sep26 3MF", "5802081850116781229"),
    ("SO3 Dec26 3MF", "2386584141984269812"),
    ("SO3 Mar27 3MF", "10370433218461137045"),
    ("SO3 Jun27 3MF", "11389244677622334461"),
    ("SO3 Sep27 3MF", "16466421796372728560"),
    ("SO3 Dec27 3MF", "18237649840534290678"),
    ("SO3 Mar28 3MF", "4750893854772769278"),
    ("SO3 Jun28 3MF", "4531131095539811721"),
    ("SO3 Sep28 3MF", "5598951019664449136"),
    ("SO3 Dec28 3MF", "16168741156696492968"),
    ("SO3 Mar29 3MF", "9980713530874556730"),
    ("SO3 Jun29 3MF", "2887552610150425375"),
    ("SO3 Sep29 3MF", "11995116076595849118"),
    ("SO3 Dec29 3MF", "16675935867207389425"),
    ("SO3 Jun26-Dec26", "7606668504795640070"),
    ("SO3 Dec26-Jun27", "653505071096868951"),
    ("SO3 Jun27-Dec27", "18214479121426619754"),
    ("SO3 Dec26-Dec27", "17043499150738109556"),
    ("SO3 Dec27-Dec28", "5003331368693768291"),
    ("SO3 Dec28-Dec29", "3096584709959532749"),
    ("SO3 Dec29-Dec30", "8667256497296404623"),
]

SUBSCRIBED_CONTRACTS_SR3 = [
    ("SR3 Jun26", "2518875037886751798"),
    ("SR3 Sep26", "10056698436755136015"),
    ("SR3 Dec26", "3761391845186607269"),
    ("SR3 Mar27", "8786029629332899618"),
    ("SR3 Jun27", "6064266935547558467"),
    ("SR3 Sep27", "10582686653072545408"),
    ("SR3 Dec27", "17925935412019565973"),
    ("SR3 Mar28", "3822227243959035490"),
    ("SR3 Jun28", "12741923103719175711"),
    ("SR3 Sep28", "16673841811510079166"),
    ("SR3 Dec28", "7359239446017790966"),
    ("SR3 Mar29", "4211986922965728750"),
    ("SR3 Jun29", "11432813735419224277"),
    ("SR3 Sep29", "9909662404632894188"),
    ("SR3 Dec29", "12350987571259131621"),
    ("SR3 Sep26-Dec26", "10538177603741347940"),
    ("SR3 Dec26-Mar27", "15292306285496321895"),
    ("SR3 Mar27-Jun27", "9440282357390122061"),
    ("SR3 Jun27-Sep27", "1074193527039132483"),
    ("SR3 Sep27-Dec27", "5027144285602730053"),
    ("SR3 Dec27-Mar28", "5004080736027242281"),
    ("SR3 Mar28-Jun28", "15781040958777106512"),
    ("SR3 Jun28-Sep28", "3590265153926145762"),
    ("SR3 Sep28-Dec28", "6016657214449980661"),
    ("SR3 Dec28-Mar29", "14572902716380660001"),
    ("SR3 Mar29-Jun29", "10503523860245957343"),
    ("SR3 Jun29-Sep29", "15887690782750499864"),
    ("SR3 Sep26 3MF", "8274956702579047283"),
    ("SR3 Dec26 3MF", "1694217178440827148"),
    ("SR3 Mar27 3MF", "12864912356840246022"),
    ("SR3 Jun27 3MF", "11057434857239003809"),
    ("SR3 Sep27 3MF", "4246133136712339533"),
    ("SR3 Dec27 3MF", "2221718888031776067"),
    ("SR3 Mar28 3MF", "12412265760269376373"),
    ("SR3 Jun28 3MF", "14055147045902256771"),
    ("SR3 Sep28 3MF", "6817092586648247115"),
    ("SR3 Dec28 3MF", "17576025199489301908"),
    ("SR3 Mar29 3MF", "15975147523134469997"),
    ("SR3 Jun29 3MF", "10079344912650163936"),
    ("SR3 Sep29 3MF", "439275282675154222"),
    ("SR3 Dec29 3MF", "9665346556737164751"),
    ("SR3 Jun26-Dec26", "16287914367671165382"),
    ("SR3 Dec26-Jun27", "6229851979892159244"),
    ("SR3 Jun27-Dec27", "7303293106916000883"),
    ("SR3 Dec26-Dec27", "2250948975266807625"),
    ("SR3 Dec27-Dec28", "16177072337967459840"),
    ("SR3 Dec28-Dec29", "10171050261511673387"),
    ("SR3 Dec29-Dec30", "6603557660396962073"),
]



# Benchmark structures used to compare every auto-rolled custom formula.
# The historical codes are the vendor's native OHLC symbols, whereas the IDs
# are the Lightstreamer InstrumentIds used for live prices.
STRUCTURE_CORRELATION_BENCHMARKS = [
    ("ER3 Jun26-Dec26", "7049197886364910856", "FERM26-Z26"),
    ("I Dec26-Jun27", "9786540273641429331", "ERZ26-M27"),
    ("I Jun27-Dec27", "18266552713857873693", "ERM27-Z27"),
    ("I Dec26-Dec27", "4124494090517670240", "ERZ26-Z27"),
    ("I Dec27-Dec28", "6428533131735688129", "ERZ27-Z28"),
    ("I Dec28-Dec29", "13745741400540452914", "ERZ28-Z29"),
    ("I Dec29-Dec30", "6906502738573927788", "ERZ29-Z30"),
    ("I Dec30-Dec31", "14464341784003411666", "ERZ30-Z31"),
]

STRUCTURE_BENCHMARK_HISTORICAL_CODES = {
    name: historical_code
    for name, _, historical_code in STRUCTURE_CORRELATION_BENCHMARKS
}

# Per-curve benchmark columns for the structure-analysis correlation table.
# "I" keeps the original ER3-anchored benchmark set; SA3/SO3/SR3 compare
# against their own native long-dated calendar spreads instead.
CURVE_BENCHMARK_NAMES: dict[str, list[str]] = {
    "I": [name for name, _, _ in STRUCTURE_CORRELATION_BENCHMARKS],
    "SA3": [
        "SA3 Jun26-Dec26", "SA3 Dec26-Jun27", "SA3 Jun27-Dec27",
        "SA3 Dec26-Dec27", "SA3 Dec27-Dec28",
    ],
    "SO3": [
        "SO3 Jun26-Dec26", "SO3 Dec26-Jun27", "SO3 Jun27-Dec27",
        "SO3 Dec26-Dec27", "SO3 Dec27-Dec28", "SO3 Dec28-Dec29", "SO3 Dec29-Dec30",
    ],
    "SR3": [
        "SR3 Jun26-Dec26", "SR3 Dec26-Jun27", "SR3 Jun27-Dec27",
        "SR3 Dec26-Dec27", "SR3 Dec27-Dec28", "SR3 Dec28-Dec29", "SR3 Dec29-Dec30",
    ],
}

# A few I benchmarks are already subscribed as ordinary I-curve structures.
# Deduplicate those exact tuples while retaining the dedicated ER3 benchmark.
_BENCHMARK_LIVE_CONTRACTS = [(name, instrument_id) for name, instrument_id, _ in STRUCTURE_CORRELATION_BENCHMARKS]
ALL_CONTRACTS = list(dict.fromkeys(
    SUBSCRIBED_CONTRACTS_SA3
    + SUBSCRIBED_CONTRACTS_ER3
    + SUBSCRIBED_CONTRACTS_I
    + SUBSCRIBED_CONTRACTS_SO3
    + SUBSCRIBED_CONTRACTS_SR3
    + _BENCHMARK_LIVE_CONTRACTS
))

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
SO3_NAMES = sorted([n for n, _ in SUBSCRIBED_CONTRACTS_SO3], key=_tenor_key)
SR3_NAMES = sorted([n for n, _ in SUBSCRIBED_CONTRACTS_SR3], key=_tenor_key)

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
# each restart as more quarterly contracts expire.
_TODAY = datetime.now(timezone.utc).date()

I_OUTRIGHT_NAMES = [n for n, _ in SUBSCRIBED_CONTRACTS_I if "-" not in n and "3MF" not in n and not _is_expired(n, _TODAY)]
I_3MS_NAMES = [n for n, _ in SUBSCRIBED_CONTRACTS_I if _spread_width(n) == 1 and not _is_expired(n, _TODAY)]
I_6MS_NAMES = [n for n, _ in SUBSCRIBED_CONTRACTS_I if _spread_width(n) == 2 and not _is_expired(n, _TODAY)]
I_3MF_NAMES = [n for n, _ in SUBSCRIBED_CONTRACTS_I if "3MF" in n and not _is_expired(n, _TODAY)]


def _curve_outright_names(contracts: list[tuple[str, str]]) -> list[str]:
    return [n for n, _ in contracts if "-" not in n and "3MF" not in n and not _is_expired(n, _TODAY)]


def _curve_spread_names(contracts: list[tuple[str, str]], width: int) -> list[str]:
    return [n for n, _ in contracts if _spread_width(n) == width and not _is_expired(n, _TODAY)]


def _curve_fly_names(contracts: list[tuple[str, str]]) -> list[str]:
    return [n for n, _ in contracts if "3MF" in n and not _is_expired(n, _TODAY)]


SA3_OUTRIGHT_NAMES = _curve_outright_names(SUBSCRIBED_CONTRACTS_SA3)
SA3_3MS_NAMES = _curve_spread_names(SUBSCRIBED_CONTRACTS_SA3, 1)
SA3_6MS_NAMES = _curve_spread_names(SUBSCRIBED_CONTRACTS_SA3, 2)
SA3_3MF_NAMES = _curve_fly_names(SUBSCRIBED_CONTRACTS_SA3)

SO3_OUTRIGHT_NAMES = _curve_outright_names(SUBSCRIBED_CONTRACTS_SO3)
SO3_3MS_NAMES = _curve_spread_names(SUBSCRIBED_CONTRACTS_SO3, 1)
SO3_6MS_NAMES = _curve_spread_names(SUBSCRIBED_CONTRACTS_SO3, 2)
SO3_3MF_NAMES = _curve_fly_names(SUBSCRIBED_CONTRACTS_SO3)

SR3_OUTRIGHT_NAMES = _curve_outright_names(SUBSCRIBED_CONTRACTS_SR3)
SR3_3MS_NAMES = _curve_spread_names(SUBSCRIBED_CONTRACTS_SR3, 1)
SR3_6MS_NAMES = _curve_spread_names(SUBSCRIBED_CONTRACTS_SR3, 2)
SR3_3MF_NAMES = _curve_fly_names(SUBSCRIBED_CONTRACTS_SR3)

# Rolling calendar-time curve-history store + stats scheduler settings.
CURVE_HISTORY_BAR_SEC = 60             # bar resolution for the persistent history store
CURVE_HISTORY_WINDOW_DAYS = 30         # rolling window used by the stats tables
CURVE_STATS_INTERVAL_SEC = 60.0        # how often the curve stats scheduler recomputes
CURVE_HISTORY_DIR = Path(__file__).parent.parent / "data_cache" / "curve_history"
CURVE_CORRELATION_HISTORY_DIR = Path(__file__).parent.parent / "data_cache" / "curve_correlation"
CURVE_CORRELATION_HISTORY_DAYS = 180   # trailing window shown in every correlation chart (~6 months)

# --- Chart history for the Live OR candle charts ---------------------------
# Deliberately SEPARATE stores from CURVE_HISTORY_DIR above: that store's
# 30-day/60-second window is what every stats table (z-scores, correlations,
# percentiles) is computed over, and widening or re-resolving it would
# silently change all of them.
#
# One store per native vendor resolution, because mixing resolutions in a
# single series makes the fine timeframes lie: a daily bar stamped at
# midnight, sitting in a 5-minute grid, would render as one lone candle at
# 00:00 for that whole day. So intraday timeframes aggregate up from the 5M
# series, and the daily chart reads the 1D series directly.
CURVE_CHART_HISTORY_DIR = Path(__file__).parent.parent / "data_cache" / "chart_history"
CHART_RESOLUTIONS: dict[str, dict] = {
    # key -> vendor interval, bar seconds, bars to request, retention
    "5m": {"interval": "5M", "bar_sec": 300, "count": 6000, "window_days": 45},
    "1d": {"interval": "1D", "bar_sec": 86400, "count": 400, "window_days": 500},
}
# Which persisted resolution backs each timeframe the UI offers. Intraday
# timeframes all aggregate from the 5-minute series (exact, since each is a
# whole multiple of 5 minutes).
CHART_INTERVAL_SOURCE: dict[str, tuple[str, int]] = {
    # ui interval -> (resolution key, aggregation bucket seconds)
    "5m": ("5m", 300),
    "10m": ("5m", 600),
    "30m": ("5m", 1800),
    "1h": ("5m", 3600),
    "1d": ("1d", 86400),
}
# Instruments that get the deep chart history (curve_id, display name).
LIVE_OR_DEEP_INSTRUMENTS: list[tuple[str, str]] = [
    ("SR3", "SR3 Sep27"),
    ("SO3", "SO3 Sep27"),
    ("I", "I Sep27"),
    ("SA3", "SA3 Sep27"),
]

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
    "SO3": 12.50,
    "SR3": 12.50,
}
TICK_SIZE = {
    "SA3": 0.005,
    "ER3": 0.0025,
    "I": 0.005,
    "SO3": 0.005,
    "SR3": 0.005,
}

# The live Lightstreamer feed reports SR3 (SOFR) price-like fields 100x too
# large relative to every other curve on this platform (e.g. 9589.5 instead
# of 95.895 — bid/ask/open/high/low all affected uniformly). Corrected at
# ingestion, keyed by product prefix; see streaming/utils.rescale_price_fields.
LIVE_PRICE_SCALE: dict[str, float] = {
    "SR3": 0.01,
}
