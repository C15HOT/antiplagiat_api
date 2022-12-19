import asyncio
import datetime
import os

import httpx
import suds.client
import time

import zeep
from zeep.transports import AsyncTransport

from antiplagiat.libs.schemas import SimpleCheckResult, Service, Source, Author
import base64

from antiplagiat.libs.logger import logger


class AntiplagiatClient:

    def __init__(self, login,
                 password,
                 company_name,
                 apicorp_address="api.antiplagiat.ru:44902",
                 antiplagiat_uri="https://testapi.antiplagiat.ru",):

        self.antiplagiat_uri = antiplagiat_uri
        self.login = login
        self.password = password
        self.company_name = company_name
        self.apicorp_address = apicorp_address
        self.client = suds.client.Client(f'https://{self.apicorp_address}/apiCorp/{self.company_name}?singleWsdl',
                                         username=self.login,
                                         password=self.password)

    def _get_doc_data(self, filename: str, external_user_id: str):
        data = self.client.factory.create("DocData")
        data.Data = base64.b64encode(open(filename, "rb").read()).decode()
        data.FileName = os.path.splitext(filename)[0]
        data.FileType = os.path.splitext(filename)[1]
        data.ExternalUserID = external_user_id
        return data

    def simple_check(self, filename: str, author_surname='',
                     author_other_names='',
                     external_user_id='ivanov', custom_id='original'
                     ) -> SimpleCheckResult:
        logger.info("SimpleCheck filename=" + filename)

        data = self._get_doc_data(filename, external_user_id=external_user_id)

        docatr = self.client.factory.create("DocAttributes")
        personIds = self.client.factory.create("PersonIDs")
        personIds.CustomID = custom_id

        arr = self.client.factory.create("ArrayOfAuthorName")

        author = self.client.factory.create("AuthorName")
        author.OtherNames = author_other_names
        author.Surname = author_surname
        author.PersonIDs = personIds

        arr.AuthorName.append(author)

        docatr.DocumentDescription.Authors = arr

        # Загрузка файла
        try:
            uploadResult = self.client.service.UploadDocument(data, docatr)

        except Exception:
            raise

        # Идентификатор документа. Если загружается не архив, то список загруженных документов будет состоять из одного элемента.
        id = uploadResult.Uploaded[0].Id

        try:
            # Отправить на проверку с использованием всех подключеных компании модулей поиска
            self.client.service.CheckDocument(id)
        # Отправить на проверку с использованием только собственного модуля поиска и модуля поиска "wikipedia". Для получения списка модулей поиска см. пример get_tariff_info()
        # client.service.CheckDocument(id, ["wikipedia", COMPANY_NAME])
        except suds.WebFault:
            raise

        # Получить текущий статус последней проверки
        status = self.client.service.GetCheckStatus(id)

        # Цикл ожидания окончания проверки
        while status.Status == "InProgress":
            time.sleep(status.EstimatedWaitTime * 0.1)
            status = self.client.service.GetCheckStatus(id)

        # Проверка закончилась не удачно.
        if status.Status == "Failed":
            logger.error(f"An error occurred while validating the document {filename}: {status.FailDetails}")

        # Получить краткий отчет
        report = self.client.service.GetReportView(id)

        logger.info(f"Report Summary: {report.Summary.Score:.2f}%")
        result = SimpleCheckResult(filename=os.path.basename(filename),
                                   plagiarism=f'{report.Summary.Score:.2f}%',
                                   services=[],
                                   author=Author())

        for checkService in report.CheckServiceResults:
            # Информация по каждому поисковому модулю

            service = Service(service_name=checkService.CheckServiceName,
                              originality=f'{checkService.ScoreByReport.Legal:.2f}%',
                              plagiarism=f'{checkService.ScoreByReport.Plagiarism:.2f}%',
                              source=[])

            logger.info(f"Check service: {checkService.CheckServiceName}, "
                        f"Score.White={checkService.ScoreByReport.Legal:.2f}% "
                        f"Score.Black={checkService.ScoreByReport.Plagiarism:.2f}%")
            if not hasattr(checkService, "Sources"):
                result.services.append(service)
                continue
            for source in checkService.Sources:
                _source = Source(hash=source.SrcHash,
                                 score_by_report=f'{source.ScoreByReport:.2f}%',
                                 score_by_source=f'{source.ScoreBySource:.2f}%',
                                 name=source.Name,
                                 author=source.Author,
                                 url=source.Url)

                service.source.append(_source)
                # Информация по каждому найденному источнику
                logger.info(
                    f'\t{source.SrcHash}: Score={source.ScoreByReport:.2f}%({source.ScoreBySource:.2f}%), '
                    f'Name="{source.Name}" Author="{source.Author}"'
                    f' Url="{source.Url}"')

                # Получить полный отчет
            result.services.append(service)

        options = self.client.factory.create("ReportViewOptions")
        options.FullReport = True
        options.NeedText = True
        options.NeedStats = True
        options.NeedAttributes = True
        fullreport = self.client.service.GetReportView(id, options)

        logger.info(f"Author Surname={fullreport.Attributes.DocumentDescription.Authors.AuthorName[0].Surname} "
                    f"OtherNames={fullreport.Attributes.DocumentDescription.Authors.AuthorName[0].OtherNames} "
                    f"CustomID={fullreport.Attributes.DocumentDescription.Authors.AuthorName[0].PersonIDs.CustomID}")

        result.author.surname = fullreport.Attributes.DocumentDescription.Authors.AuthorName[0].Surname
        result.author.othernames = fullreport.Attributes.DocumentDescription.Authors.AuthorName[0].OtherNames
        result.author.custom_id = fullreport.Attributes.DocumentDescription.Authors.AuthorName[0].PersonIDs.CustomID

        return result.dict()

    def _get_report_name(self, id, reportOptions):
        author = u''

        if reportOptions is not None:
            if reportOptions.Author:
                author = '_' + reportOptions.Author

        curDate = datetime.datetime.today().strftime('%Y%m%d')
        return f'Certificate_{id.Id}_{curDate}_{author}.pdf'

    def get_verification_report_pdf(self, filename: str,
                                    author: str,
                                    department: str,
                                    type: str,
                                    verifier: str,
                                    work: str,
                                    path: str = None,
                                    external_user_id: str = 'ivanov'
                                    ):

        logger.info("Get report pdf:" + filename)

        data = self._get_doc_data(filename, external_user_id=external_user_id)

        uploadResult = self.client.service.UploadDocument(data)

        id = uploadResult.Uploaded[0].Id

        self.client.service.CheckDocument(id)

        status = self.client.service.GetCheckStatus(id)

        while status.Status == "InProgress":
            time.sleep(status.EstimatedWaitTime)
            status = self.client.service.GetCheckStatus(id)

        if status.Status == "Failed":
            logger.error(f"An error occurred while validating the document {filename}: {status.FailDetails}")
            return

        try:

            reportOptions = self.client.factory.create("VerificationReportOptions")
            reportOptions.Author = author  # ФИО автора работы
            reportOptions.Department = department  # Факультет (структурное подразделение)
            reportOptions.ShortReport = True  # Требуется ли ссылка на краткий отчёт? (qr код)
            reportOptions.Type = type  # Тип работы
            reportOptions.Verifier = verifier  # ФИО проверяющего
            reportOptions.Work = work  # Название работы

            reportWithFields = self.client.service.GetVerificationReport(id, reportOptions)

            decoded = base64.b64decode(reportWithFields)
            fileName = self._get_report_name(id, reportOptions)

            if path:
                if not os.path.exists(path):
                    os.makedirs(path)
                filepath = os.path.join(path, f'{fileName}')


            else:
                filepath = fileName

            f = open(f"{filepath}", 'wb')
            f.write(decoded)
        except suds.WebFault as e:
            if e.fault.faultcode == "a:InvalidArgumentException":
                raise Exception(
                    u"У документа нет отчёта/закрытого отчёта или в качестве id в GetVerificationReport передано None: " + e.fault.faultstring)
            if e.fault.faultcode == "a:DocumentIdException":
                raise Exception(u"Указан невалидный DocumentId" + e.fault.faultstring)
            raise
        logger.info("Success create report in path: " + filepath)


class AsyncAntiplagiatClient:

    def __init__(self, login,
                 password,
                 company_name,
                 apicorp_address="api.antiplagiat.ru:44902",
                 antiplagiat_uri="https://testapi.antiplagiat.ru"):
        self.antiplagiat_uri = antiplagiat_uri
        self.login = login
        self.password = password
        self.company_name = company_name
        self.apicorp_address = apicorp_address
        self.httpx_client = httpx.AsyncClient(auth=(self.login, self.password))
        self.client = zeep.AsyncClient(
            f'https://{self.apicorp_address}/apiCorp/{self.company_name}?singleWsdl',
            transport=AsyncTransport(client=self.httpx_client))
        self.factory = self.client.type_factory('ns0')

    async def _get_doc_data(self, filename: str, external_user_id: str):
        Data = base64.b64encode(open(filename, "rb").read()).decode()
        FileName = os.path.splitext(filename)[0]
        FileType = os.path.splitext(filename)[1]
        ExternalUserID = external_user_id

        data = self.factory.DocData(Data=Data, FileName=FileName, FileType=FileType, ExternalUserID=ExternalUserID)
        return data

    async def simple_check(self, filename: str, author_surname='',
                           author_other_names='',
                           external_user_id='ivanov', custom_id='original'
                           ) -> SimpleCheckResult:
        logger.info("SimpleCheck filename=" + filename)

        data = await self._get_doc_data(filename, external_user_id=external_user_id)
        docatr = self.factory.DocAttributes()
        personIds = self.factory.PersonIDs()
        personIds.CustomID = personIds
        arr = self.factory.ArrayOfAuthorName()
        author = self.factory.AuthorName()
        author.OtherNames = author_other_names
        author.Surname = author_surname
        author.PersonIDs = personIds
        arr.AuthorName.append(author)

        # docatr.DocumentDescription.Authors = arr

        try:
            uploadResult = await self.client.service.UploadDocument(data, docatr)
        except Exception:
            raise

        id = uploadResult[0]['Id']

        try:
            await self.client.service.CheckDocument(id)
        except suds.WebFault:
            raise

        status = await self.client.service.GetCheckStatus(id)

        while status.Status == "InProgress":
            await asyncio.sleep(status.EstimatedWaitTime * 0.1)
            status = await self.client.service.GetCheckStatus(id)

        if status.Status == "Failed":
            print(f"An error occurred while validating the document {filename}: {status.FailDetails}")

        report = await self.client.service.GetReportView(id)

        logger.info(f"Report Summary: {report.Summary.Score:.2f}%")
        result = SimpleCheckResult(filename=os.path.basename(filename),
                                   plagiarism=f'{report.Summary.Score:.2f}%',
                                   services=[],
                                   author=Author())

        for checkService in report.CheckServiceResults:
            # Информация по каждому поисковому модулю

            service = Service(service_name=checkService.CheckServiceName,
                              originality=f'{checkService.ScoreByReport.Legal:.2f}%',
                              plagiarism=f'{checkService.ScoreByReport.Plagiarism:.2f}%',
                              source=[])

            logger.info(f"Check service: {checkService.CheckServiceName}, "
                        f"Score.White={checkService.ScoreByReport.Legal:.2f}% "
                        f"Score.Black={checkService.ScoreByReport.Plagiarism:.2f}%")
            if not hasattr(checkService, "Sources"):
                result.services.append(service)
                continue
            for source in checkService.Sources:
                _source = Source(hash=source.SrcHash,
                                 score_by_report=f'{source.ScoreByReport:.2f}%',
                                 score_by_source=f'{source.ScoreBySource:.2f}%',
                                 name=source.Name,
                                 author=source.Author,
                                 url=source.Url)

                service.source.append(_source)
                # Информация по каждому найденному источнику
                logger.info(
                    f'\t{source.SrcHash}: Score={source.ScoreByReport:.2f}%({source.ScoreBySource:.2f}%), '
                    f'Name="{source.Name}" Author="{source.Author}"'
                    f' Url="{source.Url}"')

                # Получить полный отчет
            result.services.append(service)

        options = self.factory.ReportViewOptions()
        options.FullReport = True
        options.NeedText = True
        options.NeedStats = True
        options.NeedAttributes = True
        fullreport = await self.client.service.GetReportView(id, options)

        # Авторы не заполняются т.к. невозможно корректно передать запрос на сервер

        result.author.surname = None
        result.author.othernames = None
        result.author.custom_id = None

        return result.dict()

    async def _get_report_name(self, id, reportOptions):
        author = u''

        if reportOptions is not None:
            if reportOptions.Author:
                author = '_' + reportOptions.Author

        curDate = datetime.datetime.today().strftime('%Y%m%d')
        return f'Certificate_{id.Id}_{curDate}_{author}.pdf'

    async def get_verification_report_pdf(self, filename: str,
                                          author: str,
                                          department: str,
                                          type: str,
                                          verifier: str,
                                          work: str,
                                          path: str = None,
                                          external_user_id: str = 'ivanov'
                                          ):

        logger.info("Get report pdf:" + filename)

        data = await self._get_doc_data(filename, external_user_id=external_user_id)

        uploadResult = await self.client.service.UploadDocument(data)

        id = uploadResult[0]['Id']

        await self.client.service.CheckDocument(id)

        status = await self.client.service.GetCheckStatus(id)

        while status.Status == "InProgress":
            await asyncio.sleep(status.EstimatedWaitTime * 0.1)
            status = await self.client.service.GetCheckStatus(id)

        if status.Status == "Failed":
            logger.error(f"An error occurred while validating the document {filename}: {status.FailDetails}")
            return

        try:

            reportOptions = self.factory.VerificationReportOptions()

            reportOptions.Author = author  # ФИО автора работы
            reportOptions.Department = department  # Факультет (структурное подразделение)
            reportOptions.ShortReport = True  # Требуется ли ссылка на краткий отчёт? (qr код)
            reportOptions.Type = type  # Тип работы
            reportOptions.Verifier = verifier  # ФИО проверяющего
            reportOptions.Work = work  # Название работы

            reportWithFields = await self.client.service.GetVerificationReport(id, reportOptions)
            #Декодирование не нужно
            # decoded = base64.b64decode(reportWithFields)

            fileName = await self._get_report_name(id, reportOptions)

            if path:
                if not os.path.exists(path):
                    os.makedirs(path)
                filepath = os.path.join(path, f'{fileName}')


            else:
                filepath = fileName

            f = open(f"{filepath}", 'wb')
            f.write(reportWithFields)
            logger.info("Success create report in path: " + filepath)
        except Exception as exc:
            logger.error(f'Error: {exc}')


