from operator import itemgetter
import webapp2
import jinja2
from google.appengine.api import users
import os
from model import Board
from model import User
from model import Task
from google.appengine.ext import ndb
import logging
from webapp2_extras import sessions
from webapp2_extras import sessions_memcache
from datetime import datetime
import time

JINJA_ENVIRONMENT = jinja2.Environment(loader=jinja2.FileSystemLoader(
    os.path.dirname(__file__)),extensions=["jinja2.ext.autoescape"], autoescape=True)

# To display messages
class BasicReqHandler(webapp2.RequestHandler):
    @webapp2.cached_property
    def session(self):
        """Returns a session using the default cookie key"""
        # return self.session_store.get_session()
        return self.session_store.get_session(
            name='mc_session',
            factory=sessions_memcache.MemcacheSessionFactory)

    def dispatch(self):
        # Get a session store for this request.
        self.session_store = sessions.get_store(request=self.request)
        try:
            # Dispatch the request.
            webapp2.RequestHandler.dispatch(self)
        finally:
            # Save all sessions.
            self.session_store.save_sessions(self.response)

    def add_message(self, message, level=None):
        self.session.add_flash(message, level, key='_messages')

    @webapp2.cached_property
    def messages(self):
        return self.session.get_flashes(key='_messages')

# To create a task board
class CreateBoard(BasicReqHandler):
    def post(self):
        user = users.get_current_user()
        if user:
            key_user = ndb.Key(User, user.email())
            user_details = key_user.get()
            board = Board()
            board.boardTitle = self.request.get('title').strip()
            board.owner = user.email()
            board.users.append(user_details)
            boardKey = board.put()
            boardKeyId = boardKey.get().key.id()
            if user_details:
                if user_details.boards: key_dict = user_details.boards
                else: key_dict = {}
                key_dict[boardKeyId] = boardKey.urlsafe()
                userModel = User(key=key_user, boards=key_dict, email=user.email())
                userModel.put()

            self.add_message('Task Board created successfully.', 'success')
            self.redirect('/boards', abort=False)
            return
        else:
            self.redirect('/', abort=False)

# To View a task board
class BoardView(BasicReqHandler):
    def get(self, id=None):
        user = users.get_current_user()
        ex_user = True
        board = []
        cmpTask = []
        actTask = []
        cmpToday = []
        taskLen = []
        if user:
            url = users.create_logout_url(self.request.uri)
            url = url.split("board")[0]+"boards"
            url_string = "Logout"
            key_user = ndb.Key(User, user.email())
            if not key_user.get():
                userModel = User(key=key_user, email=user.email())
                userModel.put()
                ex_user = False
            board = Board.get_by_id(int(id))
            if board:
                if board.tasks:
                    taskLen = board.tasks
                    for task in board.tasks:
                        if task.status == "not completed":
                            actTask.append(task.status)
                        if task.status == "completed":
                            cmpTask.append(task.status)
                            if datetime.now().date() == task.completionDate.date():
                                cmpToday.append(task.status)

        else:
            url = users.create_login_url(self.request.uri)
            url_string = "Login"

        template_values = {
            "messages": self.messages,
            "url": url,
            "url_string": url_string,
            "user": user,
            "ex_user": ex_user,
            "board_url": "board/"+id,
            "key_board": id,
            "board": board,
            "taskLen": len(taskLen),
            "cmpTask": len(cmpTask),
            "actTask": len(actTask),
            "cmpToday": len(cmpToday)
        }
        template = JINJA_ENVIRONMENT.get_template("/TaskManagement/taskboard.html")
        self.response.write(template.render(template_values))

# To view a list of task boards
class Boards(BasicReqHandler):
    def get(self):
        user = users.get_current_user()
        ex_user = True
        tasksBoards = []
        if user:
            url = users.create_logout_url(self.request.uri)
            url_string = "Logout"
            key_user = ndb.Key(User, user.email())
            user_details = key_user.get()
            if not user_details:
                userModel = User(key=key_user, email=user.email())
                userModel.put()
                ex_user = False

            if user_details:
                if user_details.boards != None:
                    for boa in user_details.boards.values():
                        t_key = ndb.Key(urlsafe=boa)
                        tasksBoards.append(t_key.get())

        else:
            url = users.create_login_url(self.request.uri)
            url_string = "Login"

        template_values = {
            "messages": self.messages,
            "tasksBoards": tasksBoards,
            "url": url,
            "url_string": url_string,
            "user": user,
            "ex_user": ex_user
        }
        template = JINJA_ENVIRONMENT.get_template("/TaskManagement/boards.html")
        self.response.write(template.render(template_values))

# To create a task
class CreateTask(BasicReqHandler):
    def post(self):
        board_url = self.request.get("board_url")
        keyconcat = self.request.get("taskName").lower().strip()+'/'+self.request.get("key_board")
        key_name = ndb.Key(Task, keyconcat)
        if not key_name.get():
            task = Task(key=key_name)
            task.taskTitle = self.request.get("taskName").lower().strip()
            task.dueDate = datetime.strptime(self.request.get("dueDate"), '%Y-%m-%d')
            task.description = self.request.get("description")
            task.status = self.request.get("status")
            task.assignee = self.request.get("assignee")
            task.put()
            board = Board.get_by_id(int(self.request.get("key_board")))
            board.tasks.append(key_name.get())
            board.put()
            self.add_message('Task Created successfully.', 'success')
        else:
            self.add_message('Task with same task name already exists.', 'danger')

        self.redirect(str(board_url), abort=False)

# To invite a user to task board
class BoardInvite(BasicReqHandler):
    def post(self):
        user = users.get_current_user()
        board_url = self.request.get("board_url")
        if user:
            board = Board.get_by_id(int(self.request.get("key_board")))
            user_email_key = ndb.Key(User, str(self.request.get("email_id").strip()))
            invited_user = user_email_key.get()
            if invited_user:
                if invited_user.boards:
                    board_dict = invited_user.boards
                else:
                    board_dict = {}
                board_dict[board.key.id()] = board.key.urlsafe()
                invited_user.boards = board_dict
                invited_user.put()
                existing_u = []
                for addedUser in board.users:
                    existing_u.append(addedUser.email.strip())

                if invited_user.key.id().strip() not in existing_u:
                    board.users.append(invited_user)
                    board.put()
                    self.add_message('User invited successfully.', 'success')
                    self.redirect(str(board_url), abort=False)
                else:
                    self.add_message('User already invited.', 'danger')
                    self.redirect(str(board_url), abort=False)

                return
            else:
                self.add_message('User not found.', 'danger')
                self.redirect(str(board_url), abort=False)
                return

        else:
            self.add_message('Not authorized.', 'danger')
            self.redirect('/', abort=False)
            return

# To delete a task
class DeleteTask(BasicReqHandler):
    def get(self):
        tName = self.request.get("name")
        board_url = self.request.get("board_url")
        keyconcat = tName.lower().strip()+'/'+self.request.get("key_board")
        key_name = ndb.Key(Task, keyconcat)
        taskDel = key_name.get()
        if taskDel:
            taskDel.key.delete()
            boardDel = Board.get_by_id(int(self.request.get("key_board")))
            for i in range(0,len(boardDel.tasks)):
                if str(boardDel.tasks[i].taskTitle.lower()).strip() == tName.lower().strip():
                    boardDel.tasks.pop(i)
                    break
            boardDel.put()
            self.add_message('Task Deleted successfully.', 'success')
        else:
            boardDel = Board.get_by_id(int(self.request.get("key_board")))
            for i in range(0,len(boardDel.tasks)):
                if str(boardDel.tasks[i].taskTitle.lower()).strip() == tName.lower().strip():
                    boardDel.tasks.pop(i)
                    break
            boardDel.put()
            self.add_message('Task not found in database.', 'danger')
        self.redirect(str(board_url), abort=False)

# To update a task board status
class UpdateTaskStatus(BasicReqHandler):
    def post(self):
        tName = self.request.get("name")
        board_url = self.request.get("board_url")
        checkbovVal = self.request.get("checkbovVal")
        keyconcat = tName.lower().strip()+'/'+self.request.get("key_board")
        key_name = ndb.Key(Task, keyconcat)
        taskStatus = key_name.get()
        if taskStatus:
            if checkbovVal == "true":
                taskStatus.status = "completed"
                now = datetime.now() #using utc time
                taskStatus.completionDate = now
            elif checkbovVal == "false":
                taskStatus.status = "not completed"
                taskStatus.completionDate = None

            taskStatus.put()
            boardCheck = Board.get_by_id(int(self.request.get("key_board")))

            for i in range(0,len(boardCheck.tasks)):
                if str(boardCheck.tasks[i].taskTitle.lower()).strip() == tName.lower().strip():
                    boardCheck.tasks[i].status = taskStatus.status
                    boardCheck.tasks[i].completionDate = taskStatus.completionDate
            boardCheck.put()
            self.add_message('Task status updated successfully', 'success')
        else:
            self.add_message('Task not found.', 'danger')
        self.redirect(str(board_url), abort=False)

# To update a task 
class UpdateTask(BasicReqHandler):
    def post(self):
        tName = self.request.get("taskName").lower().strip()
        board_url = self.request.get("board_url")
        keyconcat = tName+'/'+self.request.get("key_board")
        key_name = ndb.Key(Task, keyconcat)
        task = key_name.get()
        if task:
            task.dueDate = datetime.strptime(self.request.get("dueDate"), '%Y-%m-%d')
            task.description = self.request.get("description")
            task.assignee = self.request.get("assignee")
            if task.status == self.request.get("status"):
                task.completionDate = task.completionDate
            else:
                if self.request.get("status") == "completed":
                    now = datetime.now() #using utc time
                    task.completionDate = now
                elif self.request.get("status") == "not completed":
                    task.completionDate = None
            task.status = self.request.get("status")
            task.put()
            boardCheck = Board.get_by_id(int(self.request.get("key_board")))
            for i in range(0,len(boardCheck.tasks)):
                if str(boardCheck.tasks[i].taskTitle.lower()).strip() == tName.lower().strip():
                    boardCheck.tasks[i].status = task.status
                    boardCheck.tasks[i].description = task.description
                    boardCheck.tasks[i].assignee = task.assignee
                    boardCheck.tasks[i].dueDate = task.dueDate
                    boardCheck.tasks[i].completionDate = task.completionDate
            boardCheck.put()
            self.add_message('Task updated successfully', 'success')
        else:
            self.add_message('Task not found.', 'danger')
        self.redirect(str(board_url), abort=False)

# To edit a task board d
class EditBoard(BasicReqHandler):
    def post(self):
        user = users.get_current_user()
        board_url = self.request.get("board_url")
        boardName = self.request.get("boardName").strip()
        userToRem = self.request.get("userRemove").strip()
        board = Board.get_by_id(int(self.request.get("key_board")))
        if board:
            board.boardTitle = boardName
            if userToRem != "" and user.email() == board.owner:
                key_user = ndb.Key(User, userToRem)
                user_details = key_user.get()
                if user_details:
                    if user_details.boards != None:
                        del user_details.boards[str(self.request.get("key_board"))]
                        user_details.put()

                for i in range(0,len(board.users)):
                    if str(board.users[i].email.lower()).strip() == userToRem.lower():
                        board.users.pop(i)
                        break

            for i in range(0,len(board.tasks)):
                if str(board.tasks[i].assignee.lower()).strip() == userToRem.lower().strip():
                    board.tasks[i].assignee = 'Unassigned'

            board.put()
            self.add_message('Board updated successfully', 'success')
        else:
            self.add_message("Board doesn't exist", 'success')

        self.redirect(str(board_url), abort=False)

#To delete a task board d
class DeleteBoard(BasicReqHandler):
    def get(self, id=None):
        user = users.get_current_user()
        board = Board.get_by_id(int(id))
        board_url = self.request.get("board_url")
        form_url = '/board/{}'.format(id)
        if board:
            if len(board.users) == 1 and len(board.tasks) == 0 and user.email() == board.users[0].email.strip():
                key_user = ndb.Key(User, user.email())
                user_details = key_user.get()
                if user_details:
                    if user_details.boards != None:
                        del user_details.boards[str(id)]
                        user_details.put()
                board.key.delete()
                self.add_message('Board deleted successfully.', 'success')
                self.redirect('/boards', abort=False)
            else:
                self.add_message('Please remove all the tasks and users in order to delete this board', 'danger')
                self.redirect(form_url, abort=False)
        else:
            self.add_message('Board not found in database.', 'danger')
            self.redirect(form_url, abort=False)


# welcome to application class D
class MainPage(BasicReqHandler):
    def get(self):
        self.response.headers["Content-Type"] = "text/html"
        url = ""
        url_string = ""
        user = users.get_current_user()
        ex_user = True
        if user:
            url = users.create_logout_url(self.request.uri)
            url_string = "Logout"
            key_user = ndb.Key(User, user.email())
            if not key_user.get():
                userModel = User(key=key_user, email=user.email())
                userModel.put()
                ex_user = False
        else:
            url = users.create_login_url(self.request.uri)
            url_string = "Login"

        template_values = {"url": url, "url_string": url_string, "user": user, "ex_user": ex_user}
        template = JINJA_ENVIRONMENT.get_template("/TaskManagement/welcome.html")
        self.response.write(template.render(template_values))


config = {}
config["webapp2_extras.sessions"] = {
    "secret_key": "_session_key",
}

app = webapp2.WSGIApplication(
    [
        ("/", MainPage),
        ("/create_board", CreateBoard),
        ("/boards", Boards),
        ("/board/(\d+)", BoardView),
        ("/create_task", CreateTask),
        ("/board_invite", BoardInvite),
        ("/delete_task", DeleteTask),
        ("/update_status", UpdateTaskStatus),
        ("/update_task", UpdateTask),
        ("/edit_board", EditBoard),
        ("/delete_board/(\d+)", DeleteBoard)
    ],
    debug=True,
    config=config)
