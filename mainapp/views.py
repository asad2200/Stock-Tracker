from django.http.response import HttpResponse
from django.shortcuts import render
from yahoo_fin.stock_info import tickers_nifty50, get_quote_table
import queue
from threading import Thread

# Create your views here.


def stockpicker(request):
    all_stocks = tickers_nifty50()
    return render(request, 'mainapp/stockpicker.html', {'stocks': all_stocks})


def stocktracker(request):
    stocks = request.GET.getlist("stockpicker")
    all_stocks = tickers_nifty50()
    data = {}

    for i in stocks:
        if i not in all_stocks:
            return HttpResponse("You have selected wrong stocks. do it again")

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

    # for i in stocks:
    #     result = get_quote_table(i)
    #     data.update({i: result})

    return render(request, 'mainapp/stocktracker.html', {'data': data})
