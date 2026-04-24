# Content Queue v4.0 - Deployment Guide

## 🚀 Quick Start (Local Development)

### 1. Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python packages
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your keys:
nano .env
```

Generate secret keys:
```python
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Initialize Database

```bash
python3 app.py
# Database will be created automatically on first run
```

### 4. Run Locally

```bash
python3 app.py
# App runs on http://localhost:5555
```

---

## 🌐 Production Deployment (Railway.app - Recommended)

### Why Railway?
- Free tier available
- PostgreSQL included
- Auto-deploys from Git
- Custom domains
- Easy environment variables

### Step-by-Step:

**1. Push Code to GitHub**

```bash
git init
git add .
git commit -m "Initial commit - Content Queue v4.0"
git remote add origin https://github.com/yourusername/contentqueue.git
git push -u origin main
```

**2. Deploy to Railway**

1. Go to https://railway.app
2. Click "New Project" → "Deploy from GitHub"
3. Select your contentqueue repository
4. Railway will detect Python and deploy automatically

**3. Add PostgreSQL Database**

1. In Railway project, click "New" → "Database" → "PostgreSQL"
2. Railway automatically sets DATABASE_URL environment variable

**4. Set Environment Variables**

In Railway project settings → Variables, add:
```
SECRET_KEY=<generate-random-string>
JWT_SECRET_KEY=<generate-random-string>
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PRICE_ID=price_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

**5. Set Up Custom Domain**

1. In Railway project → Settings → Domains
2. Add your domain: contentqueue.app
3. Update DNS with Railway's CNAME records

**6. Initialize Database**

Railway runs migrations automatically, or SSH in:
```bash
railway run python3 -c "from app import init_db; init_db()"
```

---

## 💳 Stripe Setup

### 1. Create Stripe Account
- Go to https://stripe.com
- Sign up for account
- Get API keys from Dashboard

### 2. Create Product & Price

1. Dashboard → Products → Add Product
2. Name: "Content Queue Pro"
3. Price: $39/month recurring
4. Copy the Price ID (starts with `price_`)

### 3. Set Up Webhook

1. Dashboard → Developers → Webhooks
2. Add endpoint: `https://your domain.com/api/stripe/webhook`
3. Select events:
   - `customer.subscription.created`
   - `customer.subscription.deleted`
   - `customer.subscription.updated`
4. Copy webhook secret (starts with `whsec_`)

### 4. Test Mode vs Live Mode

- Use `sk_test_` keys for development
- Switch to `sk_live_` keys for production
- Create separate products in each mode

---

## 📁 Project Structure

```
contentqueue/
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (DO NOT COMMIT)
├── .env.example           # Environment template
├── static/
│   ├── landing.html       # Marketing landing page
│   ├── app.html           # Main application (logged in)
│   └── login.html         # Login/signup page
├── README.md
└── .gitignore
```

---

## 🔒 Security Checklist

- [ ] Use strong SECRET_KEY and JWT_SECRET_KEY
- [ ] Enable HTTPS (Railway does this automatically)
- [ ] Set FLASK_ENV=production
- [ ] Use PostgreSQL (not SQLite) in production
- [ ] Add rate limiting (TODO: implement)
- [ ] Set up monitoring (Railway provides basic metrics)

---

## 📊 Monitoring & Analytics

### Railway Built-in:
- Logs: Railway → Project → Deployments → View Logs
- Metrics: CPU, Memory, Network usage
- Alerts: Set up in Railway dashboard

### Optional Add-ons:
- **Sentry** - Error tracking
- **LogTail** - Log aggregation
- **Stripe Dashboard** - Payment analytics

---

## 🔄 Updates & Maintenance

### Deploy Updates:
```bash
git add .
git commit -m "Update description"
git push
# Railway auto-deploys
```

### Database Migrations:
If you change models in app.py:
```bash
# Add migration code or use Flask-Migrate
# For now, manual changes via Railway shell
```

### Backup Database:
```bash
# From Railway dashboard
railway run pg_dump > backup.sql
```

---

## 💰 Cost Breakdown

### Railway (Recommended)
- **Hobby Plan**: $5/month
  - 512MB RAM
  - 1GB Storage
  - Includes PostgreSQL
  - Custom domain
  - SSL/HTTPS

### Stripe
- **2.9% + $0.30** per transaction
- No monthly fees
- Example: $39 subscription = $1.43 fee, you keep $37.57

### Total Monthly Cost:
- **Fixed**: $5 (Railway)
- **Variable**: ~3% of revenue (Stripe)
- **100 users @ $39/mo** = $3,900 revenue - $117 Stripe fees - $5 Railway = **$3,778 profit/month**

---

## 🆘 Troubleshooting

### Database Connection Error
```bash
# Check DATABASE_URL is set correctly
railway variables
```

### Stripe Webhook Not Working
- Verify webhook URL is correct
- Check webhook secret matches .env
- Test with Stripe CLI: `stripe listen --forward-to localhost:5555/api/stripe/webhook`

### App Won't Start
```bash
# Check logs
railway logs
```

---

## 📈 Next Steps After Deployment

1. **Test full flow**:
   - Sign up
   - Add payment
   - Use app
   - Cancel subscription

2. **Set up monitoring**:
   - Sentry for errors
   - Google Analytics on landing page

3. **Marketing**:
   - Launch Product Hunt
   - Post on Reddit
   - Creator outreach

4. **Iterate**:
   - User feedback
   - Analytics
   - A/B testing pricing

---

## 🎯 Launch Checklist

- [ ] Backend deployed to Railway
- [ ] PostgreSQL database connected
- [ ] Stripe keys configured (live mode)
- [ ] Custom domain pointing to Railway
- [ ] SSL/HTTPS working
- [ ] Landing page live
- [ ] Sign up flow tested
- [ ] Payment flow tested
- [ ] Webhooks receiving events
- [ ] Error monitoring set up
- [ ] Backup strategy in place

**You're ready to launch! 🚀**
