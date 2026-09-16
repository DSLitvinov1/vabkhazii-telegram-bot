import os

from telethon.sync import TelegramClient
from telethon.sessions import StringSession


API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]


def main():
    with TelegramClient(
        StringSession(),
        API_ID,
        API_HASH
    ) as client:
        session_string = client.session.save()

        print("")
        print("=" * 70)
        print("TG_SESSION")
        print("=" * 70)
        print(session_string)
        print("=" * 70)
        print("")
        print(
            "Copy the value above and save it "
            "as GitHub secret TG_SESSION."
        )


if __name__ == "__main__":
    main()
