"""Demo content for local development (the Apps Script demo's seedDemoData). Run: python -m app.cli seed-demo

App-level fixture script: like migrations and tests it writes rows directly instead of going through
every module's service, so it can create a consistent world in one transaction.
"""
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.core.utils import slugify, utcnow
from app.modules import load_models
from app.modules.companies.models import Company, CompanyLocation, CompanyMember
from app.modules.feed.models import Post
from app.modules.identity.models import User
from app.modules.opportunities.models import Event, Job
from app.modules.profiles.models import Experience, Profile, Skill, UserSkill

load_models()

DEMO_DOMAIN = "@demo.koforlink"
DEMO_PASSWORD = "Demo@1234"
PEOPLE = [
    ("Ama", "Mensah", "Software Engineer", "Koforidua", "Professional",
     "Full-stack engineer building tools for African SMEs", ["JavaScript", "Node.js", "Python", "SQL"]),
    ("Kwame", "Boateng", "HR Manager", "Koforidua", "Employer",
     "Talent & People Operations at Eastern Tech Hub", ["Recruiting", "HR Policy", "Training"]),
    ("Akosua", "Adjei", "Graphic Designer", "Koforidua", "Professional",
     "Brand identity & digital design for growing businesses", ["Figma", "Illustrator", "Branding"]),
    ("Yaw", "Asante", "Agribusiness Consultant", "Nsawam", "Professional",
     "Helping farmers reach markets", ["Agribusiness", "Supply Chain", "Market Research"]),
    ("Efua", "Owusu", "Student", "Koforidua", "Student",
     "Final year IT student at Koforidua Technical University", ["Python", "Data Analysis"]),
]
COMPANY_EMAIL = "hello@easterntechhub.example.com"
COMPANY_PHONE = "+233 34 000 0000"


def seed(db: Session) -> dict:
    existing = db.scalars(select(User).where(User.email.like(f"%{DEMO_DOMAIN}"))).all()
    if existing:
        return {"skipped": True, "demoUsers": len(existing)}
    password_hash = hash_password(DEMO_PASSWORD)
    users = []
    for idx, (first, last, title, city, role, headline, skills) in enumerate(PEOPLE):
        email = f"{first.lower()}.{last.lower()}{DEMO_DOMAIN}"
        user = User(first_name=first, last_name=last, email=email, phone=f"+233 20 000 000{idx}",
                    password_hash=password_hash, role=role, status="Active", city=city, professional_title=title,
                    verified=idx < 2, email_verified=True)
        db.add(user)
        db.flush()
        db.add(Profile(user_id=user.id, headline=headline, about=f"{first} is a {title} based in {city}, Ghana.",
                       location=city, country="Ghana", region="Eastern Region", city=city,
                       website=f"https://example.com/{first.lower()}", languages="English, Twi",
                       interests="Technology, Community", contact_email=email, contact_visibility="Public",
                       completion_pct=80))
        for name in skills:
            db.add(UserSkill(user_id=user.id, skill_name=name, level="Advanced", endorsements=3))
            if not db.scalar(select(Skill.id).where(Skill.name == name)):
                db.add(Skill(name=name, category="General"))
                db.flush()
        db.add(Experience(user_id=user.id, title=title, company="Eastern Tech Hub", location=city,
                          start_date="2021-01", current=True, description=f"Working on regional projects in {city}."))
        users.append(user)
    owner = users[1]
    company = Company(
        name="Eastern Tech Hub", slug=slugify("Eastern Tech Hub"), industry="Information Technology",
        description="A technology hub in Koforidua supporting startups, training and digital skills across the "
                    "Eastern Region.",
        website="https://easterntechhub.example.com", email=COMPANY_EMAIL, phone=COMPANY_PHONE, founded="2018",
        size="11-50", owner_id=owner.id, verified=True, status="Active",
    )
    db.add(company)
    db.flush()
    for user in users:
        is_owner = user is owner
        db.add(CompanyMember(company_id=company.id, user_id=user.id, role="Owner" if is_owner else "Employee",
                             title="HR Manager" if is_owner else "Team Member", status="Active"))
    head_office = CompanyLocation(
        company_id=company.id, name="Koforidua Head Office", address="Effiduase Road, Koforidua", country="Ghana",
        region="Eastern Region", city="Koforidua", area="Effiduase", ghana_post_gps="EN-0123-4567",
        landmark="Opposite Total Filling Station", latitude=6.0940, longitude=-0.2591, phone=COMPANY_PHONE,
        email=COMPANY_EMAIL, opening_time="08:00", closing_time="17:00", is_hq=True, status="Active")
    branch = CompanyLocation(
        company_id=company.id, name="Accra Branch", address="Ring Road Central, Accra", country="Ghana",
        region="Greater Accra", city="Accra", area="Central", ghana_post_gps="GA-0234-5678", landmark="Near Circle",
        latitude=5.5600, longitude=-0.2057, phone=COMPANY_PHONE, email=COMPANY_EMAIL, opening_time="08:00",
        closing_time="17:00", is_hq=False, status="Active")
    db.add_all([head_office, branch])
    db.flush()
    deadline = (utcnow() + timedelta(days=30)).date()
    for title, kind, arrangement, level, skills, location in (
        ("Frontend Developer", "Full-time", "On-site", "Mid", "JavaScript, HTML, CSS, React", head_office),
        ("Digital Marketing Officer", "Full-time", "Hybrid", "Junior", "SEO, Content, Social Media", head_office),
        ("Data Analyst Intern", "Internship", "On-site", "Entry", "Excel, SQL, Python", branch),
    ):
        db.add(Job(
            company_id=company.id, posted_by=owner.id, title=title,
            description=f"Join Eastern Tech Hub as a {title} and help build digital solutions for the Eastern Region.",
            responsibilities="Collaborate with the team, deliver quality work, support clients.",
            requirements="Relevant experience, strong communication, willingness to learn.", skills=skills,
            salary="GHS 3,000 - 6,000 monthly", salary_min=3000, salary_max=6000, currency="GHS",
            employment_type=kind, experience_level=level, deadline=deadline, work_arrangement=arrangement,
            location_id=location.id, city=location.city, region=location.region, country="Ghana",
            latitude=location.latitude, longitude=location.longitude, status="Open",
        ))
    for i, (author, content, as_company) in enumerate((
        (owner, "We are hiring a Frontend Developer at Eastern Tech Hub, Koforidua. Come build with us!", True),
        (users[2], "Just finished a design sprint with a local SME in Koforidua. Great to see businesses "
                   "embracing digital branding.", False),
        (users[4], "Looking for internship opportunities in data analysis around the Eastern Region. Any leads?",
         False),
    )):
        posted = utcnow() - timedelta(hours=i * 6)
        db.add(Post(user_id=author.id, company_id=company.id if as_company else None, content=content,
                    view_count=12, status="Active", created_at=posted, updated_at=posted))
    event_day = (utcnow() + timedelta(days=21)).date()
    db.add(Event(
        title=f"Koforidua Tech Career Fair {event_day.year}",
        description="Meet employers, attend workshops and discover opportunities across the Eastern Region.",
        organizer_id=owner.id, company_id=company.id, event_date=event_day, start_time="09:00", end_time="16:00",
        location_name="Eastern Tech Hub, Koforidua", address="Effiduase Road, Koforidua", city="Koforidua",
        region="Eastern Region", latitude=6.0940, longitude=-0.2591, registration_required=True,
        max_attendees=200, status="Active",
    ))
    db.commit()
    return {"skipped": False, "demoUsers": len(users), "companyId": company.id, "password": DEMO_PASSWORD}
