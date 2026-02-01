# Zerodha Authentication Debugging Guide

## Issue: "Incorrect `api_key` or `access_token`"

This error means your Zerodha credentials are no longer valid. Here's how to diagnose and fix it.

## 🔍 What the Enhanced Logging Shows

I've added comprehensive logging that will now show you exactly where authentication fails:

### Expected Success Logs
```
✓ Credentials decrypted successfully
📋 API key: length=32, non-empty=True
📋 API secret: length=64, non-empty=True
📋 Access token: length=28, non-empty=True
📋 Broker config: api_key_stored=True, access_token_stored=True
🔐 Creating KiteConnect instance with api_key
✓ KiteConnect instance created
🔐 Setting access token on KiteConnect
✓ Access token set successfully
🔐 Calling profile API to validate credentials
✓ Profile API call successful: user_name=YourName, user_id=ABC123
```

### Expected Failure Logs (with Help)
```
✗ Profile API call failed: Incorrect `api_key` or `access_token` (code: 403)
⚠️  This usually means: 1) Access token expired, 2) API key invalid, or 3) Network issue
⚠️  Solution: Try reconnecting Zerodha from the Brokers page
```

## 🛠️ Root Causes & Solutions

### 1. **Access Token Expired** (Most Common)
- **Symptom**: Profile API call fails immediately with "Incorrect api_key or access_token"
- **Why**: Zerodha access tokens expire after 8 hours or when you log out of Zerodha web
- **Solution**: 
  - Go to **Brokers page** → **Zerodha section**
  - Click **"Reconnect Zerodha"** button
  - This will get a fresh access token

### 2. **Credentials Not Stored Properly**
- **Symptom**: Logs show `api_key_stored=False` or `access_token_stored=False`
- **Why**: Setup failed to save credentials to database
- **Solution**:
  - Remove the existing Zerodha config
  - Try setting up Zerodha again from the Brokers page
  - Make sure you see the "Successfully connected" message

### 3. **Decryption Failed**
- **Symptom**: Logs show `✗ Failed to decrypt credentials`
- **Why**: Encryption key changed or credentials corrupted
- **Solution**:
  - Check `.env` file has `ENCRYPTION_KEY` set consistently
  - If key changed, reconnect Zerodha to re-encrypt with new key
  - Contact support if issue persists

### 4. **API Key Invalid**
- **Symptom**: Logs show `api_key: length=0` or `api_key: non-empty=False`
- **Why**: API key not saved during setup
- **Solution**:
  - Verify your Zerodha API Key from [https://kite.zerodha.com/settings/api](https://kite.zerodha.com/settings/api)
  - Reconnect Zerodha with correct credentials

## 📝 How to Get Detailed Logs

### Option 1: Backend Console (Recommended)
1. Start the backend: `uv run uvicorn portfolio_tracker.main:app --reload`
2. When syncing fails, check the terminal output
3. Look for lines with `✓`, `✗`, `📋`, and `🔐` symbols

### Option 2: Browser Console
1. Open browser developer tools (F12)
2. Go to **Network** tab
3. Try syncing Zerodha holdings
4. Click on the failing request to `/api/zerodha/sync-holdings`
5. Check the **Response** tab for error details

### Option 3: Enable Debug Logging
Add this to your code (temporarily):
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🔄 Complete Reconnection Steps

1. **Go to Brokers Page**
   - Navigate to `http://localhost:8000/app/brokers`

2. **Find Zerodha Section**
   - Look for "Zerodha" broker

3. **Click "Reconnect" or "Setup"**
   - This will redirect you to Zerodha login

4. **Enter Your Credentials**
   - Zerodha API Key
   - Zerodha API Secret

5. **Approve Access**
   - Click "Authorize" when asked

6. **Verify Success**
   - You should see "Successfully connected" message
   - Check the backend logs for success confirmation

## ⚠️ Common Mistakes

❌ **Don't**: Use old access tokens from yesterday
✅ **Do**: Get fresh token by reconnecting

❌ **Don't**: Modify credentials in database directly
✅ **Do**: Use the Brokers page setup flow

❌ **Don't**: Use test/demo API credentials
✅ **Do**: Use your actual Zerodha API Key from settings

## 📞 If Problem Persists

After reconnecting, if you still see the error:

1. **Check the backend logs carefully** - note exact error message
2. **Try in incognito mode** - clear browser cache
3. **Verify your Zerodha credentials** at https://kite.zerodha.com/settings/api
4. **Check if Zerodha API is enabled** on your account

## 🔑 Technical Details

- **Credential Storage**: All credentials are encrypted at rest in the database
- **Token Lifetime**: Zerodha access tokens are valid for ~8 hours
- **Encryption Key**: Uses `ENCRYPTION_KEY` from `.env` (auto-generated if not set)
- **API Endpoint**: `POST /api/zerodha/sync-holdings?portfolio_id=1`

---

**Updated**: Now with enhanced debugging logging! Check your backend console for detailed step-by-step logs.
