"""
SurveyMonkey adaptor.

Test the Survey Monkey API.
"""


import os
import qi
import json
import surveymonty
import time

import stk.events
import stk.logging
import stk.runner
import stk.services

__version__ = '0.0.1'
__copyright__ = 'Copyright 2017, Aldebaran Robotics'
__author__ = 'hkuntz'
__email__ = 'hkuntz@aldebaran.com'

class ALSurveyMonkey:
    """Get the content from Survey Monkey."""

    PKG_PATH = os.getcwd()  # get the behavior directory
    PKG_ID = os.path.split(PKG_PATH)[-1]
    APP_ID = 'com.aldebaran.{}'.format(PKG_ID)

    DATA_DIRECTORY = os.path.join(PKG_PATH, 'data')
    DATA_SURVEYS_PATH = os.path.join(DATA_DIRECTORY, 'surveys.json')
    DATA_ANSWERS_DIRECTORY = os.path.join(DATA_DIRECTORY, 'answers')

    PREFERENCES_DOMAIN = 'com.softbank.surveymonkey'

    def __init__(self, qiapp):
        """Docstring for StoreProviderService."""
        self.qiapp = qiapp
        self.s = stk.services.ServiceCache(qiapp.session)
        self.logger = stk.logging.get_logger(qiapp.session, self.APP_ID)

        self._init_files()

        self._surveys = None

    #
    # STK.runner required functions
    #
    @qi.nobind
    def on_start(self):
        """Called when the application is intialized."""
        self.logger.info('on_start')
        self._init()  # Read the default configuration

    @qi.nobind
    def on_stop(self):
        """Cleanup."""
        self.logger.info('on_stop')
        self.stop()

    @qi.bind(returnType=qi.Void, paramsType=[])
    def stop(self):
        """Stop the application."""
        self.logger.info('Stopped by user request.')
        self.qiapp.stop()

    #
    # Core
    #
    @qi.nobind
    def _init(self):
        self._access_token = self._get_preference('AccessToken')
        self._survey_ids = self._get_preference('SurveyIds', []).split(',')
        self._collector_id = self._get_preference('CollectorId')

        if self._access_token is None:
            self.logger.warning("No access token found!")
            return

        self._client = surveymonty.Client(self._access_token)

        # qi.async(self._download_data)
        self._load_data()

    @qi.nobind
    def _get_preference(self, key, default_value=None):
        self.logger.info("Get preference : %s/%s " % (self.PREFERENCES_DOMAIN, key))
        try:
            return self.s.ALPreferenceManager.getValue(self.PREFERENCES_DOMAIN, key)
        except Exception as e:
            self.logger.error("error on read preference : %s" % e)
            return None

    #
    # Data management
    #
    @qi.nobind
    def _init_files(self):
        self.logger.info("Init files")
        try:
            if not os.path.isdir(self.DATA_DIRECTORY):
                os.makedirs(self.DATA_DIRECTORY)

            if not os.path.isdir(self.DATA_ANSWERS_DIRECTORY):
                os.makedirs(self.DATA_ANSWERS_DIRECTORY)

            if not os.path.exists(self.DATA_SURVEYS_PATH):
                with open(self.DATA_SURVEYS_PATH, 'w') as f:
                    json.dump({}, f)

        except Exception as e:
            self.logger.error("Error on creating files : %s" % e)

    @qi.nobind
    def _download_data(self):
        data = {}
        for survey_id in self._survey_ids:
            self.logger.info("Start download data for survey %s" % survey_id)
            try:
                survey_data = self._client.get_survey(survey_id)
                survey_data['pages'] = []
                pages = self._client.get_survey_pages(survey_id)
                for page in pages['data']:
                    questions = self._client.get_survey_page_questions(survey_id, page['id'])
                    page['questions'] = []
                    for q in questions['data']:
                        question = self._client.get_survey_page_question(survey_id, page['id'], q['id'])
                        page['questions'].append(question)

                    survey_data['pages'].append(page)

                survey_data['collector'] = self._client.get_collector(self._collector_id)

                self.logger.info('Survey data downloaded')

            except Exception as e:
                self.logger.error("Error on download data for survey %s : %s" % (survey_id, e))

            data[survey_id] = survey_data

        self._save_surveys_data(data)

    @qi.nobind
    def _save_surveys_data(self, data):
        self.logger.info("Save surveys data in %s" % self.DATA_SURVEYS_PATH)
        try:
            with open(self.DATA_SURVEYS_PATH, 'w') as f:
                json.dump(data, f)

        except Exception as e:
            self.logger.error("Error on save surveys data : %s" % e)

        self._load_data()

    @qi.nobind
    def _load_data(self):
        self.logger.info("Load surveys from : %s" % self.DATA_SURVEYS_PATH)
        try:
            with open(self.DATA_SURVEYS_PATH, 'r') as f:
                self._surveys = json.load(f)

        except Exception as e:
            self.logger.error("Error on load data : %s" % e)

    @qi.nobind
    def _submit_answer(self):
        # TODO: Add a mutex
        self.logger.info("Submit the answer(s) ...")
        try:
            for file in os.listdir(self.DATA_ANSWERS_DIRECTORY):
                path = os.path.join(self.DATA_ANSWERS_DIRECTORY, file)
                with open(path, 'r') as f:
                    data = json.load(f)

                    payload = data['payload']

                    self.logger.info("Send answer : %s => %s" % (path, payload))

                    res = self._client.create_collector_response(data['collector_id'], data=payload)

                    self.logger.info("response : %s" % res)

                    os.remove(path)

            self.logger.info("Answer(s) sent !")

        except Exception as e:
            self.logger.error("Error on submit answer : %s" % e)

    #
    # API
    #
    @qi.bind(returnType=qi.Bool, methodName="downloadData")
    def download_data(self):
        """
        Doanload the surveys data from SurveyMonkey.

        Returns:
            True if everything ok, False otherwise, check the logs in case of errors
        """
        try:
            self._download_data()
            return True
        except Exception as e:
            self.logger.error("Error on download data : %s" % e)

        return False

    @qi.bind(returnType=qi.Dynamic, paramsType=(qi.Int32, ), methodName="getSurvey")
    def get_survey(self, survey_id):
        """
        Return the survey of the survey id.

        Parameters:
            survey_id - (String) The id of the desired survey

        Returns:
            Survey - (JSON) The survey data if exists, None otherwise
        """
        self.logger.info("Get survey : %s" % survey_id)
        try:
            return self._surveys[str(survey_id)]
        except Exception as e:
            self.logger.error("Error on get survey : %s" % e)
            return None

    @qi.bind(returnType=qi.Bool, paramsType=(qi.Int32, qi.Dynamic), methodName="addAnswer")
    def add_answer(self, collector_id, answer):
        """
        Collect the answer and send them to the collector when is possible.

        Parameters:
            collectorId - (Integer) The collector id used to collect data
            answer - (JSON) the answer data.

        Returns:
            True if everything is ok, False otherwise (check the log in case of error)
        """
        path = os.path.join(self.DATA_ANSWERS_DIRECTORY, "%s.json" % int(time.time()))
        self.logger.info("Save new answer in : %s" % path)
        try:
            with open(path, 'w') as f:
                json.dump({
                    "collector_id": collector_id,
                    "payload": answer
                }, f)

            qi.async(self._submit_answer)
            return True
        except Exception as e:
            self.logger.error("Error on add answer: %s" % e)
            return False

####################
# Setup and Run
####################

if __name__ == '__main__':
    stk.runner.run_service(ALSurveyMonkey)
