from __future__ import absolute_import, unicode_literals

import getpass
import re
from time import sleep

import pytz
from datetime import datetime

import requests
from lxml import html

import urllib3

urllib3.disable_warnings()

base_url = 'https://ico.info'
headers = {'user-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 '
                         '(KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36'}
user_email = input('User login email address: ')
user_password = getpass.getpass('Password: ')
project_num = input('ICO project number: ')
token = input('Token used in ICO application: ')
token_amount = input('Token amount: ')

session = requests.session()

print('Getting authenticity token from URL: {}/sign_in'.format(base_url))
token_response = session.get('{}/sign_in'.format(base_url), headers=headers, verify=False)

if token_response.status_code != 200:
    raise RuntimeError('Failed to get authenticity token. Try later')

authenticity_token = html.fromstring(token_response.text).xpath('//meta[@name="csrf-token"]')[0].attrib['content']
print('Authenticity token: {}'.format(authenticity_token))

login_data = {'user[email]': user_email,
              'user[password]': user_password,
              'authenticity_token': authenticity_token,
              'commit': 'login',
              'utf8': '✓'
              }

print('Authenticating for user: {}'.format(user_email))
login_response = session.post('{}/sign_in'.format(base_url), headers=headers, data=login_data, verify=False)

if login_response.status_code != 200:
    raise RuntimeError('User: {} authentication failed. Check your username and password and try again'
                       .format(user_email))

print('User: {} authenticated'.format(user_email))

account_response = session.get('{}/account'.format(base_url), headers=headers, verify=False)
account_tree = html.fromstring(account_response.text)

print('User: {} account information:'.format(user_email))
for node in account_tree.xpath('//div[@class="col-md-6 account-wallets-content"]'):
    currency = re.search('\w+', node.find_class('currency')[0].text).group(0)
    balance = re.search('(\d+[,|.])+\d+', node.find_class('balance')[0].text).group(0)
    print('Token: {}, balance: {}'.format(currency, balance))

project_response = session.get('{}/projects/{}'.format(base_url, project_num), headers=headers, verify=False)
project_name = html.fromstring(project_response.text).xpath('//title')[0].text

print('Project: {}'.format(project_name))

ico_starting_datetime = datetime.strptime(html.fromstring(project_response.text).xpath('//p[@class="time"]')[0].text,
                                          '%Y-%m-%d %H:%M:%S').astimezone(pytz.timezone('Asia/Shanghai'))

while True:
    server_time_response = requests.get(base_url, headers=headers, verify=False)

    if server_time_response.status_code != 200:
        continue

    server_datetime = datetime.strptime(server_time_response.headers['Date'],
                                        '%a, %d %b %Y %H:%M:%S %Z').replace(
        tzinfo=pytz.timezone('GMT')).astimezone(pytz.timezone('Asia/Shanghai'))

    delta = ico_starting_datetime - server_datetime
    delta_in_seconds = delta.total_seconds()

    if delta_in_seconds > 3 * 60:
        print('ICO application will start in {}'.format(delta), end='\r')
        sleep(1)
        continue

    if delta_in_seconds > 0:
        print('Less than 3 minutes left')
    else:
        print('ICO already started')

    print('Begin ICO application. Will move forward once a previous step is completed successfully '
          'until ICO completed successfully or error occurred')
    print('Applying project with token: {}...'.format(token))
    while True:
        project_response = session.get('{}/projects/{}'.format(base_url, project_num), headers=headers,
                                       verify=False)

        if project_response.status_code != 200:
            continue

        ico_started = False
        supported_token_found = False
        for node in html.fromstring(project_response.text).xpath('//div[@class="plan-card"]'):
            supported_token = re.search('\w+', node.xpath('p[@class="plan-price"]')[0].text).group(0)
            if supported_token == token:
                supported_token_found = True
                support_node = node.xpath('div[@class="plan-support-btn-block"]')[0].xpath('a')[0]
                support_href = support_node.attrib['href']
                support_reason = support_node.text
                if support_href == '#':
                    if support_reason == '限额已满':
                        raise RuntimeError('ICO application has been closed on token: {}'.format(token))
                else:
                    ico_started = True

                support_url = '{}{}'.format(base_url, support_href)
                break

        if supported_token_found is False:
            raise RuntimeError('Token: {} is not supported in this ICO application'.format(token))

        if ico_started is False:
            sleep(0.1)
            continue

        support_response = session.get(support_url, headers=headers, verify=False)

        if support_response.status_code == 200:
            print('Completed. Moving forward...')
            break

    print('Confirming terms and conditions...')
    confirm_href = html.fromstring(
        support_response.text).xpath('//a[@class="btn btn-theme btn-block"]')[0].attrib['href']
    while True:
        confirm_response = session.get('{}{}'.format(base_url, confirm_href), headers=headers, verify=False)

        if confirm_response.status_code == 200:
            print('Completed. Moving forward...')
            break

    verification = html.fromstring(
        confirm_response.text).xpath('//div[@class="title math-title"]')[0].xpath('span')[0].text
    verification_tip = html.fromstring(
        confirm_response.text).xpath('//input[@name="math_challenage_ans"]')[0].attrib['placeholder']
    print('{}{}'.format(verification, verification_tip))
    answer = input('Please answer the above question for the final submitting: ')
    print('Submitting ICO application, project: {}, token: {}, amount: {}...'.format(
        project_name, token, token_amount))
    submit_authenticity_token = html.fromstring(
        confirm_response.text).xpath('//meta[@name="csrf-token"]')[0].attrib['content']
    submit_data = {
        'utf8': '✓',
        'authenticity_token': submit_authenticity_token,
        'order[total_price]': token_amount,
        'math_challenage_ans': answer,
        'button': ''
    }
    while True:
        submit_response = session.post(confirm_response.url.rstrip('/new'), headers=headers, data=submit_data,
                                       verify=False)

        if submit_response.status_code == 200:
            warning = html.fromstring(
                submit_response.text).xpath('//button[@data-dismiss="alert"]')

            if warning:
                print('Server respond status code 200. But failed to submit ICO application. Error: {}'
                      .format(warning[0].tail.strip()))
                input('Press any key to exit...')
                exit(1)

            print('Completed. Moving forward...')
            break

    print('Your ICO application has been submitted successfully. Login your account and check full details')
    break

session.close()
exit(0)
