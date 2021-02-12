# Simple-Binance-Backtester

## Description
This repository holds code created for a simple back tester that can be used to test strategies over historic candles, You will also be able to export the tested strategy into the Simple-Binance-Trader for real-time testing.

### NOTE
This backtester is used to easily create/test stratergies that can then easily be migrated over to the trader part of this tool: https://github.com/EasyAI/Simple-Binance-Trader

### Repository Contains:
TO-DO
  
## Usage
I recommend setting this all up within a virtual python enviornment:
First get the base modules:
 - To quickly install all the required modules use 'pip3 install -r requirements'.

Secondly get the required techinal indicators module adn binance api.
 - https://github.com/EasyAI/binance_api, This is the binance API that the trader uses.
 - https://github.com/EasyAI/Python-Charting-Indicators, This contains the logic to calculate technical indicators. (only the file technical_indicators.py is needed)

Move them into the site-packages folder. NOTE: If you get an error saying that either the technical_indicators or binance_api is not found you can move them in to the same directory as the run.py file for the trader.

To pull candle data you wish to test use: 
  python run.py pull -s \[SYMBOL\] -i \[INTERVAL\] -l \[CANDLE_LIMIT\]
example: python run.py pull -s "EUR-BTC" -i 5m -l 100000

Then to run the test use:
  python run.py test -ds \[FILE_NAME\] -l \[CANDLE_LIMIT\]
example: python run.py test -ds "candles_5m_BTCEUR.json" -l 10000

To run on live data you can use the following:
  python run.py test -ds live -i \[INTERVAL\] -s \[SYMBOL\] -l \[CANDLE_LIMIT\]
example: python run.py test -ds live -i 1m -s BTC-LTC -l 1000




Then navigate to the web ui and it should load a chart showing buy/sell points in a visual display however this does need some work.

### Contact
Please if you find any bugs or issues contact me so I can improve.
EMAIL: jlennie1996@gmail.com

