# Antiplagiat api

## Description:

The library is designed to use the API of the "Antiplagiate" service.

The library allows you to work in both synchronous and asynchronous mode.

Before using the API, you must access the "Antiplagiate" website 
(Without this, the library can be used in test mode, verification will be carried out on behalf of the test user on Wikipedia)
___

## Version 0.0.1:
We implemented the functions of searching for borrowings with the receipt of a detailed report, as well as the receipt of a report in pdf format.
### Classes:

***AntiplagiatClient*** - synchronous client

Getting parameters:

    login="testapi@antiplagiat.ru", 
    password="testapi",
    company_name="testapi", 
    apicorp_address="api.antiplagiat.ru:44902"
    antiplagiat_uri="https://testapi.antiplagiat.ru"


***AsyncAntiplagiatClient*** - asynchronous client

Getting parameters:

    login="testapi@antiplagiat.ru", 
    password="testapi",
    company_name="testapi", 
    apicorp_address="api.antiplagiat.ru:44902"
    antiplagiat_uri="https://testapi.antiplagiat.ru"


### Methods:

***simple_check*** - verifying the document using all connected services

Getting parameters:

    filename: str, 
    author_surname='',
    author_other_names='',
    external_user_id='ivanov', 
    custom_id='original'

return:

pydantic validated dictionary of the form:

    {'filename': '1.txt', 
    'plagiarism': '83.48%', 
    'services': [{'service_name': 'testapi', 'originality': '0.00%', 'plagiarism': '0.00%', 
                'source': []}, 
                {'service_name': 'wikipedia', 'originality': '0.00%', 'plagiarism': '83.48%', 
                'source': [{'hash': '72347658949231192', 'score_by_report': '83.48%', 'score_by_source': '83.48%', 'name': 'Википедия', 'author': None, 'url': None}, 
                            {'hash': '72347658949264292', 'score_by_report': '0.00%', 'score_by_source': '9.37%', 'name': 'Уэйлс, Джимми', 'author': None, 'url': None}, 
                            {'hash': '72347658950487137', 'score_by_report': '0.00%', 'score_by_source': '9.37%', 'name': 'Медаль Нильса Бора', 'author': None, 'url': None}]}], 
    'author': {'surname': None, 'othernames': None, 'custom_id': None}}


***get_verification_report_pdf*** - Document Review and Report PDF

Getting parameters:

     filename: str,
     author: str,
     department: str,
     type: str,
     verifier: str,
     work: str,
     path: str = None,
     external_user_id: str = 'ivanov'

Creates a pdf - report file in the specified directory.


## Usage example


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
client.simple_check('1.txt')


```

For asynchronous usage create AsyncAntiplagiatClient and use await to call methods
