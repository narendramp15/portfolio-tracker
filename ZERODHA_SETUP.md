# Zerodha Broker Integration Guide

## Overview
Your portfolio tracker now supports Zerodha broker integration using the KiteConnect API. You can connect your Zerodha account, fetch your holdings, and automatically import them into your portfolio.

## Setup

### 1. Get Zerodha API Credentials
1. Visit [Zerodha Kite Connect](https://kite.trade)
2. Sign up for a developer account
3. Create a new app and get your:
   - API Key
   - API Secret

### 2. Configure Environment Variables
Add to your `.env` file:
```
ZERODHA_API_KEY=your_api_key_here
ZERODHA_API_SECRET=your_api_secret_here
ZERODHA_REDIRECT_URL=http://localhost:8000/app/brokers
```

For production, update the redirect URL to match your domain.

## How to Use

### Connect Zerodha Account
1. Navigate to **Brokers** in the sidebar
2. Click **Connect Zerodha** button
3. Login with your Zerodha credentials
4. Authorize the app
5. You'll be redirected back to the broker settings page

### Sync Holdings to Portfolio
1. Go to **Brokers** page
2. Find your connected Zerodha account
3. Click **Sync Holdings**
4. Select the portfolio where you want to import holdings
5. Holdings will be fetched from Zerodha and added/updated in your portfolio

### View and Manage Brokers
- **Connected Brokers**: See all connected broker accounts with:
  - Last sync date
  - Connection status
  - Broker user ID

- **Actions**:
  - **Sync Holdings**: Update portfolio with latest holdings
  - **Remove**: Disconnect the broker account

## Database Schema

### BrokerConfig Table
Stores broker connection information:
- `id`: Primary key
- `user_id`: Link to user account
- `broker_name`: 'zerodha', 'angel', '5paisa', etc.
- `broker_user_id`: Broker's user identifier
- `access_token`: Encrypted access token
- `refresh_token`: Encrypted refresh token (if applicable)
- `api_key`: Encrypted API key (if applicable)
- `is_active`: Connection status
- `last_synced`: Last sync timestamp
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

## API Endpoints

### Get Broker Configurations
```
GET /api/broker/configs?token={access_token}
```
Returns list of all broker configs for the current user.

### Get Zerodha Login URL
```
GET /api/broker/zerodha/login-url?token={access_token}
```
Returns the Zerodha authorization URL.

### Zerodha OAuth Callback
```
POST /api/broker/zerodha/callback?request_token={token}&token={access_token}
```
Handles Zerodha OAuth callback and saves credentials.

### Sync Holdings
```
POST /api/broker/zerodha/sync-holdings?portfolio_id={id}&token={access_token}
```
Fetches holdings from Zerodha and imports them into the specified portfolio.

### Delete Broker Config
```
DELETE /api/broker/configs/{config_id}?token={access_token}
```
Removes a broker connection.

## Imported Data

When you sync holdings from Zerodha, the following asset information is imported:
- Symbol (e.g., INFY, HDFC, RELIANCE)
- Quantity held
- Average buy price
- Current market price
- ISIN code (stored but not used in portfolio value calculation)

## Future Broker Support

The architecture is designed to support multiple brokers. Planned integrations:
- **Angel**: Stockal API
- **5Paisa**: REST API
- **Upstox**: API integration
- **Others**: Easy to add with broker-specific adapter classes

## Security

- Access tokens are encrypted in the database
- Passwords are never stored (OAuth-based)
- API keys and secrets are environment variables
- User data is isolated by user_id

## Troubleshooting

### "Zerodha not connected" Error
- Make sure you've clicked "Connect Zerodha" and completed the authorization
- Check that your access token hasn't expired

### Holdings not syncing
- Verify your Zerodha API credentials in `.env`
- Check that your Zerodha account has active holdings
- Ensure the portfolio exists and is owned by your account

### Import failed
- Check portfolio_tracker logs for detailed error messages
- Verify that the selected portfolio is correct
- Try removing and reconnecting the Zerodha account

## Architecture

### Broker Integration Flow
1. User clicks "Connect Zerodha"
2. App redirects to Zerodha login
3. Zerodha returns request token to callback URL
4. App exchanges request token for access token
5. App stores encrypted credentials in database
6. User can sync holdings anytime (access token is retrieved from DB)

### Holdings Sync Flow
1. User selects portfolio and clicks "Sync Holdings"
2. App fetches holdings from Zerodha KiteConnect API
3. For each holding:
   - Check if asset exists in portfolio
   - If exists: update quantity and prices
   - If new: create asset with fetched data
4. Update last_synced timestamp
5. Return summary to user

## Next Steps

1. Connect your Zerodha account using the Broker Settings page
2. Sync your holdings to a portfolio
3. View your complete portfolio on the Dashboard
4. Add/edit transactions as needed

For issues or feature requests, please check the GitHub repository.
