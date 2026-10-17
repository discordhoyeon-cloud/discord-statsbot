import os
import asyncio
import discord
from discord.ext import tasks, commands

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix="!", 
    intents=intents,
    chunk_guild_with_intent=True
)

MY_GUILD_ID_VALUE = 1558388838462652498
MY_GUILD_ID = discord.Object(id=1558388838462652498) 

# 🔒 통계 전용 카테고리 ID (이 카테고리 외부는 절대 접근 불가)
STATS_CATEGORY_ID = 1560692772426612916

async def run_update():
    guild = bot.get_guild(MY_GUILD_ID_VALUE)
    if not guild:
        return

    total_members = guild.member_count
    human_members = sum(1 for m in guild.members if not m.bot)
    
    # 음성 인원 집계 (통계 카테고리 외부에 있는 일반 채널들만 대상으로 계산)
    voice_member_ids = set()
    for vc in guild.voice_channels:
        if vc.category_id == STATS_CATEGORY_ID:
            continue
        for member in vc.members:
            voice_member_ids.add(member.id)
            
    for m in guild.members:
        if m.voice and m.voice.channel and m.voice.channel.category_id != STATS_CATEGORY_ID:
            voice_member_ids.add(m.id)
            
    voice_members = len(voice_member_ids)

    category = guild.get_channel(STATS_CATEGORY_ID)
    if not category or not isinstance(category, discord.CategoryChannel):
        print("⚠️ 통계 카테고리를 찾을 수 없습니다.")
        return

    # 🔒 오직 통계 카테고리 내부에 있는 채널들만 검사
    for chan in category.voice_channels:
        name = chan.name
        new_name = None

        # 띄어쓰기(공백)를 모두 무시하고 키워드 검사
        clean_name = name.replace(" ", "")

        if "전체" in clean_name:
            prefix = name.split(":")[0].strip() if ":" in name else "👥 전 체 인 원"
            new_name = f"{prefix} : {total_members}"
        elif "서버" in clean_name or "사람" in clean_name:
            prefix = name.split(":")[0].strip() if ":" in name else "👤 서 버 인 원"
            new_name = f"{prefix} : {human_members}"
        elif "음성" in clean_name:
            prefix = name.split(":")[0].strip() if ":" in name else "🔊 음 성 인 원"
            new_name = f"{prefix} : {voice_members}"

        if new_name and chan.name != new_name:
            try:
                await chan.edit(name=new_name)
                print(f"✨ 통계 채널 갱신 완료: '{chan.name}' -> '{new_name}'")
                await asyncio.sleep(2.5) # API 리밋 방지 대기
            except Exception as e:
                print(f"❌ 채널 갱신 에러: {e}")

@bot.event
async def on_ready():
    print(f'로그인 성공: {bot.user.name}')
    try:
        bot.tree.copy_global_to(guild=MY_GUILD_ID)
        synced = await bot.tree.sync(guild=MY_GUILD_ID)
        print(f"슬래시 명령어 {len(synced)}개 동기화 완료!")
    except Exception as e:
        print(f"동기화 실패: {e}")
        
    await run_update()
    
    if not update_stats.is_running():
        update_stats.start()

@tasks.loop(minutes=5)
async def update_stats():
    try:
        await run_update()
    except Exception as e:
        print(f"자동 갱신 에러: {e}")

@bot.tree.command(name="통계갱신", description="통계 카테고리 내부 채널만 안전하게 갱신합니다.")
async def refresh_stats(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 관리자 권한이 없습니다!", ephemeral=True)
        return

    await interaction.response.send_message("🔄 통계 채널을 안전하게 갱신 중입니다...", ephemeral=True)
    try:
        await run_update()
        await interaction.edit_original_response(content="✅ 통계 채널이 안전하게 갱신되었습니다!")
    except Exception as e:
        await interaction.edit_original_response(content=f"❌ 오류 발생: {e}")

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)