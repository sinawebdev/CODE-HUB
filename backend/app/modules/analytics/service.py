"""Analytics composes earlier module services with manager authorization."""
from app.modules.feed import service as feed_service
from app.modules.opportunities import service as opportunities_service


def company_analytics(db, user, company_id):
    payload = opportunities_service.company_analytics_base(db, user, company_id)
    posts = feed_service.company_post_stats(db, company_id)
    payload.update(posts=len(posts),
                   engagement=sum(p["likeCount"] + p["commentCount"] + p["shareCount"] for p in posts),
                   postEngagement=[{"title": p["content"][:60] or "Post",
                                    "likes": p["likeCount"], "comments": p["commentCount"]}
                                   for p in posts[:10]])
    return payload


def job_analytics(db, user, job_id):
    return opportunities_service.job_analytics(db, user, job_id)
