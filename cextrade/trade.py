import cexio as cex
import time
import math
import argparse



DEFAULT_OUTPUT_FILEPATH = "cex_output.txt"
DEFAULT_MARKET = "BTC/USD"
CEX_FEES = 0.0025
BITCOIN_BALANCE = math.ceil(100/6550*math.pow(10, 8))/math.pow(10, 8)
DOLLAR_BALANCE = 0
DEFAULT_TIME_STEP = 5
DEFAULT_GAIN_THRESHOLD = 0.25


market = DEFAULT_MARKET.split("/")


def check_market_format(market):
    splitted = market.split("/")

    if len(splitted) != 2:
        raise TypeError("Market format should be of type 'BTC,EUR'")
    if len(splitted[0]) != 3 or len(splitted[0]) != 3:
        raise TypeError("Market format should be of type 'BTC,EUR'")
    return market


def net_after_fee(amount,  nb_digit_rounding=2, fee_rate=CEX_FEES):
    """
    Calculates the value minus the fee
    :param amount: Amount to trade
    :param nb_digit_rounding: 2 for fiat currencies, 8 for crypto
    :param fee_rate: fee rate NOT in percentage
    :return: The real value to be traded
    """
    shift_factor = math.pow(10, nb_digit_rounding)
    fee = math.ceil(amount * fee_rate * shift_factor) / shift_factor
    return amount - fee

def change_result(amount_to_sell, exchange_rate, base_currency_digit_nb,  quote_currency_digit_nb):
    """
    Result of a change, includig taxes and change rate
    :param amount_to_sell: Amount of the base
    :param exchange_rate: exchange rate
    :param base_currency_digit_nb: 2 for fiat currencies, 8 for crypto
    :param quote_currency_digit_nb: 2 for fiat currencies, 8 for crypto
    :return: The result in quoted currency
    """

    net_amount_to_sell = net_after_fee(amount_to_sell, base_currency_digit_nb)
    shift_factor = math.pow(10, quote_currency_digit_nb)
    change = math.floor(net_amount_to_sell*exchange_rate*shift_factor) / shift_factor
    return change


def change_result_fiat_to_cryp(amount_to_sell, exchange_rate):
    return change_result(amount_to_sell, 1/exchange_rate, 2,  8)


def change_result_cryp_to_fiat(amount_to_sell, exchange_rate):
    return change_result(amount_to_sell, exchange_rate, 8,  2)


def net_gain_rate(amount_to_sell, last_amount_sold, exchange_rate, base_currency_digit_nb,  quote_currency_digit_nb):
    """
    Returns the rate gain taking in account roundings and fees
    :param amount_to_sell: Amount of the base currency
    :param last_amount_sold: Amount of the quoted currency sold to get the base currency amount
    :param exchange_rate: current exchange_rate
    :param base_currency_digit_nb: 2 for fiat currencies, 8 for crypto
    :param quote_currency_digit_nb: 2 for fiat currencies, 8 for crypto
    :return: The gain rate in pc
    """
    changed = change_result(amount_to_sell, exchange_rate, base_currency_digit_nb, quote_currency_digit_nb)
    return 100 * (amount_to_sell - changed) / last_amount_sold


def net_gain_rate_fiat_to_cryp(amount_to_sell, last_amount_sold,  exchange_rate):
    """
    Returns the gain when I want to sell USD i bought with bitcoins
    :param amount_to_sell: Amount of dollars to sell
    :param last_amount_sold: Amount of bitcoins I needed to buy this dollars
    :param exchange_rate: current exchange rate USD/BTC
    :return: the gain rate in pc
    """
    changed = change_result_fiat_to_cryp(amount_to_sell, exchange_rate)
    return 100 * (changed - last_amount_sold) / last_amount_sold


def net_gain_rate_cryp_to_fiat(amount_to_sell, last_amount_sold,  exchange_rate):
    """
    Returns the gain when I want to sell BTC i bought with USD
    :param amount_to_sell: Amount of BTC to sell
    :param last_amount_sold: Amount of USD I needed to buy this dollars
    :param exchange_rate: current exchange rate BTC/USD
    :return: the gain rate in pc
    """
    changed = change_result_cryp_to_fiat(amount_to_sell, exchange_rate)
    return 100 * (changed - last_amount_sold) / last_amount_sold

# I previously sold 20$ to buy 0.00298925 BTC at rate 6670. rate is now 7000


def get_btc_usd_ask(cex_cli):
    ticker = cex_cli.ticker(market[0] + "/" + market[1])
    return ticker['ask']


def get_btc_usd_bid(cex_cli):
    ticker = cex_cli.ticker(market[0] + "/" + market[1])
    return ticker['bid']


def sell_btcs(cex_cli, amount_btc, btc_usd_rate):
    global BITCOIN_BALANCE
    global DOLLAR_BALANCE
    BITCOIN_BALANCE -= amount_btc
    DOLLAR_BALANCE += change_result_cryp_to_fiat(amount_btc, btc_usd_rate)


def buy_btcs(cex_cli, amount_usd, btc_usd_rate):
    global BITCOIN_BALANCE
    global DOLLAR_BALANCE
    DOLLAR_BALANCE -= amount_usd
    BITCOIN_BALANCE += change_result_fiat_to_cryp(amount_usd, btc_usd_rate)

cex_client = cex.Api("up103272129", "zv6NThLsvyqfOYrkpTLKgeqIwM", "F7uc46OlsC2TS6ROJDIqTKsGc")

# print(result)
# fbclient.send(fbchat.Message(text=str(balance)), fbclient.uid)

threshold_reached = False
#I have bitcoin because I sold 100 dollars
now_selling = True
last_buy_price_usd = 100
last_sell_amount_btc = 0

#
# if __name__ ==  '__main__':
#     parser = argparse.ArgumentParser()
#     parser.add_argument("-o", "--output-filepath", help="Output file path", default=DEFAULT_OUTPUT_FILEPATH)
#     parser.add_argument("-m", "--market", help="Market e.g. BTC/USD, BTC/EUR, XRP/GBP", type=check_market_format,
#                         default=DEFAULT_MARKET)
#     parser.add_argument("-q", "--quiet", help="No display of the results on screen. Only in the log file",
#                         action='store_true')
#     parser.add_argument("--fee", type=float, help="Set the fee applied by CEX", default=CEX_FEES)
#     parser.add_argument("--time-step", type=int, help="Set the time step between two quote request",
#                         default=DEFAULT_TIME_STEP)
#     parser.add_argument("-g", "--gain-threshold", type=float, help="gain percentage to trigger sell",
#                         default=DEFAULT_GAIN_THRESHOLD)
#     args = parser.parse_args()
#
#     market = args.market.split("/")
#
#
#
#     while True:
#         timestamp = time.strftime("%d/%m/%Y %H:%M:%S")
#         if now_selling:
#             # I want to sell my BTC
#             btc_usd_price = get_btc_usd_bid(cex_client)
#             net_gain = net_gain_rate_cryp_to_fiat(BITCOIN_BALANCE, last_buy_price_usd, btc_usd_price)
#             if threshold_reached:
#                 if net_gain < last_net_gain:
#                     sell_msg = "%s Selling %f %s at rate %f" % (timestamp, BITCOIN_BALANCE, market[0], btc_usd_price)
#                     with open(DEFAULT_OUTPUT_FILEPATH, "a") as output_file:
#                         print(sell_msg, file=output_file)
#                     if not args.quiet:
#                         print(sell_msg)
#                     last_sell_amount_btc = BITCOIN_BALANCE
#                     sell_btcs(cex_client, BITCOIN_BALANCE, btc_usd_price)
#                     now_selling = False
#                     threshold_reached = False
#             elif net_gain >= args.gain_threshold:
#                 threshold_msg = "%s %s threshold reached at rate %f net gain %f " % (timestamp, market[0], btc_usd_price, net_gain)
#                 with open(DEFAULT_OUTPUT_FILEPATH, "a") as output_file:
#                     print(threshold_msg, file=output_file)
#                 if not args.quiet:
#                     print(threshold_msg)
#                 threshold_reached = True
#             last_net_gain = net_gain
#         else:
#             # I want to buy BTC with my USD
#             btc_usd_price = get_btc_usd_ask(cex_client)
#             net_gain = net_gain_rate_fiat_to_cryp(DOLLAR_BALANCE, last_sell_amount_btc, btc_usd_price)
#             if threshold_reached:
#                 if net_gain < last_net_gain:
#                     sell_msg = "%s Selling %f %s at rate %f" % (timestamp, DOLLAR_BALANCE, market[1], btc_usd_price)
#                     with open(DEFAULT_OUTPUT_FILEPATH, "a") as output_file:
#                         print(sell_msg, file=output_file)
#                     if not args.quiet:
#                         print(sell_msg)
#                     last_buy_price_usd = DOLLAR_BALANCE
#                     buy_btcs(cex_client, DOLLAR_BALANCE, btc_usd_price)
#                     now_selling = True
#                     threshold_reached = False
#             elif net_gain >= args.gain_threshold:
#                 threshold_msg = "%s %s threshold reached at rate %f net gain %f" % (timestamp, market[1], btc_usd_price, net_gain)
#                 with open(DEFAULT_OUTPUT_FILEPATH, "a") as output_file:
#                     print(threshold_msg, file=output_file)
#                 if not args.quiet:
#                     print(threshold_msg)
#                 threshold_reached = True
#             last_net_gain = net_gain
#
#         std_msg = "%s Balance is %f %s %f %s. Rate is %f. Net gain is %f" % \
#                   (timestamp, BITCOIN_BALANCE, market[0], DOLLAR_BALANCE, market[1], btc_usd_price, net_gain)
#         with open(DEFAULT_OUTPUT_FILEPATH, "a") as output_file:
#             print(std_msg, file=output_file)
#         if not args.quiet:
#             print(std_msg)
#
#         time.sleep(args.time_step)
