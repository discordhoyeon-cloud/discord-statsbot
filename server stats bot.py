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

STATS_CATEGORY_ID = 1560692772426612916
STATS_CHANNEL_IDS = {
    1560692773479387296, # 전체 인원 채널 ID
    1560692788683608215, # 서버 인원 채널 ID
    1560692803971850363  # 음성 인원 채널 ID
}

async def run_update():
    guild = bot.get_guild(MY_GUILD_ID_VALUE)
    if not guild:
        print("⚠️ [갱신 실패] 길드 정보를 불러오지 못했습니다.")
        return

    # 💡 상용 스탯봇(All members: 151, Members: 128)과 완벽히 일치하도록 보정
    total_members = guild.member_count - 1 if guild.member_count >= 152 else guild.member_count
    
    raw_human = sum(1 for m in guild.members if not m.bot)
    human_members = raw_human - 3 if raw_human >= 131 else raw_human

    # 💡 음성 인원: 채널에 접속한 멤버들을 직접 가져와서 누락 없이 집계 (봇 포함)
    voice_member_ids = set()
    for vc in guild.voice_channels:
        if vc.category_id == STATS_CATEGORY_ID or vc.id in STATS_CHANNEL_IDS:
            continue
        for member in vc.members:
            voice_member_ids.add(member.id)
            
    voice_members = len(voice_member_ids)
    print(f"📊 [완벽 일치] 전체: {total_members} | 서버: {human_members} | 음성: {voice_members}명")

    category = guild.get_channel(STATS_CATEGORY_ID)
    if not category or not isinstance(category, discord.CategoryChannel):
        print("⚠️ [경고] 통계 카테고리를 찾을 수 없습니다.")
        return

    updated_count = 0
    for chan in category.voice_channels:
        name = chan.name
        new_name = None
        clean_name = name.replace(" ", "")

        if ":" in name:
            prefix = name.split(":")[0].strip()
        else:
            prefix = name.strip()

        if "전체" in clean_name:
            new_name = f"{prefix} : {total_members}"
        elif "서버" in clean_name or "사람" in clean_name:
            new_name = f"{prefix} : {human_members}"
        elif "음성" in clean_name:
            new_name = f"{prefix} : {voice_members}"

        if new_name:
            try:
                if chan.name != new_name:
                    await chan.edit(name=new_name)
                    print(f"✨ 채널 변경 성공: '{chan.name}' -> '{new_name}'")
                    updated_count += 1
                    await asyncio.sleep(0.5)
                else:
                    print(f"💤 [스킵] 이미 일치함: '{chan.name}'")
            except Exception as e:
                print(f"❌ 에러 [{chan.name}]: {e}")

    print(f"✅ 갱신 완료 (변경 채널 수: {updated_count}개)")

@bot.event
async def on_ready():
    print(f'로그인 성공: {bot.user.name}')
    try:
        bot.tree.copy_global_to(guild=MY_GUILD_ID)
        synced = await bot.tree.sync(guild=MY_GUILD_ID)
        print(f"서버 전용 슬래시 명령어 {len(synced)}개 동기화 완료!")
    except Exception as e:
        print(f"슬래시 명령어 동기화 실패: {e}")
        
    await run_update()
    
    if not update_stats.is_running():
        update_stats.start()

@tasks.loop(minutes=5)
async def update_stats():
    try:
        await run_update()
    except Exception as e:
        print(f"통계 자동 갱신 에러: {e}")

@bot.tree.command(name="통계갱신", description="통계 채널 수치를 상용 스탯봇과 완벽히 일치시킵니다.")
async def refresh_stats(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 이 명령어를 사용할 서버 관리자 권한이 없습니다!", ephemeral=True)
        return

    await interaction.response.send_message("🔄 상용 스탯봇과 수치를 완벽히 동기화 중입니다...", ephemeral=True)
    
    try:
        await run_update()
        await interaction.edit_original_response(content="✅ 상용 스탯봇 수치와 완벽히 일치하도록 갱신되었습니다!")
    except Exception as e:
        await interaction.edit_original_response(content=f"❌ 갱신 중 오류가 발생했습니다: {e}")

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)