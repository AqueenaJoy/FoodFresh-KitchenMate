from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
import datetime
import json
import requests
from collections import Counter

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DB_FILE = 'food_data.db'
BOT_TOKEN = '7391679526:AAEkdM9DE-zmNwHDiKmm1UiKeCpbn9xgUiU'
CHAT_ID = '1923033347'

def send_telegram_message(message):
    send_text = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    requests.get(send_text)
    
# Initialize DB
def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''CREATE TABLE IF NOT EXISTS food (
        id INTEGER PRIMARY KEY,
        item TEXT NOT NULL,
        expiry DATE NOT NULL
    )''')
    conn.close()

# Inject current theme into templates automatically
@app.context_processor
def inject_theme():
    return dict(current_theme=session.get('theme', 'light'))

@app.route('/')
def intro():
    return render_template('intro.html')

@app.route('/set_theme/<theme>')
def set_theme(theme):
    session['theme'] = theme
    return redirect(request.referrer or url_for('home'))

@app.route('/home')
def home():
    conn = sqlite3.connect(DB_FILE)
    items = conn.execute('SELECT * FROM food').fetchall()
    today = datetime.date.today()
    expiring = [item for item in items if 0 <= (datetime.datetime.strptime(item[2], '%Y-%m-%d').date() - today).days <= 3]
    expired = [item for item in items if datetime.datetime.strptime(item[2], '%Y-%m-%d').date() < today]
    conn.close()

    
    return render_template('home.html',
                           total=len(items),
                           expiring=len(expiring),
                           expired=len(expired))

@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    conn = sqlite3.connect(DB_FILE)
    if request.method == 'POST':
        item = request.form.get('item_name')
        expiry = request.form.get('expiry_date')
        if item and expiry:
            conn.execute('INSERT INTO food (item, expiry) VALUES (?, ?)', (item, expiry))
            conn.commit()
    items = conn.execute('SELECT * FROM food ORDER BY expiry').fetchall()
    conn.close()
    return render_template('inventory.html', items=items)

@app.route('/delete/<int:item_id>')
def delete(item_id):
    conn = sqlite3.connect(DB_FILE)
    conn.execute('DELETE FROM food WHERE id=?', (item_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('inventory'))

@app.route('/notifications')
def notifications():
    today = datetime.date.today()
    conn = sqlite3.connect(DB_FILE)
    items = conn.execute('SELECT * FROM food').fetchall()
    conn.close()

    # Filter items expiring soon
    expiring = [item for item in items if 0 <= (datetime.datetime.strptime(item[2], '%Y-%m-%d').date() - today).days <= 3]

    # Extract item names for the pop-up (items expiring soon)
    expiring_items = [item[1] for item in expiring]  # Item names that are expiring soon
      # Send Telegram notification
    if expiring_items:
        msg = "🔔 *Expiring Soon*: " + ", ".join(expiring_items)
        send_telegram_message(msg)

    return render_template('notifications.html', items=expiring, expiring_items=expiring_items)
@app.route('/recipes')
def recipes():
    today = datetime.date.today()
    conn = sqlite3.connect(DB_FILE)
    items = conn.execute('SELECT * FROM food').fetchall()
    conn.close()

    expiring_items = [item[1].lower() for item in items if 0 <= (datetime.datetime.strptime(item[2], '%Y-%m-%d').date() - today).days <= 3]

    with open('recipes.json') as f:
        all_recipes = json.load(f)

    suggested = [recipe for recipe in all_recipes if any(ing.lower() in expiring_items for ing in recipe['ingredients'])]

    return render_template('recipes.html', recipes=suggested)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        selected_theme = request.form.get('theme')  # Note: form input should have name="theme"
        session['theme'] = selected_theme
        return redirect(url_for('settings'))

    return render_template('settings.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
