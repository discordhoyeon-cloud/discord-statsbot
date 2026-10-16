import os
import discord
from discord.ext import tasks, commands
import json

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix="!", 
    intents=intents,
    chunk_guild_with_intent=True
)

CONFIG_FILE = "stats_config.json"

# ⚠️ 여기에 본인 디스코드 서버 ID 숫자를 정확히 넣어주세요!
MY_GUILD_ID_VALUE = 1558388838462652498
MY_GUILD_ID = discord.Object(id=1558388838462652498) 

config_data = {
    "managed_category_id": None,
    "stats_channels": {
        "total": [],
        "human": [],
        "voice": [],
        "bot": []
    }
}

if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            config_data.update(loaded)
    except Exception as e:
        print(f"설정 파일 로드 중 오류: {e}")

def save_config():
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"설정 파일 저장 중 오류: {e}")

async def run_update():
    """5분 주기 및 수동 실행 전용 안전한 갱신 함수"""
    guild = bot.get_guild(MY_GUILD_ID_VALUE)
    if not guild:
        return

    total_members = guild.member_count
    human_members = sum(1 for m in guild.members if not m.bot)
    bot_count = sum(1 for m in guild.members if m.bot)
    
    voice_member_ids = set()
    for vc in guild.voice_channels:
        for member in vc.members:
            voice_member_ids.add(member.id)
            
    for m in guild.members:
        if m.voice and m.voice.channel is not None:
            voice_member_ids.add(m.id)
            
    voice_members = len(voice_member_ids)

    for kind, cids in config_data["stats_channels"].items():
        for cid in cids:
            chan = guild.get_channel(cid)
            if chan:
                try:
                    if kind == "total":
                        default_prefix = "👥 전체 인원"
                        current_value = total_members
                    elif kind == "human":
                        default_prefix = "👤 서버인원"
                        current_value = human_members
                    elif kind == "voice":
                        default_prefix = "🔊 음성인원"
                        current_value = voice_members
                    elif kind == "bot":
                        default_prefix = "🤖 봇 개수"
                        current_value = bot_count
                    else:
                        continue

                    if ":" in chan.name:
                        prefix = chan.name.rsplit(":", 1)[0].strip()
                        new_name = f"{prefix} : {current_value}"
                    else:
                        new_name = f"{default_prefix} : {current_value}"

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

@tasks.loop(minutes=5)
async def update_stats():
    try:
        await run_update()
    except Exception as e:
        print(f"통계 자동 갱신 에러: {e}")

@bot.tree.command(name="카테고리생성", description="통계 채널들이 들어갈 카테고리를 생성합니다.")
async def create_category(interaction: discord.Interaction, 카테고리이름: str):
    # 🔒 관리자 권한(Administrator) 체크로 변경
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 이 명령어를 사용할 서버 관리자 권한이 없습니다!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    try:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True)
        }
        new_category = await guild.create_category(카테고리이름, overwrites=overwrites)
        
        config_data["managed_category_id"] = new_category.id
        save_config()
        
        await interaction.followup.send(f"✅ 통계 카테고리 **'{카테고리이름}'**이(가) 성공적으로 생성되었습니다!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ 카테고리 생성 중 오류 발생: {e}", ephemeral=True)

@bot.tree.command(name="생성", description="선택한 통계 음성 채널을 생성합니다.")
@discord.app_commands.choices(kind=[
    discord.app_commands.Choice(name="서버 총인원 (멤버+봇)", value="total"),
    discord.app_commands.Choice(name="순인원 (사람만)", value="human"),
    discord.app_commands.Choice(name="보이스 접속자수", value="voice"),
    discord.app_commands.Choice(name="봇 개수", value="bot")
])
async def create_stat_channel(interaction: discord.Interaction, kind: str):
    # 🔒 관리자 권한(Administrator) 체크로 변경
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 이 명령어를 사용할 서버 관리자 권한이 없습니다!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    category = None
    if config_data["managed_category_id"]:
        category = discord.utils.get(guild.categories, id=config_data["managed_category_id"])
    
    if not category:
        category = discord.utils.get(guild.categories, name="📊 서버 통계")
        if not category:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True)
            }
            category = await guild.create_category("📊 서버 통계", overwrites=overwrites)
        config_data["managed_category_id"] = category.id
        save_config()

    names = {
        "total": "👥 전체 인원",
        "human": "👤 서버인원",
        "voice": "🔊 음성인원",
        "bot": "🤖 봇 개수"
    }

    try:
        initial_name = f"{names[kind]} : 0"
        new_channel = await guild.create_voice_channel(initial_name, category=category)
        config_data["stats_channels"][kind].append(new_channel.id)
        save_config()
        
        await interaction.followup.send(f"✅ 통계 채널이 성공적으로 생성되었습니다! (종류: `{kind}`)", ephemeral=True)
        await run_update()
    except Exception as e:
        await interaction.followup.send(f"❌ 채널 생성 중 오류 발생: {e}", ephemeral=True)

@bot.tree.command(name="통계갱신", description="모든 통계 채널 수치를 즉시 갱신합니다.")
async def refresh_stats(interaction: discord.Interaction):
    # 🔒 관리자 권한(Administrator) 체크 추가
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 이 명령어를 사용할 서버 관리자 권한이 없습니다!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    try:
        await run_update()
        await interaction.followup.send("✅ 모든 통계 채널이 즉시 갱신되었습니다!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ 갱신 중 오류가 발생했습니다: {e}", ephemeral=True)

@bot.tree.command(name="통계초기화", description="등록된 채널뿐만 아니라 통계 관련 채널/카테고리를 강제로 싹 다 삭제합니다.")
async def reset_stats(interaction: discord.Interaction):
    # 🔒 관리자 권한(Administrator) 체크로 변경
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 이 명령어를 사용할 서버 관리자 권한이 없습니다!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    try:
        deleted_count = 0

        for kind, cids in config_data["stats_channels"].items():
            for cid in cids:
                chan = guild.get_channel(cid)
                if chan:
                    await chan.delete()
                    deleted_count += 1

        if config_data["managed_category_id"]:
            cat = guild.get_channel(config_data["managed_category_id"])
            if cat:
                for chan in cat.channels:
                    await chan.delete()
                    deleted_count += 1
                await cat.delete()

        for cat in guild.categories:
            if "통계" in cat.name or "서버정보" in cat.name:
                for chan in cat.channels:
                    await chan.delete()
                    deleted_count += 1
                await cat.delete()

        config_data["managed_category_id"] = None
        for kind in config_data["stats_channels"]:
            config_data["stats_channels"][kind] = []
        save_config()

        await interaction.followup.send(f"✅ 초기화 완료! (총 {deleted_count}개의 채널/카테고리 삭제됨)", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ 초기화 중 오류 발생: {e}", ephemeral=True)

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)