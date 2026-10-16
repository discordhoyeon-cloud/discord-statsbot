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

# 🔒 통계 전용 카테고리 ID (이 카테고리 외부의 채널은 봇이 아예 볼 수도, 접근할 수도 없습니다)
STATS_CATEGORY_ID = 1560692772426612916

async def run_update():
    guild = bot.get_guild(MY_GUILD_ID_VALUE)
    if not guild:
        return

    total_members = guild.member_count
    human_members = sum(1 for m in guild.members if not m.bot)
    
    # 음성 인원 계산 (통계 카테고리 외부 채널인 '전체회의실' 등은 철저히 배제)
    voice_member_ids = set()
    for vc in guild.voice_channels:
        # 통계 카테고리 안에 있는 채널들은 인원 집계에서 제외 (중복 방지)
        if vc.category_id == STATS_CATEGORY_ID:
            continue
        for member in vc.members:
            voice_member_ids.add(member.id)
            
    for m in guild.members:
        if m.voice and m.voice.channel and m.voice.channel.category_id != STATS_CATEGORY_ID:
            voice_member_ids.add(m.id)
            
    voice_members = len(voice_member_ids)

    # 카테고리 가져오기
    category = guild.get_channel(STATS_CATEGORY_ID)
    if not category or not isinstance(category, discord.CategoryChannel):
        print("⚠️ 통계 카테고리를 찾을 수 없습니다.")
        return

    # 🔒 오직 통계 카테고리 안에 속한 음성 채널들만 순회
    for chan in category.voice_channels:
        name = chan.name
        new_name = None

        if "전체" in name:
            prefix = name.split(":")[0].strip() if ":" in name else "전체 인원"
            new_name = f"{prefix} : {total_members}"
        elif "서버" in name or "사람" in name:
            prefix = name.split(":")[0].strip() if ":" in name else "서버 인원"
            new_name = f"{prefix} : {human_members}"
        elif "음성" in name:
            prefix = name.split(":")[0].strip() if ":" in name else "음성 인원"
            new_name = f"{prefix} : {voice_members}"

        if new_name and chan.name != new_name:
            try:
                await chan.edit(name=new_name)
                print(f"✨ 통계 채널 갱신 완료: '{chan.name}' -> '{new_name}'")
                await asyncio.sleep(2.5)
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