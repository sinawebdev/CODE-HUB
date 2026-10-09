"""PostgreSQL regression: simultaneous viewers must preserve all engagement counts.

Set TEST_DATABASE_URL to a disposable PostgreSQL database whose name ends in _tests.
Run from the backend folder: python ../tools/check_concurrency.py
"""
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from threading import Barrier
from uuid import uuid4

from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.core.database import Base
from app.core.utils import utcnow
from app.modules import load_models
from app.modules.feed import service as feed_service
from app.modules.feed.models import Comment, Post, Reaction
from app.modules.identity.models import User
from app.modules.profiles import service as profiles_service
from app.modules.stories import service as stories_service
from app.modules.stories.models import Story, StoryView

url = os.environ.get("TEST_DATABASE_URL", "")
if not url or not make_url(url).drivername.startswith("postgresql") or not make_url(url).database.endswith("_tests"):
    raise SystemExit("Set TEST_DATABASE_URL to a disposable PostgreSQL database ending in _tests.")
load_models()
engine = create_engine(url)
Base.metadata.create_all(engine)
stamp = uuid4().hex
with Session(engine, expire_on_commit=False) as db:
    people = [User(first_name="Concurrency", last_name=f"Viewer{i}", email=f"{stamp}.{i}@example.com",
                   password_hash="unused-in-this-check", email_verified=True) for i in range(4)]
    db.add_all(people)
    db.flush()
    for user in people:
        profiles_service.create_profile(db, user)
    ids = [u.id for u in people]
    post = Post(user_id=ids[0], content="Concurrent engagement check")
    story = Story(user_id=ids[0], file_id="test-only", expires_at=utcnow() + timedelta(hours=1))
    db.add_all([post, story])
    db.commit()
    post_id, story_id = post.id, story.id

barrier = Barrier(3)


def engage(user_id):
    with Session(engine, expire_on_commit=False) as db:
        # Deliberately retain stale objects in three independent sessions before mutation.
        cached_post, cached_story = db.get(Post, post_id), db.get(Story, story_id)
        user = db.get(User, user_id)
        barrier.wait(timeout=10)
        stories_service.view_story(db, user, cached_story.id)
        feed_service.get_post(db, cached_post.id, user.id)
        feed_service.react(db, user, post_id, "like")
        feed_service.comment(db, user, post_id, "Concurrent comment", None)
        feed_service.share_post(db, user, post_id)


try:
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(engage, ids[1:]))
    with Session(engine) as db:
        post, story = db.get(Post, post_id), db.get(Story, story_id)
        counts = {"storyViews": story.view_count, "postViews": post.view_count,
                  "likes": post.like_count, "comments": post.comment_count, "shares": post.share_count}
        assert all(value == 3 for value in counts.values()), counts
        for model, field, value in ((StoryView, StoryView.story_id, story_id),
                                    (Reaction, Reaction.post_id, post_id), (Comment, Comment.post_id, post_id)):
            assert db.scalar(select(func.count()).select_from(model).where(field == value)) == 3
        print(f"Concurrent PostgreSQL regression passed: {counts}")
finally:
    with Session(engine) as db:
        db.execute(delete(User).where(User.id.in_(ids)))
        db.commit()
    engine.dispose()
