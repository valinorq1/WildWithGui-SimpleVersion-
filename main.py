# -*- coding: utf-8 -*-
import time
import os
import sys
import datetime
import threading
from threading import Timer
import csv
import re


from PyQt5.QtWidgets import QFileDialog
from PyQt5 import QtWidgets
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize, QTimer, QTime
import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup


from ui import Ui_Dialog
#from utils import *





products_data = []


class WildParser(QtWidgets.QMainWindow):
    def __init__(self):
        super(WildParser, self).__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.init_UI()

    def init_UI(self):
        self.setWindowIcon(QIcon('mail.png'))
        self.ui.start_parse.clicked.connect(self.start_work)
        #  self.ui.start_parse.hide()
        self.ui.stop_parse.clicked.connect(lambda:self.start_work(stop=True))
        self.ui.stop_parse.hide()
        self.ui.work_text_status.setText("<font color='black'>Ожидаем работы</font>")





    def normalize_url(self, url):
        if '?xsubject=94' in url:
            return url

        elif '?' in url:
            return '-'.join(url.split('?')[:-1])
        else:
            return url

    async def fetch_content(self, url, session):
        async with session.get(url) as respone:
            product_html = await respone.text()
            await self.parse_selected_product_data(product_html)


    def get_selected_option_from_check_box(self):
        selected_option_list = {'parse_full_name': self.ui.full_name.isChecked(),
                                'parse_brand': self.ui.brand.isChecked(),
                                'parse_current_price': self.ui.current_price.isChecked(),
                                'parse_default_price': self.ui.default_price.isChecked(),
                                'parse_articul': self.ui.articul.isChecked(),
                                'parse_rating': self.ui.rating.isChecked(),
                                'parse_seller': self.ui.seller.isChecked(),
                                'parse_link': self.ui.url_to_product.isChecked()
                                }

        print(selected_option_list)
        return selected_option_list

    async def parser(self, main_url, stop):
        url = self.normalize_url(main_url)  # приводим ссылку к нормальному виду
        total_page = self.get_total_page(url)  # считаем кол-во страниц
        all_product_link = self.parse_all_product_link(url, total_page)  #  спарсили все ссылки на товары
        tasks = []
        async with aiohttp.ClientSession() as session:
            for url in all_product_link:
                if stop():
                    break
                task = asyncio.create_task(self.fetch_content(url, session))
                tasks.append(task)
            await asyncio.gather(*tasks)

    def get_total_page(self, url):
        """
            Фукнция в тупую берет максимальное коль-во страниц с выбранным товаром и начинает считать кол-во страниц
        """
        self.ui.work_text_status.setText("<font color='blue'>Считаем кол-во страниц</font>")
        s = requests.Session()
        get_page = s.get(url + '?page=1')
        page_count = 0
        if 'pagination-next' in get_page.text:
            i = 1
            while i <= 5000:
                get_next_page = s.get(url + '?page={}'.format(i))
                page_count += 1
                i += 1

                if 'dtList-inner' not in get_next_page.text:
                    break

            return page_count - 1
        else:
            page_count = 1
            return page_count

    def parse_all_product_link(self, url, page_count):
        self.ui.work_text_status.setText("<font color='blue'>Собираем ссылки на страницы товаров</font>")
        base_url = 'https://www.wildberries.ru'
        products_link = []
        """
            - Функция работает с базовым урлом на страницу с нужными товарами + {page}
            - Коротко говоря, просто считает сколько страниц с выбранным товаром есть
        """
        s = requests.Session()

        if page_count > 1:
            for i in range(1, page_count + 1):
                html = s.get(url + f'?page={i}')
                soup = BeautifulSoup(html.text, 'lxml')
                all_product_link = soup.find_all('div', {'class': 'dtList-inner'})
                for k in all_product_link:
                    products_link.append(base_url + k.span.span.a.get('href'))

            return products_link
        else:
            html = requests.get(url)
            soup = BeautifulSoup(html.text, 'lxml')
            all_product_link = soup.find_all('div', {'class': 'dtList-inner'})
            for i in all_product_link:
                products_link.append(base_url + i.span.span.a.get('href'))

            return products_link

    async def parse_selected_product_data(self, product_url):
        self.ui.work_text_status.setText("<font color='blue'>Собираем детальную информацию о товарах</font>")
        """
        Функция скрапинга информации о товаре
        Переходим по ссылке - парсим данные - записываем в cловарь
        """

        soup = BeautifulSoup(product_url, 'lxml')
        product_detailt_page = soup.find_all('div', {'class': 'product-content-v1'})

        for child in product_detailt_page:
            try:
                full_name = child.find(class_='brand-and-name').get_text().strip().encode('ascii', 'ignore').decode(
                    encoding="utf-8")
            except AttributeError:
                full_name = ''
            try:
                brand = child.find(class_='brand').get_text().strip().encode('ascii', 'ignore').decode(encoding="utf-8")
            except AttributeError:
                brand = ''
            try:
                current_price = child.find(class_='final-cost').get_text().strip().encode('ascii', 'ignore').decode(
                    encoding="utf-8")
            except AttributeError:
                current_price = ''
            try:
                default_price = child.find(class_='c-text-base').get_text().strip().encode('ascii', 'ignore').decode(
                    encoding="utf-8")
            except AttributeError:
                default_price = ''

            try:
                articul = child.find(class_='article').get_text().strip().encode('ascii', 'ignore').decode(
                    encoding="utf-8")
            except AttributeError:
                articul = ''

            try:
                rating = child.find(class_='stars-line-lg').get_text().strip().encode('ascii', 'ignore').decode(
                    encoding="utf-8")
            except AttributeError:
                rating = ''

            data = {'full_name': full_name, 'brand': brand, 'current_price': current_price,
                    'default_price': default_price
                    }  # 'url': base_url + product_url
            products_data.append(data)
            #  update GUI data
            total_product = self.ui.total_product_parsed.text()
            total_product = int(total_product)
            total_product += 1
            self.ui.total_product_parsed.setText(str(total_product))
            print(data)

    def clear_string(self, string):  # В основном только для того, что удать знак "рубль" из строки "цена"
        return re.sub(r'\D', '', string)

    def write_csv(self, data):
        with open('result.csv', 'a') as f:
            fields = ['full_name', 'brand', 'current_price', 'default_price']  # , 'url'
            writer = csv.DictWriter(f, fieldnames=fields)
            for product in data:
                writer.writerow(product)


    def main(self, stop):
        start = datetime.datetime.now().replace(microsecond=0)
        self.ui.work_text_status.setText("<font color='green'>Получаем информацию о товарах</font>")
        asyncio.run(self.parser(self.ui.url_to_parse.text(), stop))
        end = datetime.datetime.now().replace(microsecond=0)
        self.ui.work_text_status.setText(f"<font color='green'>Завершили!</span> времени ушло: {end - start}")
        #self.ui.stop_parse.hide()
        self.write_csv(products_data)

        #self.ui.saving_info.setText("<font color='blue'>Сохранили файл в папку с программой</font>")
        #self.ui.start_parse.show()


    def stop(self):
        return True


    def start_work(self, stop=False):
        global stop_parsing
        if stop == True:
            stop_parsing = True
            self.ui.start_parse.setEnabled(True)
            self.ui.start_parse.show()
        else:
            self.ui.total_product_parsed.setText('0')
            self.ui.start_parse.hide()
            self.ui.stop_parse.show()
            stop_parsing = False
            parser_thread = threading.Thread(target=self.main, name='parse_thread', args=(lambda: stop_parsing,))
            parser_thread.daemon = True
            parser_thread.start()

app = QtWidgets.QApplication([])
if __name__ == "__main__":

    application = WildParser()
    application.setMaximumSize(506, 385)
    application.setMinimumWidth(380)
    application.setMinimumHeight(506)
    application.show()
sys.exit(app.exec_())

