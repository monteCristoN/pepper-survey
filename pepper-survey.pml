<?xml version="1.0" encoding="UTF-8" ?>
<Package name="pepper-survey" format_version="4">
    <Manifest src="manifest.xml" />
    <BehaviorDescriptions>
        <BehaviorDescription name="behavior" src="." xar="behavior.xar" />
    </BehaviorDescriptions>
    <Dialogs>
        <Dialog name="pepper-survey" src="dialogs/pepper-survey/pepper-survey.dlg" />
    </Dialogs>
    <Resources>
        <File name="surveys.beautified" src="data/surveys.beautified.json" />
        <File name="surveys" src="data/surveys.json" />
        <File name="index" src="html/index.html" />
        <File name="custom" src="html/css/custom.css" />
        <File name="custom.css" src="html/css/custom.css.src" />
        <File name="style.beautified" src="html/css/style.beautified.css" />
        <File name="style" src="html/css/style.css" />
        <File name="fontawesome-webfont" src="html/css/fonts/fontawesome-webfont.ttf" />
        <File name="roboto-regular" src="html/css/fonts/roboto-regular.ttf" />
        <File name="roboto-thin" src="html/css/fonts/roboto-thin.ttf" />
        <File name="jquery-1.11.0.min" src="html/js/jquery-1.11.0.min.js" />
        <File name="jquery.textfill" src="html/js/jquery.textfill.js" />
        <File name="main" src="html/js/main.js" />
        <File name="robotutils" src="html/js/robotutils.js" />
        <File name="robotutils.min" src="html/js/robotutils.min.js" />
        <File name="alsurveymonkey" src="scripts/alsurveymonkey.py" />
        <File name="main" src="scripts/main.py" />
        <File name="__init__" src="scripts/adapters/__init__.py" />
        <File name="surveymonkey" src="scripts/adapters/surveymonkey.py" />
        <File name="__init__" src="scripts/stk/__init__.py" />
        <File name="events" src="scripts/stk/events.py" />
        <File name="logging" src="scripts/stk/logging.py" />
        <File name="runner" src="scripts/stk/runner.py" />
        <File name="services" src="scripts/stk/services.py" />
        <File name="__init__" src="scripts/surveymonty/__init__.py" />
        <File name="client" src="scripts/surveymonty/client.py" />
        <File name="constants" src="scripts/surveymonty/constants.py" />
        <File name="exceptions" src="scripts/surveymonty/exceptions.py" />
        <File name="utils" src="scripts/surveymonty/utils.py" />
        <File name="VERSION" src="scripts/surveymonty/VERSION" />
        <File name="__init__" src="scripts/surveymonty/versions/__init__.py" />
        <File name="v3" src="scripts/surveymonty/versions/v3.json" />
        <File name="translation_en_US" src="translations/translation_en_US.qm" />
    </Resources>
    <Topics>
        <Topic name="pepper-survey_enu" src="dialogs/pepper-survey/pepper-survey_enu.top" topicName="pepper-survey" language="en_US" />
    </Topics>
    <IgnoredPaths />
    <Translations auto-fill="en_US">
        <Translation name="translation_en_US" src="translations/translation_en_US.ts" language="en_US" />
    </Translations>
</Package>
