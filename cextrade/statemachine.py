
#!/bin/python3.6
from cextrade.trade import net_gain_rate_cryp_to_fiat, net_gain_rate_fiat_to_cryp
import time
import cexio
from threading import Thread
import argparse
import sys

output_file = sys.stdout

def frmt_print(string):
    print(time.strftime("%d/%m/%Y %H:%M:%S") + " : " + string, file=output_file, flush=True)


def selling_state_message(amount_cryp, rate, market, net_gain, state_name="SellingState"):
    crypt_cur = market.split("/")[0]
    tmstp = time.strftime("%d/%m/%Y %H:%M:%S")
    return "%s : %s. Now selling %.8f%s at rate %f. Gain is %f" %\
           (tmstp, state_name, amount_cryp, crypt_cur, rate, net_gain)


def buying_state_message(amount_fiat, rate, market, net_gain, state_name="BuyingState"):
    crypt_cur = market.split("/")[0]
    fiat_cur = market.split("/")[1]
    tmstp = time.strftime("%d/%m/%Y %H:%M:%S")
    return "%s : %s. Now buying %s currency for an amount of %.2f%s at rate %f. Gain is %f" %\
           (tmstp, state_name, crypt_cur,amount_fiat, fiat_cur, rate, net_gain)


class State:
    def __init__(self, context):
        self.context = context

    def run(self):
        assert 0, "run not implemented"

    def next(self):
        assert 0, "next not implemented"


class StateMachine:
    def __init__(self, initial_state, timestep=6):
        self.currentState = initial_state
        self.timestep =timestep
        self.currentState.run()

    def run_all(self):
        while True:
            self.set_ask_bid()
            self.set_net_gain()
            self.currentState.run()
            self.currentState = self.currentState.next()
            time.sleep(self.timestep)


class InitialState(State):
    def run(self):
        print(self.context.current_state_message("InitialState"), file=output_file, flush=True)
        self.context.set_balance()
        self.context.set_ask_bid()
        if self.context.now_selling_cryp:
            print("Start by Selling Cryp", file=output_file, flush=True)
        else:
            print("Start by Buying Cryp", file=output_file, flush=True)

    def next(self):
        if self.context.now_selling_cryp:
            return self.context.initial_cryp_sell_state
        else:
            if self.context.first_buy_flag:
                return self.context.buying_state
            return self.context.initial_cryp_buy_state


class InitialCrypSellState(State):
    def run(self):
        print(self.context.current_state_message("InitialCrypSellState"), file=output_file, flush=True)
        self.context.set_time_step(self.context.time_step)

    def next(self):
        if self.context.net_gain >= self.context.first_threshold_gain:
            return self.context.first_threshold_sell_state
        return self.context.initial_cryp_sell_state


class InitialCrypBuyState(State):
    def run(self):
        print(self.context.current_state_message("InitialCrypBuyState"), file=output_file, flush=True)
        self.context.set_time_step(self.context.time_step)

    def next(self):
        if self.context.net_gain >= self.context.first_threshold_gain:
            return self.context.first_threshold_buy_state
        return self.context.initial_cryp_buy_state


class FirstThresholdSellState(State):
    def run(self):
        print(self.context.current_state_message("FirstThresholdSellState"), file=output_file, flush=True)

    def next(self):
        if self.context.net_gain < self.context.first_threshold_gain:
            return self.context.initial_cryp_sell_state
        if self.context.net_gain < self.context.previous_net_gain:
            self.context.set_time_step(self.context.time_step)
            return self.context.selling_state
        return self.context.first_threshold_sell_state


class FirstThresholdBuyState(State):
    def run(self):
        print(self.context.current_state_message("FirstThresholdBuyState"), file=output_file, flush=True)

    def next(self):
        if self.context.net_gain < self.context.first_threshold_gain:
            return self.context.initial_cryp_buy_state
        if self.context.net_gain < self.context.previous_net_gain:
            self.context.set_time_step(self.context.time_step)
            return self.context.buying_state
        return self.context.first_threshold_buy_state


class SellingState(State):
    def run(self):
        print(self.context.current_state_message("SellingState"), file=output_file)
        print(selling_state_message(self.context.cryp_balance, self.context.cryp_fiat_bid, self.context.market,
                                    self.context.net_gain), file=output_file, flush=True)
        ret = self.context.sell_cryp(self.context.cryp_balance, self.context.cryp_fiat_bid, flush=True)
        self.context.set_balance()
        self.context.set_previous()
        if ret:
            self.context.set_buy_mode()
        else:
            self.context.set_sell_mode()

    def next(self):
        return self.context.initial_cryp_buy_state


class BuyingState(State):
    def run(self):
        print(self.context.current_state_message("BuyingState"), file=output_file, flush=True)
        print(buying_state_message(self.context.fiat_balance, self.context.cryp_fiat_ask, self.context.market,
                                   self.context.net_gain), file=output_file, flush=True)
        ret = self.context.buy_cryp(self.context.fiat_balance*0.95, self.context.cryp_fiat_ask)
        self.context.set_balance()
        self.context.set_previous()
        self.context.first_buy_flag = False

        if ret:
            self.context.set_sell_mode()
        else:
            self.context.set_buy_mode()

    def next(self):
        return self.context.initial_state


class TradingStateMachine(StateMachine, Thread):

    def __init__(self, cex_client, market, time_step=6, first_threshold_gain=0.7, time_step_sell=0.25):
        self.first_threshold_gain = first_threshold_gain
        self.time_step_sell = time_step_sell

        self.now_selling_cryp = False
        self.cex_client = cex_client
        self.market = market

        self.crypt_cur = self.market.split("/")[0]
        self.fiat_cur = self.market.split("/")[1]
        self.net_gain = 0
        self.previous_net_gain = 0

        self.last_buy_price_fiat = 1
        self.last_buy_amount_cryp = 1

        self.last_sell_amount_cryp = 1
        self.last_sell_income_fiat = 1

        self.balance = self.cex_client.balance
        self.cryp_balance = float(self.balance[self.crypt_cur]['available'])
        self.fiat_balance = float(self.balance[self.fiat_cur]['available'])

        self.cryp_fiat_ask = 0
        self.cryp_fiat_bid = 0

        self.first_buy_flag = False

        self.time_step = time_step

        self.initial_state = InitialState(self)
        self.initial_cryp_sell_state = InitialCrypSellState(self)
        self.initial_cryp_buy_state = InitialCrypBuyState(self)
        self.first_threshold_sell_state = FirstThresholdSellState(self)
        self.selling_state = SellingState(self)
        self.buying_state = BuyingState(self)
        self.initial_cryp_buy_state = InitialCrypBuyState(self)
        self.first_threshold_buy_state = FirstThresholdBuyState(self)

        self.set_previous()
        self.set_balance()
        self.set_ask_bid()

        StateMachine.__init__(self, self.initial_state, time_step)
        Thread.__init__(self)

    def current_state_message(self, state_name):
        tmstp = time.strftime("%d/%m/%Y %H:%M:%S")

        return "%s : %s : %s. Balance is %.8f%s/%.2f%s. Prices are %.8f/%.8f. Gain is %f" % \
               (tmstp, self.market, state_name, self.cryp_balance, self.crypt_cur, self.fiat_balance, self.fiat_cur,
                self.cryp_fiat_ask,
                self.cryp_fiat_bid, self.net_gain)

    def set_ask_bid(self):
        ticker = self.cex_client.ticker(self.market)
        self.cryp_fiat_ask = ticker['ask']
        self.cryp_fiat_bid = ticker['bid']

    def set_net_gain(self):
        self.previous_net_gain = self.net_gain
        if self.now_selling_cryp:
            # Now I sell, this means that I bought before
            # So I want to know what would be the gain if I sold the cryp I bought
            self.net_gain = net_gain_rate_cryp_to_fiat(self.last_buy_amount_cryp, self.last_buy_price_fiat,
                                                       self.cryp_fiat_bid)
        else:
            # Now I buy, this means that I sold before
            # So I want to know what would be the gain if I bought crypt with the income of my last sell
            self.net_gain = net_gain_rate_fiat_to_cryp(self.last_sell_income_fiat, self.last_sell_amount_cryp,
                                                       self.cryp_fiat_ask)

    def set_balance(self):
        balance = self.cex_client.balance
        self.cryp_balance = float(balance[self.crypt_cur]['available'])
        self.fiat_balance = float(balance[self.fiat_cur]['available'])

    def set_previous(self):

        last_orders = self.cex_client.api_call('archived_orders', None, self.market)

        last_buys = [order for order in last_orders if order['type'] == 'buy']
        last_sells = [order for order in last_orders if order['type'] == 'sell']

        # If not buy has been made yet buy directly
        if len(last_buys) == 0:
            self.last_buy_price_fiat = 99
            self.last_buy_amount_cryp = 99
            self.last_sell_income_fiat = 99
            self.last_sell_amount_cryp = 99
            self.first_buy_flag = True
            self.set_buy_mode()
            return

        # If we are there there's at least been one buy
        last_buy = last_buys[0]
        self.last_buy_amount_cryp = float(last_buy['amount'])
        if "tta:" + self.fiat_cur in last_buy:
            self.last_buy_price_fiat = float(last_buy["tta:" + self.fiat_cur])
        else:
            self.last_buy_price_fiat = float(last_buy["ta:" + self.fiat_cur])

        # If no sells has been made let's consider that the last sell brought the the whole fiat balance
        # at the current price
        if len(last_sells) == 0:
            self.last_sell_income_fiat = self.fiat_balance
            self.last_sell_amount_cryp = self.fiat_balance / self.cryp_fiat_bid
        else:
            last_sell = last_sells[0]

            self.last_sell_amount_cryp = float(last_sell['amount'])
            if "tta:" + self.fiat_cur in last_sell:
                self.last_sell_income_fiat = float(last_sell["tta:" + self.fiat_cur])
            else:
                self.last_sell_income_fiat = float(last_sell["ta:" + self.fiat_cur])

        last_order_type = last_orders[0]['type']

        if last_order_type == 'buy':
            self.set_sell_mode()
        else:
            self.set_buy_mode()

    def set_time_step(self, value):
        self.time_step = value

    def sell_cryp(self, amount, rate):
        ret = self.cex_client.sell_limit_order(amount, rate, self.market)
        print(ret, file=output_file, flush=True)
        if 'error' in ret:
            return False
        # print("Now selling", amount, "at rate", rate, "on maket", self.market)
        self.last_sell_amount_cryp = amount
        return True

    def buy_cryp(self, price_fiat, rate):
        ret = self.cex_client.buy_limit_order(float(price_fiat/rate), rate, self.market)
        print(ret, file=output_file, flush=True)
        if 'error' in ret:
            return False
        # print("Now buying", price_fiat/rate, "at rate", rate, "on market", self.market)
        self.last_buy_price_fiat = price_fiat
        return True

    def set_sell_mode(self):
        self.now_selling_cryp = True

    def set_buy_mode(self):
        self.now_selling_cryp = False

    def run(self):
        self.run_all()


def main():
    global output_file

    parser = argparse.ArgumentParser(description="Run a crypto currency state machine based "
                                                 "on a small variation strategy")

    parser.add_argument('currency_pair',metavar="CUR_PAIR", help="Currency pair e.g. 'BTC/USD'. Check cex.io website to"
                                                                 "know which are available")
    parser.add_argument("--output", type=argparse.FileType('a'), metavar='OUTPUT_PATH',
                        help="Output path. Default is stdout.", default=sys.stdout)
    parser.add_argument("--timestep", type=int, metavar="STEP", default=10,
                        help="time step in seconds between 2 states switch computation. Default is 10.")
    parser.add_argument("--gain-threshold", type=float, metavar="GAIN", default=0.35,
                        help="gain threshold (in percentage) to start sellling or buying. Default is 0.35%")

    args = parser.parse_args()
    output_file = args.output
    cex_client = cexio.Api("up103272129", "zv6NThLsvyqfOYrkpTLKgeqIwM", "F7uc46OlsC2TS6ROJDIqTKsGc")
    machines = list()
    machines.append(TradingStateMachine(cex_client, args.currency_pair, args.timestep,
                                        first_threshold_gain=args.gain_threshold))

    for machine in machines:
        machine.start()
        time.sleep(1)


if __name__ == "__main__":
    main()
