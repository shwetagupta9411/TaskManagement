from google.appengine.ext import ndb

class Task(ndb.Model):
    taskTitle = ndb.StringProperty()
    description = ndb.StringProperty(indexed=False)
    status = ndb.StringProperty()
    assignee = ndb.StringProperty()
    dueDate = ndb.DateTimeProperty()
    completionDate = ndb.DateTimeProperty()

class User(ndb.Model):
    email = ndb.StringProperty()
    boards = ndb.JsonProperty()

class Board(ndb.Model):
    boardTitle = ndb.StringProperty()
    tasks = ndb.StructuredProperty(Task, repeated=True)
    owner = ndb.StringProperty()
    users = ndb.StructuredProperty(User, repeated=True)
