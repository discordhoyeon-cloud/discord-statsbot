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

MY_GUILD_ID_VALUE = 1558388838462652498
MY_GUILD_ID = discord.Object(id=1558388838462652498) 

async def run_update():
    guild = bot.get_guild(MY_GUILD_ID_VALUE)
    if not guild:
        return

    total_members = guild.member_count
    human_members = sum(1 for m in guild.members if not m.bot)
    
    # 봇 포함 음성 인원 계산
    voice_member_ids = set()
    for vc in guild.voice_channels:
        for member in vc.members:
            voice_member_ids.add(member.id)
    for m in guild.members:
        if m.voice and m.voice.channel is not None:
            voice_member_ids.add(m.id)
    voice_members = len(voice_member_ids)

    # 서버 내 모든 음성 채널을 뒤져서 이름에 키워드가 포함된 것들을 찾아 갱신
    for chan in guild.voice_channels:
        name = chan.name
        new_name = None

        if "전체 인원" in name:
            prefix = name.split(":")[0].strip() if ":" in name else "👥 전체 인원"
            new_name = f"{prefix} : {total_members}"
        elif "서버인원" in name or "사람 인원" in name:
            prefix = name.split(":")[0].strip() if ":" in name else "👤 서버인원"
            new_name = f"{prefix} : {human_members}"
        elif "음성인원" in name or "음성 인원" in name:
            prefix = name.split(":")[0].strip() if ":" in name else "🔊 음성인원"
            new_name = f"{prefix} : {voice_members}"

        if new_name and chan.name != new_name:
            try:
                await chan.edit(name=new_name)
                print(f"✨ 채널 이름 갱신됨: '{chan.name}' -> '{new_name}'")
            except Exception as e:
                print(f"❌ 채널 갱신 에러 [{chan.name}]: {e}")

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

@tasks.loop(minutes=5)
async def update_stats():
    try:
        await run_update()
    except Exception as e:
        print(f"통계 자동 갱신 에러: {e}")

@bot.tree.command(name="통계갱신", description="모든 통계 채널 수치를 즉시 갱신합니다.")
async def refresh_stats(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 이 명령어를 사용할 서버 관리자 권한이 없습니다!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    try:
        await run_update()
        await interaction.followup.send("✅ 통계 채널들이 즉시 갱신되었습니다!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ 갱신 중 오류가 발생했습니다: {e}", ephemeral=True)

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)