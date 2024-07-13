"""
This file defines the database models
"""

from .common import db, Field, auth
from pydal.validators import *

### Define your table below
#
# db.define_table('thing', Field('name'))
#
## always commit your models to avoid problems later
#
# db.commit()
#

db.define_table(
    "task", 
    Field("title", "text", requires=IS_NOT_EMPTY()), 
    Field("description", "text", requires=IS_NOT_EMPTY()),
    Field("deadline", "date", requires=[IS_NOT_EMPTY(), 
          IS_DATE(error_message='must be DD-MM-YYYY')]),
    Field("status", requires=IS_IN_SET(['pending', 'acknowledged', 'rejected', 'completed', 'failed'])),
    Field('assigned_user_id', 'reference auth_user', requires=[IS_NOT_EMPTY(), IS_IN_DB(db, "auth_user", lambda r:f"{r.first_name}{r.last_name}")]),
    auth.signature
)

db.define_table(
    "comment",
    Field("task_id", "reference task"),
    Field("content", "text", requires=IS_NOT_EMPTY()),
    auth.signature
)


