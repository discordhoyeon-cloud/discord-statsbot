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

    print(f"📊 [통계 계산] 전체: {total_members} | 서버인원: {human_members} | 음성: {voice_members}")

    updated_count = 0
    for chan in guild.voice_channels:
        name = chan.name
        new_name = None

        if "전체" in name:
            prefix = name.split(":")[0].strip() if ":" in name else "👥 ( 🔥 ) 전 체 인 원"
            new_name = f"{prefix} : {total_members}"
        elif "서버" in name or "사람" in name:
            prefix = name.split(":")[0].strip() if ":" in name else "🔊 ( 🌷 ) 서 버 인 원"
            new_name = f"{prefix} : {human_members}"
        elif "음성" in name:
            prefix = name.split(":")[0].strip() if ":" in name else "📞 ( 💎 ) 음 성 인 원"
            new_name = f"{prefix} : {voice_members}"

        # 💡 핵심 방어 로직: 이름이 기존과 정확히 똑같으면 API 요청을 아예 안 보냄 (리밋 방지)
        if new_name and chan.name != new_name:
            try:
                await chan.edit(name=new_name)
                print(f"✨ 채널 이름 변경 성공: '{chan.name}' -> '{new_name}'")
                updated_count += 1
                
                # 🛡️ 리밋 방지를 위해 채널 수정 사이에 2.5초 안전 대기
                await asyncio.sleep(2.5)
            except discord.HTTPException as e:
                if e.status == 429:
                    print(f"⚠️ [경고] 디스코드 레이트 리밋(429) 감지됨! 대기 시간을 늘려야 합니다.")
                else:
                    print(f"❌ API 에러 [{chan.name}]: {e}")
            except Exception as e:
                print(f"❌ 기타 에러 [{chan.name}]: {e}")
        elif new_name:
            print(f"💤 [스킵] 변경 사항 없음: '{chan.name}'")

    print(f"✅ 갱신 작업 완료 (실제 변경된 채널 수: {updated_count}개)")

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

# ⏱️ 너무 자주 바꾸지 않도록 5분 간격 유지 (리밋 방지에 가장 이상적)
@tasks.loop(minutes=5)
async def update_stats():
    try:
        await run_update()
    except Exception as e:
        print(f"통계 자동 갱신 에러: {e}")

@bot.tree.command(name="통계갱신", description="모든 통계 채널 수치를 리밋 방지하며 안전하게 갱신합니다.")
async def refresh_stats(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 이 명령어를 사용할 서버 관리자 권한이 없습니다!", ephemeral=True)
        return

    await interaction.response.send_message("🔄 API 리밋을 방지하며 안전하게 순차 갱신 중입니다. 잠시만 기다려주세요...", ephemeral=True)
    
    try:
        await run_update()
        await interaction.edit_original_response(content="✅ 통계 채널들이 안전하게 갱신되었습니다! (변경 사항이 없다면 스킵되었습니다)")
    except Exception as e:
        await interaction.edit_original_response(content=f"❌ 갱신 중 오류가 발생했습니다: {e}")

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)