# step 1: Look in database for all actively running subminds.

# step 2: For each submind, check for related thoughts that were recorded after the last time the submind checked for them.

# step 3: Based on current status of submind + new thoughts, figure out what you should focus on for this action cycle.

# step 4: based on that focus item, generate a list of questions that need to be answered, and whether they should be answered by the user or by an internet search

# step 5: for each question, do a lookup of information related to that question, and record the answers as thoughts.

# step 6: update the current status of the submind based on the new thoughts that were recorded.

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker

from submind.models import Submind
from submind.thoughts import find_related_thoughts


def name_for_scalar_relationship(base, local_cls, referred_cls, constraint):
    name = referred_cls.__name__.lower() + "_ref"
    return name

def name_for_collection_relationship(base, local_cls, referred_cls, constraint):
    name = referred_cls.__name__.lower() + "_collection"
    return name



# Replace 'database_url' with your actual database connection URL
database_url = "postgresql://thoughts_owner:cxYU8TpgO9Wd@ep-noisy-firefly-a5bez5i9.us-east-2.aws.neon.tech/thoughts?sslmode=require"
engine = create_engine(database_url)

Session = sessionmaker(bind=engine)
session = Session()

# Now you can query for all Submind records with 'ACTIVE' status
active_subminds = session.query(Submind).filter(Submind.status == 'ACTIVE').all()

for submind in active_subminds:
    last_checked = submind.lastRun

    related_thoughts = find_related_thoughts(submind,session)



    print(submind.id, submind.name, submind.status)