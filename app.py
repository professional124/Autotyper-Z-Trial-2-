from flask import Flask, render_template, request, redirect, url_for, jsonify
from bot_manager import BotManager

app = Flask(__name__)
bot_manager = BotManager()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/start', methods=['GET', 'POST'])
def start_bot():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        avg_wpm = float(request.form['avg_wpm'])
        min_accuracy = float(request.form['min_accuracy'])
        race_count = int(request.form['race_count'])
        bot_manager.start_bot(username, password, avg_wpm, min_accuracy, race_count)
        return redirect(url_for('dashboard'))
    return render_template('start.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/bots')
def api_bots():
    return jsonify(bot_manager.get_bots_status())

@app.route('/api/stop/<bot_id>', methods=['POST'])
def stop_bot(bot_id):
    bot_manager.stop_bot(bot_id)
    return jsonify({'status': 'stopped'})

if __name__ == '__main__':
    app.run(debug=True)
