import sqlite3
from datetime import date, timedelta


def init_db():
    conn = sqlite3.connect("habits.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS habits (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   user_id INTEGER,
                   name TEXT
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS completions (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   habit_id INTEGER,
                   date TEXT
        )
    """
    )
    conn.commit()
    conn.close()


def add_habit(user_id, name):
    conn = sqlite3.connect("habits.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO habits (user_id, name) VALUES (?, ?)", (user_id, name))
    conn.commit()
    conn.close()


def delete_habit(habit_id):
    conn = sqlite3.connect("habits.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM completions WHERE habit_id = ?", (habit_id,))
    cursor.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
    conn.commit()
    conn.close()


def get_habits(user_id):
    conn = sqlite3.connect("habits.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM habits WHERE user_id = ?", (user_id,))
    habits = cursor.fetchall()
    conn.close()
    return habits


from datetime import date


def mark_done(habit_id):
    conn = sqlite3.connect("habits.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO completions (habit_id, date) VALUES (?, ?)",
        (habit_id, str(date.today())),
    )
    conn.commit()
    conn.close()


def get_today_completions(user_id):
    conn = sqlite3.connect("habits.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT habit_id FROM completions
        WHERE date = ? AND habit_id IN (
            SELECT id FROM habits WHERE user_id = ?
        )
        """,
        (str(date.today()), user_id),
    )
    done = [row[0] for row in cursor.fetchall()]
    conn.close()
    return done


def get_streak(habit_id):
    conn = sqlite3.connect("habits.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT date FROM completions WHERE habit_id = ? ORDER BY date DESC",
        (habit_id,),
    )
    dates = [row[0] for row in cursor.fetchall()]
    conn.close()

    if not dates:
        return 0

    streak = 0
    check_date = date.today()

    for d in dates:
        if d == str(check_date):
            streak += 1
            from datetime import timedelta

            check_date = check_date - timedelta(days=1)
        else:
            break
    return streak


def get_all_users():
    conn = sqlite3.connect("habits.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT user_id FROM habits")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users


def init_user_settings(user_id):
    conn = sqlite3.connect("habits.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            user_id INTEGER PRIMARY KEY,
            reminder_enabled INTEGER DEFAULT 1,
            reminder_hour INTEGER DEFAULT 20
        )
    """
    )
    cursor.execute("INSERT OR IGNORE INTO settings (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()


def get_user_settings(user_id):
    conn = sqlite3.connect("habits.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT reminder_enabled, reminder_hour FROM settings WHERE user_id = ?",
        (user_id,),
    )
    result = cursor.fetchone()
    conn.close()
    return result if result else (1, 20)


def update_reminder(user_id, enabled=None, hour=None):
    conn = sqlite3.connect("habits.db")
    cursor = conn.cursor()
    if enabled is not None:
        cursor.execute(
            "UPDATE settings SET reminder_enabled = ? WHERE user_id = ?",
            (enabled, user_id),
        )
    if hour is not None:
        cursor.execute(
            "UPDATE settings SET reminder_hour = ? WHERE user_id = ?", (hour, user_id)
        )
    conn.commit()
    conn.close()
