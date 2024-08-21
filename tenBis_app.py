import pandas as pd
import requests
from bs4 import BeautifulSoup as bs
from datetime import datetime
import re
import io
import smtplib
from settings import *
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.mime.text import MIMEText

URL = "https://www.10bis.co.il/reshome/"
PAYLOAD = {
        "UserName": user_name,
        "Password": password
        }


class App:
    def __init__(self, mail_sender, recipient):
        self.TenBisScrapper = TenBisScrapper(URL, PAYLOAD)
        self.full_order_list = None
        self.mail_sender = mail_sender
        self.recipient = recipient

    def run_and_get_orders_list(self):
        self.TenBisScrapper.run_scrapper()
        self.full_order_list = self.TenBisScrapper.get_full_order_list()

    def send_mail(self):
        mail = Mail(self.full_order_list, self.mail_sender, self.recipient)
        mail.sending_gmail()

    def run_app(self):
        self.run_and_get_orders_list()
        self.send_mail()


class TenBisScrapper:
    def __init__(self, url, payload):
        self.url = url
        self.payload = payload
        self.order_hrefs_list = []
        self.all_orders = []

    def log_in(self):
        with requests.Session() as s:
            page = s.post(self.url + "Account/LogOn", data=self.payload)
            page = s.get(self.url)
            main_page_after_login_soup = bs(page.content, 'html.parser')
            return main_page_after_login_soup

    def extract_orders_href(self):
        main_page = self.log_in()
        order_href = main_page.find_all('a', {'href': re.compile(r'/reshome/Orders/\b')})  #I added \b we need to check it further
         # /reshome/Orders/Standard/xxxxx?printOrder=False each item in list looks like that
        for href in order_href:
            self.order_hrefs_list.append(href['href'])

    def go_to_order_info_page(self, link):
        base_url = "https://www.10bis.co.il/"
        with requests.Session() as s:
            page = s.post(self.url + "Account/LogOn", data=self.payload)
            page = s.get(base_url + str(link))
            order_info_soup = bs(page.content, 'html.parser')
        return order_info_soup

    def extract_info_per_general_order(self, link):
        soup_info_per_order = self.go_to_order_info_page(link)
        if self.check_if_pooled_order(link) is True:
            self.extract_info_per_pooled_order(soup_info_per_order)
        else:
            self.extract_info_per_regular_order(soup_info_per_order)

    def extract_info_per_pooled_order(self, soup):
        info = soup.find_all('td', class_='PooledOrderSerialNumberClass')
        address = soup.find('td', class_='OrderCustomerBoldClass CustomerHighlightData') \
            .text.replace("\r\n", "").replace("\t", "").strip()

        company = soup.find('span', class_='OrderCustomerBoldClass CustomerHighlightData').text.strip()
        for one_order in info:
            data_per_order_dict = {}
            name = one_order.find('span', class_='CustomerHighlightData').text.strip()  ## extracct names
            data_per_order_dict['Name'] = name
            phone_numbers = re.findall(r"(\d{2,3}-?\d{6,7})", one_order.text.strip())
            phone_numbers_unique = set(phone_numbers)

            for i in range(len(phone_numbers_unique)):
                data_per_order_dict[f'Phone Number {i + 1}'] = list(phone_numbers_unique)[i]

            data_per_order_dict['Address'] = address
            data_per_order_dict['Company'] = company
            self.all_orders.append(data_per_order_dict)

    def extract_info_per_regular_order(self, soup):
        data_per_order_dict = {}
        info = soup.find('table', id="OrderCustomerDetailsTable")
        data_per_order_dict['Name'] = info.find('span', class_="CustomerHighlightData").text.replace(";", "").strip()
        phone_numbers = re.findall(r"(\d{2,3}-?\d{7})", info.text)  # phone numbers - need to address duplicates
        phone_numbers_unique = set(phone_numbers)

        for i in range(len(phone_numbers_unique)):
            data_per_order_dict[f'Phone Number {i+1}'] = list(phone_numbers_unique)[i]

        address, apartment_number, floor_number = "", "", ""
        # Iterate over all 'td' elements directly
        for td in info.find_all('td')[2:]:
            text = td.get_text(strip=True)
            if 'כתובת:' in text:
                address = td.find_next('td').text.strip()  # every time the content being shown 1 td after the title
            elif 'דירה:' in text:
                apartment_number = td.find_next('td').text.strip()
            elif 'קומה:' in text:
                floor_number = td.find_next('td').text.strip()

        data_per_order_dict['Address'] = address
        data_per_order_dict['Apartment Number'] = apartment_number
        data_per_order_dict['Floor Number'] = floor_number
        self.all_orders.append(data_per_order_dict)

    @staticmethod
    def check_if_pooled_order(link):
        pattern = re.compile(r"\bPooled\b")
        if pattern.search(link):
            return True
        else:
            return False

    def run_scrapper(self):
        self.extract_orders_href()
        for href in self.order_hrefs_list:
            self.extract_info_per_general_order(href)

    def get_full_order_list(self):
        return self.all_orders


class Mail:
    def __init__(self, all_orders_list, mail_sender, recipient):
        self.mail_sender = mail_sender
        self.recipient = recipient
        self.passw = EMAIL_PASSWORD
        self.all_orders_list = all_orders_list
        self.buffer = None

    def create_excel_buffer(self):
        df = pd.DataFrame(self.all_orders_list)
        df.index += 1
        self.buffer = io.BytesIO()
        with pd.ExcelWriter(self.buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Sheet1')
        self.buffer.seek(0)

    def sending_gmail(self):
        self.create_excel_buffer()

        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        current_date = datetime.now().strftime('%d-%m-%Y')

        msg = MIMEMultipart()
        msg['From'] = self.mail_sender
        msg['To'] = self.recipient
        msg['Subject'] = f"Your last day summery 10Bis - {current_date}"
        msg.attach(MIMEText("", 'plain'))
        part = MIMEBase('application', "octet-stream")
        part.set_payload(self.buffer.getvalue())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{current_date} - 10Bis daily summery.xlsx"')
        msg.attach(part)
        # Send the email
        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()  # Secure the connection
                server.login(self.mail_sender, self.passw)
                server.sendmail(self.mail_sender, self.recipient, msg.as_string())
                print("Email sent successfully!")
        except Exception as e:
            print(f"Failed to send email: {e}")
