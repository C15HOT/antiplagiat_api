# Antiplagiat api

##Описание:

Библиотека предназначена для использования API сервиса "Антиплагиат".

Библиотека  позволяет работать как в синхронном, так и в асинхронном режиме.

Перед использованием API необходимо получить доступ на сайте "Антиплагиата" (Без этого библиотека может быть использована в тестовом режиме, проверка будет осуществляться от имени тестового пользователя в "Википедии")
___

## Версия 0.0.1:
Реализованы фукнции поиска заимствований с получением подробного отчета, а такж получения отчета в pdf - формате.

### Классы:

***AntiplagiatClient*** - синхронный клиент

Принимает параметры:

    login="testapi@antiplagiat.ru", 
    password="testapi",
    company_name="testapi", 
    apicorp_address="api.antiplagiat.ru:44902"
    antiplagiat_uri="https://testapi.antiplagiat.ru"


***AsyncAntiplagiatClient*** - асинхронный клиент

Принимает параметры:

    login="testapi@antiplagiat.ru", 
    password="testapi",
    company_name="testapi", 
    apicorp_address="api.antiplagiat.ru:44902"
    antiplagiat_uri="https://testapi.antiplagiat.ru"


### Методы:

***simple_check*** - Проверка документа с использованием всех подключенных сервисов

Принимает параметры:

    filename: str, author_surname='',
    author_other_names='',
    external_user_id='ivanov', 
    custom_id='original'

Возвращает:

pydantic валидированный словарь вида:

    {'filename': '1.txt', 
    'plagiarism': '83.48%', 
    'services': [{'service_name': 'testapi', 'originality': '0.00%', 'plagiarism': '0.00%', 
                'source': []}, 
                {'service_name': 'wikipedia', 'originality': '0.00%', 'plagiarism': '83.48%', 
                'source': [{'hash': '72347658949231192', 'score_by_report': '83.48%', 'score_by_source': '83.48%', 'name': 'Википедия', 'author': None, 'url': None}, 
                            {'hash': '72347658949264292', 'score_by_report': '0.00%', 'score_by_source': '9.37%', 'name': 'Уэйлс, Джимми', 'author': None, 'url': None}, 
                            {'hash': '72347658950487137', 'score_by_report': '0.00%', 'score_by_source': '9.37%', 'name': 'Медаль Нильса Бора', 'author': None, 'url': None}]}], 
    'author': {'surname': None, 'othernames': None, 'custom_id': None}}


***get_verification_report_pdf*** - Проверка документа и получение отчета в pdf - формате

Принимает параметры:

     filename: str,
     author: str,
     department: str,
     type: str,
     verifier: str,
     work: str,
     path: str = None,
     external_user_id: str = 'ivanov'

Создает pdf - файл отчета в указанной директории.


## Пример использования:

```python

client = AntiplagiatClient(login="testapi@antiplagiat.ru",
                           password="testapi",
                           company_name="testapi")
client.get_verification_report_pdf('1.txt', 
                                   author='Ivanov',                              
                                   department='ITMO',
                                   type='Diplom',
                                   verifier='Petrov',
                                   work='topic of work')

```

