"""
Template Application.

This is the defautl Template Application.
"""

import qi
import os
import re
import numbers
import ast

import stk.events
import stk.logging
import stk.runner
import stk.services

from adapters import surveymonkey

__version__ = '0.0.1'
__copyright__ = 'Copyright 2016, Aldebaran Robotics'
__author__ = 'hkuntz'
__email__ = 'hkuntz@aldebaran.com'

SERVICE_NAME = 'PepperSurvey'  # name of the registered service

@qi.multiThreaded()
class MyApplication(object):
    """Glorious Pepper survey application."""

    PKG_PATH = os.getcwd()  # get the behavior directory
    PKG_ID = os.path.split(PKG_PATH)[-1]
    APP_ID = 'com.softbank.{}'.format(PKG_ID)

    TOPIC_NAMES = None
    TOPIC_NAME = None
    TOPIC_PATHS = None
    SOUND_PATH = '{0}/sounds/{1}'.format(PKG_PATH, '{}')

    THRESHOLDS = {
        'age': 0.4,
        'gender': 0.4,
        'smile': 0.5,
        'expression': 0
    }

    EXPRESSION_LABELS = ['neutral', 'happy', 'surprised', 'angry', 'sad']

    # TODO: Retrieve these data through preferences
    SURVEY_ID = "115029485"

    DIALOG_TAG_ANIMATIONS = {
        'tablet_free': [
            'animations/Stand/BodyTalk/Listening/Listening_1',
            'animations/Stand/BodyTalk/Listening/Listening_2',
            'animations/Stand/BodyTalk/Listening/Listening_3',
            'animations/Stand/BodyTalk/Listening/Listening_4',
            'animations/Stand/BodyTalk/Listening/Listening_5',
            'animations/Stand/BodyTalk/Listening/Listening_6',
            'animations/Stand/BodyTalk/Speaking/BodyTalk_10',
            'animations/Stand/BodyTalk/Speaking/BodyTalk_12',
            'animations/Stand/BodyTalk/Speaking/BodyTalk_15',
            'animations/Stand/BodyTalk/Speaking/BodyTalk_16',
            'animations/Stand/BodyTalk/Speaking/BodyTalk_6',
            'animations/Stand/BodyTalk/Speaking/BodyTalk_7',
            'animations/Stand/BodyTalk/Speaking/BodyTalk_8',
            'animations/Stand/BodyTalk/Speaking/BodyTalk_9'
        ]
    }

    CUSTOM_FILES_SRC = os.path.join(PKG_PATH, 'html', 'css', 'custom.css.src')
    CUSTOM_FILES_DEST = os.path.join(PKG_PATH, 'html', 'css', 'custom.css')

    CUSTOMIZATION_DATA = {
        'customBody': 'radial-gradient(ellipse at top, rgba(76, 76, 76, 1) 0%, rgb(0, 0, 0) 50%)',
        'primaryColor': '#2e4058',
        'secondaryColor': '#f08f02',
        'alternativePrimaryColor': '#4d6d82',
        'primaryFontColor': '#FFFFFF',
        'secondaryFontColor': '#FFFFFF'
    }

    def __init__(self, qiapp):
        """Init application."""
        self.qiapp = qiapp
        self.s = stk.services.ServiceCache(qiapp.session)
        self.events = stk.events.EventHelper(qiapp.session)
        self.logger = stk.logging.get_logger(qiapp.session, self.APP_ID)

        self._init_dialog(['pepper-survey'], 'pepper-survey')
        self._init_customization()
        self._init_survey()
        self._init_inactivity_watcher()

        # Signals
        self.tabletEvent = qi.Signal()

    #
    # Tablet
    #
    @qi.nobind
    def _show_webview(self):
        self.logger.verbose('Attempting to start tablet webview')
        tablet = self.s.ALTabletService
        if tablet:
            robot_ip = tablet.robotIp()
            app_url = 'http://{}/apps/{}/'.format(robot_ip, self.PKG_ID)
            tablet.showWebview(app_url)
        else:
            self.logger.warning('Lost tablet service, cannot load application: {}'.format(self.PKG_ID))

    @qi.nobind
    def _hide_webview(self):
        try:
            self.s.ALTabletService.hideWebview()
        except Exception as e:
            self.logger.error("error on hide webview : %s" % e)

    #
    # STK.runner required functions
    #
    @qi.nobind
    def on_start(self):
        """Called when the application is intialized."""
        self.logger.info('on_start')
        self._start_survey()
        self._start_watch_face_characteristics()
        self._deactivate_autonomous_magic()
        self._show_webview()  # load the web view that will start the dialog

    @qi.nobind
    def on_stop(self):
        """Cleanup."""
        self.logger.info('on_stop')
        self.stop()

    @qi.bind(returnType=qi.Void, paramsType=[])
    def stop(self):
        """Stop the application."""
        self.logger.info('Stopped by user request.')
        self._stop_watch_face_characteristics()
        self._activate_autonomous_magic()
        self._clean_dialog()
        self.qiapp.stop()

    #
    # Customization part
    #
    @qi.nobind
    def _init_customization(self):
        self.logger.info("Init Customization.")

        data = self._get_customization_data()

        try:
            pattern = re.compile(r'\{{2}(' + '|'.join(data.keys()) + ')\}{2}')
            with open(self.CUSTOM_FILES_SRC, 'r') as fin:
                with open(self.CUSTOM_FILES_DEST, 'w') as fout:
                    content = pattern.sub(lambda x: data[x.group()[2:-2]], fin.read())
                    fout.write(content)
        except Exception as e:
            self.logger.error("Error on init customization : %s" % e)

    def _get_customization_data(self):
        self.logger.info("Get customization data")

        try:
            data = self.s.ALPreferenceManager.getValue('com.softbank.peppersurvey', 'CustomizationData')
            self.logger.info("custom data : %s (%s)" % (data, type(data)))
            if data is not None:
                return ast.literal_eval(data)
        except Exception as e:
            self.logger.error("Error on get customization data : %s" % e)

        self.logger.error("Use the default customization data.")
        return self.CUSTOMIZATION_DATA

    #
    # Autonomous Magic
    #
    @qi.nobind
    def _deactivate_autonomous_magic(self):
        try:
            # self.s.ALBasicAwareness.setEnabled(False, _async=True)
            # self.s.ALBackgroundMovement.setEnabled(False, _async=True)
            self.s.ALListeningMovement.setEnabled(False, _async=True)
            self.s.ALSpeakingMovement.setEnabled(False, _async=True)
        except Exception as e:
            self.logger.error("error during activate Basic Awareness : %s " % e)

    @qi.nobind
    def _activate_autonomous_magic(self):
        try:
            # self.s.ALBackgroundMovement.setEnabled(True, _async=True)
            self.s.ALListeningMovement.setEnabled(True, _async=True)
            self.s.ALSpeakingMovement.setEnabled(True, _async=True)
            # self.s.ALBasicAwareness.setEnabled(True, _async=True)
            # self.s.ALBasicAwareness.setTrackingMode("Head")
        except Exception as e:
            self.logger.error("error during activate Basic Awareness : %s " % e)

    #
    # ALMemory
    #
    @qi.nobind
    def _get_almemory_answer(self, key):
        self.logger.info("Get ALMemory answer : %s" % key)
        try:
            value = self.s.ALMemory.getData(key)
            if value is not None:
                return [{'text': str(value)}]
        except Exception as e:
            self.logger.error("Error on get almemory answer : %s" % e)

        return []

    #
    # Dialog
    #
    @qi.nobind
    def _init_dialog(self, directories, file_name):
        self.logger.info("Init dialog")
        language = self.s.ALDialog.getLanguage()
        code = self.s.ALDialog.convertLongToNU(language)
        self.TOPIC_NAMES = directories  # ['music-boxes-b2b']
        self.TOPIC_NAME = file_name  # 'music-boxes-b2b'
        self.TOPIC_PATHS = {topic: '{0}/dialogs/{1}/{1}_{2}.top'.format(self.PKG_PATH, topic, '{}') for topic in self.TOPIC_NAMES}
        self.TOPIC_PATH = self.TOPIC_PATHS[self.TOPIC_NAME].format(code)

        self._dialog_future = None

        try:
            self._clean_dialog()  # in case of ...
        except Exception:
            pass

        def _task():
            try:
                self.s.ALDialog._addDialogFromTopicBox(self.TOPIC_PATH, self.PKG_ID)
                self.s.ALDialog.activateTopic(self.TOPIC_NAME)
                self.s.ALDialog.subscribe(self.APP_ID)
            except Exception as e:
                self.logger.error("Error on init dialog : %s" % e)

            try:
                self.s.ALAnimationPlayer.addTagForAnimations(self.DIALOG_TAG_ANIMATIONS)
            except Exception as e:
                self.logger.error("Error on set tag for animation : %s" % e)

            self._deactivate_tag('nps')
            self._deactivate_tag('rating')
            self._deactivate_tag('choices')

        qi.async(_task)

    @qi.nobind
    def _clean_dialog(self):

        def _clean_almemory(key):
            try:
                self.s.ALMemory.removeData(key)
            except Exception as e:
                self.logger.error("Error on clean almemory : %s" % e)

        # TODO: call the clean almemory for the current key

        try:
            self.s.ALDialog.deactivateTopic(self.TOPIC_NAME)
        except Exception as e:
            self.logger.warning("Error on deactivate topic : %s" % e)

        try:
            self.s.ALDialog.unloadTopic(self.TOPIC_NAME)
        except Exception as e:
            self.logger.warning("Error on unloading topic: : %s" % e)

        try:
            self.s.ALDialog.unsubscribe(self.APP_ID)
        except Exception as e:
            self.logger.warning("Error on unsubscribing dialog: %s" % e)

    @qi.nobind
    def _say(self, tag, wait=False):
        try:
            if self._dialog_future:
                self._dialog_future.cancel()

            self._dialog_future = self.s.ALAnimatedSpeech._stopAll(True, _async=True) \
                .andThen(lambda x: self.s.ALDialog.gotoTag("EMPTY", self.TOPIC_NAME, _async=True)).unwrap() \
                .andThen(lambda x: self.s.ALDialog.gotoTag(tag, self.TOPIC_NAME, _async=True))

            if wait:
                self._dialog_future.unwrap().wait()

        except Exception as e:
            self.logger.error("Error in say : %s" % e)

    @qi.nobind
    def _activate_tag(self, tag):
        self.logger.info('Activate tag : %s' % tag)
        try:
            self.s.ALDialog.activateTag(tag, self.TOPIC_NAME, _async=True)
        except Exception as e:
            self.logger.error('Error on activate tag: %s' % e)

    @qi.nobind
    def _deactivate_tag(self, tag):
        self.logger.info('Deactivate tag : %s' % tag)
        try:
            self.s.ALDialog.deactivateTag(tag, self.TOPIC_NAME, _async=True)
        except Exception as e:
            self.logger.error('Error on activate tag: %s' % e)

    @qi.nobind
    def _set_dynamic_concepts(self, concept_name, data):
        self.logger.info("Set dynamic concepts ")
        try:
            self.s.ALDialog.setConcept(concept_name, "English", data)
        except Exception as e:
            self.logger.error("Error on set dynamic concepts : %s" % e)

    #
    # People Perception
    #
    @qi.nobind
    def _start_watch_face_characteristics(self):
        self.logger.info('Start watch face characteristics')

        self._face_characteristics = {
            'age': None,
            'gender': None,
            'smile': None,
            'expression': None
        }

        self._detection_task = qi.PeriodicTask()
        self._detection_task.setCallback(self._update_face_characteristics_info)
        self._detection_task.setUsPeriod(1*2000000)
        self._detection_task.start(True)

    @qi.nobind
    def _stop_watch_face_characteristics(self):
        self.logger.info('Stop watch face characteristics')
        self._detection_task.stop()

    @qi.nobind
    def _compute_face_characteristic(self, key, value, confidence):
        if confidence <= self.THRESHOLDS[key]:
            return

        if self._face_characteristics[key] is None:
            new_value = value
        else:
            if isinstance(value, list):
                new_value = []
                for old, new in zip(self._face_characteristics[key], value):
                    new_value.append((old + new) / 2)
            if isinstance(value, numbers.Number):
                new_value = (self._face_characteristics[key] + value) / 2

        self._face_characteristics[key] = new_value

    @qi.nobind
    def _update_face_characteristics_info(self):
        ids = self.s.ALMemory.getData("PeoplePerception/PeopleList")
        if len(ids) != 1 or len(ids) > 1:
            return

        self._face_id = ids[0]
        self.s.ALFaceCharacteristics.analyzeFaceCharacteristics(self._face_id, _async=True).then(self._on_face_characteristics_analyzed)

    @qi.nobind
    def _on_face_characteristics_analyzed(self, value):

        if not value:
            return

        try:
            gender = self.s.ALMemory.getData("PeoplePerception/Person/"+str(self._face_id)+"/GenderProperties")
            if gender is not None:
                self._compute_face_characteristic('gender', gender[0], gender[1])

            age = self.s.ALMemory.getData("PeoplePerception/Person/"+str(self._face_id)+"/AgeProperties")
            if age is not None:
                self._compute_face_characteristic('age', age[0], age[1])

            smile = self.s.ALMemory.getData("PeoplePerception/Person/"+str(self._face_id)+"/SmileProperties")
            if smile is not None:
                self._compute_face_characteristic('smile', smile[0], smile[1])

            expression = self.s.ALMemory.getData("PeoplePerception/Person/"+str(self._face_id)+"/ExpressionProperties")
            if expression is not None:
                self._compute_face_characteristic('expression', expression, sum(expression))  # expression [neutral, happy, surprised, angry, sad]

        except Exception as e:
            self.logger.error("Error update face characteristics : %s" % e)

    @qi.nobind
    def _get_label_gender(self):
        if self._face_characteristics['gender'] is None:
            return 'unknown'
        elif self._face_characteristics['gender'] > 0.5:
            return 'male'
        else:
            return 'female'

    @qi.nobind
    def _get_label_expression(self):
        if self._face_characteristics['expression'] is None:
            return 'unknown'

        values = self._face_characteristics['expression']
        index = values.index(max(values))
        return self.EXPRESSION_LABELS[index]

    @qi.nobind
    def _get_label_age(self):
        if self._face_characteristics['age'] is None:
            return 'unknown'

        return str(int(self._face_characteristics['age']))

    @qi.nobind
    def _get_label_smile(self):
        if self._face_characteristics['smile'] is None:
            return 'unknown'

        return str(self._face_characteristics['smile'])

    @qi.nobind
    def _get_face_characteristic_answer(self, key):
        self.logger.info("Get face characteristic answer for %s" % key)

        if key not in self._face_characteristics:
            return []

        if key == 'age':
            value = self._get_label_age()

        if key == 'gender':
            value = self._get_label_gender()

        if key == 'smile':
            value = self._get_label_smile()

        if key == 'expression':
            value = self._get_label_expression()

        try:
            return [{'text': value}]
        except Exception as e:
            self.logger.error("Error on face characteristic answer : %s" % e)

        return []

    #
    # Inactivity
    #
    @qi.nobind
    def _init_inactivity_watcher(self):
        self._inactity_future = None

    @qi.nobind
    def _cancel_inactivity_watcher(self):
        try:
            if self._inactity_future:
                self._inactity_future.cancel()
        except Exception as e:
            self.logger.error("Error on cancel inactivity wtcher : %s" % e)

        self._inactity_future = None

    @qi.nobind
    def _start_inactivity_watcher(self, delay):
        self._cancel_inactivity_watcher()
        self._inactity_future = qi.async(self._say, 'INACTIVITY', delay=delay*1000000)

    #
    # Survey management
    #
    @qi.nobind
    def _init_survey(self):
        self.logger.info("Init survey")
        self._survey_id = None
        self._survey_provider = surveymonkey.SurveyMonkeyAdapter(self.s.ALSurveyMonkey, self.logger)

        try:
            self._survey_id = self.s.ALPreferenceManager.getValue('com.softbank.peppersurvey', 'SurveyId')
        except Exception as e:
            self.logger.error("Error on init survey : %s" % e)

    @qi.nobind
    def _start_survey(self):
        self.logger.info("Start survey %s" % self._survey_id)
        if self._survey_id is None:
            qi.async(self._on_event, 'internal', "INTERNAL_ERROR", None)
            return

        self._survey_provider.start_survey(self._survey_id)
        self._survey_provider.first()

    @qi.nobind
    def _set_question(self, question):
        self.logger.info("Set question : %s" % question)
        try:
            self.s.ALMemory.insertData('pepper-survey/CurrentQuestion/Title', question['title'])
            self.s.ALMemory.insertData('pepper-survey/TabletFocus', 0)

            self.tabletEvent("SET_QUESTION", question)

            self._current_tag_input = None

            # Activate the right dialog input
            if question['type'] == 'nps':
                self._activate_tag('nps')
                self._current_tag_input = 'nps'

            if question['type'] == 'rating':
                self._activate_tag('rating')
                self._current_tag_input = 'rating'

            if question['type'] in ['single_choice', 'multiple_choice']:
                data = [choice['text']for choice in question['answers']['choices']]
                self._set_dynamic_concepts('choices', data)
                self._activate_tag('choices')
                self._current_tag_input = 'choices'

            if question['type'] in ['matrix', 'slider', 'single_line', 'multiple_line']:
                self.s.ALMemory.insertData('pepper-survey/TabletFocus', 1)

        except Exception as e:
            self.logger.error("Error on set question : %s" % e)

    @qi.nobind
    def _set_next_button_state(self, answers):
        self.logger.info("Check answers: %s" % answers)
        try:
            activate = self._survey_provider.validate_requirements(answers)
            self.tabletEvent('TOGGLE_NEXT_BUTTON', activate)
        except Exception as e:
            self.logger.error("Error on check answers : %s" % e)

    @qi.nobind
    def _go_to_next_question(self):
        self.logger.info("Go to next question")
        try:
            self._survey_provider.next()
            evt = 'ASK_QUESTION'
        except StopIteration:
            evt = "SURVEY_FINISHED"

        qi.async(self._on_event, 'internal', evt, None)

    @qi.nobind
    def _process_automatic_question(self, question):
        self.logger.info("Process automatic question : %s" % question)

        if question['options'][0] == 'FaceCharacteristics':
            answer = self._get_face_characteristic_answer(question['options'][1].lower())

        if question['options'][0] == 'ALMemory':
            answer = self._get_almemory_answer(question['options'][1])

        try:
            self._survey_provider.set_answers(answer)
        except Exception as e:
            self.logger.error("Error on process automatic question : %s" % e)

    @qi.nobind
    def _say_presentation(self, question):
        self.logger.info("Say presentation : %s" % question)
        try:
            self.s.ALMemory.insertData('pepper-survey/Speech/Presentation', question['title'])
            self._say('SPEECH', True)
        except Exception as e:
            self.logger.error("Error on say presentation : %s" % e)

    @qi.nobind
    def _process_input_dialog(self, key, value):
        choice = self._survey_provider.get_choice(key, value)
        if choice is not None:
            self.tabletEvent("SELECT_ANSWER", choice['id'])

    @qi.nobind
    def _get_value_from_word(self, word):
        inputs = {
            'awesome': 10,
            'great': 10,
            'amazing': 10,
            'excellent': 10,
            'very good': 10,
            'magnificent': 10,
            'super': 10,
            'superb': 10,
            'incredible': 10,
            'impressive': 10,
            'marvelous': 10,
            'a lot': 10,
            'nice': 7,
            'funny': 7,
            'okay': 5,
            'fine': 5,
            'soso': 5,
            'average': 5,
            'not bad': 5,
            'a little': 5,
            'a little bit': 5,
            'not much': 5,
            'bad': 0,
            'very bad': 0,
            'awful': 0,
            'ridiculous': 0,
            'terrible': 0,
            'horrible': 0,
            'boring': 0,
            'extremely boring': 0,
            'very boring': 0,
            'not at all': 0
        }
        if word in inputs:
            return inputs[word]

        return None

    @qi.nobind
    def _on_input_dialog_choices(self, value):
        """
        Process the input received by the dialog for single/multiple choices.

        Parameters:
                value - (String) the input from the dialog
        """
        self._process_input_dialog('text', value)

    @qi.nobind
    def _on_input_dialog_nps(self, value):
        """
        Process the input received by the dialog for NPS.

        Parameters:
                value - (String) the input from the dialog
        """
        note = self._get_value_from_word(value)
        if note is not None:
            value = note
        self._process_input_dialog('position', value+1)

    @qi.nobind
    def _on_input_dialog_rating(self, value):
        """
        Process the input received by the dialog for NPS.

        Parameters:
                value - (String) the input from the dialog
        """
        note = self._get_value_from_word(value)
        if note is not None:
            value = note
        self._process_input_dialog('position', value)

    #
    # Event handlers
    #
    @qi.nobind
    def _set_state(self, state):
        self.logger.info("Set state : %s" % state)
        try:
            self._say(state)
            self.tabletEvent("STATE_CHANGED", state)
        except Exception as e:
            self.logger.error("Error on set state : %s" % e)

    @qi.nobind
    def _on_event(self, sender, evt, value):
        if evt == 'LOADED':
            evt = "ASK_QUESTION"

        if evt == "ASK_QUESTION":
            question = self._survey_provider.get_current_question()

            if question['type'] == 'automatic':
                self._process_automatic_question(question)
                self._go_to_next_question()
                return

            if question['type'] == 'speech':
                self._say_presentation(question)
                self._survey_provider.set_answers([])
                self._go_to_next_question()
                return

            self._answers = []
            self._set_question(question)
            self._set_next_button_state(self._answers)
            self._set_state("QUESTION")

        if evt == "INPUT_DIALOG_CHOICES":
            self._on_input_dialog_choices(value)

        # NPS INPUT DIALOG
        if evt == "INPUT_DIALOG_RATING":
            self._on_input_dialog_rating(value)

        if evt == "INPUT_DIALOG_NPS":
            self._on_input_dialog_nps(value)

        if evt == "ON_ANSWER_CHANGED":
            self._say('ON_ANSWER_SELECTED')
            self._answers = value
            self._set_next_button_state(value)

        if evt == "ON_NEXT_QUESTION":
            if not self._survey_provider.validate_requirements(self._answers):
                self._say('NO_ANSWER')
                return

            if self._current_tag_input is not None:
                self._deactivate_tag(self._current_tag_input)

            self._survey_provider.set_answers(self._answers)
            self.tabletEvent("STATE_CHANGED", 'ANSWERED')
            self._say('ANSWERED', True)
            self._go_to_next_question()

        if evt == "SURVEY_FINISHED":
            try:
                robot_id = self.s.ALMemory.getData('RobotConfig/Head/FullHeadId')
                self._survey_provider.set_custom_value(robot_id)
                self._survey_provider.set_custom_variable('ROBOT_ID', robot_id)
            except Exception as e:
                self.logger.error("Error on get robot_id : %s" % e)
            self._survey_provider.submit()
            self._set_state("END_OF_SURVEY")

        # Inactivity
        if evt == "INACTIVITY":
            self._say('INACTIVITY')

        if evt == "INACTIVITY_FINISHED":
            self._cancel_inactivity_watcher()
            self._inactity_future = qi.async(self._on_event, 'internal', 'INACTIVITY_REACHED', None, delay=10000000)
            return  # Not start the inactivity watcher

        if evt == "INACTIVITY_REACHED":
            evt = 'QUIT'

        if evt == "QUIT":
            self._set_state('QUIT')

        if evt == "INTERNAL_ERROR":
            self._say('INTERNAL_ERROR', True)
            evt = 'EXIT'

        if evt == "EXIT":
            self.stop()

        # self._start_inactivity_watcher(15)

    @qi.bind(returnType=qi.Void, paramsType=(qi.String, qi.String), methodName="onTabletEvent")
    def on_tablet_event_with_value(self, evt, value):
        """Called to send event from the tablet."""
        self.logger.info('onTabletEvent %s : %s' % (evt, value))
        self._on_event('tablet', evt, value)

    @qi.bind(returnType=qi.Void, paramsType=(qi.String, ), methodName="onTabletEvent")
    def on_tablet_event(self, evt):
        """Called to send event from the tablet."""
        self.logger.info('onTabletEvent %s' % (evt))
        self._on_event('tablet', evt, None)

    @qi.bind(returnType=qi.Void, paramsType=(qi.String, qi.String), methodName="onDialogEvent")
    def on_dialog_event_with_value(self, evt, value):
        """Called to send event from the dialog."""
        self.logger.info('onDialogEvent %s : %s' % (evt, value))
        self._on_event('dialog', evt, value)

    @qi.bind(returnType=qi.Void, paramsType=(qi.String, ), methodName="onDialogEvent")
    def on_dialog_event(self, evt):
        """Called to send event from the dialog."""
        self.logger.info('onDialogEvent %s' % evt)
        self._on_event('dialog', evt, None)

####################
# Setup and Run
####################

if __name__ == '__main__':
    stk.runner.run_service(MyApplication, SERVICE_NAME)
