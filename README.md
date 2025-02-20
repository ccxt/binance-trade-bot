# Binance Trade Bot
> An automated cryptocurrency trading bot for Binance

## Author
Created by **Eden Gaon**

[![Twitter Follow](https://img.shields.io/twitter/url/https/twitter.com/cloudposse.svg?style=social&label=Follow%20%400xedeng)](https://twitter.com/shapeden)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?style=flat&logo=linkedin)](https://www.linkedin.com/in/eden-gaon-6956a219/)

## Project Status
[![GitHub Status](https://img.shields.io/github/workflow/status/edeng23/binance-trade-bot/binance-trade-bot?label=build)](https://github.com/edeng23/binance-trade-bot/actions)
[![Docker Pulls](https://img.shields.io/docker/pulls/edeng23/binance-trade-bot)](https://hub.docker.com/r/edeng23/binance-trade-bot)

## Quick Deploy
[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/edeng23/binance-trade-bot)
[![Deploy to DigitalOcean](https://mp-assets1.sfo2.digitaloceanspaces.com/deploy-to-do/do-btn-blue.svg)](https://cloud.digitalocean.com/apps/new?repo=https://github.com/coinbookbrasil/binance-trade-bot/tree/master&refcode=a076ff7a9a6a)

## Community
Join our growing community on Telegram to discuss strategies, get help, or just chat!

[![Telegram Chat](https://patrolavia.github.io/telegram-badge/chat.png)](https://t.me/binancetradebotchat)

#### Community Telegram Chat
https://t.me/binancetradebotchat

## Why?

This project was inspired by the observation that all cryptocurrencies pretty much behave in the same way. When one spikes, they all spike, and when one takes a dive, they all do. _Pretty much_. Moreover, all coins follow Bitcoin's lead; the difference is their phase offset.

So, if coins are basically oscillating with respect to each other, it seems smart to trade the rising coin for the falling coin, and then trade back when the ratio is reversed.

## How?

The trading is done in the Binance market platform, which of course, does not have markets for every altcoin pair. The workaround for this is to use a bridge currency that will complement missing pairs. The default bridge currency is Tether (USDT), which is stable by design and compatible with nearly every coin on the platform.

<p align="center">
  Coin A → USDT → Coin B
</p>

The way the bot takes advantage of the observed behaviour is to always downgrade from the "strong" coin to the "weak" coin, under the assumption that at some point the tables will turn. It will then return to the original coin, ultimately holding more of it than it did originally. This is done while taking into consideration the trading fees.

<div align="center">
  <p><b>Coin A</b> → USDT → Coin B</p>
  <p>Coin B → USDT → Coin C</p>
  <p>...</p>
  <p>Coin C → USDT → <b>Coin A</b></p>
</div>

The bot jumps between a configured set of coins on the condition that it does not return to a coin unless it is profitable in respect to the amount held last. This means that we will never end up having less of a certain coin. The risk is that one of the coins may freefall relative to the others all of a sudden, attracting our reverse greedy algorithm.

## Binance Setup

-   Create a [Binance account](https://accounts.binance.com/register?ref=PGDFCE46) (Includes my referral link, I'll be super grateful if you use it).
-   Enable Two-factor Authentication.
-   Create a new API key.
-   Get a cryptocurrency. If its symbol is not in the default list, add it.

## Tool Setup

### Install Python dependencies

Run the following line in the terminal: `pip install -r requirements.txt`.

### Create user configuration

Create a .cfg file named `user.cfg` based off `.user.cfg.example`, then add your API keys and current coin.

**The configuration file consists of the following fields:**

-   **api_key** - Binance API key generated in the Binance account setup stage.
-   **api_secret_key** - Binance secret key generated in the Binance account setup stage.
-   **current_coin** - This is your starting coin of choice. This should be one of the coins from your supported coin list. If you want to start from your bridge currency, leave this field empty - the bot will select a random coin from your supported coin list and buy it.
-   **bridge** - Your bridge currency of choice. Notice that different bridges will allow different sets of supported coins. For example, there may be a Binance particular-coin/USDT pair but no particular-coin/BUSD pair.
-   **tld** - 'com' or 'us', depending on your region. Default is 'com'.
-   **hourToKeepScoutHistory** - Controls how many hours of scouting values are kept in the database. After the amount of time specified has passed, the information will be deleted.
-   **scout_sleep_time** - Controls how many seconds are waited between each scout.
-   **use_margin** - 'yes' to use scout_margin. 'no' to use scout_multiplier.
-   **scout_multiplier** - Controls the value by which the difference between the current state of coin ratios and previous state of ratios is multiplied. For bigger values, the bot will wait for bigger margins to arrive before making a trade.
-   **scout_margin** - Minimum percentage coin gain per trade. 0.8 translates to a scout multiplier of 5 at 0.1% fee.
-   **strategy** - The trading strategy to use. See [`binance_trade_bot/strategies`](binance_trade_bot/strategies/README.md) for more information
-   **buy_timeout/sell_timeout** - Controls how many minutes to wait before cancelling a limit order (buy/sell) and returning to "scout" mode. 0 means that the order will never be cancelled prematurely.
-   **scout_sleep_time** - Controls how many seconds bot should wait between analysis of current prices. Since the bot now operates on websockets this value should be set to something low (like 1), the reasons to set it above 1 are when you observe high CPU usage by bot or you got api errors about requests weight limit.

#### Environment Variables

All of the options provided in `user.cfg` can also be configured using environment variables.

```
CURRENT_COIN_SYMBOL:
SUPPORTED_COIN_LIST: "XLM TRX ICX EOS IOTA ONT QTUM ETC ADA XMR DASH NEO ATOM DOGE VET BAT OMG BTT"
BRIDGE_SYMBOL: USDT
API_KEY: vmPUZE6mv9SD5VNHk4HlWFsOr6aKE2zvsw0MuIgwCIPy6utIco14y7Ju91duEh8A
API_SECRET_KEY: NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j
SCOUT_MULTIPLIER: 5
SCOUT_SLEEP_TIME: 1
TLD: com
STRATEGY: default
BUY_TIMEOUT: 0
SELL_TIMEOUT: 0
```

### Paying Fees with BNB
You can [use BNB to pay for any fees on the Binance platform](https://www.binance.com/en/support/faq/how-to-use-bnb-to-pay-for-fees-and-earn-25-discount-115000583311), which will reduce all fees by 25%. In order to support this benefit, the bot will always perform the following operations:
-   Automatically detect that you have BNB fee payment enabled.
-   Make sure that you have enough BNB in your account to pay the fee of the inspected trade.
-   Take into consideration the discount when calculating the trade threshold.

### Notifications with Apprise

Apprise allows the bot to send notifications to all of the most popular notification services available such as: Telegram, Discord, Slack, Amazon SNS, Gotify, etc.

To set this up you need to create a apprise.yml file in the config directory.

There is an example version of this file to get you started.

If you are interested in running a Telegram bot, more information can be found at [Telegram's official documentation](https://core.telegram.org/bots).

### Run

```shell
python -m binance_trade_bot
```

### Docker

The official image is available [here](https://hub.docker.com/r/edeng23/binance-trade-bot) and will update on every new change.

```shell
docker-compose up
```

If you only want to start the SQLite browser

```shell
docker-compose up -d sqlitebrowser
```

## Backtesting

You can test the bot on historic data to see how it performs.

```shell
python backtest.py
```

Feel free to modify that file to test and compare different settings and time periods

## Developing

To make sure your code is properly formatted before making a pull request,
remember to install [pre-commit](https://pre-commit.com/):

```shell
pip install pre-commit
pre-commit install
```

The scouting algorithm is unlikely to be changed. If you'd like to contribute an alternative
method, [add a new strategy](binance_trade_bot/strategies/README.md).

## Related Projects

Thanks to a group of talented developers, there is now a [Telegram bot for remotely managing this project](https://github.com/lorcalhost/BTB-manager-telegram).

## Support the Project

<a href="https://www.buymeacoffee.com/edeng" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>

## Join the Chat

-   **Discord**: [Invite Link](https://discord.gg/m4TNaxreCN)

## FAQ

A list of answers to what seem to be the most frequently asked questions can be found in our discord server, in the corresponding channel.

<p align="center">
  <img src = "https://usercontent2.hubstatic.com/6061829.jpg">
</p>

## Want to build a bot from scratch?

- Check out [CCXT](https://github.com/ccxt/ccxt)  for more than 100 crypto exchanges with a unified trading API.
- Check out [Python-Binance](https://github.com/sammchardy/python-binance) for a complete Python Wrapper.


## Disclaimer

This project is for informational purposes only. You should not construe any
such information or other material as legal, tax, investment, financial, or
other advice. Nothing contained here constitutes a solicitation, recommendation,
endorsement, or offer by me or any third party service provider to buy or sell
any securities or other financial instruments in this or in any other
jurisdiction in which such solicitation or offer would be unlawful under the
securities laws of such jurisdiction.

If you plan to use real money, USE AT YOUR OWN RISK.

Under no circumstances will I be held responsible or liable in any way for any
claims, damages, losses, expenses, costs, or liabilities whatsoever, including,
without limitation, any direct or indirect damages for loss of profits.
