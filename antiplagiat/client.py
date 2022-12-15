import os
from pprint import pprint

import suds.client
import time
from antiplagiat.libs.schemas import SimpleCheckResult, Service, Source, Author
import base64

from antiplagiat.libs.logger import logger


class AntiplagiatClient:

    def __init__(self, login, password, company_name, apicorp_address):

        self.antiplagiat_uri = "https://testapi.antiplagiat.ru"
        self.login = login
        self.password = password
        self.company_name = company_name
        self.apicorp_address = apicorp_address
        self.client = suds.client.Client(f'https://{self.apicorp_address}/apiCorp/{self.company_name}?singleWsdl',
                                         username=self.login,
                                         password=self.password)

    async def _get_doc_data(self, filename: str, external_user_id: str):
        data = self.client.factory.create("DocData")
        data.Data = base64.b64encode(open(filename, "rb").read()).decode()
        data.FileName = os.path.splitext(filename)[0]
        data.FileType = os.path.splitext(filename)[1]
        data.ExternalUserID = external_user_id
        return data

    async def simple_check(self, filename: str,  author_surname='',
                 author_other_names='',
                 external_user_id='ivanov', custom_id='original'
                           ) -> SimpleCheckResult:
        logger.info("SimpleCheck filename=" + filename)

        data = await self._get_doc_data(filename, external_user_id=external_user_id)

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
            logger.error(f"При проверке документа {filename} произошла ошибка: {status.FailDetails}")

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
        # if fullreport.Details.CiteBlocks:
        #     # Найти самый большой блок заимствований и вывести его
        #     maxBlock = max(fullreport.Details.CiteBlocks, key=lambda x: x.Length)
        #     print(u"Max block length=%s Source=%s text:\n%s..." % (maxBlock.Length, maxBlock.SrcHash,
        #            fullreport.Details.Text[maxBlock.Offset:maxBlock.Offset + min(maxBlock.Length, 200)]))

        logger.info(f"Author Surname={fullreport.Attributes.DocumentDescription.Authors.AuthorName[0].Surname} "
                    f"OtherNames={fullreport.Attributes.DocumentDescription.Authors.AuthorName[0].OtherNames} "
                    f"CustomID={fullreport.Attributes.DocumentDescription.Authors.AuthorName[0].PersonIDs.CustomID}")

        result.author.surname = fullreport.Attributes.DocumentDescription.Authors.AuthorName[0].Surname
        result.author.othernames = fullreport.Attributes.DocumentDescription.Authors.AuthorName[0].OtherNames
        result.author.custom_id = fullreport.Attributes.DocumentDescription.Authors.AuthorName[0].PersonIDs.CustomID

        return result.dict()


client = AntiplagiatClient(login="testapi@antiplagiat.ru", password="testapi",
                           company_name="testapi", apicorp_address="api.antiplagiat.ru:44902")

import asyncio

pprint(asyncio.run(client.simple_check("../1.txt")))
