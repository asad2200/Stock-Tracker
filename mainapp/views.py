from asgiref.sync import sync_to_async
from django.http.response import HttpResponse
from django.shortcuts import render
from yahoo_fin.stock_info import tickers_nifty50, get_quote_table
import queue
from threading import Thread

# Create your views here.


def stockpicker(request):
    all_stocks = tickers_nifty50()
    return render(request, 'mainapp/stockpicker.html', {'stocks': all_stocks})


@sync_to_async
def check_authenticated(request):
    if request.user.is_authenticated:
        return False
    else:
        return True


async def stocktracker(request):
    logged_in = check_authenticated(request)
    if not logged_in:
        return HttpResponse("Login First")

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

    return render(request, 'mainapp/stocktracker.html', {'data': data, 'room_name': 'track'})
