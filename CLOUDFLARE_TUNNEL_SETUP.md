# Cloudflare Tunnel Setup for Stella Backend
# Exposes localhost:8765 to internet without domain/DNS

# Step 1: Install Cloudflared
# Run as Administrator
choco install cloudflared -y

# Step 2: Login to Cloudflare
cloudflared tunnel login

# This opens browser for authentication
# After login, creates credentials in %USERPROFILE%\.cloudflared\

# Step 3: Create Tunnel
cloudflared tunnel create stella-backend

# This outputs tunnel ID like: 12345678-1234-1234-1234-123456789abc

# Step 4: Create config file
mkdir C:\Users\%USERNAME%\.cloudflared

# Create C:\Users\%USERNAME%\.cloudflared\config.yml
# Replace <TUNNEL_ID> with actual tunnel ID from step 3

# Step 5: Start Tunnel
cloudflared tunnel run stella-backend

# This gives you a URL like:
# https://abc123.trycloudflare.com

# Step 6: Set Vercel Environment Variables
# In Vercel Dashboard:
NEXT_PUBLIC_BACKEND_WS_URL=wss://abc123.trycloudflare.com
NEXT_PUBLIC_BACKEND_API_URL=https://abc123.trycloudflare.com

# Step 7: Run Stella Backend
cd E:\Projects\stella
python main.py --host 0.0.0.0 --port 8765

# The tunnel connects localhost:8765 to internet
