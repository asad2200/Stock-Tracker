from celery import shared_task
from yahoo_fin.stock_info import tickers_nifty50, get_quote_table
from threading import Thread
from channels.layers import get_channel_layer
import asyncio
import queue
import simplejson


@shared_task(bind=True)
def update_stock(self, stocks):
    all_stocks = tickers_nifty50()
    data = {}

    for i in stocks:
        if i not in all_stocks:
            stocks.remove(i)

    n_threads = len(stocks)
    thread_list = []
    que = queue.Queue()
    for i in range(n_threads):
        thread = Thread(target=lambda q, arg1: q.put(
            {stocks[i]: simplejson.loads(simplejson.dumps(get_quote_table(arg1), ignore_nan=True))}), args=(que, stocks[i]))
        thread_list.append(thread)
        thread_list[i].start()

    for thread in thread_list:
        thread.join()

    while not que.empty():
        result = que.get()
        data.update(result)

    # send data to group
    channel_layer = get_channel_layer()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.run_until_complete(channel_layer.group_send("stock_track", {
        'type':  'stock_update',
        'message': data,
    }))

    return 'Done'
