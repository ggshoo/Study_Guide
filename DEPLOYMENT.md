# Deployment Guide for AI Study Assistant

This guide covers multiple options for deploying your AI Study Assistant so friends in different states (or anywhere) can access it.

## Overview

The app can be deployed using several platforms:
1. **Streamlit Cloud** (Easiest, Free tier available)
2. **Railway** (Easy, Developer-friendly)
3. **Render** (Simple, Free tier available)
4. **Heroku** (Traditional PaaS)
5. **Self-hosted** (VPS like DigitalOcean, AWS EC2)

## Option 1: Streamlit Cloud (Recommended for Beginners)

**Pros:** Free, easiest setup, designed for Streamlit apps
**Cons:** Public apps are visible to anyone, limited resources on free tier

### Steps:

1. **Prepare your repository:**
   ```bash
   git add .
   git commit -m "Prepare for deployment"
   git push origin main
   ```

2. **Create a `requirements.txt` for deployment:**
   ```txt
   streamlit==1.28.1
   chromadb==0.4.15
   openai==0.28.1
   PyPDF2==3.0.1
   python-dotenv==1.0.0
   langchain==0.0.335
   tqdm==4.66.1
   ```

3. **Add a `.streamlit/config.toml` file:**
   ```toml
   [server]
   headless = true
   port = 8501
   enableCORS = false
   enableXsrfProtection = true
   ```

4. **Go to [share.streamlit.io](https://share.streamlit.io)**
   - Sign in with GitHub
   - Click "New app"
   - Select your repository
   - Choose branch: `main`
   - Main file path: `app_enhanced.py` (or `app.py`)
   - Click "Deploy"

5. **Set up secrets (API keys):**
   - In Streamlit Cloud dashboard, go to App Settings → Secrets
   - Add your OpenAI API key:
     ```toml
     OPENAI_API_KEY = "sk-your-api-key-here"
     ```

6. **Share the URL** with your friend (e.g., `https://your-app-name.streamlit.app`)

### Important Security Notes for Streamlit Cloud:
- API costs: Your OpenAI API key will be used for all queries
- Consider adding usage limits or authentication
- Monitor your OpenAI usage dashboard

## Option 2: Railway

**Pros:** Easy deployment, good free tier, supports multiple services
**Cons:** Requires credit card for free tier

### Steps:

1. **Create a `Procfile`:**
   ```
   web: streamlit run app_enhanced.py --server.port $PORT
   ```

2. **Create `railway.json`:**
   ```json
   {
     "build": {
       "builder": "NIXPACKS"
     },
     "deploy": {
       "startCommand": "streamlit run app_enhanced.py --server.port $PORT",
       "restartPolicyType": "ON_FAILURE",
       "restartPolicyMaxRetries": 10
     }
   }
   ```

3. **Deploy:**
   - Go to [railway.app](https://railway.app)
   - Click "Start a New Project"
   - Connect your GitHub repo
   - Add environment variable: `OPENAI_API_KEY`
   - Railway will auto-deploy

## Option 3: Render

**Pros:** Free tier available, simple setup
**Cons:** Cold starts on free tier (app sleeps after inactivity)

### Steps:

1. **Create a `render.yaml`:**
   ```yaml
   services:
     - type: web
       name: ai-study-assistant
       env: python
       buildCommand: pip install -r requirements.txt
       startCommand: streamlit run app_enhanced.py --server.port $PORT --server.address 0.0.0.0
       envVars:
         - key: OPENAI_API_KEY
           sync: false
   ```

2. **Deploy:**
   - Go to [render.com](https://render.com)
   - Create new Web Service
   - Connect your GitHub repo
   - Render will detect Python and deploy automatically

## Option 4: Self-Hosted (Advanced)

For full control and multi-user support:

### Using DigitalOcean/AWS EC2:

1. **Create a Droplet/Instance** (Ubuntu 22.04)

2. **SSH into server:**
   ```bash
   ssh root@your-server-ip
   ```

3. **Install dependencies:**
   ```bash
   apt update
   apt install python3-pip python3-venv nginx -y
   ```

4. **Clone your repo:**
   ```bash
   cd /opt
   git clone https://github.com/yourusername/your-repo.git
   cd your-repo
   ```

5. **Set up virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

6. **Create systemd service** (`/etc/systemd/system/streamlit.service`):
   ```ini
   [Unit]
   Description=Streamlit AI Study Assistant
   After=network.target

   [Service]
   Type=simple
   User=root
   WorkingDirectory=/opt/your-repo
   Environment="PATH=/opt/your-repo/venv/bin"
   Environment="OPENAI_API_KEY=your-key-here"
   ExecStart=/opt/your-repo/venv/bin/streamlit run app_enhanced.py --server.port 8501 --server.address 0.0.0.0
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

7. **Start service:**
   ```bash
   systemctl enable streamlit
   systemctl start streamlit
   ```

8. **Configure Nginx** as reverse proxy (`/etc/nginx/sites-available/streamlit`):
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:8501;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
           proxy_cache_bypass $http_upgrade;
       }
   }
   ```

9. **Enable site and restart Nginx:**
   ```bash
   ln -s /etc/nginx/sites-available/streamlit /etc/nginx/sites-enabled/
   systemctl restart nginx
   ```

10. **Set up SSL with Let's Encrypt:**
    ```bash
    apt install certbot python3-certbot-nginx -y
    certbot --nginx -d your-domain.com
    ```

## Security Best Practices for Production

### 1. Add Authentication

Create a simple password protection in `app_enhanced.py`:

```python
import streamlit as st
import hmac

def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.text_input("Password", type="password", on_change=password_entered, key="password")
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False

# Add at the start of main():
if not check_password():
    st.stop()
```

Then add to your secrets:
```toml
password = "your-secure-password"
```

### 2. Rate Limiting

Add to prevent API abuse:

```python
import time
from collections import defaultdict

# Initialize rate limiter
if 'rate_limit' not in st.session_state:
    st.session_state.rate_limit = defaultdict(list)

def check_rate_limit(user_id, max_requests=10, time_window=60):
    """Allow max_requests per time_window seconds."""
    now = time.time()
    requests = st.session_state.rate_limit[user_id]
    
    # Remove old requests
    requests = [req_time for req_time in requests if now - req_time < time_window]
    
    if len(requests) >= max_requests:
        st.error(f"Rate limit exceeded. Please wait {int(time_window - (now - requests[0]))} seconds.")
        return False
    
    requests.append(now)
    st.session_state.rate_limit[user_id] = requests
    return True
```

### 3. Cost Management

Monitor and limit OpenAI API usage:

```python
# Set monthly budget alert
MAX_MONTHLY_COST = 50.00  # USD

# Track usage in a persistent database or file
# Consider using Redis or SQLite for production
```

### 4. User Data Isolation

The enhanced app already uses session-specific databases:
```python
persist_directory=f"db_{user_id}"
```

For production, consider:
- Using a proper user authentication system
- Storing user data in separate cloud storage buckets
- Implementing data retention policies
- Adding "Clear my data" functionality

### 5. Environment Variables

Never commit API keys. Use environment variables:

```bash
# .env file (never commit this!)
OPENAI_API_KEY=sk-your-key
PASSWORD=your-secure-password
MAX_FILE_SIZE=10485760  # 10MB
```

## Cost Considerations

### OpenAI API Costs (as of 2025):
- GPT-4: ~$0.03 per 1K input tokens, ~$0.06 per 1K output tokens
- Embeddings (text-embedding-3-small): ~$0.0001 per 1K tokens

### Example usage:
- Processing 10 lecture PDFs (~100 pages): ~$1-2
- 100 Q&A queries: ~$5-10
- Monthly for active user: ~$10-30

### Ways to reduce costs:
1. Use GPT-3.5-turbo instead of GPT-4 (10x cheaper)
2. Cache common queries
3. Limit context window size
4. Use smaller embedding models
5. Implement rate limiting

## Sharing with Friends

Once deployed, share:

1. **The URL** (e.g., `https://your-app.streamlit.app`)
2. **The password** (if you added authentication)
3. **Instructions:**
   - How to upload their PDFs
   - Available study tools
   - Best practices for queries

## Monitoring & Maintenance

### Streamlit Cloud:
- Built-in logs in dashboard
- Monitor app health
- View deployment history

### Self-hosted:
```bash
# Check service status
systemctl status streamlit

# View logs
journalctl -u streamlit -f

# Monitor resource usage
htop
```

## Troubleshooting

### Common Issues:

1. **App crashes on large PDFs:**
   - Add file size limits
   - Implement chunked processing

2. **Slow response times:**
   - Cache embeddings
   - Use faster embedding models
   - Optimize chunk sizes

3. **API rate limits:**
   - Implement exponential backoff
   - Add request queuing

4. **Memory issues:**
   - Clear old user sessions
   - Implement pagination
   - Use streaming responses

## Next Steps

For production deployment, consider:
1. Adding analytics (Plausible, Google Analytics)
2. Implementing feedback collection
3. Adding export functionality (PDF, Markdown)
4. Creating admin dashboard for monitoring
5. Setting up automated backups
6. Implementing proper logging (Sentry, LogRocket)

## Need Help?

- Streamlit docs: https://docs.streamlit.io
- OpenAI docs: https://platform.openai.com/docs
- Railway docs: https://docs.railway.app
- Render docs: https://render.com/docs