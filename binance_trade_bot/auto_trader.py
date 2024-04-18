from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

from sqlalchemy.orm import Session

from .binance_api_manager import BinanceAPIManager
from .config import Config
from .database import Database
from .logger import Logger
from .models import Coin, CoinValue, Pair

class AutoTrader:
    def __init__(self, binance_manager: BinanceAPIManager, database: Database, logger: Logger, config: Config):
        self.manager = binance_manager
        self.db = database
        self.logger = logger
        self.config = config

    def initialize(self):
        self.initialize_trade_thresholds()

    def transaction_through_bridge(self, pair: Pair):
        """
        Salta de la moneda de origen a la moneda de destino a través de la moneda puente
        """
        can_sell = False
        balance = self.manager.get_currency_balance(pair.from_coin.symbol)
        from_coin_price = self.manager.get_ticker_price(pair.from_coin + self.config.BRIDGE)

        if balance and balance * from_coin_price > self.manager.get_min_notional(
            pair.from_coin.symbol, self.config.BRIDGE.symbol
        ):
            can_sell = True
        else:
            self.logger.info("Saltando venta")

        if can_sell and self.manager.sell_alt(pair.from_coin, self.config.BRIDGE) is None:
            self.logger.info("No se pudo vender, volviendo al modo de exploración...")
            return None

        result = self.manager.buy_alt(pair.to_coin, self.config.BRIDGE)
        if result is not None:
            self.db.set_current_coin(pair.to_coin)
            self.update_trade_threshold(pair.to_coin, result.price)
            return result

        self.logger.info("No se pudo comprar, volviendo al modo de exploración...")
        return None

    def update_trade_threshold(self, coin: Coin, coin_price: float):
        """
        Actualiza todas las monedas con el umbral de compra de la moneda actualmente retenida
        """

        if coin_price is None:
            self.logger.info(f"Saltando actualización... moneda actual {coin + self.config.BRIDGE} no encontrada")
            return

        session: Session
        with self.db.db_session() as session:
            for pair in session.query(Pair).filter(Pair.to_coin == coin):
                from_coin_price = self.manager.get_ticker_price(pair.from_coin + self.config.BRIDGE)

                if from_coin_price is None:
                    self.logger.info(f"Saltando actualización para moneda {pair.from_coin + self.config.BRIDGE} no encontrada")
                    continue

                pair.ratio = from_coin_price / coin_price

    def initialize_trade_thresholds(self):
        session: Session
        with self.db.db_session() as session:
            pairs = session.query(Pair).filter(Pair.ratio.is_(None)).all()
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(self._initialize_single_pair, pair) for pair in pairs]
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        self.logger.info(result)

    def _initialize_single_pair(self, pair: Pair):
        if not pair.from_coin.enabled or not pair.to_coin.enabled:
            return f"Saltando inicialización de {pair.from_coin} vs {pair.to_coin} por estar deshabilitadas"
        from_coin_price = self.manager.get_ticker_price(pair.from_coin + self.config.BRIDGE)
        if from_coin_price is None:
            return f"Saltando inicialización, símbolo {pair.from_coin + self.config.BRIDGE} no encontrado"
        to_coin_price = self.manager.get_ticker_price(pair.to_coin + self.config.BRIDGE)
        if to_coin_price is None:
            return f"Saltando inicialización, símbolo {pair.to_coin + self.config.BRIDGE} no encontrado"
        pair.ratio = from_coin_price / to_coin_price
        return f"Inicializado {pair.from_coin} vs {pair.to_coin} con ratio {pair.ratio}"

    def scout(self):
        """
        Busca posibles saltos desde la moneda actual a otra moneda
        """
        raise NotImplementedError()

    def _get_ratios(self, coin: Coin, coin_price):
        """
        Dada una moneda, obtén la proporción de precio actual para cada otra moneda habilitada
        """
        ratio_dict: Dict[Pair, float] = {}

        for pair in self.db.get_pairs_from(coin):
            optional_coin_price = self.manager.get_ticker_price(pair.to_coin + self.config.BRIDGE)

            if optional_coin_price is None:
                self.logger.info(f"Saltando exploración... moneda opcional {pair.to_coin + self.config.BRIDGE} no encontrada")
                continue

            self.db.log_scout(pair, pair.ratio, coin_price, optional_coin_price)

            # Obtener (moneda actual)/(moneda opcional)
            coin_opt_coin_ratio = coin_price / optional_coin_price

            # Comisiones
            from_fee = self.manager.get_fee(pair.from_coin, self.config.BRIDGE, True)
            to_fee = self.manager.get_fee(pair.to_coin, self.config.BRIDGE, False)
            transaction_fee = from_fee + to_fee - from_fee * to_fee

            if self.config.USE_MARGIN == "yes":
                ratio_dict[pair] = (
                    (1 - transaction_fee) * coin_opt_coin_ratio / pair.ratio - 1 - self.config.SCOUT_MARGIN / 100
                )
            else:
                ratio_dict[pair] = (
                    coin_opt_coin_ratio - transaction_fee * self.config.SCOUT_MULTIPLIER * coin_opt_coin_ratio
                ) - pair.ratio
        return ratio_dict

    def _jump_to_best_coin(self, coin: Coin, coin_price: float):
        """
        Dada una moneda, busca una moneda a la cual saltar
        """
        ratio_dict = self._get_ratios(coin, coin_price)

        # mantener solo las proporciones mayores que cero
        ratio_dict = {k: v for k, v in ratio_dict.items() if v > 0}

        # si tenemos opciones viables, elegir la que tenga la mayor proporción
        if ratio_dict:
            best_pair = max(ratio_dict, key=ratio_dict.get)
            self.logger.info(f"Se saltará de {coin} a {best_pair.to_coin_id}")
            self.transaction_through_bridge(best_pair)

    def bridge_scout(self):
        """
        Si tenemos alguna moneda puente sobrante, comprar una moneda con ella que no vayamos a intercambiar inmediatamente
        """
        bridge_balance = self.manager.get_currency_balance(self.config.BRIDGE.symbol)

        for coin in self.db.get_coins():
            current_coin_price = self.manager.get_ticker_price(coin + self.config.BRIDGE)

            if current_coin_price is None:
                continue

            ratio_dict = self._get_ratios(coin, current_coin_price)
            if not any(v > 0 for v in ratio_dict.values()):
                # Solo habrá una moneda donde todas las proporciones sean negativas. Cuando la encontremos, la compramos si podemos
                if bridge_balance > self.manager.get_min_notional(coin.symbol, self.config.BRIDGE.symbol):
                    self.logger.info(f"Se comprará {coin} utilizando moneda puente")
                    self.manager.buy_alt(coin, self.config.BRIDGE)
                    return coin
        return None

    def update_values(self):
        now = datetime.now()
        session: Session
        with self.db.db_session() as session:
            coins = session.query(Coin).all()
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(self._update_single_coin, coin, now) for coin in coins if self.manager.get_currency_balance(coin.symbol) != 0]
                results = [future.result() for future in as_completed(futures)]
                for result in results:
                    if result:
                        self.db.send_update(result)

    def _update_single_coin(self, coin: Coin, now: datetime):
        balance = self.manager.get_currency_balance(coin.symbol)
        if balance == 0:
            return None
        usd_value = self.manager.get_ticker_price(coin + "USDT")
        btc_value = self.manager.get_ticker_price(coin + "BTC")
        cv = CoinValue(coin, balance, usd_value, btc_value, datetime=now)
        return cv
