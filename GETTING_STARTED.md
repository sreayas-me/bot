# Getting Started with BronxBot

## Prerequisites

- Python 3.8 or higher
- MongoDB instance (local or cloud)
- Discord Bot Token
- pip (Python package manager)

## Initial Setup

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy `config.example.json` to `data/config.json` and fill in:
```json
{
    "TOKEN": "your-bot-token-here",
    "OWNER_IDS": ["your-discord-id"],
    "OWNER_REPLY": ["nickname1", "nickname2"],
    "MONGO_URI": "mongodb://localhost:27017"  # or your MongoDB connection string
}
```

## Configuration Details

### Required Fields

- `TOKEN`: Your Discord bot token from [Discord Developer Portal](https://discord.com/developers/applications)
- `OWNER_IDS`: Array of Discord user IDs who will have owner permissions
- `MONGO_URI`: MongoDB connection string 
  - For local MongoDB: `mongodb://localhost:27017`
  - For MongoDB Atlas: `mongodb+srv://...`

### Directory Structure

Make sure these directories exist:
```
bronxbot/
├── data/           # Bot data storage
├── cogs/           # Bot commands and features
└── utils/          # Utility functions
```

## First Launch

1. Start MongoDB service (if using local instance)
2. Create required directories:
```bash
mkdir -p data
```

3. Start the bot:
```bash
python bronxbot.py
```

## Required Data Files

The bot expects these files in the `data` directory:
- `config.json`: Main configuration
- `welcome.json`: Welcome messages and settings
- `shop.json`: Shop items and settings (created automatically)
- `modmail.json`: ModMail tickets (created automatically)

## Common Issues

1. **MongoDB Connection**
   - Ensure MongoDB is running
   - Check connection string is correct
   - Verify network access if using cloud MongoDB

2. **Permission Issues**
   - Bot needs proper Discord permissions
   - Requires `GUILD`, `MEMBERS`, and `MESSAGE_CONTENT` intents

3. **Directory Permissions**
   - Ensure write permissions in `data` directory
   - Check file ownership matches running user

## Support

If you need help:
1. Check the error messages in console
2. Verify all configuration files exist
3. Ensure MongoDB is accessible
4. Check bot has required permissions in Discord

For more help, join the [support server](https://discord.gg/furryporn).
> This bot was coded using VISUAL STUDIO CODE on LINUX MINT, if your OS is different, expect different problems.