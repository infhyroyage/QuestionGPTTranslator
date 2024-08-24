"""
Entry Point of Functions Application
"""

import azure.functions as func
from src.answer import bp_answer
from src.en2ja import bp_en2ja
from src.healthcheck import bp_healthcheck
from src.import_items import bp_import_items
from src.question import bp_question
from src.test import bp_test
from src.tests import bp_tests
from src.upsert_answers import bp_upsert_answers

app = func.FunctionApp()

app.register_blueprint(bp_answer)
app.register_blueprint(bp_en2ja)
app.register_blueprint(bp_healthcheck)
app.register_blueprint(bp_import_items)
app.register_blueprint(bp_question)
app.register_blueprint(bp_test)
app.register_blueprint(bp_tests)
app.register_blueprint(bp_upsert_answers)
