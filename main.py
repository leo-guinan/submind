from enum import Enum
from typing import Optional

import typer
from decouple import config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from submind.models import Submind, SubmindSchedule
from submind.new_answers import pull_new_answers
from submind.research import update_research
from submind.twitter_style import twitter_style_submind_run

class Schedule(str, Enum):
    instant = "now"
    four_hour = "4h"
    eight_hour = "8h"
    daily = "daily"


def main(schedule: Optional[Schedule] = typer.Option(Schedule.daily)):
    # Replace 'database_url' with your actual database connection URL
    database_url = config('DATABASE_URL')
    engine = create_engine(database_url)

    Session = sessionmaker(bind=engine)
    session = Session()
    subminds = session.query(Submind).all()

    for submind in subminds:
        pull_new_answers(session, submind)

    update_research(session)
    # Now you can query for all Submind records with 'ACTIVE' status

    if schedule == Schedule.daily:

        all_subminds = session.query(Submind).filter(Submind.schedule == SubmindSchedule.DAILY).all()
        for submind in all_subminds:
            twitter_style_submind_run(submind, session)

    elif schedule == Schedule.eight_hour:
        all_subminds = session.query(Submind).filter(Submind.schedule == SubmindSchedule.EIGHT_HOUR).all()
        for submind in all_subminds:
            twitter_style_submind_run(submind, session)

    elif schedule == Schedule.four_hour:
        all_subminds = session.query(Submind).filter(Submind.schedule == SubmindSchedule.FOUR_HOUR).all()
        for submind in all_subminds:
            twitter_style_submind_run(submind, session)

    elif schedule == Schedule.instant:
        all_subminds = session.query(Submind).filter(Submind.schedule == SubmindSchedule.INSTANT).all()
        for submind in all_subminds:
            twitter_style_submind_run(submind, session)


if __name__ == "__main__":
    typer.run(main)
