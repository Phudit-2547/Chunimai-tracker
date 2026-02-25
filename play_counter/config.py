from pathlib import Path

from envparse import env

# Only read .env file if it exists on disk.
# In Docker, env vars are injected via docker-compose env_file — no .env file needed.
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.is_file():
    env.read_envfile(str(_env_path))

DISCORD_WEBHOOK_URL = env("DISCORD_WEBHOOK_URL")
WEEKREPORT_WEBHOOK = env.str("WEEKREPORT_WEBHOOK", default=DISCORD_WEBHOOK_URL)
DATABASE_URL = env("DATABASE_URL")
LOCAL_DATABASE_URL = env.str("LOCAL_DATABASE_URL", default="")
USERNAME = env("USERNAME")
PASSWORD = env("PASSWORD")
CONFIG = {"chunithm": True, "maimai": True}

NOTIFICATION_CONFIG = {
    "default": {
        "username": "毎日みのり",
        "avatar_url": "https://pbs.twimg.com/media/GjfKtY6acAIo5Ga?format=jpg",
    },
    "weekly": {
        "username": "毎週みのり",
        "avatar_url": "https://cdn.discordapp.com/attachments/917303163470635018/1381649633981239407/GCaygD2XUAAFTrl.png?ex=684848fe&is=6846f77e&hm=5e7af379f28414de436e5ebf133581eb3a5b94a78b010f3b79d9b86278148007&",
    },
    "maimai": {
        "username": "毎日みのり",
        "avatar_url": "https://cdn.discordapp.com/attachments/917303163470635018/1383463722483449859/3a9fa41c9b0ef014.png?ex=684ee27e&is=684d90fe&hm=5581ac98a03f9559cd04a3034116ddd255d1077db5a65deafa4c9b2662ef2606&",
        "message_template": "**{game}**: You played **{new_plays}** credit(s) today!",
        "emoji": "🎵",
    },
    "chunithm": {
        "username": "毎日みのり",
        "avatar_url": "https://cdn.discordapp.com/attachments/917303163470635018/1383463722483449859/3a9fa41c9b0ef014.png?ex=684ee27e&is=684d90fe&hm=5581ac98a03f9559cd04a3034116ddd255d1077db5a65deafa4c9b2662ef2606&",
        "message_template": "**{game}**: You played **{new_plays}** credit(s) today!",
        "emoji": "🎶",
    },
}
