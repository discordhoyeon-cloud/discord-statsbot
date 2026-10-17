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

    # 💡 디스코드 캐시/멤버 정보를 강제로 동기화하여 누락 방지
    try:
        await guild.chunk()
    except Exception as e:
        print(f"⚠️ 멤버 chunk 로딩 중 예외 발생: {e}")

    total_members = guild.member_count 
    human_members = sum(1 for m in guild.members if not m.bot)
    
    # 💡 서버의 모든 음성 채널을 직접 순회하며 방에 있는 진짜 사람들을 완벽하게 수집
    voice_member_ids = set()
    for vc in guild.voice_channels:
        # 통계 채널 자체이거나 통계 카테고리에 속한 채널은 집계 대상에서 제외
        if vc.id in STATS_CHANNEL_IDS or vc.category_id == STATS_CATEGORY_ID:
            continue
        for member in vc.members:
            if not member.bot: # 봇 제외
                voice_member_ids.add(member.id)
            
    voice_members = len(voice_member_ids)
    print(f"📊 [강력 집계] 전체: {total_members} | 사람: {human_members} | 음성: {voice_members}명")

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
                # 💡 강제로 이름을 갱신하도록 기존 이름과 달라도 바로 수정 적용
                if chan.name != new_name:
                    await chan.edit(name=new_name)
                    print(f"✨ 채널 변경 성공: '{chan.name}' -> '{new_name}'")
                    updated_count += 1
                    await asyncio.sleep(2.5) # API 429 레이트 리밋 방지
                else:
                    print(f"💤 [스킵] 이미 일치함: '{chan.name}'")
            except Exception as e:
                print(f"❌ 에러 [{chan.name}]: {e}")

    print(f"✅ 갱신 완료 (실제 변경된 채널 수: {updated_count}개)")

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

@bot.tree.command(name="통계갱신", description="통계 채널 수치를 리밋 방지하며 안전하게 갱신합니다.")
async def refresh_stats(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 이 명령어를 사용할 서버 관리자 권한이 없습니다!", ephemeral=True)
        return

    await interaction.response.send_message("🔄 통계 채널을 안전하게 강제 갱신 중입니다...", ephemeral=True)
    
    try:
        await run_update()
        await interaction.edit_original_response(content="✅ 통계 채널들이 안전하게 갱신되었습니다!")
    except Exception as e:
        await interaction.edit_original_response(content=f"❌ 갱신 중 오류가 발생했습니다: {e}")

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)