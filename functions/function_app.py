"""関数アプリのエントリーポイント"""

import azure.functions as func
from src.blob_triggered_import import bp_blob_triggered_import
from src.delete_progresses import bp_delete_progresses
from src.get_answer import bp_get_answer
from src.get_healthcheck import bp_get_healthcheck
from src.get_progresses import bp_get_progresses
from src.get_question import bp_get_question
from src.get_tests import bp_get_tests
from src.post_answer import bp_post_answer
from src.post_progress import bp_post_progress
from src.put_en2ja import bp_put_en2ja
from src.queue_triggered_answer import bp_queue_triggered_answer

app = func.FunctionApp()

app.register_blueprint(bp_blob_triggered_import)
app.register_blueprint(bp_delete_progresses)
app.register_blueprint(bp_get_answer)
app.register_blueprint(bp_get_healthcheck)
app.register_blueprint(bp_get_progresses)
app.register_blueprint(bp_get_question)
app.register_blueprint(bp_get_tests)
app.register_blueprint(bp_post_answer)
app.register_blueprint(bp_post_progress)
app.register_blueprint(bp_put_en2ja)
app.register_blueprint(bp_queue_triggered_answer)
