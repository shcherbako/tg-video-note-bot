import asyncio
import os
import subprocess
from pathlib import Path

import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile

BOT_TOKEN = os.getenv("BOT_TOKEN")

WORKDIR = Path("work")
WORKDIR.mkdir(exist_ok=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def run_ffmpeg_make_videonote(src: Path, dst: Path, max_seconds: int = 60):
    cmd = [
        "ffmpeg", "-y",
        "-i", str(src),
        "-t", str(max_seconds),
        "-vf", "crop=min(iw\\,ih):min(iw\\,ih),scale=360:360,fps=30",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-an",
        str(dst),
    ]
    subprocess.run(cmd, check=True)

async def download_by_url(file_path: str, dst: Path):
    url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    timeout = aiohttp.ClientTimeout(total=600)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:
            resp.raise_for_status()
            with open(dst, "wb") as f:
                async for chunk in resp.content.iter_chunked(1024 * 1024):
                    f.write(chunk)

@dp.message(F.video)
async def handle_video(message: Message):
    await message.answer("Делаю кружок…")

    max_size = 50 * 1024 * 1024  # 50MB
    if message.video.file_size and message.video.file_size > max_size:
        await message.answer("Видео слишком большое (макс 50 МБ).")
        return

    file = await bot.get_file(message.video.file_id)
    src = WORKDIR / "input.mp4"
    dst = WORKDIR / "output.mp4"

    await download_by_url(file.file_path, src)
    run_ffmpeg_make_videonote(src, dst, max_seconds=60)

    await bot.send_video_note(chat_id=message.chat.id, video_note=FSInputFile(dst))

    src.unlink(missing_ok=True)
    dst.unlink(missing_ok=True)

async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
