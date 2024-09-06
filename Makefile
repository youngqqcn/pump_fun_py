
start:
	nohup python3 -u ./bot/fanslandai_trade_bot.py > ./bot.log 2>&1 &


stop:
	@ps aux | grep 'python3 -u fanslandai_trade_bot.py' | grep -v grep  | awk '{print $$2}' | xargs kill