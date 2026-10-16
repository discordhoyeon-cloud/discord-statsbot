import os
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

# ⚠️ 서버 ID 및 보내주신 카테고리/채널 3개 ID 하드코딩
MY_GUILD_ID_VALUE = 1558388838462652498
MY_GUILD_ID = discord.Object(id=1558388838462652498) 

STATS_CATEGORY_ID = 1560692772426612916
STATS_CHANNELS = {
    "total": 1560692773479387296, # 전체 인원
    "human": 1560692788683608215, # 서버인원
    "voice": 1560692803971850363  # 음성인원
}

async def run_update():
    """지정된 채널 ID에 맞춰 통계 숫자를 즉시 갱신하는 함수"""
    guild = bot.get_guild(MY_GUILD_ID_VALUE)
    if not guild:
        return

    total_members = guild.member_count
    human_members = sum(1 for m in guild.members if not m.bot)
    
    # 봇 포함해서 음성 채널에 접속한 총 인원 계산
    voice_member_ids = set()
    for vc in guild.voice_channels:
        for member in vc.members:
            voice_member_ids.add(member.id)
            
    for m in guild.members:
        if m.voice and m.voice.channel is not None:
            voice_member_ids.add(m.id)
            
    voice_members = len(voice_member_ids)

    # 채널별 매핑 데이터 (3개)
    target_data = {
        "total": ("👥 전체 인원", total_members),
        "human": ("👤 서버인원", human_members),
        "voice": ("🔊 음성인원", voice_members)
    }

    for kind, cid in STATS_CHANNELS.items():
        if not cid:
            continue
        chan = guild.get_channel(cid)
        if chan:
            try:
                default_prefix, current_value = target_data[kind]

                # 기존 채널 이름 형식 유지
                if ":" in chan.name:
                    prefix = chan.name.rsplit(":", 1)[0].strip()
                    new_name = f"{prefix} : {current_value}"
                else:
                    new_name = f"{default_prefix} : {current_value}"

                # 이름이 같으면 API 요청 스킵
                if chan.name == new_name:
                    continue

                await chan.edit(name=new_name)
                print(f"✨ 채널 이름 갱신됨: '{chan.name}' -> '{new_name}'")
            except discord.HTTPException as e:
                if e.status == 429:
                    print(f"⚠️ 디스코드 API 레이트 리밋(429) 감지됨.")
                else:
                    print(f"❌ 디스코드 API 에러 발생 [{cid}]: {e}")
            except Exception as e:
                print(f"❌ 기타 오류 발생 ({cid}): {e}")

@bot.event
async def on_ready():
    print(f'로그인 성공: {bot.user.name}')
    
    try:
        bot.tree.copy_global_to(guild=MY_GUILD_ID)
        synced = await bot.tree.sync(guild=MY_GUILD_ID)
        print(f"서버 전용 슬래시 명령어 {len(synced)}개 즉시 동기화 완료!")
    except Exception as e:
        print(f"슬래시 명령어 동기화 실패: {e}")
        
    await run_update()
    
    if not update_stats.is_running():
        update_stats.start()

# ⏱️ 5분마다 자동 갱신
@tasks.loop(minutes=5)
async def update_stats():
    try:
        await run_update()
    except Exception as e:
        print(f"통계 자동 갱신 에러: {e}")

# 수동으로 강제 갱신하고 싶을 때 쓰는 명령어 (서버 관리자만 가능)
@bot.tree.command(name="통계갱신", description="모든 통계 채널 수치를 즉시 갱신합니다.")
async def refresh_stats(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 이 명령어를 사용할 서버 관리자 권한이 없습니다!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    try:
        await run_update()
        await interaction.followup.send("✅ 지정된 3개의 채널 통계가 즉시 갱신되었습니다!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ 갱신 중 오류가 발생했습니다: {e}", ephemeral=True)

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)