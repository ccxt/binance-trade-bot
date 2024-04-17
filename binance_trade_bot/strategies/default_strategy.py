import random
import sys
from datetime import datetime
import concurrent.futures

from binance_trade_bot.auto_trader import AutoTrader


class Strategy(AutoTrader):
    def initialize(self):
        super().initialize()
        self.initialize_current_coin()

    def scout(self):
        """
        Scout for potential jumps from the current coin to another coin
        """
        with concurrent.futures.ThreadPoolExecutor() as executor:
            current_coin = self.db.get_current_coin()
            print(
                f"{datetime.now()} - CONSOLA - INFO - Estoy buscando los mejores intercambios. "
                f"Moneda actual: {current_coin + self.config.BRIDGE} ",
                end="\r",
            )
            
            future_price = executor.submit(self.manager.get_ticker_price, current_coin + self.config.BRIDGE)
            current_coin_price = future_price.result()
        
            if current_coin_price is None:
                self.logger.info(f"Skipping scouting... current coin {current_coin + self.config.BRIDGE} not found")
                return

            self._jump_to_best_coin(current_coin, current_coin_price)

    def bridge_scout(self):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            current_coin = self.db.get_current_coin()
            if self.manager.get_currency_balance(current_coin.symbol) > self.manager.get_min_notional(
                current_coin.symbol, self.config.BRIDGE.symbol
            ):
                return
            new_coin = super().bridge_scout()
            if new_coin is not None:
                future_set_coin = executor.submit(self.db.set_current_coin, new_coin)
                future_set_coin.result()  # Wait for the operation to complete.

    def initialize_current_coin(self):
        """
        Decide what is the current coin, and set it up in the DB.
        """
        if self.db.get_current_coin() is None:
            current_coin_symbol = self.config.CURRENT_COIN_SYMBOL
            if not current_coin_symbol:
                current_coin_symbol = random.choice(self.config.SUPPORTED_COIN_LIST)

            self.logger.info(f"Estableciendo moneda inicial en {current_coin_symbol}")

            if current_coin_symbol not in self.config.SUPPORTED_COIN_LIST:
                sys.exit("***\nERROR!\nSince there is no backup file, a proper coin name must be provided at init\n***")
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_set_initial_coin = executor.submit(self.db.set_current_coin, current_coin_symbol)
                future_set_initial_coin.result()  # Wait for the operation to complete.

            if self.config.CURRENT_COIN_SYMBOL == "":
                current_coin = self.db.get_current_coin()
                self.logger.info(f"Purchasing {current_coin} to begin trading")
                self.manager.buy_alt(current_coin, self.config.BRIDGE)
                self.logger.info("Ready to start trading")
