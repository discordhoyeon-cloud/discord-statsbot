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

# 🔒 보내주신 정확한 채널 ID 3개만 단독 타겟팅 (다른 채널은 절대 접근 불가)
STATS_CHANNELS = {
    "total": 1560692773479387296, # 전체인원 채널 ID
    "human": 1560692788683608215, # 서버인원 채널 ID
    "voice": 1560692803971850363  # 음성인원 채널 ID
}

async def run_update():
    guild = bot.get_guild(MY_GUILD_ID_VALUE)
    if not guild:
        print("⚠️ [갱신 실패] 길드 정보를 불러오지 못했습니다.")
        return

    total_members = guild.member_count
    human_members = sum(1 for m in guild.members if not m.bot)
    
    # 봇 포함 음성 채널 접속 인원 계산
    voice_member_ids = set()
    for vc in guild.voice_channels:
        for member in vc.members:
            voice_member_ids.add(member.id)
    for m in guild.members:
        if m.voice and m.voice.channel is not None:
            voice_member_ids.add(m.id)
    voice_members = len(voice_member_ids)

    target_data = {
        "total": ("전체 인원", total_members),
        "human": ("서버 인원", human_members),
        "voice": ("음성 인원", voice_members)
    }

    updated_count = 0
    # 오직 위에 정의된 지정된 ID 3개만 반복문을 돌림
    for kind, cid in STATS_CHANNELS.items():
        chan = guild.get_channel(cid)
        if not chan:
            print(f"⚠️ [경고] ID [{cid}]에 해당하는 채널을 찾을 수 없습니다. (채널이 삭제되었거나 ID가 다를 수 있음)")
            continue

        default_name, current_value = target_data[kind]
        name = chan.name

        # 콜론(:) 앞의 꾸미기 요소(이모지 등)는 그대로 유지하고 뒤의 숫자만 교체
        if ":" in name:
            prefix = name.split(":")[0].strip()
            new_name = f"{prefix} : {current_value}"
        else:
            new_name = f"{default_name} : {current_value}"

        # 이름이 다를 때만 변경하고 API 리밋 방지를 위해 2.5초 대기
        if chan.name != new_name:
            try:
                await chan.edit(name=new_name)
                print(f"✨ 지정 통계 채널 갱신 성공: '{chan.name}' -> '{new_name}'")
                updated_count += 1
                await asyncio.sleep(2.5) # API 레이트 리밋 방지 딜레이
            except discord.HTTPException as e:
                if e.status == 429:
                    print(f"⚠️ [경고] 디스코드 API 레이트 리밋(429) 감지됨!")
                else:
                    print(f"❌ API 에러 [{chan.name}]: {e}")
            except Exception as e:
                print(f"❌ 기타 에러 [{chan.name}]: {e}")
        else:
            print(f"💤 [스킵] 변경 사항 없음: '{chan.name}'")

    print(f"✅ 갱신 작업 완료 (실제 변경된 통계 채널 수: {updated_count}개)")

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

@bot.tree.command(name="통계갱신", description="지정된 3개의 통계 채널 수치만 안전하게 갱신합니다.")
async def refresh_stats(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 이 명령어를 사용할 서버 관리자 권한이 없습니다!", ephemeral=True)
        return

    await interaction.response.send_message("🔄 지정된 통계 채널들만 안전하게 순차 갱신 중입니다...", ephemeral=True)
    
    try:
        await run_update()
        await interaction.edit_original_response(content="✅ 지정된 3개의 통계 채널이 안전하게 갱신되었습니다!")
    except Exception as e:
        await interaction.edit_original_response(content=f"❌ 갱신 중 오류가 발생했습니다: {e}")

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)