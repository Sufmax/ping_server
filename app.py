import os
import time
import threading
import platform
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

# --- Configuration de l'application ---
app = Flask(__name__)
# Une clé secrète est INDISPENSABLE pour gérer les sessions de manière sécurisée.
app.secret_key = os.urandom(24) 

# --- État partagé de l'application (en mémoire) ---
# Dans une vraie application, on utiliserait une base de données (ex: SQLite, Redis).
# Pour cet exemple, un dictionnaire en mémoire suffit.
# Le 'threading.Lock' est crucial pour éviter les conflits d'accès entre le serveur web et le worker.
app_state = {
    "user": {
        "username": generate_password_hash("admin"),
        "password_hash": generate_password_hash("Mo7D3P455353CUR153")
    },
    "ping_jobs": {
        # Exemple de structure:
        # "8.8.8.8": {"mode": "continuous", "interval": 5, "status": "pending", "last_ping_time": 0, "last_result": "", "count": 0},
        # "1.1.1.1": {"mode": "custom", "target_count": 10, "interval": 10, "status": "running", "last_ping_time": 0, "last_result": "", "count": 0}
    },
    "last_api_call_timestamp": 0,
    "lock": threading.Lock()
}

# --- Worker asynchrone pour les Pings ---

def ping_worker():
    """
    Ce worker tourne en boucle dans un thread séparé pour exécuter les pings.
    """
    ping_command = "ping -c 1" if platform.system().lower() != "windows" else "ping -n 1"

    while True:
        with app_state["lock"]:
            # On fait une copie pour ne pas garder le lock pendant les pings (qui peuvent être longs)
            jobs_to_run = dict(app_state["ping_jobs"])

        for target, job in jobs_to_run.items():
            now = time.time()
            is_due = (now - job.get("last_ping_time", 0)) > job.get("interval", 5)
            
            should_run = False
            if job.get("status") == "running" and is_due:
                if job["mode"] == "continuous":
                    should_run = True
                elif job["mode"] == "custom" and job.get("count", 0) < job.get("target_count", 1):
                    should_run = True
                elif job["mode"] == "single" and job.get("count", 0) < 1:
                     should_run = True

            if should_run:
                # Exécute le ping
                response = os.system(f"{ping_command} {target} > /dev/null 2>&1") # Redirige la sortie pour ne pas polluer la console
                result = "success" if response == 0 else "failure"
                
                # Mise à jour des résultats de manière sécurisée
                with app_state["lock"]:
                    app_state["ping_jobs"][target]["last_ping_time"] = now
                    app_state["ping_jobs"][target]["last_result"] = result
                    app_state["ping_jobs"][target]["count"] = job.get("count", 0) + 1
                    app_state["ping_jobs"][target]["last_update_str"] = datetime.now().strftime('%H:%M:%S')

                    # Arrêter le job s'il a atteint sa cible
                    if (job["mode"] == "custom" and app_state["ping_jobs"][target]["count"] >= job["target_count"]) or \
                       (job["mode"] == "single" and app_state["ping_jobs"][target]["count"] >= 1):
                        app_state["ping_jobs"][target]["status"] = "stopped"

        time.sleep(1) # Le worker vérifie les tâches à faire chaque seconde

# --- Routes d'Authentification ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = app_state["user"]
        if check_password_hash(user["username"], username) and check_password_hash(user["password_hash"], password):
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Identifiants incorrects")
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Middleware pour la protection des routes ---

@app.before_request
def require_login():
    # Redirige vers /login si l'utilisateur n'est pas connecté
    # et qu'il n'essaie pas d'accéder à la page de login elle-même.
    if not session.get('logged_in') and request.endpoint not in ['login', 'static']:
        return redirect(url_for('login'))

# --- Routes principales de l'application ---

@app.route('/')
def index():
    # Sera automatiquement redirigé vers /dashboard/ par le middleware si loggé, sinon /login
    return redirect(url_for('dashboard'))

@app.route('/dashboard/')
def dashboard():
    # La seule page accessible une fois connecté
    return render_template('dashboard.html')

# --- API Endpoints ---

def api_check():
    """Fonction utilitaire pour vérifier l'authentification et le rate-limiting."""
    if not session.get('logged_in'):
        return {"status": "error", "message": "Non autorisé"}, 401

    with app_state["lock"]:
        now = time.time()
        if now - app_state["last_api_call_timestamp"] < 1.0:
            return {"status": "error", "message": "Trop de requêtes. Veuillez patienter une seconde."}, 429
        app_state["last_api_call_timestamp"] = now
    
    return None, None # Pas d'erreur

@app.route('/api/get-pings', methods=['GET'])
def get_pings():
    error_response, status_code = api_check()
    if error_response:
        return jsonify(error_response), status_code
        
    with app_state["lock"]:
        # On retourne une copie pour être thread-safe
        current_jobs = dict(app_state["ping_jobs"])

    return jsonify(current_jobs)

@app.route('/api/mod-ping', methods=['POST'])
def mod_ping():
    error_response, status_code = api_check()
    if error_response:
        return jsonify(error_response), status_code

    data = request.get_json()
    if not data or 'target' not in data:
        return jsonify({"status": "error", "message": "Données invalides"}), 400

    target = data.get("target")
    action = data.get("action") # 'add', 'update', 'remove', 'start', 'stop'

    with app_state["lock"]:
        if action == "add" or action == "update":
            # Validation simple
            if not all(k in data for k in ["mode", "interval"]):
                return jsonify({"status": "error", "message": "Champs manquants"}), 400

            app_state["ping_jobs"][target] = {
                "mode": data["mode"],
                "interval": int(data["interval"]),
                "target_count": int(data.get("target_count", 1)),
                "status": "running", # On démarre par défaut
                "last_ping_time": 0,
                "last_result": "N/A",
                "count": 0,
                "last_update_str": datetime.now().strftime('%H:%M:%S'),
            }
        elif action == "remove" and target in app_state["ping_jobs"]:
            del app_state["ping_jobs"][target]
        elif action == "start" and target in app_state["ping_jobs"]:
            # On réinitialise pour un nouveau départ
            app_state["ping_jobs"][target]["status"] = "running"
            app_state["ping_jobs"][target]["count"] = 0
            app_state["ping_jobs"][target]["last_ping_time"] = 0
        elif action == "stop" and target in app_state["ping_jobs"]:
            app_state["ping_jobs"][target]["status"] = "stopped"
        
        current_jobs = dict(app_state["ping_jobs"])

    return jsonify(current_jobs)

@app.route('/api/change-password', methods=['POST'])
def change_password():
    error_response, status_code = api_check()
    if error_response:
        return jsonify(error_response), status_code

    data = request.get_json()
    new_password = data.get('new_password')

    if not new_password or len(new_password) < 12:
        return jsonify({"status": "error", "message": "Le mot de passe doit faire au moins 12 caractères."}), 400

    with app_state["lock"]:
        app_state["user"]["password_hash"] = generate_password_hash(new_password)

    return jsonify({"status": "success", "message": "Mot de passe changé avec succès."})


if __name__ == '__main__':
    # Démarrer le worker de ping dans un thread de fond
    ping_thread = threading.Thread(target=ping_worker, daemon=True)
    ping_thread.start()
    
    # Démarrer le serveur Flask
    # host='0.0.0.0' pour le rendre accessible sur votre réseau local
    app.run(host='0.0.0.0', port=5000, debug=True)