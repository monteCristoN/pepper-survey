"""
SurveyMonkey adaptor.

Test the Survey Monkey API.
"""

import json
import datetime
import random

from dateutil.tz import tzlocal

__version__ = '0.0.1'
__copyright__ = 'Copyright 2017, Aldebaran Robotics'
__author__ = 'hkuntz'
__email__ = 'hkuntz@aldebaran.com'

class SurveyMonkeyAdapter:
    """Get the content from Survey Monkey."""

    def __init__(self, service, logger):
        """Init application."""
        self.service = service
        self.logger = logger

    def start_survey(self, survey_id):
        """
        Start, or restart, the survey corresponding of the id.

        Parameters:
            survey_id - (String) The survey id

        Return:
            Bool - True if ok, False if the sruvey doesn't exists
        """
        self.logger.info("Adapter: Start survey : %s" % survey_id)
        survey = self.service.getSurvey(survey_id)
        if survey is None:
            raise Exception("Survey Not found")

        self._current_survey = survey

        # Pre format the payload
        self._answer_payload = {
            "date_created": datetime.datetime.now(tzlocal()).replace(microsecond=0).isoformat(),
            "pages": []
        }

    #
    # Core
    #
    def _get_progression(self, question_id):
        current_question = 0
        for index in range(int(self._current_page['position'])):
            page = self._get_item(self._current_survey['pages'], 'position', index+1)
            for question in page['questions']:
                if question['id'] == question_id:
                    break
                current_question += 1

        return int(float(current_question) / float(self._current_survey['question_count']) * 100)

    def _get_item(self, array, key, value):
        self.logger.info("Search item with %s : %s" % (key, value))
        for item in array:
            if item[key] == value:
                return item
        self.logger.info("No item found")
        return None

    def _get_title(self, headings):
        try:
            if 'random_assignment' in headings[0]:  # Randomization
                self.logger.info("Adapter: get a title randomly ... ")
                rand = random.randint(0, 100)
                self.logger.info("Adapter: rand value : %s" % rand)
                min = 0
                max = 0
                for heading in headings:
                    max += int(heading['random_assignment']['percent'])
                    self.logger.info("Adapter: rand value : %s, min : %s, max: %s" % (rand, min, max))
                    if rand >= min and rand <= max:
                        self.logger.info("Found title !")
                        return str(heading['random_assignment']['id']), heading['heading']
                    min = int(heading['random_assignment']['percent'])
            return None, random.choice(headings)['heading']
        except Exception as e:
            self.logger.error("Error on get title : %s" % e)

    def _get_type(self, question):

        if question['family'] == 'open_ended':
            if question['subtype'] == 'single':
                if 'display_options' in question:
                    if question['display_options']['display_type'] == 'slider':
                        return 'slider'

                return 'single_line'

            if question['subtype'] == 'essay':
                return 'multiple_line'

        if question['family'] == 'presentation':
            return 'speech'

        if question['family'] == 'matrix':
            if question['subtype'] == 'rating':
                if 'display_options' in question and question['display_options']['display_type'] == 'emoji':
                    return 'rating'

                choice = self._get_item(question['answers']['choices'], 'position', 1)
                if choice is not None and choice['text'] == 'Not at all likely - 0':
                    return 'nps'

            return 'matrix'

        return question['family']

    # output = {
    #     "id": The question id,
    #     "title": The title of the question
    #     "type": the type of the question
    #     "progression": the progression of the survey
    #
    #  Otional:
    #     "required": the requirements of the question
    #     "validation": the validation of the question
    #     "answers": the list of the answers
    #     "options": The question options
    #
    #  Internal use:
    #     "variable_id": the id of the random assignment, can be None
    #     "position": the position of the question, can be None
    # }

    def _format_question(self, question):
        self.logger.info("Format question ...")
        try:
            type = self._get_type(question)

            options = None

            variable_id, title = self._get_title(question['headings'])

            if title.startswith('Pepper:'):
                type = 'automatic'
                options = title.split(':')[1::]

            q = {
                'id': question['id'],
                'title': title,
                'type': type,
                'subtype': question['subtype'],
                'options': options,
                'required': question['required'],
                'validation': '',
                'position': question['position'],
                'variable_id': variable_id,
                'progression': self._get_progression(question['id'])
            }

            if 'answers' in question:
                if question['sorting'] is not None:
                    if question['sorting']['type'] == 'random':
                        random.shuffle(question['answers']['choices'])

                    if question['sorting']['type'] == 'flip':
                        rand = random.random()
                        if rand >= 0.5:
                            question['answers']['choices'].reverse()

                    if question['sorting']['type'] == 'textasc':
                        question['answers']['choices'] = sorted(question['answers']['choices'], key=lambda choice: choice['text'])

                q['answers'] = question['answers']

            if 'validation' in question:
                q['validation'] = question['validation']

            if 'display_options' in question:
                q['display_options'] = question['display_options']

            self.logger.info("Adapter: Question : %s" % q)
            return q
        except Exception as e:
            self.logger.error("Adapter: Error on format question: %s" % e)

    def _get_text(self, choice):
        return choice['text']

    #
    # API
    #
    def first(self):
        """Go to the first question."""
        self._current_page = self._get_item(self._current_survey['pages'], 'position', 1)
        question = self._get_item(self._current_page['questions'], 'position', 1)
        self._current_question = self._format_question(question)

    def next(self):
        """Go to the next question."""
        question = self._get_item(self._current_page['questions'], 'position', self._current_question['position'] + 1)
        if question is None:
            page = self._get_item(self._current_survey['pages'], 'position', self._current_page['position'] + 1)
            if page is None:  # no more question
                raise StopIteration()

            self._current_page = page
            question = self._get_item(self._current_page['questions'], 'position', 1)

        self._current_question = self._format_question(question)

    def get_current_question(self):
        """Get the next question."""
        self.logger.info("Adapter: Get next question")
        try:
            return self._current_question
        except Exception as e:
            self.logger.info("Error on get question : %s" % e)
            return None

    def get_choice(self, key, value):
        """Get the choice of the text."""
        self.logger.info("Get choice id in %s" % self._current_question['answers']['choices'])
        try:
            return self._get_item(self._current_question['answers']['choices'], key, value)
        except Exception as e:
            self.logger.error("Error on get choice id : %s" % e)

        return None

    def validate_requirements(self, answers):
        """
        Validate if the requirements are satisfied for the current question.

        Parameters:
            answers - (JSON) The set of answers of the current question

        Returns:
            True if the answers are correct, False otherwise.
        """
        self.logger.info("Validate answers : %s" % answers)
        try:
            is_valid = False
            if self._current_question['required'] is None:
                is_valid = True

            if self._current_question['type'] in ['single_choice', 'multiple_choice']:
                if len(answers) > 0:
                    is_valid = True

            if self._current_question['type'] == 'matrix':
                if len(answers) > 0:
                    is_valid = True

            if self._current_question['type'] == 'open_ended':
                for answer in answers:
                    if len(answer['text']) > 0:
                        is_valid = True

            return is_valid
        except Exception as e:
            self.logger.error("Error on check answers : %s" % e)

    def set_answers(self, answers):
        """Set the answer for the current question."""
        self.logger.info("Add answer : %s" % answers)
        try:
            page_index = 0
            for page in self._answer_payload['pages']:
                if page['id'] == self._current_page['id']:
                    break
                page_index += 1

            if page_index == len(self._answer_payload['pages']):  # page not found
                self._answer_payload['pages'].append({
                    "id": self._current_page['id'],
                    "questions": []
                })

            question_index = 0
            for question in self._answer_payload['pages'][page_index]['questions']:
                if question['id'] == self._current_question['id']:
                    break
                question_index += 1

            if question_index == len(self._answer_payload['pages'][page_index]['questions']):  # question not found
                self._answer_payload['pages'][page_index]['questions'].append({
                    "id": self._current_question['id']
                })

            _answers = []
            for answer in answers:
                _answers.append(answer)

            self._answer_payload['pages'][page_index]['questions'][question_index]['answers'] = _answers

            if self._current_question['variable_id'] is not None:
                self._answer_payload['pages'][page_index]['questions'][question_index]['variable_id'] = str(self._current_question['variable_id'])

        except Exception as e:
            self.logger.error("Error on add answer : %s" % e)

    def set_custom_variable(self, key, value):
        """
        Set a custom variable for the current survey.

        Parameters:
            key - (String) the key for the custom variable.
            value - (String) the value of the custom variable.

        Returns:
            Void
        """
        self.logger.info("Set custom variable : %s:%s" % (key, value))

        try:
            if 'custom_variables' not in self._answer_payload:
                self._answer_payload['custom_variables'] = {}
            self._answer_payload['custom_variables'][key] = value
        except Exception as e:
            self.logger.error("Error on set custom variables : %s" % e)

    def set_custom_value(self, value):
        """
        Set the custom value for the current response.

        Parameters:
            value - (String) the value of the custom value

        Returns:
            Void
        """
        self.logger.info("Set custom value : %s" % value)

        try:
            self._answer_payload['custom_value'] = value
        except Exception as e:
            self.logger.error("Error on set custom variables : %s" % e)

    def submit(self):
        """Submit the answers."""
        self.logger.info("Submit ... ")
        self._answer_payload['response_status'] = "completed"
        try:
            self.service.addAnswer(self._current_survey['collector']['id'], json.dumps(self._answer_payload))
        except Exception as e:
            self.logger.error("Error on submit : %s" % e)
