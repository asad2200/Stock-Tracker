import json
from os import name, remove
from re import S
from typing import KeysView
from celery.utils import objects
from channels.generic.websocket import AsyncWebsocketConsumer
from urllib.parse import parse_qs
from asgiref.sync import sync_to_async, async_to_sync
from django.utils.translation import get_supported_language_variant
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from .models import StockDetail
import copy


class StockConsumer(AsyncWebsocketConsumer):

    @sync_to_async
    def add_to_celery_beat(self, stockpicker):
        task = PeriodicTask.objects.filter(name="every-10-seconds")
        if len(task) > 0:
            task = task.first()
            args = json.loads(task.args)
            args = args[0]
            for i in stockpicker:
                if i not in args:
                    args.append(i)
            task.args = json.dumps([args])
            task.save()
        else:
            schedule, created = IntervalSchedule.objects.get_or_create(
                every=10, period=IntervalSchedule.SECONDS)
            task = PeriodicTask.objects.create(
                interval=schedule, name="every-10-seconds", task="mainapp.tasks.update_stock", args=json.dumps([stockpicker]))

    @sync_to_async
    def add_to_stockdetail(self, stockpicker):
        user = self.scope['user']
        for i in stockpicker:
            stock, created = StockDetail.objects.get_or_create(stock=i)
            stock.user.add(user)
            stock.save()

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = 'stock_%s' % self.room_name

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # Parse query_string
        query_params = parse_qs(self.scope['query_string'].decode())
        # print(querydictionary_params)
        stockpicker = query_params['stockpicker']

        # Add to celry beat
        await self.add_to_celery_beat(stockpicker)

        # Add user to stockdetail
        await self.add_to_stockdetail(stockpicker)

        await self.accept()

    @sync_to_async
    def remove_stocks(self):
        user = self.scope['user']
        stocks = StockDetail.objects.filter(user__id=user.id)
        task = PeriodicTask.objects.get(name="every-10-seconds")
        args = json.loads(task.args)
        args = args[0]

        for i in stocks:
            i.user.remove(user)
            if i.user.count() == 0:
                args.remove(i.stock)
                i.delete()

        if args == None:
            args = []

        if len(args) == 0:
            task.delete()
        else:
            task.args = json.dumps([args])
            task.save()

    async def disconnect(self, close_code):
        # remove stocks
        await self.remove_stocks()

        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'stock_update',
                'message': message
            }
        )

    @sync_to_async
    def get_user_stock(self):
        user = self.scope['user']
        user_stocks = user.stockdetail_set.values_list('stock', flat=True)
        return list(user_stocks)

    # Receive message from room group
    async def stock_update(self, event):
        message = event['message']
        message = copy.copy(message)

        user_stocks = await self.get_user_stock()
        keys = message.keys()

        for i in list(keys):
            if i not in user_stocks:
                del message[i]

        # Send message to WebSocket
        await self.send(text_data=json.dumps(message))
