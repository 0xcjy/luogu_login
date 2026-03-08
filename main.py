import time
import requests
import re
import random

# 初始化Session，自动维护Cookie（包括C3VK）
session = requests.Session()
# 基础请求头，模拟Chrome浏览器
BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive"
}
session.headers.update(BASE_HEADERS)

def extract_c3vk_from_js(js_content):
    """从返回的JS代码中提取C3VK值"""
    # 匹配 JS 中的 C3VK=xxx; 部分
    c3vk_pattern = r'C3VK=([^;]+)'
    match = re.search(c3vk_pattern, js_content)
    if match:
        return match.group(1)
    return None

def get_c3vk_and_csrf():
    """
    适配洛谷JS重定向逻辑：先解析JS获取C3VK→手动设置Cookie→再拿Csrf Token
    返回：csrf_token（成功）/None（失败）
    """
    # 第一步：首次访问，获取JS代码并提取C3VK
    print("🔍 第一步：解析JS获取C3VK...")
    for _ in range(5):
        try:
            # 禁用重定向（避免自动跳转后拿不到JS代码）
            response = session.get(
                "https://www.luogu.com.cn/",
                timeout=10,
                allow_redirects=False
            )
            if response.status_code == 200:
                # 提取JS中的C3VK
                c3vk = extract_c3vk_from_js(response.text)
                if c3vk:
                    # 手动将C3VK设置到Session的Cookie中（模拟浏览器执行JS）
                    session.cookies.set("C3VK", c3vk, path="/", max_age=300)
                    print(f"✅ 解析JS获取C3VK成功: {c3vk}")
                    break
            print(f"⚠️ 解析C3VK失败，响应内容: {response.text[:200]}... 重试中...")
            time.sleep(1)
        except Exception as e:
            print(f"❌ 解析C3VK出错: {e}，重试中...")
            time.sleep(1)
    else:
        print("❌ 多次重试仍未解析到C3VK，退出")
        return None

    # 第二步：携带手动设置的C3VK Cookie，再次请求拿Csrf Token
    print("\n🔍 第二步：携带C3VK获取Csrf Token...")
    for _ in range(5):
        try:
            # 此时Session已携带C3VK Cookie，请求会返回正常HTML
            response = session.get("https://www.luogu.com.cn/", timeout=10)
            if response.status_code == 200:
                # 提取Csrf Token
                csrf_pattern = r'<meta\s+name=["\']csrf-token["\']\s+content=["\']([^"\']+)["\']'
                match = re.search(csrf_pattern, response.text)
                if match:
                    csrf_token = match.group(1)
                    session.headers["X-Csrf-Token"] = csrf_token  # 保存到Session头
                    print(f"✅ 成功获取Csrf Token: {csrf_token[:10]}...")
                    return csrf_token
            print(f"⚠️ 获取Csrf Token失败，状态码: {response.status_code}，重试中...")
            time.sleep(1)
        except Exception as e:
            print(f"❌ 获取Csrf Token出错: {e}，重试中...")
            time.sleep(1)
    print("❌ 多次重试仍未获取Csrf Token，退出")
    return None

def get_captcha():
    """获取验证码图片（需携带C3VK和__client_id）"""
    print("\n🔍 第三步：获取验证码图片...")
    for _ in range(5):
        try:
            # 加随机时间戳避免缓存
            _t = time.time() * 1000 + random.random()
            response = session.get(
                f"https://www.luogu.com.cn/lg4/captcha?_t={_t}",
                timeout=10
            )
            if response.status_code == 200:
                with open("captcha.png", "wb") as f:
                    f.write(response.content)
                print("✅ 验证码图片已保存为 captcha.png")
                return True
            print(f"⚠️ 获取验证码失败，状态码: {response.status_code}，重试中...")
            time.sleep(1)
        except Exception as e:
            print(f"❌ 获取验证码出错: {e}，重试中...")
            time.sleep(1)
    print("❌ 多次重试仍未获取验证码，退出")
    return False

def login(username, password, captcha, csrf_token):
    """执行登录（核心流程，适配洛谷实际参数）"""
    print("\n🔍 第四步：提交登录请求...")
    # 登录请求头（仅保留必要字段，避免冗余）
    login_headers = {
        "Referer": "https://www.luogu.com.cn/auth/login",  # 首字母大写，洛谷验证
        "X-Csrf-Token": csrf_token,  # 必须携带与C3VK绑定的Token
        "X-Requested-With": "XMLHttpRequest",  # 模拟AJAX请求，洛谷要求
        "Content-Type": "application/json"  # 明确JSON格式
    }
    # 登录参数（仅保留洛谷实际需要的3个字段）
    payload = {
        "username": username,
        "password": password,
        "captcha": captcha
    }

    try:
        response = session.post(
            url="https://www.luogu.com.cn/do-auth/password",
            headers=login_headers,
            json=payload,
            timeout=10
        )
        # 打印关键调试信息
        print(f"📌 登录请求状态码: {response.status_code}")
        print(f"📌 登录响应内容: {response.text}")  # 洛谷会返回具体错误原因
        return response
    except Exception as e:
        print(f"❌ 登录请求出错: {e}")
        return None

def refresh_session_and_csrf():
    """刷新会话（适配JS重定向逻辑）并获取最新Csrf Token"""
    print("\n🔍 刷新会话，获取最新Csrf Token...")
    for _ in range(3):
        try:
            # 第一步：先请求首页，处理JS重定向逻辑，更新C3VK
            response = session.get(
                "https://www.luogu.com.cn/",
                timeout=10,
                allow_redirects=False
            )
            # 如果返回JS代码，提取并更新C3VK
            if "window.open" in response.text and "C3VK=" in response.text:
                c3vk = extract_c3vk_from_js(response.text)
                if c3vk:
                    session.cookies.set("C3VK", c3vk, path="/", max_age=300)
            
            # 第二步：携带最新C3VK请求首页，拿最新Token
            response = session.get("https://www.luogu.com.cn/", timeout=10)
            if response.status_code == 200:
                csrf_pattern = r'<meta\s+name=["\']csrf-token["\']\s+content=["\']([^"\']+)["\']'
                match = re.search(csrf_pattern, response.text)
                if match:
                    new_csrf_token = match.group(1)
                    session.headers["X-Csrf-Token"] = new_csrf_token
                    print(f"✅ 刷新会话成功，最新Csrf Token: {new_csrf_token[:10]}...")
                    return new_csrf_token
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ 刷新会话失败: {e}，重试中...")
            time.sleep(1)
    print("❌ 刷新会话失败，无法继续创建剪贴板")
    return None

def create_luogu_paste(data_content, is_public=True):
    """
    新建洛谷云剪贴板（修复会话过期问题）
    :param data_content: 剪贴板内容（比如"test"）
    :param is_public: 是否公开（True=公开，False=私有）
    :return: 剪贴板ID / None（失败）
    """
    print("\n🔍 第五步：新建云剪贴板...")
    
    # 关键修复：新建剪贴板前先刷新会话+获取最新Token
    new_csrf_token = refresh_session_and_csrf()
    if not new_csrf_token:
        return None
    
    # 新建剪贴板的接口地址
    paste_url = "https://www.luogu.com.cn/paste/new"
    
    # 请求头（使用最新的Csrf Token）
    paste_headers = {
        "Referer": "https://www.luogu.com.cn/paste",
        "X-Csrf-Token": new_csrf_token,  # 使用刷新后的最新Token
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/json"
    }
    
    # 请求体（严格按格式）
    paste_payload = {
        "public": is_public,
        "data": data_content
    }
    
    try:
        # 先访问剪贴板页面，进一步刷新会话（双重保险）
        session.get("https://www.luogu.com.cn/paste", timeout=10)
        
        # 发起POST请求（Session自动携带最新的__client_id/_uid/C3VK Cookie）
        response = session.post(
            url=paste_url,
            headers=paste_headers,
            json=paste_payload,
            timeout=10
        )
        
        # 解析响应
        if response.status_code == 200:
            response_json = response.json()
            print(f"📌 新建剪贴板响应: {response_json}")
            
            # 提取剪贴板ID并返回
            if "id" in response_json:
                paste_id = response_json["id"]
                paste_full_url = f"https://www.luogu.com.cn/paste/{paste_id}"
                print(f"✅ 新建云剪贴板成功！")
                print(f"📎 剪贴板地址: {paste_full_url}")
                return paste_id
            else:
                print(f"❌ 新建剪贴板失败：响应无ID字段")
                return None
        else:
            print(f"❌ 新建剪贴板失败，状态码: {response.status_code}")
            # 解码Unicode响应，方便查看具体错误
            response_text = response.text.encode('utf-8').decode('unicode_escape')
            print(f"📌 响应内容: {response_text}")
            return None
    except Exception as e:
        print(f"❌ 新建剪贴板出错: {e}")
        return None

# 主流程（严格按洛谷实际顺序执行）
if __name__ == "__main__":
    # 1. 先获取C3VK，再获取Csrf Token（核心顺序）
    csrf_token = get_c3vk_and_csrf()
    if not csrf_token:
        exit(1)
    
    # 2. 获取验证码图片（需C3VK）
    if not get_captcha():
        exit(1)
    
    # 3. 输入账号密码验证码
    username = input("\n请输入洛谷账号: ")
    password = input("请输入洛谷密码: ")
    captcha = input("请输入验证码（查看 captcha.png）: ")
    
    # 4. 提交登录
    response = login(username, password, captcha, csrf_token)
    
    # 5. 验证登录结果
    if response:
        if response.status_code == 200:
            print("\n🎉 登录成功！")
        elif response.status_code == 400:
            print("\n❌ 登录失败（400）：请检查以下点")
            print("  - 验证码是否输入正确（区分大小写）")
            print("  - 账号/密码是否正确")
            print("  - Csrf Token是否与C3VK绑定（代码已自动处理）")
        else:
            print(f"\n❌ 登录失败，状态码: {response.status_code}")
    
    paste_content = input("\n请输入云剪贴板内容（默认test）: ").strip() or "test"
    create_luogu_paste(data_content=paste_content, is_public=True)
