# Ping Server

Une solution simple pour monitorer des adresses IP via des pings automatiques, avec interface web et authentification.

## 🚀 Petite description

Ce projet fournit un serveur Flask qui ping en continu des adresses IP configurables et expose les résultats via une interface web ou des API sécurisées.  
Il inclut un système d'authentification minimaliste, la possibilité de changer le mot de passe et un processus de ping asynchrone sécurisé.

## 🛠️ Installation

1. Cloner le dépôt :
```bash
git clone https://github.com/Sufmax/ping_server.git
cd ping_server
````

2. Installer les dépendances Python (Flask)  Flask directement :

```bash
pip install flask
```

## ▶️ Déploiement

1. Lancer le serveur Flask :

```bash
python app.py
```

2. Accéder à l’interface web via :

```
http://127.0.0.1:5000/
```

ou l’IP/port configuré.

3. Se connecter avec l’identifiant et mot de passe par défaut :

* id : `admin`
* mot de passe : `Mo7D3P455353CUR153`

> L’utilisateur une fois connecté peut modifier le mot de passe.

## 🧩 Explications détaillées

### Serveur Python (app.py)

* **Flask** : Gère toutes les requêtes HTTP.
* **Authentification & sessions** : Vérifie si l'utilisateur est connecté, sinon redirige vers `/login`.
* **Thread de ping asynchrone** : Pinge les IP configurées en arrière-plan. Utilise un `threading.Lock` pour sécuriser l'accès aux résultats.
* **API `/get-ping`** : Renvoie les derniers résultats des pings en JSON.
* **API `/mod-ping`** : Permet de modifier la liste des IP à pinger via une requête sécurisée.
* **Sécurité API** : Vérification par hash et limitation de débit (max 1 appel par seconde, toutes IP confondues).

### Page HTML intégrée

* Contient **HTML, CSS et JavaScript**.
* Affiche les résultats de ping en direct.
* Communique avec le serveur via les API.

### Fonctionnement général

1. L’utilisateur se connecte via `/login`.
2. Le serveur démarre le thread de ping et stocke les résultats en mémoire.
3. L’utilisateur peut consulter les résultats en direct ou modifier les IPs à pinger via l’interface ou les API.
4. Toutes les actions sont sécurisées pour éviter les accès non autorisés ou les appels trop fréquents.

## 🔍 Utilisations possibles

* Monitoring simple de serveurs ou équipements réseau.
* Base pour développer un tableau de bord réseau complet.
* Démo ou apprentissage de Flask, threading et API sécurisées.

## 📄 Licence

Aucune.
