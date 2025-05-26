# Getting Started with BronxBot

## Prerequisites

- Python 3.8 or higher
- MongoDB instance (local or cloud)
- Discord Bot Token
- pip (Python package manager)
- systemd (for Linux service)

## Initial Setup

1. Clone the repository
2. Install Python venv package:
```bash
sudo apt install python3.12-venv python3-pip
```

3. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

4. Install dependencies:
```bash
pip install flask discord.py python-dotenv gunicorn
```

5. Set up the service:
```bash
sudo cp bronxbot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable bronxbot
sudo systemctl start bronxbot
```

## Web Interface

The bot includes a web interface running on port 5000. To access:
1. Make sure the service is running
2. Visit http://localhost:5000
3. For external access, configure your firewall to allow port 5000

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
├── templates/      # Web interface templates
└── utils/          # Utility functions
```

## Service Management

Start the bot:
```bash
sudo systemctl start bronxbot
```

Check status:
```bash
sudo systemctl status bronxbot
```

View logs:
```bash
sudo journalctl -u bronxbot -f
```

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

4. **Web Interface Issues**
   - Check if port 5000 is available
   - Verify permissions for web templates
   - Ensure Flask is installed correctly

## Support

If you need help:
1. Check the error messages in console
2. Verify all configuration files exist
3. Ensure MongoDB is accessible
4. Check bot has required permissions in Discord

For more help, join the [support server](https://discord.gg/jUnNzm29Un).
> This bot was coded using VISUAL STUDIO CODE on LINUX MINT, if your OS is different, expect different problems.