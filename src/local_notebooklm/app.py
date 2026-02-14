from dotenv import load_dotenv

from .bot import run_bot
from .config import settings


def main() -> None:
    load_dotenv()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    run_bot(settings)


if __name__ == "__main__":
    main()
