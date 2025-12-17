import os
import yaml
import secrets
import string
import subprocess
import time
import requests
from datetime import datetime, date
from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify

# --- CONFIGURATION ---
# Change this to your actual domain
DOMAIN = "line.yfgfiusustgf.cfd"
# API Domain (separate from client config domain)
# Leave empty to use the same domain as admin panel, or set a different domain/URL
API_DOMAIN = "line.yfgfiusustgf.cfd"  # e.g., "https://api.example.com" or "http://192.168.1.100:5000"
# Paths
CONFIG_FILE = 'config.yaml'
BINARY_PATH = './outline-ss-server'
METRICS_PORT = 9091
METRICS_URL = f"http://127.0.0.1:{METRICS_PORT}/metrics"

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# --- HTML TEMPLATE (Embedded for single-file simplicity) ---

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Outline User Manager</title>
    <meta http-equiv="refresh" content="30">
    <style>
        body { font-family: sans-serif; max-width: 1000px; margin: 40px auto; padding: 20px; background: #f4f7f6; }
        h1 { color: #333; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #007bff; color: white; }
        tr:hover { background-color: #f1f1f1; }
        .btn { padding: 8px 12px; text-decoration: none; color: white; border-radius: 4px; border: none; cursor: pointer; display: inline-block; margin: 2px; font-size: 14px; }
        .btn-green { background-color: #4CAF50; }
        .btn-red { background-color: #f44336; }
        .btn-blue { background-color: #008CBA; }
        .btn-orange { background-color: #ff9800; }
        .box { background: #f9f9f9; padding: 15px; border: 1px solid #ddd; margin-bottom: 20px; border-radius: 4px; }
        textarea { width: 100%; height: 150px; }
        .secret-masked { font-family: monospace; font-size: 0.9em; }
        form { display: inline; }
        .badge { padding: 5px 10px; border-radius: 12px; background: #e9ecef; font-weight: bold; font-size: 0.9em; display: inline-block; }
        .badge-active { background: #d4edda; color: #155724; }
        .status-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 5px; }
        .status-active { background-color: #28a745; }
        .status-idle { background-color: #6c757d; }
        .usage-info { font-size: 0.85em; color: #666; margin-top: 5px; }
        .expired { background-color: #f8d7da !important; }
        .expired-text { color: #dc3545; font-weight: bold; }
        .expire-date { font-size: 0.9em; }
        .search-box { background: #e9ecef; padding: 15px; border: 1px solid #ddd; margin-bottom: 20px; border-radius: 4px; }
        .search-form { display: flex; gap: 10px; align-items: center; }
        .search-input { flex: 1; padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }
        .btn-gray { background-color: #6c757d; }
        .btn-purple { background-color: #6f42c1; }
        .copy-success { color: #28a745; font-size: 0.85em; margin-left: 5px; }
    </style>
</head>
<body>
    <h1>🚀 Outline User Manager</h1>
    
    {% with messages = get_flashed_messages() %}
        {% if messages %}
            <div style="background: #fff3cd; padding: 15px; margin-bottom: 20px; border-radius: 4px; border: 1px solid #ffeeba;">
                {{ messages[0] }}
            </div>
        {% endif %}
    {% endwith %}

    <div class="search-box">
        <form action="/" method="get" class="search-form">
            <input type="text" name="search" class="search-input" placeholder="🔍 Search by username..." value="{{ search_query or '' }}">
            <button type="submit" class="btn btn-blue">Search</button>
            {% if search_query %}
            <a href="/" class="btn btn-gray">Clear</a>
            {% endif %}
        </form>
        {% if search_query %}
        <p style="margin-top: 10px; font-size: 0.9em; color: #666;">
            Showing results for "{{ search_query }}" ({{ keys|length }} result{% if keys|length != 1 %}s{% endif %})
        </p>
        {% endif %}
    </div>

    <div class="box">
        <form action="/add" method="post">
            <div style="margin-bottom: 10px;">
                <label for="expire_date" style="display: block; margin-bottom: 5px; font-weight: bold;">Expire Date (Optional):</label>
                <input type="date" name="expire_date" id="expire_date" style="padding: 8px; width: 200px;">
                <small style="color: #666; margin-left: 10px;">Leave empty for no expiration</small>
            </div>
            <button type="submit" class="btn btn-green">➕ Add New User & Restart Server</button>
        </form>
        <p style="margin-top: 10px; font-size: 0.9em; color: #666;">Page auto-refreshes every 30 seconds to update usage stats</p>
    </div>

    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Cipher</th>
                <th>Secret</th>
                <th>Expire Date</th>
                <th>Data Usage</th>
                <th>Status</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for key in keys %}
            <tr class="{% if key.is_expired %}expired{% endif %}">
                <td><strong>{{ key.id }}</strong></td>
                <td>{{ key.get('name', '') or '—' }}</td>
                <td>{{ key.cipher }}</td>
                <td class="secret-masked">{{ key.secret_masked }}</td>
                <td class="expire-date">
                    {% if key.get('expire_date') %}
                        {% if key.is_expired %}
                            <span class="expired-text">⚠️ Expired: {{ key.expire_date }}</span>
                        {% else %}
                            <span style="color: #28a745;">✓ {{ key.expire_date }}</span>
                        {% endif %}
                    {% else %}
                        <span style="color: #6c757d;">— No expiration</span>
                    {% endif %}
                </td>
                <td>
                    <span class="badge {% if stats.get(key.id|string, 0) > 0 %}badge-active{% endif %}">
                        {{ stats.get(key.id|string, 0) | filesizeformat }}
                    </span>
                    {% if stats.get(key.id|string, 0) == 0 %}
                    <div class="usage-info">No data usage recorded</div>
                    {% endif %}
                </td>
                <td>
                    {% if key.is_expired %}
                        <span class="expired-text">● Expired</span>
                    {% elif stats.get(key.id|string, 0) > 0 %}
                        <span class="status-dot status-active"></span><span style="color: #28a745;">Active</span>
                    {% else %}
                        <span class="status-dot status-idle"></span><span style="color: #6c757d;">Idle</span>
                    {% endif %}
                </td>
                <td>
                    <a href="/client/{{ key.id }}" class="btn btn-blue">Get Client Key</a>
                    <button type="button" class="btn btn-purple" onclick="copyApiUrl('{{ key.secret }}', this)">Copy API URL</button>
                    <a href="/edit/{{ key.id }}" class="btn btn-orange">Edit</a>
                    <form action="/delete/{{ key.id }}" method="post" style="display: inline;">
                        <button type="submit" class="btn btn-red" onclick="return confirm('Are you sure you want to delete user {{ key.id }}?');">Delete</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <script>
        const API_BASE_URL = '{{ api_base_url }}';
        function copyApiUrl(secret, button) {
            const apiUrl = API_BASE_URL + '/api?key=' + secret;
            navigator.clipboard.writeText(apiUrl).then(function() {
                const originalText = button.textContent;
                button.textContent = '✓ Copied!';
                button.style.backgroundColor = '#28a745';
                setTimeout(function() {
                    button.textContent = originalText;
                    button.style.backgroundColor = '#6f42c1';
                }, 2000);
            }).catch(function(err) {
                // Fallback for older browsers
                const textarea = document.createElement('textarea');
                textarea.value = apiUrl;
                textarea.style.position = 'fixed';
                textarea.style.opacity = '0';
                document.body.appendChild(textarea);
                textarea.select();
                try {
                    document.execCommand('copy');
                    const originalText = button.textContent;
                    button.textContent = '✓ Copied!';
                    button.style.backgroundColor = '#28a745';
                    setTimeout(function() {
                        button.textContent = originalText;
                        button.style.backgroundColor = '#6f42c1';
                    }, 2000);
                } catch (err) {
                    alert('Failed to copy. Please copy manually: ' + apiUrl);
                }
                document.body.removeChild(textarea);
            });
        }
    </script>
</body>
</html>
"""

EDIT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Edit User - Outline User Manager</title>
    <style>
        body { font-family: sans-serif; max-width: 600px; margin: 40px auto; padding: 20px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, select { width: 100%; padding: 8px; box-sizing: border-box; }
        .btn { padding: 10px 20px; color: white; border: none; border-radius: 4px; cursor: pointer; margin-right: 10px; }
        .btn-green { background-color: #4CAF50; }
        .btn-blue { background-color: #008CBA; }
        .box { background: #f9f9f9; padding: 15px; border: 1px solid #ddd; margin-bottom: 20px; }
    </style>
</head>
<body>
    <h2>Edit User {{ user_id }}</h2>
    <form action="/update/{{ user_id }}" method="post">
        <div class="form-group">
            <label>ID:</label>
            <input type="text" value="{{ user_id }}" disabled>
        </div>
        <div class="form-group">
            <label>Name (Optional - for admin panel display only):</label>
            <input type="text" name="name" value="{{ name or '' }}" placeholder="e.g., John Doe, Device 1">
        </div>
        <div class="form-group">
            <label>Cipher:</label>
            <select name="cipher">
                <option value="chacha20-ietf-poly1305" {% if cipher == 'chacha20-ietf-poly1305' %}selected{% endif %}>chacha20-ietf-poly1305</option>
                <option value="aes-256-gcm" {% if cipher == 'aes-256-gcm' %}selected{% endif %}>aes-256-gcm</option>
                <option value="aes-128-gcm" {% if cipher == 'aes-128-gcm' %}selected{% endif %}>aes-128-gcm</option>
            </select>
        </div>
        <div class="form-group">
            <label>Secret:</label>
            <input type="text" name="secret" value="{{ secret }}" required>
        </div>
        <div class="form-group">
            <label>Expire Date (Optional - YYYY-MM-DD format):</label>
            <input type="date" name="expire_date" value="{{ expire_date or '' }}">
            <small style="color: #666;">Leave empty for no expiration</small>
        </div>
        <div class="box">
            <button type="submit" class="btn btn-green">Update & Restart Server</button>
            <button type="button" class="btn btn-blue" onclick="document.querySelector('input[name=secret]').value='{{ new_secret }}'">Generate New Secret</button>
        </div>
    </form>
    <a href="/">Back to Dashboard</a>
</body>
</html>
"""

CLIENT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Client Config</title>
    <style>
        body { font-family: sans-serif; max-width: 600px; margin: 40px auto; padding: 20px; }
        .btn { padding: 10px 20px; color: white; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; margin: 5px; }
        .btn-blue { background-color: #008CBA; }
        .btn-purple { background-color: #6f42c1; }
        .btn-green { background-color: #4CAF50; }
        textarea { width: 100%; height: 300px; font-family: monospace; padding: 10px; box-sizing: border-box; }
        .button-group { margin: 15px 0; }
    </style>
</head>
<body>
    <h2>Client Configuration for User {{ user_id }}</h2>
    <p>Copy the code below and paste it into the Outline Client:</p>
    <textarea readonly>{{ yaml_config }}</textarea>
    <div class="button-group">
        <button type="button" class="btn btn-purple" onclick="copyApiUrl('{{ secret }}', this)">Copy API URL</button>
        <button type="button" class="btn btn-blue" onclick="copyYaml()">Copy YAML Config</button>
    </div>
    <br><br>
    <a href="/" class="btn btn-green">Back to Dashboard</a>

    <script>
        const API_BASE_URL = '{{ api_base_url }}';
        function copyApiUrl(secret, button) {
            const apiUrl = API_BASE_URL + '/api?key=' + secret;
            navigator.clipboard.writeText(apiUrl).then(function() {
                const originalText = button.textContent;
                button.textContent = '✓ Copied!';
                button.style.backgroundColor = '#28a745';
                setTimeout(function() {
                    button.textContent = originalText;
                    button.style.backgroundColor = '#6f42c1';
                }, 2000);
            }).catch(function(err) {
                // Fallback for older browsers
                const textarea = document.createElement('textarea');
                textarea.value = apiUrl;
                textarea.style.position = 'fixed';
                textarea.style.opacity = '0';
                document.body.appendChild(textarea);
                textarea.select();
                try {
                    document.execCommand('copy');
                    const originalText = button.textContent;
                    button.textContent = '✓ Copied!';
                    button.style.backgroundColor = '#28a745';
                    setTimeout(function() {
                        button.textContent = originalText;
                        button.style.backgroundColor = '#6f42c1';
                    }, 2000);
                } catch (err) {
                    alert('Failed to copy. Please copy manually: ' + apiUrl);
                }
                document.body.removeChild(textarea);
            });
        }

        function copyYaml() {
            const yamlText = document.querySelector('textarea').value;
            navigator.clipboard.writeText(yamlText).then(function() {
                const button = event.target;
                const originalText = button.textContent;
                button.textContent = '✓ Copied!';
                button.style.backgroundColor = '#28a745';
                setTimeout(function() {
                    button.textContent = originalText;
                    button.style.backgroundColor = '#008CBA';
                }, 2000);
            }).catch(function(err) {
                const textarea = document.querySelector('textarea');
                textarea.select();
                try {
                    document.execCommand('copy');
                    alert('YAML config copied to clipboard!');
                } catch (err) {
                    alert('Failed to copy. Please select and copy manually.');
                }
            });
        }
    </script>
</body>
</html>
"""

# --- HELPERS ---
def load_config():
    """Load and validate config file structure"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = yaml.safe_load(f)
        
        # Validate config structure
        if not config:
            raise ValueError("Config file is empty")
        if 'services' not in config or not config['services']:
            raise ValueError("Config missing 'services' section")
        if 'keys' not in config['services'][0]:
            # Initialize keys if missing
            config['services'][0]['keys'] = []
        
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file '{CONFIG_FILE}' not found")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config file: {e}")

def save_config(data):
    """Save config with error handling"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    except Exception as e:
        raise IOError(f"Failed to save config: {e}")

def get_keys(config):
    """Safely get keys array from config"""
    try:
        return config.get('services', [{}])[0].get('keys', [])
    except (IndexError, KeyError, TypeError):
        return []

def set_keys(config, keys):
    """Safely set keys array in config"""
    if 'services' not in config:
        config['services'] = [{}]
    if not config['services']:
        config['services'] = [{}]
    config['services'][0]['keys'] = keys

def restart_server_process():
    """Restart server with error handling and metrics enabled"""
    try:
        # 1. Kill existing server matching the config
        subprocess.run(['pkill', '-f', f'-config={CONFIG_FILE}'], 
                      stderr=subprocess.DEVNULL, timeout=5)
        time.sleep(1)
        # 2. Start new server with metrics enabled
        # The -metrics flag exposes Prometheus metrics on the specified port
        cmd = f"nohup {BINARY_PATH} -config={CONFIG_FILE} -metrics 127.0.0.1:{METRICS_PORT} > outline.log 2>&1 &"
        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        flash("Warning: Server restart timeout", "warning")
    except Exception as e:
        flash(f"Error restarting server: {e}", "error")

def generate_secret():
    """Generate a random 20-char secret"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(20))

def mask_secret(secret, show_chars=4):
    """Mask secret showing only first and last few characters"""
    if not secret or len(secret) <= show_chars * 2:
        return secret
    return f"{secret[:show_chars]}{'*' * (len(secret) - show_chars * 2)}{secret[-show_chars:]}"

def check_expiration(expire_date_str):
    """Check if a date string is expired. Returns (is_expired, formatted_date)"""
    if not expire_date_str:
        return False, None
    
    try:
        expire_date = datetime.strptime(expire_date_str, '%Y-%m-%d').date()
        today = date.today()
        is_expired = expire_date < today
        formatted_date = expire_date.strftime('%Y-%m-%d')
        return is_expired, formatted_date
    except (ValueError, TypeError):
        # Invalid date format, treat as not expired
        return False, expire_date_str

def generate_client_yaml(target_key):
    """Generate client YAML configuration for a given key"""
    client_yaml = {
        'transport': {
            '$type': 'tcpudp',
            'tcp': {
                '$type': 'shadowsocks',
                'endpoint': {'$type': 'websocket', 'url': f'wss://{DOMAIN}/tcp-ray'},
                'cipher': target_key.get('cipher', 'chacha20-ietf-poly1305'),
                'secret': target_key.get('secret', '')
            },
            'udp': {
                '$type': 'shadowsocks',
                'endpoint': {'$type': 'websocket', 'url': f'wss://{DOMAIN}/udp-ray'},
                'cipher': target_key.get('cipher', 'chacha20-ietf-poly1305'),
                'secret': target_key.get('secret', '')
            }
        }
    }
    return yaml.dump(client_yaml, default_flow_style=False, sort_keys=False)

def get_metrics():
    """Scrape the Outline Prometheus metrics endpoint to calculate usage per key"""
    usage_map = {}
    try:
        response = requests.get(METRICS_URL, timeout=2)
        if response.status_code == 200:
            lines = response.text.split('\n')
            for line in lines:
                # Look for lines like: shadowsocks_data_bytes{access_key="1",...} 5000
                if line.startswith('shadowsocks_data_bytes') and not line.startswith('#'):
                    parts = line.split(' ')
                    if len(parts) >= 2:
                        try:
                            val = float(parts[-1])
                            
                            # Extract access_key ID from the metric line
                            # Format is usually: shadowsocks_data_bytes{access_key="1",direction="down",...} 5000
                            if 'access_key="' in line:
                                key_id = line.split('access_key="')[1].split('"')[0]
                                if key_id not in usage_map:
                                    usage_map[key_id] = 0
                                usage_map[key_id] += val
                        except (ValueError, IndexError):
                            continue
    except requests.exceptions.RequestException:
        # Metrics server might not be ready yet or not running
        pass
    except Exception:
        # Any other error, just return empty map
        pass
    return usage_map

# --- ROUTES ---
@app.route('/')
def index():
    try:
        config = load_config()
        keys = get_keys(config)
        
        # Get search query from URL parameters
        search_query = request.args.get('search', '').strip()
        
        # Filter keys by username if search query is provided
        if search_query:
            search_lower = search_query.lower()
            keys = [key for key in keys if search_lower in key.get('name', '').lower()]
        
        # Add masked secret and expiration status for display
        for key in keys:
            key['secret_masked'] = mask_secret(key.get('secret', ''))
            # Check expiration
            expire_date_str = key.get('expire_date', '')
            is_expired, formatted_date = check_expiration(expire_date_str)
            key['is_expired'] = is_expired
            key['expire_date'] = formatted_date if formatted_date else expire_date_str
        
        # Get metrics data usage for each user
        stats = get_metrics()
        
        # Determine API base URL
        api_base_url = API_DOMAIN if API_DOMAIN else request.url_root.rstrip('/')
        
        return render_template_string(HTML_TEMPLATE, keys=keys, stats=stats, search_query=search_query, api_base_url=api_base_url)
    except Exception as e:
        flash(f"Error loading config: {e}", "error")
        api_base_url = API_DOMAIN if API_DOMAIN else request.url_root.rstrip('/')
        return render_template_string(HTML_TEMPLATE, keys=[], stats={}, search_query='', api_base_url=api_base_url)

@app.route('/add', methods=['POST'])
def add_user():
    try:
        config = load_config()
        keys = get_keys(config)
        
        # Calculate new ID
        new_id = 1
        if keys:
            try:
                new_id = max(int(k.get('id', 0)) for k in keys) + 1
            except (ValueError, TypeError):
                new_id = len(keys) + 1
        
        # Get expiration date from form
        expire_date = request.form.get('expire_date', '').strip()
        
        new_user = {
            'id': new_id,
            'name': '',  # Optional name field for admin display
            'cipher': 'chacha20-ietf-poly1305',
            'secret': generate_secret(),
            'expire_date': expire_date if expire_date else None
        }
        
        # Remove None values to keep config clean
        if new_user['expire_date'] is None:
            new_user.pop('expire_date', None)
        
        keys.append(new_user)
        set_keys(config, keys)
        save_config(config)
        restart_server_process()
        
        flash(f"User {new_id} added and Server Restarted!")
    except Exception as e:
        flash(f"Error adding user: {e}", "error")
    return redirect(url_for('index'))

@app.route('/edit/<int:user_id>')
def edit_user(user_id):
    try:
        config = load_config()
        keys = get_keys(config)
        target_key = next((k for k in keys if int(k.get('id', 0)) == user_id), None)
        
        if not target_key:
            flash(f"User {user_id} not found", "error")
            return redirect(url_for('index'))
        
        new_secret = generate_secret()
        expire_date = target_key.get('expire_date', '')
        return render_template_string(EDIT_TEMPLATE, 
                                    user_id=user_id,
                                    name=target_key.get('name', ''),
                                    cipher=target_key.get('cipher', 'chacha20-ietf-poly1305'),
                                    secret=target_key.get('secret', ''),
                                    expire_date=expire_date,
                                    new_secret=new_secret)
    except Exception as e:
        flash(f"Error loading user: {e}", "error")
        return redirect(url_for('index'))

@app.route('/update/<int:user_id>', methods=['POST'])
def update_user(user_id):
    try:
        config = load_config()
        keys = get_keys(config)
        
        target_key = next((k for k in keys if int(k.get('id', 0)) == user_id), None)
        if not target_key:
            flash(f"User {user_id} not found", "error")
            return redirect(url_for('index'))
        
        # Update name, cipher, secret, and expiration date
        name = request.form.get('name', '').strip()
        cipher = request.form.get('cipher', 'chacha20-ietf-poly1305')
        secret = request.form.get('secret', '').strip()
        expire_date = request.form.get('expire_date', '').strip()
        
        if not secret:
            flash("Secret cannot be empty", "error")
            return redirect(url_for('edit_user', user_id=user_id))
        
        target_key['name'] = name
        target_key['cipher'] = cipher
        target_key['secret'] = secret
        
        # Update expiration date
        if expire_date:
            target_key['expire_date'] = expire_date
        else:
            # Remove expiration date if empty
            target_key.pop('expire_date', None)
        
        set_keys(config, keys)
        save_config(config)
        restart_server_process()
        
        flash(f"User {user_id} updated and Server Restarted!")
    except Exception as e:
        flash(f"Error updating user: {e}", "error")
    return redirect(url_for('index'))

@app.route('/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    try:
        config = load_config()
        keys = get_keys(config)
        
        original_count = len(keys)
        keys = [k for k in keys if int(k.get('id', 0)) != user_id]
        
        if len(keys) == original_count:
            flash(f"User {user_id} not found", "error")
        else:
            set_keys(config, keys)
            save_config(config)
            restart_server_process()
            flash(f"User {user_id} deleted and Server Restarted!")
    except Exception as e:
        flash(f"Error deleting user: {e}", "error")
    return redirect(url_for('index'))

@app.route('/client/<int:user_id>')
def get_client_config(user_id):
    try:
        config = load_config()
        keys = get_keys(config)
        target_key = next((k for k in keys if int(k.get('id', 0)) == user_id), None)
        
        if not target_key:
            return "User not found", 404

        # Generate the Client YAML structure
        yaml_text = generate_client_yaml(target_key)
        secret = target_key.get('secret', '')
        # Determine API base URL
        api_base_url = API_DOMAIN if API_DOMAIN else request.url_root.rstrip('/')
        return render_template_string(CLIENT_TEMPLATE, user_id=user_id, yaml_config=yaml_text, secret=secret, api_base_url=api_base_url)
    except Exception as e:
        return f"Error generating client config: {e}", 500

@app.route('/api')
def api_get_client_key():
    """API endpoint to retrieve client key by password/secret only"""
    try:
        key_param = request.args.get('key', '').strip()
        
        if not key_param:
            return jsonify({'error': 'Missing key parameter. Use /api?key=password'}), 400
        
        config = load_config()
        keys = get_keys(config)
        
        # Only match by secret/password (more secure)
        target_key = next((k for k in keys if k.get('secret', '') == key_param), None)
        
        if not target_key:
            return jsonify({'error': 'User not found. Invalid password/secret.'}), 404
        
        # Generate client YAML
        yaml_text = generate_client_yaml(target_key)
        
        # Return as plain text YAML (can be used directly by clients)
        return yaml_text, 200, {'Content-Type': 'text/yaml; charset=utf-8'}
        
    except Exception as e:
        return jsonify({'error': f'Error retrieving client key: {str(e)}'}), 500

if __name__ == '__main__':
    # Running on port 5000, accessible from anywhere
    # WARNING: Ensure you have a firewall for production use
    app.run(host='0.0.0.0', port=5000)
