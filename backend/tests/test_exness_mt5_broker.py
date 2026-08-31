from collections import namedtuple

from brokers.exness_mt5 import ExnessMT5Config, ExnessMT5ReadOnlyBroker


def test_exness_status_reports_missing_config_without_connecting(monkeypatch):
    monkeypatch.delenv("EXNESS_DEMO_LOGIN", raising=False)
    monkeypatch.delenv("EXNESS_DEMO_PASSWORD", raising=False)
    monkeypatch.delenv("EXNESS_DEMO_SERVER", raising=False)

    broker = ExnessMT5ReadOnlyBroker(mt5_module=object())

    status = broker.connect()

    assert status["configured"] is False
    assert status["connected"] is False
    assert status["read_only"] is True
    assert status["trade_execution_enabled"] is False
    assert "EXNESS_DEMO_LOGIN" in status["last_error"]


def test_exness_config_preserves_symbol_case(monkeypatch):
    monkeypatch.setenv("EXNESS_DEMO_LOGIN", "12345678")
    monkeypatch.setenv("EXNESS_DEMO_PASSWORD", "secret-password")
    monkeypatch.setenv("EXNESS_DEMO_SERVER", "Exness-MT5Trial")
    monkeypatch.setenv("EXNESS_SYMBOLS", "XAUUSDm,EURUSDm,BTCUSDm")

    config = ExnessMT5Config.from_env()

    assert config.symbols == ("XAUUSDm", "EURUSDm", "BTCUSDm")


def test_exness_account_info_masks_login_and_exposes_safe_fields():
    Account = namedtuple(
        "Account",
        "login server name company currency balance equity margin margin_free margin_level leverage trade_mode",
    )

    class FakeMT5:
        def initialize(self, **kwargs):
            self.kwargs = kwargs
            return True

        def account_info(self):
            return Account(
                login=12345678,
                server="Exness-MT5Trial",
                name="Demo User",
                company="Exness",
                currency="USD",
                balance=10000.0,
                equity=10020.0,
                margin=100.0,
                margin_free=9920.0,
                margin_level=10020.0,
                leverage=200,
                trade_mode=0,
            )

        def last_error(self):
            return (0, "OK")

        def shutdown(self):
            return True

    config = ExnessMT5Config(
        login=12345678,
        password="secret-password",
        server="Exness-MT5Trial",
        terminal_path="",
        symbols=("XAUUSDm",),
    )
    broker = ExnessMT5ReadOnlyBroker(config=config, mt5_module=FakeMT5())

    result = broker.account_info()

    assert result["status"]["connected"] is True
    assert result["status"]["config"]["login"] == "12***78"
    assert result["account"]["login"] == "12***78"
    assert result["account"]["balance"] == 10000.0
    assert "password" not in result["account"]


def test_exness_quote_reads_bid_ask_from_mt5():
    Tick = namedtuple("Tick", "bid ask last time time_msc")

    class FakeMT5:
        def initialize(self, **kwargs):
            return True

        def account_info(self):
            return {"login": 12345678}

        def symbol_select(self, symbol, enabled):
            self.selected = (symbol, enabled)
            return True

        def symbol_info_tick(self, symbol):
            return Tick(bid=2301.25, ask=2301.55, last=2301.40, time=1, time_msc=1000)

        def last_error(self):
            return (0, "OK")

        def shutdown(self):
            return True

    config = ExnessMT5Config(
        login=12345678,
        password="secret-password",
        server="Exness-MT5Trial",
        terminal_path="",
        symbols=("XAUUSDm",),
    )
    broker = ExnessMT5ReadOnlyBroker(config=config, mt5_module=FakeMT5())

    result = broker.quote("xauusdm")

    assert result["status"]["connected"] is True
    assert broker._mt5.selected == ("XAUUSDm", True)
    assert result["quote"] == {
        "symbol": "XAUUSDm",
        "bid": 2301.25,
        "ask": 2301.55,
        "last": 2301.40,
        "time": 1,
        "time_msc": 1000,
    }
