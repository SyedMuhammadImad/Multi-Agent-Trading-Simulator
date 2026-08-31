"""
Read-only Exness MT5 demo integration.

This adapter deliberately has no order-placement method. It is only for
connection checks, account snapshots, and symbol quotes from a local MT5
terminal logged into an Exness demo account.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


def _mask_login(login: Optional[int]) -> Optional[str]:
    if login is None:
        return None
    value = str(login)
    if len(value) <= 4:
        return "*" * len(value)
    return f"{value[:2]}***{value[-2:]}"


def _to_dict(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "_asdict"):
        return dict(value._asdict())
    if isinstance(value, dict):
        return value
    return {
        key: getattr(value, key)
        for key in dir(value)
        if not key.startswith("_") and not callable(getattr(value, key))
    }


@dataclass(frozen=True)
class ExnessMT5Config:
    login: Optional[int]
    password: str
    server: str
    terminal_path: str
    symbols: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "ExnessMT5Config":
        raw_login = os.getenv("EXNESS_DEMO_LOGIN", "").strip()
        login = int(raw_login) if raw_login.isdigit() else None
        raw_symbols = os.getenv("EXNESS_SYMBOLS", "XAUUSDm,EURUSDm,BTCUSDm")
        symbols = tuple(s.strip().upper() for s in raw_symbols.split(",") if s.strip())
        return cls(
            login=login,
            password=os.getenv("EXNESS_DEMO_PASSWORD", ""),
            server=os.getenv("EXNESS_DEMO_SERVER", ""),
            terminal_path=os.getenv("EXNESS_MT5_PATH", ""),
            symbols=symbols,
        )

    @property
    def configured(self) -> bool:
        return bool(self.login and self.password and self.server)

    def public_dict(self) -> Dict[str, Any]:
        return {
            "configured": self.configured,
            "login": _mask_login(self.login),
            "server": self.server or None,
            "terminal_path": self.terminal_path or None,
            "symbols": list(self.symbols),
        }


class ExnessMT5ReadOnlyBroker:
    def __init__(self, config: Optional[ExnessMT5Config] = None, mt5_module: Any = None):
        self.config = config or ExnessMT5Config.from_env()
        self._mt5 = mt5_module
        self._connected = False
        self._last_error: Optional[str] = None
        self._connected_at: Optional[float] = None

    def _load_mt5(self) -> Any:
        if self._mt5 is not None:
            return self._mt5
        try:
            import MetaTrader5 as mt5
        except ImportError as exc:
            self._last_error = "MetaTrader5 package is not installed"
            raise RuntimeError(self._last_error) from exc
        self._mt5 = mt5
        return mt5

    @property
    def configured(self) -> bool:
        return self.config.configured

    @property
    def connected(self) -> bool:
        return self._connected

    def status(self) -> Dict[str, Any]:
        package_available = self._mt5 is not None
        if self._mt5 is None:
            try:
                self._load_mt5()
                package_available = True
            except RuntimeError:
                package_available = False

        return {
            "broker": "exness_mt5",
            "mode": "read_only_demo",
            "read_only": True,
            "trade_execution_enabled": False,
            "configured": self.configured,
            "connected": self._connected,
            "connected_at": self._connected_at,
            "package_available": package_available,
            "last_error": self._last_error,
            "config": self.config.public_dict(),
        }

    def connect(self) -> Dict[str, Any]:
        if not self.configured:
            self._connected = False
            self._last_error = (
                "Set EXNESS_DEMO_LOGIN, EXNESS_DEMO_PASSWORD, and "
                "EXNESS_DEMO_SERVER in backend/.env"
            )
            return self.status()

        try:
            mt5 = self._load_mt5()
            init_kwargs: Dict[str, Any] = {
                "login": self.config.login,
                "password": self.config.password,
                "server": self.config.server,
            }
            if self.config.terminal_path:
                init_kwargs["path"] = self.config.terminal_path

            if not mt5.initialize(**init_kwargs):
                self._connected = False
                self._last_error = f"MT5 initialize failed: {mt5.last_error()}"
                return self.status()

            account = mt5.account_info()
            if account is None:
                self._connected = False
                self._last_error = f"MT5 account_info failed: {mt5.last_error()}"
                return self.status()

            self._connected = True
            self._connected_at = time.time()
            self._last_error = None
            return self.status()
        except Exception as exc:
            self._connected = False
            self._last_error = str(exc)
            return self.status()

    def shutdown(self) -> Dict[str, Any]:
        try:
            if self._mt5 is not None:
                self._mt5.shutdown()
        finally:
            self._connected = False
            self._connected_at = None
        return self.status()

    def account_info(self) -> Dict[str, Any]:
        status = self.connect() if not self._connected else self.status()
        if not status["connected"]:
            return {"status": status, "account": None}

        account = _to_dict(self._mt5.account_info())
        safe_fields = [
            "login",
            "server",
            "name",
            "company",
            "currency",
            "balance",
            "equity",
            "margin",
            "margin_free",
            "margin_level",
            "leverage",
            "trade_mode",
        ]
        safe_account = {field: account.get(field) for field in safe_fields if field in account}
        if "login" in safe_account:
            safe_account["login"] = _mask_login(safe_account["login"])
        return {"status": self.status(), "account": safe_account}

    def quote(self, symbol: str) -> Dict[str, Any]:
        normalized = symbol.strip().upper()
        if not normalized:
            return {"status": self.status(), "quote": None, "error": "symbol is required"}

        status = self.connect() if not self._connected else self.status()
        if not status["connected"]:
            return {"status": status, "quote": None}

        self._mt5.symbol_select(normalized, True)
        tick = self._mt5.symbol_info_tick(normalized)
        if tick is None:
            self._last_error = f"MT5 symbol_info_tick failed for {normalized}: {self._mt5.last_error()}"
            return {"status": self.status(), "quote": None}

        data = _to_dict(tick)
        return {
            "status": self.status(),
            "quote": {
                "symbol": normalized,
                "bid": data.get("bid"),
                "ask": data.get("ask"),
                "last": data.get("last"),
                "time": data.get("time"),
                "time_msc": data.get("time_msc"),
            },
        }
