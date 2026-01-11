# Quick Deploy to Render

## 🚀 In 5 Minutes

### Step 1: Push to GitHub
```bash
git add .
git commit -m "Add Render deployment config"
git push origin main
```

### Step 2: Deploy on Render
1. Go to **https://render.com** (sign up with GitHub)
2. Click **"New +"** → **"Blueprint"**
3. Select your **portfolio-tracker** repository
4. Click **"Apply"** (it will read `render.yaml` automatically)

### Step 3: Add Broker API Keys
After deployment, go to your service → **Environment** tab:

**Required (if using brokers):**
- `ZERODHA_API_KEY` = your_key
- `ZERODHA_API_SECRET` = your_secret
- `ZERODHA_REDIRECT_URL` = https://your-app.onrender.com/api/broker/zerodha/callback

(Repeat for Angel One & 5Paisa)

**Optional (for production):**
- `ALLOWED_ORIGINS` = https://your-frontend.vercel.app,https://your-domain.com

### Step 4: Test
Visit: `https://your-app-name.onrender.com/docs`

## ✅ Done!

Your API is live with:
- ✅ Free PostgreSQL database
- ✅ Auto SSL certificate  
- ✅ Auto-deploy on git push
- ✅ Environment variables encrypted

## 📝 Notes

**Free Tier:**
- Sleeps after 15 min inactivity
- ~30 sec cold start time
- 750 hours/month free

**Keep Awake (Optional):**
- Use [UptimeRobot](https://uptimerobot.com) to ping `/health` every 5 minutes

**Frontend Options:**
1. **Vercel** (recommended): Deploy separately, set `VITE_API_URL` to your Render URL
2. **Same Server**: Build frontend (`npm run build`), backend serves it automatically

## 🔧 Troubleshooting

**Build fails?**
- Check logs in Render dashboard
- Ensure `pyproject.toml` has all dependencies

**Database errors?**
- Wait 2-3 min for PostgreSQL to initialize
- Check `DATABASE_URL` is set automatically

**CORS errors?**
- Add your frontend URL to `ALLOWED_ORIGINS` environment variable

## 📚 Full Guide

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed instructions.
