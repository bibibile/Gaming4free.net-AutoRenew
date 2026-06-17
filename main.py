import os
import time
import subprocess
import requests
from DrissionPage import ChromiumPage, ChromiumOptions

# ==========================================
# 💡 G4F-US 续期配置 (适配 90 分钟/次)
# ==========================================
URL = "https://g4f.gg/nidaye"
TARGET_HOURS = 48          # 🎯 铁血目标：不达到 48 小时绝不退出
COOLDOWN_MINUTES = 31      # 官方强制冷却时间 (预留 1 分钟容错)
MAX_LOOPS = 50            # 超高循环上限，防止因为网络波动导致的半途而废

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_tg_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("TG 环境变量未配置，跳过发送消息。")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"TG 消息发送失败: {e}")

def get_current_ip():
    try:
        return requests.get('https://api.ipify.org', timeout=5).text
    except:
        return "获取失败"

def rotate_warp_ip(old_ip):
    print("🔄 开始轮换 WARP IP...")
    max_retries = 3
    for i in range(max_retries):
        subprocess.run(['warp-cli', '--accept-tos', 'disconnect'], stdout=subprocess.DEVNULL)
        time.sleep(2)
        subprocess.run(['warp-cli', '--accept-tos', 'connect'], stdout=subprocess.DEVNULL)
        
        time.sleep(8) 
        new_ip = get_current_ip()
        
        if new_ip == "获取失败" or new_ip == old_ip:
            continue
            
        print(f"✅ WARP IP 轮换成功: {new_ip}")
        return new_ip
        
    return get_current_ip()

def get_current_hours(time_text):
    """提取倒计时文本中的小时数"""
    if not time_text:
        return -1
    try:
        parts = time_text.split(':')
        if len(parts) >= 1:
            return int(parts[0])
    except:
        pass
    return -1

def solve_turnstile(page):
    print("🛡️ 尝试处理 CF Turnstile 人机验证...")
    try:
        target_iframe = page.get_frame('css:iframe[src^="https://challenges.cloudflare.com"]', timeout=5)
        if not target_iframe: 
            print("未检测到 Turnstile 验证框，跳过。")
            return False
        time.sleep(2)
        try:
            sr = target_iframe.ele('tag:body').shadow_root
            if sr:
                target_ele = sr.ele('css:input[type="checkbox"]') or sr.ele('css:div.main-wrapper')
                if target_ele:
                    target_ele.click.at(offset_x=10, offset_y=10)
        except: 
            try: 
                target_iframe.frame_ele.click.at(offset_x=30, offset_y=30)
            except: pass
        
        for _ in range(15):
            time.sleep(1)
            resp = page.ele('css:[name="cf-turnstile-response"]', timeout=1)
            if resp and len(resp.value) > 10: 
                print("✅ Turnstile 验证通过！")
                return True
        return False
    except: 
        return False

def main():
    co = ChromiumOptions().auto_port()
    co.set_browser_path('/usr/bin/google-chrome') # 适配 GitHub Actions 环境
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-gpu')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--disable-crash-reporter') 
    
    page = ChromiumPage(co)
    page.set.timeouts(page_load=15)
    
    loop_count = 0
    success_count = 0
    current_ip = get_current_ip()
    print(f"🚀 初始运行 IP: {current_ip}")
    
    # 👑 新增：记录脚本刚启动时的时间戳
    script_start_time = time.time() 
    
    while loop_count < MAX_LOOPS:
        # 👑 新增：每次循环前检查是否超过 5.5 小时 (19800 秒)
        if time.time() - script_start_time > 5.5 * 3600:
            print("⏰ 接近 GitHub Actions 的 6 小时强制死亡线，为保证发送最终战报，主动体面退出！")
            break

        loop_count += 1
        print(f"\n" + "="*40)
        print(f"▶️ 第 {loop_count}/{MAX_LOOPS} 次尝试开始")
        print(f"="*40)
        
        try:
            page.get(URL)
        except Exception:
            pass 
            
        countdown_ele = page.ele('#countdown', timeout=10)
        
        if not countdown_ele:
            print("❌ 页面核心元素未加载，可能是 IP 被限制，尝试更换 IP...")
            current_ip = rotate_warp_ip(current_ip)
            continue
            
        current_time_text = countdown_ele.text
        current_hours = get_current_hours(current_time_text)
        print(f"⏱️ 节点当前剩余时长: 【 {current_time_text} 】")
        
        # 👑 核心逻辑 1：达标立刻退出
        if current_hours >= TARGET_HOURS:
            print(f"🎉 阶段目标达成！当前已 ≥ {TARGET_HOURS} 小时，脚本打卡下班！")
            break
            
        btn = page.ele('.vote-btn')
        
        # 👑 核心逻辑 2：按钮处于冷却状态，强制休眠，不浪费算力疯狂重试
        if not btn or not btn.states.is_enabled:
            print(f"⏳ 按钮未亮起 (网站冷却规则限制)。")
            print(f"💤 强制挂机休眠 {COOLDOWN_MINUTES} 分钟，等待冷却结束...")
            time.sleep(COOLDOWN_MINUTES * 60)
            
            # 醒来后务必换个新 IP 再去请求，防止原 IP 依然被锁
            current_ip = rotate_warp_ip(current_ip)
            continue
            
        try:
            btn.click(by_js=True)
            print("🖱️ 已发送续期点击指令...")
            
            solve_turnstile(page)
            time.sleep(5) # 等待后端处理时长
            
            try:
                page.get(URL)
            except Exception:
                pass
                
            new_countdown_ele = page.ele('#countdown', timeout=10)
            if new_countdown_ele:
                new_time_text = new_countdown_ele.text
                new_hours = get_current_hours(new_time_text)
                
                if current_time_text != new_time_text:
                    print(f"🟢 续期成功！时间已增加至: 【 {new_time_text} 】 (增加了约 90 分钟)")
                    success_count += 1
                    
                    # 👑 核心逻辑 3：续期后再次判断，满了立刻走人
                    if new_hours >= TARGET_HOURS:
                        print(f"🎉 续期后直接达标！当前已 ≥ {TARGET_HOURS} 小时，圆满结束！")
                        break
                        
                    print(f"💤 距离 {TARGET_HOURS} 小时还差一点，进入 {COOLDOWN_MINUTES} 分钟强制冷却期，醒来后继续干...")
                    time.sleep(COOLDOWN_MINUTES * 60)
                    current_ip = rotate_warp_ip(current_ip) 
                else:
                    print("⚠️ 页面时间未变化，点击可能被拦截失效，更换 IP 立即重试...")
                    current_ip = rotate_warp_ip(current_ip)
            else:
                print("❌ 无法获取刷新后的时间数据，更换 IP 立即重试...")
                current_ip = rotate_warp_ip(current_ip)
                
        except Exception as e:
            print(f"💥 点击执行过程中发生异常: {e}")
            current_ip = rotate_warp_ip(current_ip)

    final_time = "获取失败"
    expiry_info = "获取失败"
    try:
        final_time = page.ele('#countdown').text
        expiry_info = page.ele('.countdown-sub').text
    except:
        pass
        
    page.quit()
    
    report_msg = (
        f"🎮 <b>G4F-US 续期战报</b>\n"
        f"--------------------------\n"
        f"🔄 本次循环消耗: {loop_count} 次\n"
        f"✅ 成功暴击增加: {success_count} 次\n"
        f"⏳ 最终存活时长: <code>{final_time}</code>\n"
        f"📅 预计到期拔管: {expiry_info}\n"
    )
    send_tg_message(report_msg)
    print("\n✅ 所有任务圆满结束。")

if __name__ == '__main__':
    main()
