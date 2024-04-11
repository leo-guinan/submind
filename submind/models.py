import enum

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Enum, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import UniqueConstraint, Index

Base = declarative_base()

context_task_table = Table('_ContextToTask', Base.metadata,
                           Column('A', Integer, ForeignKey('Context.id'), primary_key=True),
                           Column('B', Integer, ForeignKey('task.id'), primary_key=True)
                           )

intent_thought_table = Table('_IntentToThought', Base.metadata,
                             Column('A', Integer, ForeignKey('intent.id'), primary_key=True),
                             Column('B', Integer, ForeignKey('Thought.id'), primary_key=True)
                             )

related_thoughts_table = Table('_SubmindRelatedThoughts', Base.metadata,
                                 Column('A', Integer, ForeignKey('Submind.id'), primary_key=True),
                                 Column('B', Integer, ForeignKey('Thought.id'), primary_key=True)
                                 )

pending_thoughts_table = Table('_SubmindPendingThoughts', Base.metadata,
                                Column('A', Integer, ForeignKey('Submind.id'), primary_key=True),
                                Column('B', Integer, ForeignKey('Thought.id'), primary_key=True)
                                )



class Account(Base):
    __tablename__ = 'account'

    id = Column(String, primary_key=True)
    userId = Column(String, ForeignKey('user.id', ondelete='CASCADE'))
    type = Column(String)
    provider = Column(String)
    providerAccountId = Column(String)
    refresh_token = Column(Text)
    access_token = Column(Text)
    expires_at = Column(Integer)
    token_type = Column(String)
    scope = Column(String)
    id_token = Column(Text)
    session_state = Column(String)

    user = relationship("User", back_populates="accounts")

    __table_args__ = (
        UniqueConstraint('provider', 'providerAccountId'),
    )


class Session(Base):
    __tablename__ = 'session'

    id = Column(String, primary_key=True)
    sessionToken = Column(String, unique=True)
    userId = Column(String, ForeignKey('user.id', ondelete='CASCADE'))
    expires = Column(DateTime)

    user = relationship("User", back_populates="sessions")


class User(Base):
    __tablename__ = 'user'

    id = Column(String, primary_key=True)
    createdAt = Column(DateTime)
    email = Column(String, unique=True)
    emailVerified = Column(DateTime)
    name = Column(String)
    stripeCustomerId = Column(String)
    role = Column(String, default="user")
    image = Column(String)
    acceptedPolicy = Column(DateTime)

    accounts = relationship("Account", back_populates="user")
    sessions = relationship("Session", back_populates="user")
    thoughts = relationship("Thought", back_populates="owner")
    communities = relationship("Community", back_populates="creator")
    memberships = relationship("Membership", back_populates="member")
    contexts = relationship("Context", back_populates="owner")
    tasks = relationship("Task", back_populates="owner")
    intents = relationship("Intent", back_populates="owner")
    subscriptions = relationship("Subscription", back_populates="user")
    googleCalendars = relationship("GoogleCalendar", back_populates="user")
    subminds = relationship("Submind", back_populates="owner")
    questions = relationship("Question", back_populates="owner")


class Subscription(Base):
    __tablename__ = 'subscription'

    id = Column(Integer, primary_key=True)
    createdAt = Column(DateTime)
    updatedAt = Column(DateTime)
    active = Column(Boolean, default=True)
    stripeSubscriptionId = Column(String)
    userId = Column(String, ForeignKey('user.id'))
    priceId = Column(Integer, ForeignKey('price.id'))

    user = relationship("User", back_populates="subscriptions")
    price = relationship("Price", back_populates="subscriptions")


class VerificationToken(Base):
    __tablename__ = 'verification_token'

    identifier = Column(String, primary_key=True)
    token = Column(String, unique=True)
    expires = Column(DateTime)

    __table_args__ = (
        UniqueConstraint('identifier', 'token'),
    )


class Community(Base):
    __tablename__ = 'community'

    id = Column(Integer, primary_key=True)
    creatorId = Column(String, ForeignKey('user.id'))
    name = Column(String)

    creator = relationship("User", back_populates="communities")
    memberships = relationship("Membership", back_populates="community")


class Membership(Base):
    __tablename__ = 'membership'

    id = Column(Integer, primary_key=True)
    memberId = Column(String, ForeignKey('user.id'))
    communityId = Column(Integer, ForeignKey('community.id'))

    member = relationship("User", back_populates="memberships")
    community = relationship("Community", back_populates="memberships")


class Context(Base):
    __tablename__ = 'Context'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    details = Column(String)
    ownerId = Column(String, ForeignKey('user.id'))
    path = Column(String)
    goal = Column(String)

    owner = relationship("User", back_populates="contexts")
    thoughts = relationship("Thought", back_populates="context")
    tasks = relationship("Task", secondary=context_task_table, back_populates="contexts")

    __table_args__ = (
        UniqueConstraint('ownerId', 'name'),
    )


class Thought(Base):
    __tablename__ = 'Thought'

    id = Column(Integer, primary_key=True)
    createdAt = Column(DateTime)
    content = Column(String)
    ownerId = Column(String, ForeignKey('user.id'))
    contextId = Column(Integer, ForeignKey('Context.id'))
    uuid = Column(String)
    submindId = Column(Integer, ForeignKey('Submind.id'))
    parentId = Column(Integer, ForeignKey('Thought.id'))

    parent = relationship("Thought", remote_side=[id], backref="children")
    owner = relationship("User", back_populates="thoughts")
    context = relationship("Context", back_populates="thoughts")
    intents = relationship("Intent", secondary=intent_thought_table, back_populates="thoughts")
    submind = relationship("Submind", back_populates="thoughts")
    relatedSubminds = relationship("Submind", secondary=related_thoughts_table, back_populates="relatedThoughts")
    pendingSubminds = relationship("Submind", secondary=pending_thoughts_table, back_populates="pendingThoughts")

class Tool(Base):
    __tablename__ = 'tool'

    id = Column(Integer, primary_key=True)
    url = Column(String)
    name = Column(String)
    description = Column(String)
    pattern = Column(String)
    slug = Column(String)

    __table_args__ = (
        UniqueConstraint('url', 'slug'),
    )


class Task(Base):
    __tablename__ = 'task'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    ownerId = Column(String, ForeignKey('user.id'))
    uuid = Column(String, unique=True)

    owner = relationship("User", back_populates="tasks")
    contexts = relationship("Context", secondary=context_task_table, back_populates="tasks")


class TaskDependency(Base):
    __tablename__ = 'task_dependency'

    dependentId = Column(Integer, ForeignKey('task.id'), primary_key=True)
    dependsOnId = Column(Integer, ForeignKey('task.id'), primary_key=True)

    dependent = relationship("Task", foreign_keys=[dependentId], backref="dependantOn")
    dependsOn = relationship("Task", foreign_keys=[dependsOnId], backref="dependencies")


class Intent(Base):
    __tablename__ = 'intent'

    id = Column(Integer, primary_key=True)
    content = Column(String)
    ownerId = Column(String, ForeignKey('user.id'))
    createdAt = Column(DateTime)
    documentUUID = Column(String, unique=True)
    thoughts = relationship("Thought", secondary=intent_thought_table, back_populates="intents")

    owner = relationship("User", back_populates="intents")


class EntityId(Base):
    __tablename__ = 'entity_id'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    createdAt = Column(DateTime)


class DefaultTool(Base):
    __tablename__ = 'default_tool'

    id = Column(Integer, primary_key=True)
    createdAt = Column(DateTime)
    toolId = Column(Integer, ForeignKey('tool.id'), unique=True)

    tool = relationship("Tool")


class GoogleCalendar(Base):
    __tablename__ = 'google_calendar'

    id = Column(Integer, primary_key=True)
    createdAt = Column(DateTime)
    updatedAt = Column(DateTime)
    userId = Column(String, ForeignKey('user.id'))
    accessToken = Column(String)
    refreshToken = Column(String)
    tokenType = Column(String)
    expiryDate = Column(DateTime)
    name = Column(String)
    email = Column(String)

    user = relationship("User", back_populates="googleCalendars")

    __table_args__ = (
        UniqueConstraint('userId', 'email'),
        UniqueConstraint('userId', 'accessToken'),
    )


class CalendarEvent(Base):
    __tablename__ = 'calendar_event'

    id = Column(Integer, primary_key=True)
    googleCalendarId = Column(Integer, ForeignKey('google_calendar.id'))
    googleEventId = Column(String)
    summary = Column(String)
    description = Column(String)
    start = Column(DateTime)
    end = Column(DateTime)
    timeZone = Column(String)
    location = Column(String)
    status = Column(String)

    googleCalendar = relationship("GoogleCalendar")

    __table_args__ = (
        Index('idx_google_calendar_id', 'googleCalendarId'),
    )


class Price(Base):
    __tablename__ = 'price'

    id = Column(Integer, primary_key=True)
    createdAt = Column(DateTime)
    updatedAt = Column(DateTime)
    active = Column(Boolean)
    amount = Column(Integer)
    currency = Column(String)
    interval = Column(String)
    stripePriceId = Column(String)
    productId = Column(Integer, ForeignKey('product.id'))

    product = relationship("Product", back_populates="prices")
    subscriptions = relationship("Subscription", back_populates="price")


class Product(Base):
    __tablename__ = 'product'

    id = Column(Integer, primary_key=True)
    createdAt = Column(DateTime)
    updatedAt = Column(DateTime)
    active = Column(Boolean)
    name = Column(String)
    description = Column(String)
    stripeProductId = Column(String)

    prices = relationship("Price", back_populates="product")


class SubmindSchedule(enum.Enum):
    DAILY = 'DAILY'
    EIGHT_HOUR = 'EIGHT_HOUR'
    FOUR_HOUR = 'FOUR_HOUR'
    INSTANT = 'INSTANT'


class Submind(Base):
    __tablename__ = 'Submind'

    id = Column(Integer, primary_key=True)
    createdAt = Column(DateTime)
    updatedAt = Column(DateTime)
    name = Column(String)
    description = Column(String)
    lastRun = Column(DateTime)
    ownerId = Column(String, ForeignKey('user.id'))
    contextId = Column(Integer, ForeignKey('Context.id'))
    documentUUID = Column(String, unique=True)
    status = Column(Enum('ACTIVE', 'READY', 'COMPLETED', name='submind_status'))
    questions = relationship("Question", back_populates="submind")
    owner = relationship("User", back_populates="subminds")
    context = relationship("Context")
    mindUUID = Column(String)
    founderUUID = Column(String)
    valuesUUID = Column(String)
    schedule = Column(Enum(SubmindSchedule))
    thoughts = relationship("Thought", back_populates="submind")
    relatedThoughts = relationship("Thought", secondary=related_thoughts_table, back_populates="relatedSubminds")
    pendingThoughts = relationship("Thought", secondary=pending_thoughts_table, back_populates="pendingSubminds")



class Question(Base):
    __tablename__ = 'Question'

    id = Column(Integer, primary_key=True)
    createdAt = Column(DateTime)
    updatedAt = Column(DateTime)
    content = Column(String)
    ownerId = Column(String, ForeignKey('user.id'))
    contextId = Column(Integer, ForeignKey('Context.id'))
    forHuman = Column(Boolean)
    forInternet = Column(Boolean)
    owner = relationship("User", back_populates="questions")
    submindId = Column(Integer, ForeignKey('Submind.id'))
    submind = relationship("Submind", back_populates="questions")
    context = relationship("Context")

class Answer(Base):
    __tablename__ = 'Answer'

    id = Column(Integer, primary_key=True)
    createdAt = Column(DateTime)
    updatedAt = Column(DateTime)
    content = Column(String)
    questionId = Column(Integer, ForeignKey('Question.id'))
    source = Column(String)
    requestId = Column(Integer)
    submindId = Column(Integer, ForeignKey('Submind.id'))
    submind = relationship("Submind")
    question = relationship("Question")


class Like(Base):
    __tablename__ = 'Like'

    id = Column(Integer, primary_key=True)
    createdAt = Column(DateTime)
    submindId = Column(String, ForeignKey('Submind.id'))
    thoughtId = Column(Integer, ForeignKey('Thought.id'))

    submind = relationship("Submind")
    thought = relationship("Thought")
