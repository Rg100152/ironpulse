"""
Seed IronPulse with realistic sample workouts, goals and progress milestones.
Run: python3 seed_fitness.py
Safe to run more than once (existing seed rows are cleared first).
"""

from datetime import datetime, timedelta

from app import get_db, init_db

WORKOUTS = [
    # exercise, category, sets, reps, weight, calories, notes, days ago
    ("Barbell Back Squat", "Strength", 5, 5, 82.5, 310, "Progressive overload +2.5kg", 34),
    ("Bench Press", "Strength", 4, 8, 62.5, 260, "Controlled eccentric", 33),
    ("Romanian Deadlift", "Strength", 4, 10, 70.0, 280, "Hamstring focus", 31),
    ("Pull Ups", "Strength", 4, 12, 0.0, 180, "Bodyweight", 29),
    ("Overhead Press", "Strength", 4, 8, 40.0, 210, "Standing strict", 27),
    ("Incline Dumbbell Press", "Strength", 3, 12, 24.0, 190, "30 degree bench", 25),
    ("Barbell Row", "Strength", 4, 10, 60.0, 250, "Upper back", 23),
    ("HIIT Intervals", "Cardio", 8, 4, 0.0, 420, "30s sprint / 60s jog", 21),
    ("5K Tempo Run", "Cardio", 1, 1, 0.0, 480, "26:40 finish", 19),
    ("Jump Rope", "Cardio", 5, 120, 0.0, 220, "Polykinetic conditioning", 17),
    ("Battle Ropes", "Cardio", 6, 30, 0.0, 300, "Alternate waves", 15),
    ("Bike Intervals", "Cardio", 6, 8, 0.0, 350, "Zone 2 + sprints", 13),
    ("Deadlift", "Strength", 5, 5, 100.0, 340, "New 5RM", 11),
    ("Front Squat", "Strength", 4, 8, 65.0, 290, "Core braced", 9),
    ("Dips", "Strength", 4, 15, 0.0, 200, "Chest triceps", 8),
    ("Plank Hold", "Core", 3, 90, 0.0, 90, "90 seconds", 6),
    ("Hanging Leg Raise", "Core", 3, 15, 0.0, 120, "Controlled", 5),
    ("Cable Crunch", "Core", 3, 20, 35.0, 130, "Slow reps", 4),
    ("Sprint Ladder", "Cardio", 7, 6, 0.0, 380, "10/20/30m", 3),
    ("Kettlebell Swing", "Strength", 4, 20, 24.0, 290, "Explosive hips", 2),
    ("Push Ups", "Strength", 3, 100, 0.0, 240, "100 rep challenge", 1),
    ("Mountain Climbers", "Core", 3, 60, 0.0, 180, "Finishers", 0),
]

# title, category, target, current, baseline, unit, deadline
GOALS = [
    ("Target Weight 72 kg", "Transformation", 72, 76.4, 84.0, "kg", "2026-12-31"),
    ("100 Pushups Streak", "Strength", 100, 100, 0, "reps", "2026-12-15"),
    ("5K Run Under 25 min", "Cardio", 25, 26.6, 30.0, "min", "2026-12-20"),
    ("Weekly Volume 12,000 kg", "Strength", 12000, 8650, 0, "kg", "2026-11-30"),
    ("Body Fat Below 14%", "Transformation", 14, 17.2, 19.8, "%", "2027-01-31"),
]

PHOTOS = [
    ("Week 01", "/static/assets/stage-1.jpg", "before", "transformation", 84.0, "2026-06-01"),
    ("Week 12", "/static/assets/stage-3.jpg", "after", "transformation", 76.4, "2026-08-24"),
    ("Week 04 Checkpoint", "/static/assets/stage-2.jpg", "progress", "transformation", 81.2, "2026-06-22"),
]


def main():
    init_db()
    with get_db() as db:
        db.execute("DELETE FROM workouts")
        db.execute("DELETE FROM goals")
        db.execute("DELETE FROM progress_photos")
        db.execute("DELETE FROM sqlite_sequence WHERE name IN ('workouts','goals','progress_photos')")

        for exercise, category, sets, reps, weight, calories, notes, days_ago in WORKOUTS:
            logged = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
            db.execute(
                """INSERT INTO workouts (exercise, category, sets, reps, weight, calories, notes, logged_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (exercise, category, sets, reps, weight, calories, notes, logged),
            )

        for title, category, target, current, baseline, unit, deadline in GOALS:
            db.execute(
                """INSERT INTO goals (title, category, target, current, baseline, unit, deadline)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (title, category, target, current, baseline, unit, deadline),
            )

        for title, url, kind, pair_key, weight, taken_on in PHOTOS:
            db.execute(
                """INSERT INTO progress_photos (title, photo_url, kind, pair_key, weight, taken_on)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (title, url, kind, pair_key, weight, taken_on),
            )

    print("IronPulse seeded successfully!")
    print(f"  {len(WORKOUTS)} workouts | {len(GOALS)} goals | {len(PHOTOS)} progress photos")
    print("Run the app:  python3 app.py   ->   http://127.0.0.1:5000")


if __name__ == "__main__":
    main()
