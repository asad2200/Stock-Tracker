from celery import shared_task
from yahoo_fin.stock_info import tickers_nifty50, get_quote_table
from threading import Thread
import queue


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
            {stocks[i]: get_quote_table(arg1)}), args=(que, stocks[i]))
        thread_list.append(thread)
        thread_list[i].start()

    for thread in thread_list:
        thread.join()

    while not que.empty():
        result = que.get()
        data.update(result)

    return 'Done'
