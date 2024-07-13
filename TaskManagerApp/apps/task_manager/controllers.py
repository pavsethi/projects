"""
This file defines actions, i.e. functions the URLs are mapped into
The @action(path) decorator exposed the function at URL:

    http://127.0.0.1:8000/{app_name}/{path}

If app_name == '_default' then simply

    http://127.0.0.1:8000/{path}

If path == 'index' it can be omitted:

    http://127.0.0.1:8000/

The path follows the bottlepy syntax.

@action.uses('generic.html')  indicates that the action uses the generic.html template
@action.uses(session)         indicates that the action uses the session
@action.uses(db)              indicates that the action uses the db
@action.uses(T)               indicates that the action uses the i18n & pluralization
@action.uses(auth.user)       indicates that the action requires a logged in user
@action.uses(auth)            indicates that the action requires the auth object

session, db, T, auth, and tempates are examples of Fixtures.
Warning: Fixtures MUST be declared with @action.uses({fixtures}) else your app will result in undefined behavior
"""

from py4web import action, request, abort, redirect, URL
from pydal.validators import *
from py4web.utils.form import Form, FormStyleBulma
from yatl.helpers import A
from .common import db, session, T, cache, auth, logger, authenticated, unauthenticated, flash


@action("index", method=["GET", "POST"])
@action.uses("task_page.html", auth)
def index():
    user = auth.get_user()
    if user:        
        return locals()
    else:
        redirect(URL('auth/login'))


@action("create_task", method=["GET", "POST"])
@action.uses("create_task.html", auth.user)
def create_task():
    form = Form(db.task, formstyle=FormStyleBulma)
    if form.accepted:
        redirect(URL('index'))
    return locals()


@action("edit_task/<task_id:int>", method=["GET", "POST"])
@action.uses("create_task.html", auth.user)
def edit_task(task_id):

    #hiding all the information that shouldn't be shown when a user is editing a task
    db.task.id.readable = db.task.id.writable = False
    db.task.created_on.readable = db.task.created_on.writable = False
    db.task.created_by.readable = db.task.created_by.writable = False
    db.task.modified_on.readable = db.task.modified_on.writable = False
    db.task.modified_by.readable = db.task.modified_by.writable = False

    user = auth.get_user()
    thetask = db.task[task_id]
    who_can_edit = thetask['created_by']   #What id is the task assigned to
    who_can_edit_manager = (db.auth_user[who_can_edit])['manager_id']
    if((who_can_edit != (user['id'])) and (who_can_edit_manager != (user['id'])) and (user['id'] != (db(db.auth_user).select().as_list()[0])['id'])): #Equal to current user id?
        print("not right user")
        print(user['id'])
        print((db(db.auth_user).select().as_list()[0])['id'])
        redirect(URL('index'))
        return
    print(who_can_edit_manager)
    form = Form(db.task, formstyle=FormStyleBulma, record=task_id)
    if form.accepted: #Weird issue deleting task doesn't redirect to index, so you could submit form again and go to a nonexistent webpage
        redirect(URL('index'))
    return locals()


# @action("api/tasks", method="POST")  
# @action.uses(db, auth.user)
# def api_newTask():
#     data=request.json
#     #user = auth.get_user();
#     #print(user);
#     #data['created_by'] = auth.get_user();
#     myresult = db.task.validate_and_insert(**request.json)
#     return myresult


@action("api/tasks", method="GET")
@action.uses(db)
def api_getTasks():
    current_user_id = auth.user_id

    # Fetch all subordinates recursively
    def get_all_subordinates(user_id):
        subordinates = [user_id]
        direct_subordinates = db(db.auth_user.manager_id == user_id).select(db.auth_user.id)
        for subordinate in direct_subordinates:
            # Recursive call to fetch sub-subordinates
            subordinates.extend(get_all_subordinates(subordinate.id))
        return subordinates

    subordinate_ids = get_all_subordinates(current_user_id)
    tasks = db((db.task.created_by.belongs(subordinate_ids)) |
               (db.task.assigned_user_id == current_user_id)).select()
    # tasks = db(db.task).select()
    return {"tasks": tasks.as_list()}


@action("api/filters/<filter>", method="GET")
@action.uses(db, auth.user)
def apply_filter(filter):
    user_id = auth.user_id
    print("received user_id:", request.params.get('user_id'))
    print("full Request URL:", request.url)
    if not user_id:
        return dict(tasks=[])

    if filter == 'date_created':
        tasks = db(db.task).select(orderby=~db.task.created_on).as_list()
    elif filter == 'deadline':
        tasks = db(db.task).select(orderby=~db.task.deadline).as_list()
    elif filter == 'status':
        status = request.params.get('status', 'pending')
        tasks = db(db.task.status == status).select().as_list()
    elif filter == 'created_by_self':
        tasks = db(db.task.created_by == user_id).select().as_list()
    elif filter == 'assigned_to_self':
        tasks = db(db.task.assigned_user_id == user_id).select().as_list()
    elif filter == 'created_by_specific_user':
        specific_user_id = request.params.get('user_id')
        print(specific_user_id)
        tasks = db(db.task.created_by == specific_user_id).select().as_list()
    elif filter == 'assigned_to_specific_user':
        specific_user_id = request.params.get('user_id')
        tasks = db(db.task.assigned_user_id == specific_user_id).select().as_list()
    elif filter == 'created_by_managed_user':
        tasks = db(db.task).select().as_list();
        for i in range((len(tasks)-1), -1, -1):
            tempid = (tasks[i])["created_by"];
            if((db.auth_user[tempid])['manager_id'] == None):
                del (tasks[i]);
    elif filter == 'assigned_to_managed_user':
        tasks = db(db.task).select().as_list();
        for i in range((len(tasks)-1), -1, -1):
            tempid = (tasks[i])["assigned_user_id"]
            if((db.auth_user[tempid])['manager_id'] == None):
                del (tasks[i]);
    else:
        specific_user_id = request.params.get('user_id')
        tasks = db(db.task).select().as_list()

    return dict(tasks=tasks)


@action("api/comments", method=["GET"])
@action.uses(db, auth.user)
def api_get_comments():
    task_id = request.params.get('task_id')
    if not task_id:
        return abort(400, 'Task ID is required')
    comments = db(db.comment.task_id == task_id)\
        .select(db.comment.ALL, db.auth_user.first_name, db.auth_user.last_name,
                join=db.auth_user.on(db.comment.created_by == db.auth_user.id))
    comments_list = []
    for comment in comments:
        comments_list.append({
            "id": comment.comment.id,
            "content": comment.comment.content,
            "author": f"{comment.auth_user.first_name} {comment.auth_user.last_name}"
        })
    return dict(comments=comments_list)


@action("api/comments", method=["POST"])
@action.uses(db, auth.user)
def api_post_comments():
    task_id = request.json.get('task_id')
    content = request.json.get('content')
    if not task_id or not content:
        return abort(400, 'Task ID and content are required')

    comment_id = db.comment.validate_and_insert(task_id=task_id, content=content)
    comment = db(db.comment.id == comment_id["id"])\
                .select(db.comment.ALL, db.auth_user.first_name, db.auth_user.last_name,
                        join=db.auth_user.on(db.comment.created_by == db.auth_user.id)).first()

    return dict(comment=comment.as_dict(), author=f"{comment.auth_user.first_name} {comment.auth_user.last_name}")


@action('api/users', method='GET')
@action.uses(db, auth.user)
def get_users():
    users = db(db.auth_user).select().as_list()
    return dict(users=users)

# @action('api/can_edit_task/<task_id:int>', method=['GET'])
# @action.uses(auth.user, db)
# def can_edit_task(task_id):
#     task = db.task[task_id]
#     if not task:
#         return {'can_edit': False}

#     current_user_id = auth.current_user_id

#     # Check if the current user is the task creator or the task is assigned to them
#     if current_user_id == task.created_by or current_user_id == task.assigned_user_id:
#         return {'can_edit': True}

#     # Check up the management chain
#     manager_id = db.auth_user[current_user_id].manager_id
#     while manager_id:
#         if manager_id == task.created_by or manager_id == task.assigned_user_id:
#             return {'can_edit': True}
#         manager_id = db.auth_user[manager_id].manager_id

#     return {'can_edit': False}