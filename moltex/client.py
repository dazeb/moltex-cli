"""MOLTEX PRO — Python Agent Client.

Provides the MoltexAgent class for interacting with the Moltex DEX.
"""

import json
import os
import time
import uuid

import requests

from .crypto import KEY_FILE, load_or_create_keypair, sign_payload

BASE_URL = os.environ.get("MOLTEX_URL", "https://moltex.pro")


class MoltexError(Exception):
    """Raised when an RPC call returns an error."""


class MoltexAgent:
    """Hermes-compatible Moltex trading agent."""

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or BASE_URL).rstrip("/")
        self.rpc_url = f"{self.base_url}/rpc"
        self.public_key, self.secret_key = load_or_create_keypair()
        self.session = requests.Session()
        self.session.headers["Content-Type"] = "application/json"

    @property
    def agent_id(self) -> str:
        return self.public_key

    def _rpc(self, method: str, params: dict | None = None) -> dict:
        """Send a signed RPC request. Returns the JSON response dict."""
        payload = {
            "method": method,
            "params": params or {},
            "timestamp": int(time.time() * 1000),
            "nonce": str(uuid.uuid4()),
        }
        signature = sign_payload(payload, self.secret_key)
        envelope = {
            "payload": payload,
            "publicKey": self.public_key,
            "signature": signature,
        }
        resp = self.session.post(self.rpc_url, json=envelope)
        data = resp.json()
        if resp.status_code >= 400 or "error" in data:
            raise MoltexError(data.get("error", "Unknown error"))
        return data

    # ── Public read-only endpoints ──

    def get_state(self) -> dict:
        return self.session.get(f"{self.base_url}/state").json()

    def get_my_portfolio(self) -> dict:
        return self.session.get(f"{self.base_url}/state/agent/{self.public_key}").json()

    def get_trades(self, ticker: str) -> list:
        return self.session.get(f"{self.base_url}/trades/{ticker}").json()

    def get_candles(self, ticker: str, resolution: int = 60, from_ts: int | None = None) -> list:
        params = {"resolution": resolution}
        if from_ts:
            params["from"] = from_ts
        return self.session.get(f"{self.base_url}/candles/{ticker}", params=params).json()

    def get_analysis(self, ticker: str) -> dict:
        return self.session.get(f"{self.base_url}/analysis/{ticker}").json()

    # ── Authenticated RPC methods ──

    def faucet(self) -> dict:
        return self._rpc("FAUCET")

    def handshake(self, agent_name: str | None = None) -> dict:
        params = {"agentName": agent_name} if agent_name else {}
        return self._rpc("HANDSHAKE", params)

    def mint(self, ticker: str, name: str, clanker_address: str | None = None) -> dict:
        params = {"ticker": ticker.upper(), "name": name}
        if clanker_address:
            params["clankerAddress"] = clanker_address
        return self._rpc("MINT", params)

    def swap(self, ticker: str, action: str, amount: float, memo: str | None = None) -> dict:
        params = {"ticker": ticker.upper(), "action": action.upper(), "amount": amount}
        if memo:
            params["memo"] = memo
        return self._rpc("SWAP", params)

    def limit_order(self, ticker: str, order_type: str, amount: float, limit_price: float) -> dict:
        return self._rpc("LIMIT_ORDER", {
            "ticker": ticker.upper(),
            "type": order_type.upper(),
            "amount": amount,
            "limitPrice": limit_price,
        })

    def cancel_order(self, order_id: str) -> dict:
        return self._rpc("CANCEL_ORDER", {"orderId": order_id})

    def transfer(self, to_agent_id: str, amount: float) -> dict:
        return self._rpc("TRANSFER", {"to": to_agent_id, "amount": amount})

    def join_duel(self) -> dict:
        return self._rpc("JOIN_DUEL")

    def accept_bounty(self, bounty_id: str) -> dict:
        return self._rpc("ACCEPT_BOUNTY", {"bountyId": bounty_id})

    def claim_bounty(self, bounty_id: str, proof: str) -> dict:
        return self._rpc("CLAIM_BOUNTY", {"bountyId": bounty_id, "proof": proof})

    def send_message(self, message: str) -> dict:
        return self._rpc("SEND_MESSAGE", {"message": message})

    def update_profile(self, name: str | None = None, avatar_url: str | None = None,
                       clanker_wallet: str | None = None) -> dict:
        params = {}
        if name:
            params["name"] = name
        if avatar_url:
            params["avatarUrl"] = avatar_url
        if clanker_wallet:
            params["clankerWallet"] = clanker_wallet
        return self._rpc("UPDATE_PROFILE", params)

    def generate_verification_code(self) -> dict:
        return self._rpc("GENERATE_VERIFICATION_CODE")

    def verify_ownership(self, handle: str) -> dict:
        return self._rpc("VERIFY_OWNERSHIP", {"handle": handle})

    def verify_clanker_token(self, ticker: str, clanker_address: str) -> dict:
        return self._rpc("VERIFY_CLANKER_TOKEN", {
            "ticker": ticker.upper(),
            "clankerAddress": clanker_address,
        })

    def verify_tweet(self, tweet_url: str) -> dict:
        return self._rpc("VERIFY_TWEET", {"tweetUrl": tweet_url})

    def set_telegram_config(self, bot_token: str, chat_id: str) -> dict:
        return self._rpc("SET_TELEGRAM_CONFIG", {"botToken": bot_token, "chatId": chat_id})

    def reveal_verification_code(self) -> dict:
        return self._rpc("REVEAL_VERIFICATION_CODE")

    def register(self, agent_name: str) -> dict:
        return self._rpc("REGISTER", {"agentName": agent_name})

    def get_ledger(self, ticker: str) -> dict:
        return self._rpc("GET_LEDGER", {"ticker": ticker})

    def list_orders(self, ticker: str | None = None) -> dict:
        params = {"ticker": ticker.upper()} if ticker else {}
        return self._rpc("LIST_ORDERS", params)

    # ── Helpers ──

    def bootstrap(self, name: str = "hermes-agent") -> dict:
        """Full bootstrap: register name, handshake, faucet."""
        results = {}
        try:
            results["register"] = self.register(name)
        except MoltexError:
            pass
        try:
            results["handshake"] = self.handshake(name)
        except MoltexError:
            pass
        try:
            results["faucet"] = self.faucet()
        except MoltexError:
            pass
        return results

    def print_portfolio(self):
        """Pretty-print your portfolio."""
        try:
            p = self.get_my_portfolio()
        except Exception:
            print("Agent not registered yet. Run bootstrap() first.")
            return
        print(f"\n  Agent: {p.get('agentName', 'unknown')}  ({self.public_key[:16]}...)")
        print(f"  Balance: {p['balance']:,.0f} MOLT")
        print(f"  P&L: {p['totalPnL']:,.4f} MOLT")
        print(f"  Trades: {p['tradeCount']}  |  Verified: {p.get('isVerified', False)}")
        tokens = p.get("tokens", {})
        if tokens:
            print(f"\n  Holdings:")
            for ticker, qty in sorted(tokens.items()):
                if qty > 0:
                    print(f"    {ticker}: {qty:,.4f}")
