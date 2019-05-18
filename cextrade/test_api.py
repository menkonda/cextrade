import cexio
import statistics
import time
import time
from datetime import date

def count_means_crossing(float_list):
    mean = statistics.mean(float_list)
    count = 0

    if float_list[0] <= mean:
        under = True
    else:
        under = False

    for val in float_list[1:]:
        if val > mean and under:
            count += 1
            under = False
        if val <= mean and not under:
            count += 1
            under = True

    return count


cex_client = cexio.Api("up103272129", "zv6NThLsvyqfOYrkpTLKgeqIwM", "F7uc46OlsC2TS6ROJDIqTKsGc")

cryp_list = ['BTC', 'XRP', 'ETH', 'BCH', 'BTG', 'DASH', 'LTC', 'XLM', 'ZEC' ]

# result = cex_client.api_call('archived_orders', None, "BTC/USD")
# balance_btc = float(cex_client.balance['XRP']['available'])
# print(balance_btc)
# tick = cex_client.ticker('XRP/USD')
# print(tick)
# xrp_amount = balance_btc / price * 0,9

# result = cex_client.api_call('archived_orders', None, "XRP/USD")
# last_order = result[2]
# last_order_type = last_order['type']
# if last_order_type == 'sell':
#     msg = ('last_sold_amount_cryp = ' + last_order['amount'])
# else:
#     msg = ('last_buy_price_fiat = ' + last_order['amount'])
# print(msg)


l = [1,2,3,4,5,6,5,5,3,3,1,0 ]

print(count_means_crossing(l))

for cryp in cryp_list:
    result = cex_client.api_call('price_stats', {"lastHours": 24,"maxRespArrSize": 119}, cryp + "/USD")
    # print(result)
    prices = [float(elem['price']) for elem in result]

    mean = statistics.mean(prices)
    stdev = statistics.stdev(prices)
    relative_stdev = stdev/mean
    evolution = (prices[-1] - prices[0])/prices[0]
    crossings = count_means_crossing(prices)
    coeff = crossings * relative_stdev / evolution
    

    print("Currency:", cryp)
    print("\tMean :", mean)
    print("\tStandard deviation :", stdev)
    print("\tRelative standard deviation :", relative_stdev)
    print("\tPrice evol. :", evolution)
    print("\tNr of crossings :", crossings)
    print("\tMagic coeff. :", coeff)

    time.sleep(2)