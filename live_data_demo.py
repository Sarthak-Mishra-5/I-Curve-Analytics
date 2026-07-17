"""
Minimal standalone Lightstreamer live-data fetcher.

Connects to the TT market-data Lightstreamer endpoint, subscribes to a few
contracts, and prints every tick to the console. Self-contained — no project
imports needed.

Requirements:
    pip install lightstreamer-client-lib

Run:
    python live_data_demo.py
"""
import time

from lightstreamer.client import LightstreamerClient, Subscription

# --- connection settings ----------------------------------------------------
SERVER_URL = "https://ls-md.corp.hertshtengroup.com/"
ADAPTER_SET = "TTsdkLSAdapter"
DATA_ADAPTER = "HGL1_Adapter"

# Fields requested per item.
FIELD_NAMES = [
    "Contract", "Product", "InstrumentId",
    "BestBid", "BestBidQty", "BestAsk", "BestAskQty",
    "Last", "LastQty", "Volume", "Settle", "PrevSettle",
]

# (display name, InstrumentId) — add/remove as needed.
CONTRACTS = [
    ("SA3 Jun26", "6777292727603905167"),
    ("SA3 Sep26", "10152022727750786343"),
    ("ER3 JUN26", "17887834827094596965"),
]


class TickListener:
    """Lightstreamer SubscriptionListener — onItemUpdate fires per tick."""

    def onItemUpdate(self, update):
        values = {f: update.getValue(f) for f in FIELD_NAMES}
        name = values.get("Contract") or update.getItemName()
        bid, ask, last = values.get("BestBid"), values.get("BestAsk"), values.get("Last")
        print(f"{name:12s}  bid={bid}  ask={ask}  last={last}")

    # The rest of the protocol — no-ops / simple logging.
    def onSubscription(self): pass
    def onUnsubscription(self): pass
    def onSubscriptionError(self, code, message):
        print(f"[sub error] {code}: {message}")
    def onItemLostUpdates(self, item_name, item_pos, lost):
        print(f"[lost {lost} updates on {item_name}]")
    def onClearSnapshot(self, item_name, item_pos): pass
    def onEndOfSnapshot(self, item_name, item_pos): pass
    def onCommandSecondLevelItemLostUpdates(self, lost, key): pass
    def onCommandSecondLevelSubscriptionError(self, code, message, key): pass
    def onRealMaxFrequency(self, freq): pass


def main():
    client = LightstreamerClient(SERVER_URL, ADAPTER_SET)
    client.connect()

    items = [f"TT-{iid}" for _, iid in CONTRACTS]
    sub = Subscription("MERGE", items, FIELD_NAMES)
    sub.setDataAdapter(DATA_ADAPTER)
    sub.setRequestedMaxFrequency("0.5")   # max 0.5 updates/sec per item
    sub.setRequestedSnapshot("yes")        # send current state on subscribe
    sub.addListener(TickListener())
    client.subscribe(sub)

    print("Connected — streaming live ticks (Ctrl+C to stop)...")
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        client.unsubscribe(sub)
        client.disconnect()
        print("\nDisconnected.")


if __name__ == "__main__":
    main()
